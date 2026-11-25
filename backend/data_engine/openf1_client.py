"""Real 2025/2026 F1 telemetry via OpenF1.

F1's livetiming archive (what ``fastf1.Session.load()`` reads) has answered 401
since 2026-10-15, but the live-timing feed itself is still open and OpenF1
ingests it into its own database. Historical sessions therefore remain
queryable without authentication.

OpenF1 data is licensed CC BY-NC-SA 4.0: attribution is required, commercial
use is not permitted, and redistributed data must carry the same licence.
Responses are cached under ``data/raw_cache/openf1`` so demos still work when
the API is unreachable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from backend.core import config
from backend.data_engine import f1_calendar
from backend.data_engine.circuit_geometries import generate_track_geometry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openf1.org/v1"
USER_AGENT = "Overcut.ai/1.0 (academic telemetry project; OpenF1 data CC BY-NC-SA 4.0)"
ATTRIBUTION = "Telemetry data: OpenF1 (api.openf1.org) — CC BY-NC-SA 4.0"
OPENF1_ENABLED = config.OPENF1_ENABLED
TIMEOUT = config.OPENF1_TIMEOUT
CACHE_DIR = config.CACHE_DIR / "openf1"
CACHE_TTL_SECONDS = 6 * 3600

SESSION_NAMES = {
    "FP1": ("Practice 1",),
    "FP2": ("Practice 2",),
    "FP3": ("Practice 3",),
    "Q": ("Qualifying",),
    "SQ": ("Sprint Qualifying", "Sprint Shootout"),
    "SS": ("Sprint Shootout", "Sprint Qualifying"),
    "S": ("Sprint",),
    "R": ("Race",),
}

# OpenF1's circuit_short_name per dashboard event id (measured 2026-11-25).
CIRCUIT_NAMES = {
    "australia": "Melbourne",
    "china": "Shanghai",
    "japan": "Suzuka",
    "bahrain": "Sakhir",
    "saudi_arabia": "Jeddah",
    "miami": "Miami",
    "imola": "Imola",
    "monaco": "Monte Carlo",
    "spain": "Catalunya",
    "canada": "Montreal",
    "austria": "Spielberg",
    "silverstone": "Silverstone",
    "spa": "Spa-Francorchamps",
    "hungary": "Hungaroring",
    "netherlands": "Zandvoort",
    "monza": "Monza",
    "baku": "Baku",
    "singapore": "Singapore",
    "austin": "Austin",
    "mexico": "Mexico City",
    "brazil": "Interlagos",
    "las_vegas": "Las Vegas",
    "qatar": "Lusail",
    "abu_dhabi": "Yas Marina Circuit",
}


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _format_ts(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _cache_path(url: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def _http_json(url: str) -> Any:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_json(url: str, ttl: Optional[int] = None) -> Any:
    """GET with an on-disk cache. ``ttl=None`` keeps historical payloads forever."""
    path = _cache_path(url)
    now = time.time()
    if path.exists():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if ttl is None or now - float(cached["fetched_at"]) < ttl:
                return cached["payload"]
        except (OSError, ValueError, KeyError):
            pass

    try:
        payload = _http_json(url)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:  # OpenF1 answers 404 with an empty result set
            raise
        payload = []

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps({"fetched_at": now, "payload": payload}), encoding="utf-8"
    )
    os.replace(tmp, path)
    return payload


def _resolve_session(year: int, event: str, session_type: str) -> Optional[Dict[str, Any]]:
    names = SESSION_NAMES.get(session_type.strip().upper())
    if not names:
        return None
    meta = f1_calendar.get_event_meta(year, event)
    circuit = CIRCUIT_NAMES.get(meta["id"])
    if circuit is None:
        return None

    sessions = _fetch_json(f"{BASE_URL}/sessions?year={year}", ttl=CACHE_TTL_SECONDS)
    matches = [
        item
        for item in sessions
        if item.get("session_name") in names
        and item.get("circuit_short_name") == circuit
        and not item.get("is_cancelled")
    ]
    if not matches:
        return None
    # Duplicate circuit names exist (e.g. testing at Sakhir); the race weekend
    # is the later meeting.
    return max(matches, key=lambda item: item["date_start"])


def _resolve_driver(year: int, requested: str, drivers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    clean = str(requested).strip().upper()
    code = None
    try:
        roster = f1_calendar.get_season_drivers(year)
    except ValueError:
        roster = []
    for entry in roster:
        if clean in (entry["number"].upper(), entry["code"].upper()):
            code = entry["code"].upper()
            break

    # Car numbers move between seasons (2026 car #1 is not the 2025 champion),
    # so the roster mapping wins over a bare number.
    if code:
        for driver in drivers:
            if (driver.get("name_acronym") or "").upper() == code:
                return driver
    for driver in drivers:
        if str(driver.get("driver_number")) == clean:
            return driver
    return None


def _lap_stints(stints: List[Dict[str, Any]], lap_number: int) -> Optional[Dict[str, Any]]:
    for stint in stints:
        start = stint.get("lap_start")
        end = stint.get("lap_end")
        if start is not None and end is not None and start <= lap_number <= end:
            return stint
    return None


def _build_track_map(
    event_id: str,
    total_time: float,
    location_rows: List[Dict[str, Any]],
    t0: datetime,
    times: List[float],
    speeds: List[float],
) -> Dict[str, Any]:
    geometry = generate_track_geometry(event_id, total_time)
    if not location_rows:
        return geometry

    rows = sorted(location_rows, key=lambda row: row["date"])
    xs = np.array([row["x"] for row in rows], dtype=float)
    ys = np.array([row["y"] for row in rows], dtype=float)
    loc_times = np.array(
        [(_parse_ts(row["date"]) - t0).total_seconds() for row in rows], dtype=float
    )
    car_times = np.asarray(times, dtype=float)
    car_speeds = np.asarray(speeds, dtype=float)

    pad, width, height = 25, 320, 380
    x_min, x_max = float(xs.min()), float(xs.max())
    y_min, y_max = float(ys.min()), float(ys.max())
    x_span = (x_max - x_min) or 1.0
    y_span = (y_max - y_min) or 1.0

    points = []
    svg_parts = []
    for index, row in enumerate(rows):
        sx = round(pad + ((float(xs[index]) - x_min) / x_span) * (width - 2 * pad), 1)
        sy = round(pad + (1.0 - (float(ys[index]) - y_min) / y_span) * (height - 2 * pad), 1)
        speed_index = int(np.clip(np.searchsorted(car_times, loc_times[index]), 0, len(car_speeds) - 1))
        points.append({
            "t": round(float(loc_times[index]), 2),
            "x": sx,
            "y": sy,
            "spd": int(car_speeds[speed_index]),
        })
        svg_parts.append(f"{'M' if index == 0 else 'L'} {sx} {sy}")
    svg_parts.append("Z")

    corner_pins = []
    for corner in geometry.get("corner_pins", []):
        mid_time = (corner["start"] + corner["end"]) / 2.0
        closest = int(np.argmin(np.abs(loc_times - mid_time)))
        corner_pins.append({
            "id": corner["id"],
            "name": corner["name"],
            "x": points[closest]["x"],
            "y": points[closest]["y"],
            "start": corner["start"],
            "end": corner["end"],
        })

    return {
        "viewBox": f"0 0 {width} {height}",
        "svg_path": " ".join(svg_parts),
        "points": points,
        "corner_pins": corner_pins,
        "circuit_name": geometry.get("circuit_name", event_id),
        "location": geometry.get("location", ""),
        "lap_len": geometry.get("lap_len", ""),
        "start_finish": {"x": points[0]["x"], "y": points[0]["y"]},
    }


def _assemble_telemetry(
    *,
    year: int,
    event_id: str,
    session_type: str,
    meta: Dict[str, Any],
    session: Dict[str, Any],
    driver_row: Dict[str, Any],
    laps: List[Dict[str, Any]],
    car_rows: List[Dict[str, Any]],
    location_rows: List[Dict[str, Any]],
    stints: List[Dict[str, Any]],
    pits: List[Dict[str, Any]],
    lap_number: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    valid_laps = [lap for lap in laps if lap.get("lap_duration")]
    valid_car = [row for row in car_rows if row.get("date")]
    if not valid_laps or len(valid_car) < 20:
        return None

    fastest = min(valid_laps, key=lambda lap: lap["lap_duration"])
    active = fastest
    if lap_number is not None:
        active = next(
            (lap for lap in valid_laps if lap["lap_number"] == int(lap_number)), fastest
        )

    valid_car.sort(key=lambda row: row["date"])
    t0 = _parse_ts(valid_car[0]["date"])
    times = [round((_parse_ts(row["date"]) - t0).total_seconds(), 3) for row in valid_car]
    speeds = [round(float(row.get("speed") or 0.0), 1) for row in valid_car]
    throttles = [int(row.get("throttle") or 0) for row in valid_car]
    brakes = [int(row.get("brake") or 0) for row in valid_car]
    gears = [int(row.get("n_gear") or 0) for row in valid_car]
    rpms = [int(row.get("rpm") or 0) for row in valid_car]

    total_time = round(float(active["lap_duration"]), 3)
    s1 = active.get("duration_sector_1")
    s2 = active.get("duration_sector_2")
    s1 = round(float(s1), 3) if s1 is not None else round(total_time * 0.31, 3)
    s2 = round(float(s2), 3) if s2 is not None else round(total_time * 0.38, 3)

    fastest_number = int(fastest["lap_number"])
    pit_laps = {p.get("lap_number") for p in pits}
    laps_summary = []
    for lap in valid_laps:
        number = int(lap["lap_number"])
        stint = _lap_stints(stints, number)
        def sector_s(key: str) -> Optional[float]:
            value = lap.get(key)
            return round(float(value), 3) if value is not None else None
        laps_summary.append({
            "lap_number": number,
            "lap_time": round(float(lap["lap_duration"]), 3),
            "compound": str(stint.get("compound") or "UNKNOWN").upper() if stint else "UNKNOWN",
            "pit": number in pit_laps or bool(lap.get("is_pit_out_lap")),
            "is_fastest": number == fastest_number,
            "stint": int(stint["stint_number"]) if stint and stint.get("stint_number") else 1,
            "s1": sector_s("duration_sector_1"),
            "s2": sector_s("duration_sector_2"),
            "s3": sector_s("duration_sector_3"),
        })

    track_map = _build_track_map(
        event_id, total_time, location_rows, t0, times, speeds
    )

    team_colour = driver_row.get("team_colour") or ""
    if team_colour and not team_colour.startswith("#"):
        team_colour = f"#{team_colour}"
    driver_name = " ".join(
        part for part in (driver_row.get("first_name"), driver_row.get("last_name")) if part
    ) or driver_row.get("full_name") or f"Driver #{driver_row.get('driver_number')}"

    return {
        "status": "success",
        "simulated": False,
        "source": "OPENF1",
        "data_source": ATTRIBUTION,
        "session_id": f"{year}_{meta['id']}_{session_type}",
        "openf1_session_key": session.get("session_key"),
        "driver": str(driver_row.get("driver_number")),
        "driver_name": driver_name,
        "driver_code": driver_row.get("name_acronym") or str(driver_row.get("driver_number")),
        "team_name": driver_row.get("team_name") or "",
        "team_color": team_colour or "#FFFFFF",
        "lap_number": int(active["lap_number"]),
        "total_laps": len(valid_laps),
        "lap_time_seconds": total_time,
        "compound": laps_summary[valid_laps.index(active)]["compound"],
        "is_fastest_lap": int(active["lap_number"]) == fastest_number,
        "circuit_name": meta["circuit"],
        "event_name": meta["name"],
        "country": meta["country"],
        "lap_len": f"{meta.get('lap_len', 0)} km",
        "sectors": {
            "s1_end": s1,
            "s2_end": round(s1 + s2, 3),
            "total_time": total_time,
        },
        "corners": track_map.get("corner_pins", []),
        "track_map": track_map,
        "laps_summary": laps_summary,
        "channels": ["Time (s)", "Speed (km/h)", "Throttle (%)", "Brake (%)", "Gear", "RPM"],
        "series": [times, speeds, throttles, brakes, gears, rpms],
    }


def fetch_openf1_telemetry(
    year: int,
    event: str,
    session_type: str,
    driver: str,
    lap_number: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Returns a telemetry payload shaped like the synthetic generator's, or
    None when OpenF1 has no data (so callers fall back to the labelled
    simulation)."""
    if not OPENF1_ENABLED:
        return None

    try:
        meta = f1_calendar.get_event_meta(year, event)
        session = _resolve_session(year, event, session_type)
        if session is None:
            return None
        session_key = session["session_key"]

        drivers = _fetch_json(f"{BASE_URL}/drivers?session_key={session_key}")
        driver_row = _resolve_driver(year, driver, drivers)
        if driver_row is None:
            return None
        driver_number = int(driver_row["driver_number"])

        laps = _fetch_json(
            f"{BASE_URL}/laps?session_key={session_key}&driver_number={driver_number}"
        )
        valid_laps = [lap for lap in laps if lap.get("lap_duration")]
        if not valid_laps:
            return None
        fastest = min(valid_laps, key=lambda lap: lap["lap_duration"])
        active = fastest
        if lap_number is not None:
            active = next(
                (lap for lap in valid_laps if lap["lap_number"] == int(lap_number)), fastest
            )

        lap_start = _parse_ts(active["date_start"])
        lap_end = lap_start.timestamp() + float(active["lap_duration"]) + 0.5
        window = (
            f"{BASE_URL}/car_data?session_key={session_key}&driver_number={driver_number}"
            f"&date%3E%3D{_format_ts(lap_start)}"
            f"&date%3C{_format_ts(datetime.fromtimestamp(lap_end, tz=timezone.utc))}"
        )
        car_rows = _fetch_json(window)
        location_rows = _fetch_json(window.replace("/car_data?", "/location?"))
        stints = _fetch_json(
            f"{BASE_URL}/stints?session_key={session_key}&driver_number={driver_number}"
        )
        pits = _fetch_json(
            f"{BASE_URL}/pit?session_key={session_key}&driver_number={driver_number}"
        )

        return _assemble_telemetry(
            year=year,
            event_id=meta["id"],
            session_type=session_type.strip().upper(),
            meta=meta,
            session=session,
            driver_row=driver_row,
            laps=valid_laps,
            car_rows=car_rows,
            location_rows=location_rows,
            stints=stints,
            pits=pits,
            lap_number=lap_number,
        )
    except Exception as exc:
        logger.warning(
            "OpenF1 fetch failed for %s %s %s (%s); using simulation: %s",
            year, event, session_type, driver, exc,
        )
        return None
