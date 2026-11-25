import datetime
import hmac
import logging
import os
import threading
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import List, Literal, Optional

import numpy as np
import pandas as pd
import polars as pl
from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field, model_validator

from backend.ai.diagnostics_service import DiagnosticsService
from backend.core import config
from backend.data_engine.circuit_geometries import generate_track_geometry
from backend.data_engine.cropping import ROICropper
from backend.data_engine.ev_ingestion import EVIngestionProcessor
from backend.data_engine.f1_calendar import (
    generate_f1_session_telemetry,
    get_season_calendar,
    get_season_drivers,
    get_seasons,
)
from backend.data_engine.ingestion import FastF1Processor, has_cached_session
from backend.vector_store.db import VectorDB, artifact_hash
from backend.vector_store.engine import VectorEngine

logger = logging.getLogger(__name__)

# ─── Lazy engine initialization ───────────────────────────────────────────────
_ENGINES: Optional[SimpleNamespace] = None
_ENGINES_LOCK = threading.Lock()


def get_engines() -> SimpleNamespace:
    """Initializes the heavy engines exactly once, on first use."""
    global _ENGINES
    if _ENGINES is not None:
        return _ENGINES
    with _ENGINES_LOCK:
        if _ENGINES is None:
            logger.info("Initializing Overcut.ai core engines...")
            _ENGINES = SimpleNamespace(
                vector_engine=VectorEngine(device="cpu"),
                vector_db=VectorDB(),
                diagnostics_service=DiagnosticsService(),
            )
            logger.info("Core engines initialized.")
    return _ENGINES


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        get_engines()
    except Exception:
        logger.exception("Engine initialization failed; API will report degraded health.")
    yield
    if _ENGINES is not None:
        try:
            _ENGINES.vector_db.flush()
        except Exception:
            logger.exception("Failed to flush FAISS index on shutdown.")


app = FastAPI(
    title="Overcut.ai API",
    description="Generative Multimodal Observability Gateway for High-Frequency Telemetry",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API key authentication ───────────────────────────────────────────────────
_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key_header: Optional[str] = Security(_API_KEY_HEADER)):
    """Validates X-API-Key when OVERCUT_API_KEY is configured."""
    if config.API_KEY and not hmac.compare_digest(api_key_header or "", config.API_KEY):
        raise HTTPException(status_code=403, detail="Invalid or missing API key.")


# ─── Auth router ──────────────────────────────────────────────────────────────
try:
    from backend.api.auth import router as auth_router

    app.include_router(auth_router)
    logger.info("Auth router mounted at /api/auth")
except Exception as exc:  # pragma: no cover - optional dependency path
    logger.warning("Auth router not mounted: %s", exc)

# ─── Concurrency guard ────────────────────────────────────────────────────────
# Each analysis runs a matplotlib render, CLIP embedding and possibly a 7B
# generation or cloud call. Cap concurrency so parallel requests cannot exhaust
# RAM/VRAM.
_ANALYSIS_SLOTS = threading.BoundedSemaphore(config.MAX_CONCURRENT_ANALYSES)


@contextmanager
def _analysis_slot():
    if not _ANALYSIS_SLOTS.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="The diagnostic engine is busy. Retry in a few seconds.",
        )
    try:
        yield
    finally:
        _ANALYSIS_SLOTS.release()


