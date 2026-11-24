import json

from backend.ai.diagnostics_service import DiagnosticsService
from backend.ai.schema import AnomalySeverity

EV_SUMMARY = {
    "min_voltage": 2.71,
    "max_voltage": 4.10,
    "peak_current": 58.0,
    "max_temperature": 41.2,
    "max_cell_imbalance_mv": 132.0,
    "min_soc": 38.0,
}

VALID_REPORT = {
    "dtc_code": "P0A80",
    "title": "Cell module voltage collapse under load",
    "root_cause": "Internal resistance rise in module 4 produces a 1390 mV sag at 58 A.",
    "severity": "CRITICAL",
    "confidence_score": 0.88,
    "key_evidence": [
        {"channel": "Voltage", "observation": "Minimum cell voltage 2.71 V", "delta_value": "-1390 mV"},
        {"channel": "Temperature", "observation": "Pack peak 41.2 C", "delta_value": "+9.0 C"},
    ],
    "recommended_action": "Isolate module 4 and run impedance spectroscopy.",
    "technical_notes": "dV/dt steepens after the current step.",
}


class _StubBatch(dict):
    def to(self, device):
        return self


class _StubProcessor:
    def __init__(self, replies):
        self.replies = list(replies)
        self.last_messages = None

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        self.last_messages = messages
        return "FORMATTED_PROMPT"

    def __call__(self, prompt, return_tensors="pt"):
        return _StubBatch(input_ids=[[11, 12, 13]])

    def decode(self, ids, skip_special_tokens=True):
        return self.replies.pop(0)


class _StubModel:
    def __init__(self):
        self.generate_calls = 0

    def generate(self, **kwargs):
        self.generate_calls += 1
        return [[11, 12, 13, 21, 22, 23]]


def _service_with(replies):
    service = DiagnosticsService()
    service.device = "cpu"
    service.vlm_model_name = "stub-7b"
    service.local_vlm_model = _StubModel()
    service.local_vlm_processor = _StubProcessor(replies)
    service._load_local_7b_model = lambda: True
    return service


def _diagnose(service):
    return service._diagnose_with_vlm(
        "ANOM-TEST",
        "unused.png",
        EV_SUMMARY,
        [],
        "EV_BATTERY",
    )


def test_valid_json_is_produced_without_clamping_confidence():
    service = _service_with([json.dumps(VALID_REPORT)])

    report = _diagnose(service)

    assert report.provider == "LOCAL_VLM"
    assert report.model_name == "stub-7b"
    assert report.dtc_code == "P0A80"
    assert report.severity is AnomalySeverity.CRITICAL
    assert report.confidence_score == 0.88
    assert len(report.key_evidence) == 2
    assert report.is_insufficient_data is False
    assert service.local_vlm_model.generate_calls == 1


def test_markdown_fenced_json_is_accepted():
    fenced = "```json\n" + json.dumps(VALID_REPORT) + "\n```"
    service = _service_with([fenced])

    report = _diagnose(service)

    assert report.provider == "LOCAL_VLM"
    assert report.dtc_code == "P0A80"


def test_invalid_output_is_retried_once_then_validated():
    service = _service_with(["I think the battery is hot.", json.dumps(VALID_REPORT)])

    report = _diagnose(service)

    assert report.provider == "LOCAL_VLM"
    assert service.local_vlm_model.generate_calls == 2
    # The retry must include a corrective user turn.
    assert service.local_vlm_processor.last_messages[-1]["role"] == "user"
    assert "valid DiagnosticReport JSON" in service.local_vlm_processor.last_messages[-1]["content"]


def test_two_invalid_outputs_fall_back_to_deterministic_engine():
    service = _service_with(["not json", '{"title": "missing everything else"}'])

    report = _diagnose(service)

    assert report.provider == "DETERMINISTIC_HEURISTIC"
    assert report.model_name == "Overcut Deterministic Heuristic Engine"
    assert "JSON validation" in report.technical_notes
    assert service.local_vlm_model.generate_calls == 2


def test_invalid_dtc_code_is_rejected_by_schema():
    bad = dict(VALID_REPORT, dtc_code="P1234")
    service = _service_with([json.dumps(bad), json.dumps(bad)])

    report = _diagnose(service)

    assert report.provider == "DETERMINISTIC_HEURISTIC"


def test_prompt_contains_grounding_metrics_and_dtc_rule():
    service = _service_with([json.dumps(VALID_REPORT)])
    messages = service._build_local_json_messages("EV_BATTERY", EV_SUMMARY, [])

    prompt = messages[-1]["content"]
    assert "Min voltage: 2.71 V" in prompt
    assert "Max cell imbalance: 132.0 mV" in prompt
    assert "P0[0-9A-F]{3}" in prompt
    assert messages[0]["role"] == "system"
