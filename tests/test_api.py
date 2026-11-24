import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core import config

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert isinstance(data["faiss_vectors_count"], int)
    assert data["engine_ready"] is True

def test_image_not_found():
    response = client.get("/api/images/non_existent_file.png")
    assert response.status_code == 404

def test_vlm_status_endpoint():
    response = client.get("/api/vlm/status")
    assert response.status_code == 200
    data = response.json()
    assert "7B" in data["vlm_model"]
    assert "quantization" in data
    assert data["failsafe_confidence_threshold"] == 0.65
    # Whether the local model can actually run depends on CUDA + adapter files;
    # the status must report that honestly instead of always claiming True.
    assert isinstance(data["providers_available"]["local_vlm"], bool)

def test_ev_cycle_telemetry_stream():
    response = client.get("/api/ev/telemetry/stream?cycle_key=fleet_thermal_runaway")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["cycle_key"] == "fleet_thermal_runaway"
    assert len(data["series"][0]) > 100


def test_api_key_enforced_when_configured(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "test-key-123")
    denied = client.post("/api/analyze_anomaly", json={})
    assert denied.status_code == 403

    allowed = client.post(
        "/api/analyze_anomaly",
        json={"start_offset_seconds": 75.0, "end_offset_seconds": 60.0},
        headers={"X-API-Key": "test-key-123"},
    )
    assert allowed.status_code == 422  # key accepted, body rejected by validation


def test_invalid_window_rejected():
    response = client.post(
        "/api/analyze_anomaly",
        json={"start_offset_seconds": 75.0, "end_offset_seconds": 60.0},
    )
    assert response.status_code == 422


