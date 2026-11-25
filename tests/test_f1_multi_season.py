import pytest
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.data_engine.f1_calendar import (
    get_seasons,
    get_season_calendar,
    get_season_drivers,
    generate_f1_session_telemetry,
    generate_track_geometry
)

client = TestClient(app)

def test_seasons_availability():
    assert get_seasons() == [2026, 2025]

def test_unsupported_seasons_are_rejected():
    for year in (2024, 2023, 2018):
        with pytest.raises(ValueError):
            get_season_calendar(year)
        with pytest.raises(ValueError):
            get_season_drivers(year)

def test_2025_calendar_events():
    cal_2025 = get_season_calendar(2025)
    assert len(cal_2025) == 24
    event_ids = [e["id"] for e in cal_2025]
    assert "australia" in event_ids
    assert "monaco" in event_ids
    assert "silverstone" in event_ids
    assert "monza" in event_ids
    assert "spa" in event_ids

def test_2026_calendar_events():
    cal_2026 = get_season_calendar(2026)
    assert len(cal_2026) == 23

def test_2025_driver_lineup_and_transfers():
    drivers = get_season_drivers(2025)
    assert len(drivers) == 20

    # Verify Hamilton transfer to Ferrari
    ham = next(d for d in drivers if d["code"] == "HAM")
    assert ham["number"] == "44"
    assert ham["team"] == "Ferrari"
    assert ham["color"] == "#ED1131"

    # Verify Kimi Antonelli at Mercedes
    ant = next(d for d in drivers if d["code"] == "ANT")
    assert ant["number"] == "12"
    assert ant["team"] == "Mercedes"

    # Verify Carlos Sainz at Williams
    sai = next(d for d in drivers if d["code"] == "SAI")
    assert sai["number"] == "55"
    assert sai["team"] == "Williams"

    # Mid-season swaps: Tsunoda to Red Bull, Colapinto replaced Doohan
    tsu = next(d for d in drivers if d["code"] == "TSU")
    assert tsu["team"] == "Red Bull Racing"
    assert any(d["code"] == "COL" and d["team"] == "Alpine" for d in drivers)
    assert not any(d["code"] == "DOO" for d in drivers)

def test_2026_driver_lineup():
    drivers = get_season_drivers(2026)
    assert len(drivers) == 22

    nor = next(d for d in drivers if d["code"] == "NOR")
    assert nor["number"] == "1"
    assert nor["team"] == "McLaren"

    ver = next(d for d in drivers if d["code"] == "VER")
    assert ver["number"] == "3"
    assert ver["team"] == "Red Bull Racing"

    teams = {d["team"] for d in drivers}
    assert {"Cadillac", "Audi", "Racing Bulls"} <= teams
    assert any(d["code"] == "CAM" and d["team"] == "Haas F1 Team" for d in drivers)

def test_2026_calendar_matches_the_raced_season():
    cal_2026 = get_season_calendar(2026)
    event_ids = [e["id"] for e in cal_2026]
    # Sakhir and Jeddah were cancelled; Barcelona/Madrid split the Spanish rounds
    # and the relocated Bahrain GP ran at Sepang.
    assert "bahrain" not in event_ids
    assert "saudi_arabia" not in event_ids
    assert {"barcelona", "madrid", "malaysia"} <= set(event_ids)
    assert event_ids[-1] == "abu_dhabi"

def test_generate_track_geometry():
    geom = generate_track_geometry("silverstone", lap_time=87.5)
    assert "svg_path" in geom
    assert "points" in geom
    assert len(geom["points"]) >= 200
    assert "corner_pins" in geom
    assert len(geom["corner_pins"]) > 0

def test_templated_2026_circuits_keep_their_identity():
    for circuit_id, name in (("madrid", "Madring"), ("malaysia", "Sepang International Circuit")):
        geom = generate_track_geometry(circuit_id, lap_time=90.0)
        assert geom["circuit_name"] == name
        assert geom["geometry_source"] == "template"
        assert len(geom["corner_pins"]) > 0

def test_generate_f1_session_telemetry():
    telemetry = generate_f1_session_telemetry(
        year=2025,
        event_id="monaco",
        session_type="Q",
        driver_number="44"
    )
    assert telemetry["status"] == "success"
    assert telemetry["driver_code"] == "HAM"
    assert telemetry["driver_name"] == "Lewis Hamilton"
    assert telemetry["team_name"] == "Ferrari"
    assert telemetry["circuit_name"] == "Circuit de Monaco"
    assert len(telemetry["series"]) == 6 # Time, Speed, Throttle, Brake, Gear, RPM
    assert len(telemetry["series"][0]) > 1000

def test_api_f1_seasons_endpoint():
    res = client.get("/api/f1/seasons")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["seasons"] == [2026, 2025]

def test_api_f1_calendar_endpoint():
    res = client.get("/api/f1/calendar?year=2025")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["year"] == 2025
    assert len(data["events"]) == 24
    assert data["events"][0]["name"] == "Australian Grand Prix"

def test_api_f1_drivers_endpoint():
    res = client.get("/api/f1/drivers?year=2025")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["year"] == 2025
    assert len(data["drivers"]) == 20

def test_api_telemetry_stream_2025_session():
    res = client.get("/api/telemetry/stream?year=2025&event=silverstone&session_type=R&driver=12")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["driver_code"] == "ANT"
    assert data["team_name"] == "Mercedes"
    assert len(data["series"]) == 6
    assert data["total_laps"] == 52
    assert "laps_summary" in data
    assert len(data["laps_summary"]) == 52
    assert any(l["is_fastest"] for l in data["laps_summary"])
    assert any(l["pit"] for l in data["laps_summary"])

def test_api_telemetry_stream_specific_lap():
    res = client.get("/api/telemetry/stream?year=2025&event=silverstone&session_type=R&driver=12&lap=15")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["lap_number"] == 15
    assert len(data["series"]) == 6

def test_api_telemetry_stream_rejects_legacy_season():
    res = client.get("/api/telemetry/stream?year=2023&event=monaco&session_type=Q&driver=1")
    assert res.status_code == 400
    assert "2023" in res.json()["detail"]

def test_api_calendar_rejects_legacy_season():
    res = client.get("/api/f1/calendar?year=2024")
    assert res.status_code == 400

def test_api_analyze_anomaly_2025_session():
    payload = {
        "year": 2025,
        "event": "monaco",
        "session_type": "Q",
        "driver": "44",
        "start_offset_seconds": 15.0,
        "end_offset_seconds": 25.0,
        "channels": ["Speed", "Throttle", "Brake"],
        "domain": "MOTORSPORT_F1"
    }
    res = client.post("/api/analyze_anomaly", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "crop_filename" in data
    assert "diagnostic" in data
    assert data["diagnostic"]["domain"] == "MOTORSPORT_F1"
    assert isinstance(data["historical_precedents"], list)
    assert data["persisted"] is False

