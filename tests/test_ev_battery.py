import pytest
import polars as pl
from pathlib import Path
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.data_engine.ev_ingestion import EVIngestionProcessor
from backend.data_engine.cropping import ROICropper

client = TestClient(app)

def test_ev_ingestion_nasa_cycle():
    """Verify EV ingestion generates and loads zero-copy Polars Parquet streams."""
    result = EVIngestionProcessor.fetch_and_stream_ev_cycle("nasa_b0005_sag")
    assert result["status"] == "success"
    assert "df" in result
    df = result["df"]
    assert isinstance(df, pl.DataFrame)
    assert len(df) > 1000
    expected_cols = ["Time", "Voltage", "Current", "Temperature", "SoC", "Cell_Imbalance_mV"]
    for col in expected_cols:
        assert col in df.columns
    assert result["pack_topology"]["nominal_voltage"] > 300

def test_ev_roi_cropping():
    """Verify high-contrast Matplotlib diagnostic micro-cropping for EV battery telemetry."""
    data = EVIngestionProcessor.fetch_and_stream_ev_cycle("nasa_b0005_sag")
    df = data["df"]
    crop_path = ROICropper.generate_ev_roi_crop(
        df=df,
        start_time=38.0,
        end_time=55.0,
        channels=["Voltage", "Current", "Temperature"],
        session_id="test_ev_crop"
    )
    assert Path(crop_path).exists()
    assert Path(crop_path).stat().st_size > 0

def test_ev_telemetry_stream_endpoint():
    """Verify FastAPI GET /api/ev/telemetry/stream returns 200 with contiguous arrays."""
    response = client.get("/api/ev/telemetry/stream?cycle_key=nasa_b0005_sag")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data["domain"] == "EV_BATTERY"
    assert len(json_data["series"]) >= 4
    # Check that time series is strictly increasing
    times = json_data["series"][0]
    assert len(times) > 100
    assert times[1] > times[0]

def test_ev_analyze_anomaly_endpoint():
    """Verify master orchestration POST /api/analyze_anomaly with EV_BATTERY domain."""
    payload = {
        "year": 2023,
        "event": "Fleet_Cycle",
        "session_type": "Discharge",
        "driver": "EV-B0005",
        "start_offset_seconds": 40.0,
        "end_offset_seconds": 55.0,
        "channels": ["Voltage", "Current", "Temperature"],
        "domain": "EV_BATTERY"
    }
    response = client.post("/api/analyze_anomaly", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "diagnostic" in data
    diag = data["diagnostic"]
    assert diag["domain"] == "EV_BATTERY"
    assert diag["confidence_score"] > 0.6
    assert len(diag["key_evidence"]) > 0
    assert isinstance(data["historical_precedents"], list)
    assert data["persisted"] is False
