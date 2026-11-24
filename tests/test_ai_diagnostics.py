import pytest
from backend.ai.diagnostics_service import DiagnosticsService
from backend.ai.schema import DiagnosticReport, AnomalySeverity

def test_f1_diagnostic_generation():
    service = DiagnosticsService()
    
    telemetry_summary = {
        "driver": "1",
        "min_speed": 110.0,
        "max_speed": 295.0,
        "max_brake": 100,
        "min_throttle": 0,
        "duration_seconds": 2.4
    }
    
    historical_matches = [
        {
            "session_id": "2021_Baku_Turn1",
            "driver": "44",
            "metadata": "Lockup on cold medium tires into Turn 1 braking zone",
            "score": 0.895
        }
    ]
    
    report = service.analyze_anomaly(
        image_path="test_image.png",
        telemetry_summary=telemetry_summary,
        historical_matches=historical_matches,
        domain="MOTORSPORT_F1"
    )
    
    assert isinstance(report, DiagnosticReport)
    assert report.domain == "MOTORSPORT_F1"
    assert report.severity == AnomalySeverity.HIGH
    assert report.confidence_score >= 0.8
    assert len(report.key_evidence) >= 2
    assert len(report.historical_precedents) == 1
    assert "Brake" in [e.channel for e in report.key_evidence]
    assert report.recommended_action != ""

def test_ev_diagnostic_generation():
    service = DiagnosticsService()
    
    ev_summary = {
        "voltage_drop_mv": 450,
        "max_temp_celsius": 52.0
    }
    
    report = service.analyze_anomaly(
        image_path="test_ev.png",
        telemetry_summary=ev_summary,
        historical_matches=[],
        domain="EV_BATTERY"
    )
    
    assert isinstance(report, DiagnosticReport)
    assert report.domain == "EV_BATTERY"
    assert report.severity == AnomalySeverity.CRITICAL
    assert report.confidence_score > 0.9

def test_vlm_status_and_readiness():
    service = DiagnosticsService()
    status = service.get_vlm_status()
    assert "vlm_model" in status
    assert "quantization" in status
    assert "architecture" in status
    assert "failsafe_confidence_threshold" in status
    assert status["failsafe_confidence_threshold"] == 0.65
    assert "providers_available" in status
    assert isinstance(status["providers_available"]["local_vlm"], bool)
    assert isinstance(status["providers_available"]["google_gemini"], bool)

def test_targeted_perception_prompt_construction():
    service = DiagnosticsService()
    f1_summary = {
        "driver": "1",
        "min_speed": 120.0,
        "max_speed": 280.0,
        "max_brake": 95,
        "min_throttle": 5,
        "duration_seconds": 3.1
    }
    prompt = service.build_targeted_perception_prompt("MOTORSPORT_F1", f1_summary, [])
    assert "<image>" in prompt
    assert "Formula 1" in prompt
    assert "Max Brake: 95%" in prompt

def test_local_vlm_unavailable_falls_back_honestly():
    service = DiagnosticsService()
    f1_summary = {
        "driver": "1",
        "min_speed": 90.0,
        "max_speed": 290.0,
        "max_brake": 100,
        "min_throttle": 0,
        "duration_seconds": 2.5
    }
    # Tests run on CPU without the LoRA adapter, so a VLM request must degrade
    # to the deterministic engine and say so instead of pretending it ran.
    report = service.analyze_anomaly(
        image_path="test_f1.png",
        telemetry_summary=f1_summary,
        historical_matches=[{"session_id": "2023_Monaco", "driver": "1", "metadata": "Lockup", "score": 0.91}],
        domain="MOTORSPORT_F1",
        use_vlm=True
    )
    assert report.provider == "DETERMINISTIC_HEURISTIC"
    assert report.is_insufficient_data is False

def test_insufficient_data_failsafe():
    service = DiagnosticsService()
    # Scenario: low confidence score (0.42 < 0.65) with failsafe enforced
    low_match = [{"session_id": "Noise", "driver": "0", "metadata": "Random noise", "score": 0.42}]
    report = service.analyze_anomaly(
        image_path="corrupt_trace.png",
        telemetry_summary={"driver": "1", "min_speed": 200, "max_speed": 210, "max_brake": 0},
        historical_matches=low_match,
        domain="MOTORSPORT_F1",
        enforce_failsafe=True
    )
    assert report.is_insufficient_data is True
    assert report.severity == AnomalySeverity.UNKNOWN
    assert report.provider == "HALLUCINATION_FAILSAFE"
    assert "threshold required" in report.root_cause

def test_cloud_gemini_fallback_when_key_unconfigured():
    service = DiagnosticsService()
    f1_summary = {
        "driver": "1",
        "min_speed": 90.0,
        "max_speed": 290.0,
        "max_brake": 100,
        "min_throttle": 0,
        "duration_seconds": 2.5
    }
    # No GEMINI_API_KEY in the test env: the service must fall back safely.
    report = service.analyze_anomaly(
        image_path="test_f1.png",
        telemetry_summary=f1_summary,
        historical_matches=[{"session_id": "2023_Monaco", "driver": "1", "metadata": "Lockup", "score": 0.91}],
        domain="MOTORSPORT_F1",
        use_cloud_vlm=True,
    )
    assert isinstance(report, DiagnosticReport)
    assert report.confidence_score > 0.8