class AnomalyAnalysisRequest(BaseModel):
    year: int = Field(default=2025, ge=2025, le=2026, description="Formula 1 Championship Year")
    event: str = Field(default="Monaco", min_length=1, max_length=80, description="Grand Prix Event Name")
    session_type: str = Field(default="Q", min_length=1, max_length=16, description="Session Type (FP1, Q, R)")
    driver: str = Field(default="1", min_length=1, max_length=16, description="Driver Number or Code")
    start_offset_seconds: float = Field(default=60.0, ge=0.0, description="Start offset from session start in seconds")
    end_offset_seconds: float = Field(default=75.0, ge=0.0, description="End offset from session start in seconds")
    channels: List[str] = Field(
        default_factory=lambda: ["Speed", "Throttle", "Brake"],
        max_length=8,
        description="Telemetry channels to slice",
    )
    domain: Literal["MOTORSPORT_F1", "EV_BATTERY"] = Field(default="MOTORSPORT_F1")
    use_vlm: bool = Field(default=False, description="Invoke the local fine-tuned LLM")
    use_cloud_vlm: bool = Field(default=False, description="Invoke the cloud Gemini model")
    cycle_key: Optional[str] = Field(default="nasa_b0005_sag", description="EV Battery cycle key")
    enforce_failsafe: bool = Field(default=False, description="Reject diagnoses below the 0.65 similarity gate")
    persist_artifact: bool = Field(
        default=False,
        description="Persist this artifact as a historical precedent. Off by default so "
                    "ad-hoc analyses cannot pollute the retrieval index.",
    )

    @model_validator(mode="after")
    def _validate_window(self):
        if self.end_offset_seconds <= self.start_offset_seconds:
            raise ValueError("end_offset_seconds must be greater than start_offset_seconds")
        return self


@app.get("/api/health")
def health_check():
    try:
        engines = get_engines()
        return {
            "status": "healthy",
            "faiss_vectors_count": engines.vector_db.count,
            "engine_ready": True,
        }
    except Exception as exc:
        logger.exception("Health check failed: %s", exc)
        return {
            "status": "degraded",
            "faiss_vectors_count": 0,
            "engine_ready": False,
        }


@app.get("/api/vlm/status")
def get_vlm_status():
    try:
        engines = get_engines()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Diagnostics service not initialized") from exc
    return engines.diagnostics_service.get_vlm_status()


def _require_supported_season(year: int) -> None:
    seasons = get_seasons()
    if year not in seasons:
        raise HTTPException(
            status_code=400,
            detail=f"Season {year} is not available. Supported seasons: {seasons}.",
        )


@app.get("/api/f1/seasons")
def get_f1_seasons():
    return {"status": "success", "seasons": get_seasons()}


@app.get("/api/f1/calendar")
def get_f1_calendar(year: int = 2025):
    _require_supported_season(year)
    return {"status": "success", "year": year, "events": get_season_calendar(year)}


@app.get("/api/f1/drivers")
def get_f1_drivers(year: int = 2025, event: str = "monaco", session_type: str = "Q"):
    _require_supported_season(year)
    return {"status": "success", "year": year, "event": event, "drivers": get_season_drivers(year)}


