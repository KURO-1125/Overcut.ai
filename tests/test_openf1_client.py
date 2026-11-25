import os
from datetime import datetime, timedelta, timezone

import pytest

from backend.data_engine import f1_calendar, openf1_client


def _iso(base: datetime, seconds: float) -> str:
    return (base + timedelta(seconds=seconds)).isoformat()


BASE = datetime(2025, 5, 24, 14, 10, 0, tzinfo=timezone.utc)


def _session(key=9975, name="Qualifying", circuit="Monte Carlo", start="2025-05-24T14:00:00+00:00"):
    return {
        "session_key": key,
        "meeting_key": 1250,
        "session_name": name,
        "session_type": "Qualifying",
        "circuit_short_name": circuit,
        "date_start": start,
        "is_cancelled": False,
        "year": 2025,
    }


def _drivers():
    return [
        {"driver_number": 1, "name_acronym": "NOR", "first_name": "Lando", "last_name": "Norris",
         "team_name": "McLaren", "team_colour": "FF8000"},
        {"driver_number": 3, "name_acronym": "VER", "first_name": "Max", "last_name": "Verstappen",
         "team_name": "Red Bull Racing", "team_colour": "3671C6"},
    ]


def _laps():
    return [
        {"lap_number": 16, "lap_duration": 71.9, "date_start": _iso(BASE, -80),
         "duration_sector_1": 30.0, "duration_sector_2": 22.0, "duration_sector_3": 19.9},
        {"lap_number": 17, "lap_duration": 70.7, "date_start": _iso(BASE, 0),
         "duration_sector_1": 29.5, "duration_sector_2": 21.8, "duration_sector_3": 19.4},
        {"lap_number": 18, "lap_duration": 71.2, "date_start": _iso(BASE, 70.7),
         "duration_sector_1": 29.7, "duration_sector_2": 21.9, "duration_sector_3": 19.6,
         "is_pit_out_lap": True},
    ]


def _car_rows():
    rows = []
    for index in range(280):
        t = index * 0.25
        rows.append({
            "date": _iso(BASE, t),
            "speed": 300 if index % 40 < 20 else 80,
            "throttle": 100 if index % 40 < 20 else 0,
            "brake": 100 if index % 40 >= 20 else 0,
            "n_gear": 7 if index % 40 < 20 else 2,
            "rpm": 11000 if index % 40 < 20 else 9000,
            "drs": 0,
        })
    return rows


def _location_rows():
    return [
        {"date": _iso(BASE, index * 0.25), "x": 1000 + index * 3, "y": 2000 + (index % 20) * 4, "z": 0}
        for index in range(280)
    ]


def _meta():
    return f1_calendar.get_event_meta(2025, "monaco")


def _assemble(**overrides):
    kwargs = dict(
        year=2025,
        event_id="monaco",
        session_type="Q",
        meta=_meta(),
        session=_session(),
        driver_row=_drivers()[1],
        laps=_laps(),
        car_rows=_car_rows(),
        location_rows=_location_rows(),
        stints=[{"stint_number": 1, "lap_start": 1, "lap_end": 18, "compound": "SOFT"}],
        pits=[{"lap_number": 18}],
    )
    kwargs.update(overrides)
    return openf1_client._assemble_telemetry(**kwargs)


def test_resolve_session_filters_by_circuit_and_session():
    sessions = [
        _session(key=1, name="Practice 1"),
        _session(key=2, name="Qualifying", circuit="Monza"),
        _session(key=3, name="Qualifying", start="2025-05-24T14:00:00+00:00"),
        _session(key=4, name="Qualifying", start="2025-05-25T14:00:00+00:00"),
    ]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(openf1_client, "_fetch_json", lambda url, ttl=None: sessions)
    try:
        resolved = openf1_client._resolve_session(2025, "monaco", "Q")
    finally:
        monkeypatch.undo()
    assert resolved["session_key"] == 4  # duplicate weekend -> latest meeting
    assert openf1_client._resolve_session(2025, "monaco", "XYZ") is None


def test_resolve_driver_prefers_roster_code_over_bare_number():
    # Our roster says #1 is Verstappen; in this fake session car #1 is Norris.
    driver = openf1_client._resolve_driver(2025, "1", _drivers())
    assert driver["name_acronym"] == "VER"
    assert openf1_client._resolve_driver(2025, "16", _drivers()) is None