@app.get("/api/telemetry/stream")
def get_telemetry_stream(
    year: int = 2025,
    event: str = "monaco",
    session_type: str = "Q",
    driver: str = "1",
    lap: Optional[int] = None,
):
    """Serves normalized multi-channel telemetry for F1 sessions and laps."""
    _require_supported_season(year)

    # Real fastf1 data is only used when that session is already cached locally:
    # the livetiming endpoints answer 401/404, so a network attempt would stall
    # the request and end up in the synthetic generator anyway.
    if not has_cached_session(year, event, session_type):
        return generate_f1_session_telemetry(
            year=year,
            event_id=event,
            session_type=session_type,
            driver_number=driver,
            lap_number=lap,
        )

    try:
        processor = FastF1Processor()
        session_data = processor.fetch_and_stream_session(year, event, session_type)
        session = session_data["session"]

        driver_laps = session.laps.pick_drivers(driver)
        if driver_laps.empty:
            return generate_f1_session_telemetry(year, event, session_type, driver, lap_number=lap)

        fastest_lap = driver_laps.pick_fastest()
        fastest_lap_num = int(fastest_lap.LapNumber) if hasattr(fastest_lap, "LapNumber") else 1

        laps_summary = []
        for _, row in driver_laps.iterrows():
            lap_number = int(row["LapNumber"])
            lap_time = round(float(row["LapTime"].total_seconds()), 3) if pd.notna(row["LapTime"]) else None
            sector = lambda name: (
                round(float(row[name].total_seconds()), 3)
                if pd.notna(row.get(name))
                else None
            )
            laps_summary.append({
                "lap_number": lap_number,
                "lap_time": lap_time,
                "compound": str(row["Compound"]).upper() if pd.notna(row.get("Compound")) else "SOFT",
                "pit": bool(pd.notna(row.get("PitInTime")) or pd.notna(row.get("PitOutTime"))),
                "is_fastest": bool(lap_number == fastest_lap_num),
                "stint": int(row["Stint"]) if pd.notna(row.get("Stint")) else 1,
                "s1": sector("Sector1Time"),
                "s2": sector("Sector2Time"),
                "s3": sector("Sector3Time"),
            })

        if lap is not None and int(lap) > 0:
            matched = driver_laps[driver_laps["LapNumber"] == int(lap)]
            lap_obj = matched.iloc[0] if not matched.empty else fastest_lap
        else:
            lap_obj = fastest_lap

        telemetry = lap_obj.get_telemetry()
        if telemetry.empty:
            telemetry = fastest_lap.get_telemetry()
        lap = lap_obj

        times = telemetry["Time"].dt.total_seconds().tolist()
        t0 = times[0]
        norm_times = [round(t - t0, 3) for t in times]
        speeds = [round(float(s), 1) for s in telemetry["Speed"].tolist()]
        throttles = [int(th) for th in telemetry["Throttle"].tolist()]
        brakes = [int(b * 100) if max(telemetry["Brake"]) <= 1 else int(b) for b in telemetry["Brake"].tolist()]
        gears = [int(g) for g in telemetry["nGear"].tolist()]
        rpms = [int(r) for r in telemetry["RPM"].tolist()]

        s1_time = round(float(lap.Sector1Time.total_seconds()), 3) if lap.Sector1Time is not None else round(norm_times[-1] * 0.31, 3)
        s2_time = round(float(lap.Sector2Time.total_seconds()), 3) if lap.Sector2Time is not None else round(norm_times[-1] * 0.38, 3)
        total_time = round(float(lap.LapTime.total_seconds()), 3) if lap.LapTime is not None else norm_times[-1]

        sectors = {
            "s1_end": s1_time,
            "s2_end": round(s1_time + s2_time, 3),
            "total_time": total_time,
        }

        corners = []
        try:
            circuit_info = session.get_circuit_info()
            distances = telemetry["Distance"].values
            times_np = np.array(norm_times)
            for _, row in circuit_info.corners.iterrows():
                corner_distance = row["Distance"]
                corner_index = int(np.argmin(np.abs(distances - corner_distance)))
                corner_time = round(float(times_np[corner_index]), 1)
                corner_number = int(row["Number"])
                corner_letter = str(row["Letter"]) if str(row["Letter"]) != "nan" else ""
                corners.append({
                    "name": f"Turn {corner_number}{corner_letter}",
                    "start": max(0.0, round(corner_time - 2.0, 1)),
                    "end": round(corner_time + 2.0, 1),
                    "type": "Circuit Turn",
                })
        except Exception:
            corners = [
                {"name": "Turn 1", "start": round(total_time * 0.15, 1), "end": round(total_time * 0.20, 1), "type": "Heavy Braking Zone"},
                {"name": "Turn 4", "start": round(total_time * 0.35, 1), "end": round(total_time * 0.40, 1), "type": "High Speed Crest"},
                {"name": "Turn 8", "start": round(total_time * 0.58, 1), "end": round(total_time * 0.63, 1), "type": "Traction Zone"},
                {"name": "Turn 12", "start": round(total_time * 0.80, 1), "end": round(total_time * 0.85, 1), "type": "Late Apex Braking"},
            ]

        track_map = None
        valid_coords = telemetry.dropna(subset=["X", "Y"])
        if not valid_coords.empty:
            xs = valid_coords["X"].values
            ys = valid_coords["Y"].values
            coord_times = [round(t.total_seconds() - t0, 3) for t in valid_coords["Time"]]
            pad, width, height = 25, 320, 380
            x_min, x_max = float(xs.min()), float(xs.max())
            y_min, y_max = float(ys.min()), float(ys.max())

            track_points = []
            svg_parts = []
            for index in range(len(xs)):
                sx = round(pad + ((float(xs[index]) - x_min) / (x_max - x_min)) * (width - 2 * pad), 1)
                sy = round(pad + (1.0 - (float(ys[index]) - y_min) / (y_max - y_min)) * (height - 2 * pad), 1)
                track_points.append({
                    "t": coord_times[index],
                    "x": sx,
                    "y": sy,
                    "spd": int(valid_coords["Speed"].iloc[index]),
                })
                svg_parts.append(f"{'M' if index == 0 else 'L'} {sx} {sy}")
            svg_parts.append("Z")

            corner_pins = []
            for corner in corners:
                mid_time = (corner["start"] + corner["end"]) / 2.0
                closest = int(np.argmin([abs(point["t"] - mid_time) for point in track_points]))
                clean_id = f"T{corner['name'].replace('Turn ', '').strip()}" if "Turn " in corner["name"] else corner["name"]
                corner_pins.append({
                    "id": clean_id,
                    "name": corner["name"],
                    "x": track_points[closest]["x"],
                    "y": track_points[closest]["y"],
                    "start": corner["start"],
                    "end": corner["end"],
                })

            track_map = {
                "viewBox": f"0 0 {width} {height}",
                "svg_path": " ".join(svg_parts),
                "points": track_points,
                "corner_pins": corner_pins,
                "circuit_name": f"Circuit de {event}" if "monaco" in event.lower() else f"{event.title()} Circuit",
                "location": event.title(),
                "lap_len": f"{round(float(lap.Distance.iloc[-1]) / 1000.0, 3)} km" if hasattr(lap, "Distance") and len(lap.Distance) > 0 else "3.337 km",
                "start_finish": {"x": track_points[0]["x"], "y": track_points[0]["y"]},
            }

        if track_map is None:
            track_map = generate_track_geometry(event, total_time)
            corners = track_map.get("corner_pins", corners)

        drivers_list = get_season_drivers(year)
        clean_driver = str(driver).strip().upper()
        driver_obj = next(
            (d for d in drivers_list if str(d["number"]) == clean_driver or d["code"].upper() == clean_driver),
            None,
        )
        driver_name = driver_obj["name"] if driver_obj else f"Driver #{driver}"

        lap_number = int(lap.LapNumber) if hasattr(lap, "LapNumber") else 1
        return {
            "status": "success",
            "session_id": f"{year}_{event}_{session_type}",
            "driver": driver,
            "driver_name": driver_name,
            "driver_code": driver_obj["code"] if driver_obj else f"#{driver}",
            "team_name": driver_obj["team"] if driver_obj else "F1 Team",
            "team_color": driver_obj["color"] if driver_obj else "#FFFFFF",
            "lap_number": lap_number,
            "total_laps": len(laps_summary) if laps_summary else 1,
            "lap_time_seconds": total_time,
            "compound": str(lap.Compound).upper() if hasattr(lap, "Compound") and pd.notna(lap.Compound) else "SOFT",
            "is_fastest_lap": bool(lap_number == fastest_lap_num),
            "sectors": sectors,
            "corners": corners,
            "track_map": track_map,
            "laps_summary": laps_summary,
            "channels": ["Time (s)", "Speed (km/h)", "Throttle (%)", "Brake (%)", "Gear", "RPM"],
            "series": [norm_times, speeds, throttles, brakes, gears, rpms],
        }
    except Exception as exc:
        logger.warning("FastF1 fetch failed for %s %s; using simulation: %s", year, event, exc)
        return generate_f1_session_telemetry(year, event, session_type, driver, lap_number=lap)


@app.get("/api/ev/telemetry/stream")
def get_ev_telemetry_stream(cycle_key: str = "nasa_b0005_sag"):
    try:
        data = EVIngestionProcessor.fetch_and_stream_ev_cycle(cycle_key)
        df = data["df"]
        return {
            "status": "success",
            "domain": "EV_BATTERY",
            "cycle_key": cycle_key,
            "session_id": data["cycle_meta"]["name"],
            "driver": data["cycle_meta"]["unit"],
            "lap_number": 84,
            "lap_time_seconds": data["cycle_meta"]["duration"],
            "pack_topology": data["pack_topology"],
            "phase_anchors": data["phase_anchors"],
            "channels": ["Time (s)", "Voltage (V)", "Current (A)", "Temperature (°C)", "SoC (%)", "Cell Imbalance (mV)"],
            "series": [
                df["Time"].to_list(),
                df["Voltage"].to_list(),
                df["Current"].to_list(),
                df["Temperature"].to_list(),
                df["SoC"].to_list(),
                df["Cell_Imbalance_mV"].to_list(),
            ],
        }
    except Exception as exc:
        logger.error("Failed to stream EV telemetry: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="EV telemetry streaming failed.") from exc


def _build_ev_analysis(request: AnomalyAnalysisRequest):
    cycle_key = request.cycle_key or "nasa_b0005_sag"
    ev_data = EVIngestionProcessor.fetch_and_stream_ev_cycle(cycle_key)
    df = ev_data["df"]
    session_id = f"EV_{ev_data['cycle_key']}"

    channels = request.channels if any(
        channel.lower() in {"voltage", "current", "temperature"} for channel in request.channels
    ) else ["Voltage", "Current", "Temperature"]

    image_path = ROICropper.generate_ev_roi_crop(
        df=df,
        start_time=request.start_offset_seconds,
        end_time=request.end_offset_seconds,
        channels=channels,
        session_id=session_id,
    )

    slice_df = df.filter(
        (pl.col("Time") >= request.start_offset_seconds) & (pl.col("Time") <= request.end_offset_seconds)
    )
    if slice_df.is_empty():
        raise ValueError("Selected analysis window contains no EV telemetry samples.")

    telemetry_summary = {
        "driver": ev_data["cycle_meta"]["unit"],
        "min_voltage": float(slice_df["Voltage"].min()),
        "max_voltage": float(slice_df["Voltage"].max()),
        "peak_current": float(slice_df["Current"].max()),
        "max_temperature": float(slice_df["Temperature"].max()),
        "max_cell_imbalance_mv": float(slice_df["Cell_Imbalance_mV"].max()),
        "min_soc": float(slice_df["SoC"].min()),
        "duration_seconds": request.end_offset_seconds - request.start_offset_seconds,
    }
    meta_description = (
        f"{session_id} Unit {ev_data['cycle_meta']['unit']} anomaly trace across {', '.join(channels)}"
    )
    return image_path, telemetry_summary, meta_description


def _build_f1_analysis(request: AnomalyAnalysisRequest):
    session_id = f"{request.year}_{request.event}_{request.session_type}"

    if not has_cached_session(request.year, request.event, request.session_type):
        telem_data = generate_f1_session_telemetry(
            year=request.year,
            event_id=request.event,
            session_type=request.session_type,
            driver_number=request.driver,
        )
        times, speeds, throttles, brakes, gears, rpms = telem_data["series"]
        df_telem = pl.DataFrame({
            "Time": times,
            "Speed": speeds,
            "Throttle": throttles,
            "Brake": brakes,
            "Gear": gears,
            "RPM": rpms,
        })

        channels = request.channels if any(
            channel.lower() in {"speed", "throttle", "brake"} for channel in request.channels
        ) else ["Speed", "Throttle", "Brake"]

        image_path = ROICropper.generate_dataframe_roi_crop(
            df=df_telem,
            start_time=request.start_offset_seconds,
            end_time=request.end_offset_seconds,
            channels=channels,
            session_id=session_id,
        )

        slice_df = df_telem.filter(
            (pl.col("Time") >= request.start_offset_seconds) & (pl.col("Time") <= request.end_offset_seconds)
        )
        if slice_df.is_empty():
            raise ValueError("Selected analysis window contains no telemetry samples.")

        telemetry_summary = {
            "driver": telem_data.get("driver_name", f"Driver #{request.driver}"),
            "team": telem_data.get("team_name", "F1 Team"),
            "min_speed": float(slice_df["Speed"].min()),
            "max_speed": float(slice_df["Speed"].max()),
            "avg_throttle": float(slice_df["Throttle"].mean()),
            "peak_brake": float(slice_df["Brake"].max()),
            "max_brake": float(slice_df["Brake"].max()),
            "min_throttle": float(slice_df["Throttle"].min()),
            "duration_seconds": request.end_offset_seconds - request.start_offset_seconds,
            "circuit": f"Circuit {request.event} ({request.year})",
            "event": request.event,
            "year": request.year,
        }
        meta_description = (
            f"{session_id} Driver #{request.driver} ({telem_data.get('driver_name', 'F1')}) "
            f"anomaly slice {request.start_offset_seconds}s-{request.end_offset_seconds}s"
        )
        return image_path, telemetry_summary, meta_description

    try:
        processor = FastF1Processor()
        session_data = processor.fetch_and_stream_session(request.year, request.event, request.session_type)
        session = session_data["session"]

        driver_laps = session.laps.pick_drivers(request.driver)
        lap = driver_laps.pick_fastest() if not driver_laps.empty else None
        lap_start = (
            lap.LapStartTime
            if (lap is not None and hasattr(lap, "LapStartTime") and lap.LapStartTime is not None)
            else session.session_start_time
        )

        start_time = lap_start + datetime.timedelta(seconds=request.start_offset_seconds)
        end_time = lap_start + datetime.timedelta(seconds=request.end_offset_seconds)

        image_path = ROICropper.generate_roi_crop(
            session=session,
            driver=request.driver,
            start_time=start_time,
            end_time=end_time,
            channels=request.channels,
            session_id=session_id,
        )

        car_data = session.car_data[request.driver].slice_by_time(start_time, end_time)
        empty = car_data.empty
        telemetry_summary = {
            "driver": request.driver,
            "min_speed": float(car_data["Speed"].min()) if ("Speed" in car_data.columns and not empty) else 0.0,
            "max_speed": float(car_data["Speed"].max()) if ("Speed" in car_data.columns and not empty) else 0.0,
            "max_brake": int(car_data["Brake"].max()) if ("Brake" in car_data.columns and not empty) else 0,
            "min_throttle": int(car_data["Throttle"].min()) if ("Throttle" in car_data.columns and not empty) else 0,
            "duration_seconds": request.end_offset_seconds - request.start_offset_seconds,
            "circuit": f"Circuit {request.event} ({request.year})",
            "event": request.event,
            "year": request.year,
        }
        meta_description = (
            f"{session_id} Driver {request.driver} anomaly trace across {', '.join(request.channels)}"
        )
        return image_path, telemetry_summary, meta_description
    except Exception as exc:
        logger.warning("FastF1 analysis fallback for %s %s: %s", request.year, request.event, exc)

    telem_data = generate_f1_session_telemetry(
        request.year, request.event, request.session_type, request.driver
    )
    times, speeds, throttles, brakes, gears, rpms = telem_data["series"]
    df_telem = pl.DataFrame({
        "Time": times,
        "Speed": speeds,
        "Throttle": throttles,
        "Brake": brakes,
        "Gear": gears,
        "RPM": rpms,
    })
    image_path = ROICropper.generate_dataframe_roi_crop(
        df=df_telem,
        start_time=request.start_offset_seconds,
        end_time=request.end_offset_seconds,
        channels=request.channels,
        session_id=session_id,
    )
    slice_df = df_telem.filter(
        (pl.col("Time") >= request.start_offset_seconds) & (pl.col("Time") <= request.end_offset_seconds)
    )
    if slice_df.is_empty():
        raise ValueError("Selected analysis window contains no telemetry samples.")
    telemetry_summary = {
        "driver": request.driver,
        "min_speed": float(slice_df["Speed"].min()),
        "max_speed": float(slice_df["Speed"].max()),
        "max_brake": int(slice_df["Brake"].max()),
        "min_throttle": int(slice_df["Throttle"].min()),
        "duration_seconds": request.end_offset_seconds - request.start_offset_seconds,
        "circuit": f"Circuit {request.event} ({request.year})",
        "event": request.event,
        "year": request.year,
    }
    meta_description = f"{session_id} Driver {request.driver} anomaly trace"
    return image_path, telemetry_summary, meta_description


def _run_analysis(request: AnomalyAnalysisRequest) -> dict:
    engines = get_engines()

    if request.domain == "EV_BATTERY":
        image_path, telemetry_summary, meta_description = _build_ev_analysis(request)
    else:
        image_path, telemetry_summary, meta_description = _build_f1_analysis(request)

    filename = os.path.basename(image_path)
    content_hash = artifact_hash(str(image_path), meta_description)

    # Retrieve precedents BEFORE persisting the query artifact. Adding first
    # makes the query the top-1 neighbour of itself (score ~1.0), which both
    # fabricates "historical" matches and inflates confidence.
    embedding = engines.vector_engine.embed_artifact(str(image_path), meta_description)
    historical_matches = engines.vector_db.search(
        embedding, top_k=3, exclude_hashes={content_hash}
    )

    persisted = False
    if request.persist_artifact:
        engines.vector_db.add_embedding(
            embedding=embedding,
            session_id=f"{request.year}_{request.event}_{request.session_type}"
            if request.domain != "EV_BATTERY"
            else f"EV_{request.cycle_key}",
            driver=telemetry_summary.get("driver", "unknown"),
            image_path=str(image_path),
            metadata=meta_description,
            content_hash=content_hash,
        )
        engines.vector_db.flush()
        persisted = True

    diagnostic_report = engines.diagnostics_service.analyze_anomaly(
        image_path=str(image_path),
        telemetry_summary=telemetry_summary,
        historical_matches=historical_matches,
        domain=request.domain,
        use_vlm=request.use_vlm,
        use_cloud_vlm=request.use_cloud_vlm,
        enforce_failsafe=request.enforce_failsafe,
    )

    return {
        "status": "success",
        "image_url": f"/api/images/{filename}",
        "crop_filename": filename,
        "persisted": persisted,
        "telemetry_metrics": telemetry_summary,
        "historical_precedents": historical_matches,
        "diagnostic": diagnostic_report.model_dump(),
        "embedding_preview": embedding[0][:5].tolist(),
        "vector_shape": list(embedding.shape),
    }


@app.post("/api/analyze_anomaly", dependencies=[Security(verify_api_key)])
def analyze_anomaly(request: AnomalyAnalysisRequest):
    """Crop the selected window, retrieve precedents, then diagnose it."""
    with _analysis_slot():
        try:
            return _run_analysis(request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Anomaly analysis failed: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Anomaly analysis failed. Check server logs for details.",
            ) from exc


@app.post("/api/demo", dependencies=[Security(verify_api_key)])
def run_demo():
    """Runs the full pipeline on a deterministic Monaco qualifying slice."""
    demo_request = AnomalyAnalysisRequest(
        year=2025,
        event="Monaco",
        session_type="Q",
        driver="1",
        start_offset_seconds=60.0,
        end_offset_seconds=75.0,
        channels=["Speed", "Throttle", "Brake"],
    )
    with _analysis_slot():
        try:
            return _run_analysis(demo_request)
        except Exception as exc:
            logger.error("Demo analysis failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Demo analysis failed.") from exc


@app.get("/api/images/{filename}")
def get_image(filename: str):
    """Serves a generated ROI crop, refusing path traversal attempts."""
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=404, detail="Image not found")

    base_dir = config.ROI_DIR.resolve()
    file_path = (base_dir / safe_name).resolve()
    if file_path.parent != base_dir or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)