def test_assemble_telemetry_matches_dashboard_contract():
    telemetry = _assemble()

    assert telemetry["status"] == "success"
    assert telemetry["simulated"] is False
    assert telemetry["source"] == "OPENF1"
    assert "CC BY-NC-SA" in telemetry["data_source"]
    assert len(telemetry["series"]) == 6
    times, speeds, throttles, brakes, gears, rpms = telemetry["series"]
    assert len(times) == len(speeds) == len(throttles) == len(brakes) == len(gears) == len(rpms)
    assert times[0] == 0 and times == sorted(times)
    assert set(brakes) <= {0, 100}
    assert all(isinstance(value, int) for value in gears)

    assert telemetry["lap_number"] == 17  # fastest, since no lap requested
    assert telemetry["total_laps"] == 3
    assert telemetry["lap_time_seconds"] == 70.7
    assert telemetry["sectors"]["s1_end"] == 29.5
    assert telemetry["compound"] == "SOFT"
    assert telemetry["driver_code"] == "VER"
    assert telemetry["team_color"] == "#3671C6"

    assert len(telemetry["track_map"]["points"]) == 280
    assert telemetry["track_map"]["start_finish"] == {
        "x": telemetry["track_map"]["points"][0]["x"],
        "y": telemetry["track_map"]["points"][0]["y"],
    }
    assert telemetry["track_map"]["corner_pins"]

    pit_lap = next(lap for lap in telemetry["laps_summary"] if lap["lap_number"] == 18)
    assert pit_lap["pit"] is True
    assert pit_lap["is_fastest"] is False

    requested = _assemble(lap_number=18)
    assert requested["lap_number"] == 18


def test_assemble_requires_enough_samples():
    assert _assemble(car_rows=_car_rows()[:10]) is None
    assert _assemble(laps=[]) is None


def test_fetch_disabled_returns_none(monkeypatch):
    monkeypatch.setattr(openf1_client, "OPENF1_ENABLED", False)
    assert openf1_client.fetch_openf1_telemetry(2025, "monaco", "Q", "1") is None


def test_cache_roundtrip(tmp_path, monkeypatch):
    calls = {"count": 0}

    def fake_http(url):
        calls["count"] += 1
        return {"ok": True}

    monkeypatch.setattr(openf1_client, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(openf1_client, "_http_json", fake_http)
    url = "https://api.openf1.org/v1/sessions?year=2025"
    assert openf1_client._fetch_json(url) == {"ok": True}
    assert openf1_client._fetch_json(url) == {"ok": True}
    assert calls["count"] == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_fetch_end_to_end_with_mocked_http(monkeypatch, tmp_path):
    monkeypatch.setattr(openf1_client, "OPENF1_ENABLED", True)
    monkeypatch.setattr(openf1_client, "CACHE_DIR", tmp_path)

    def fake_fetch(url, ttl=None):
        if "/sessions" in url:
            return [_session()]
        if "/drivers" in url:
            return _drivers()
        if "/laps" in url:
            return _laps()
        if "/car_data" in url:
            assert "date%3E%3D2025-05-24T14:10:00" in url
            return _car_rows()
        if "/location" in url:
            return _location_rows()
        if "/stints" in url:
            return [{"stint_number": 1, "lap_start": 1, "lap_end": 18, "compound": "SOFT"}]
        if "/pit" in url:
            return []
        raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr(openf1_client, "_fetch_json", fake_fetch)
    telemetry = openf1_client.fetch_openf1_telemetry(2025, "monaco", "Q", "1")

    assert telemetry is not None
    assert telemetry["source"] == "OPENF1"
    assert telemetry["openf1_session_key"] == 9975
    assert telemetry["driver_code"] == "VER"
    assert telemetry["lap_number"] == 17


@pytest.mark.skipif(
    os.getenv("OVERCUT_OPENF1_LIVE") != "1",
    reason="opt-in: hits api.openf1.org",
)
def test_live_monaco_2025_qualifying(monkeypatch):
    monkeypatch.setattr(openf1_client, "OPENF1_ENABLED", True)
    telemetry = openf1_client.fetch_openf1_telemetry(2025, "monaco", "Q", "1")
    assert telemetry is not None
    assert telemetry["source"] == "OPENF1"
    assert len(telemetry["series"][0]) > 150
