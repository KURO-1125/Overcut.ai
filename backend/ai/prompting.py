"""Prompt text shared by the runtime diagnostic tier and the offline data scripts.

Keeping the EV system/user turns and output schema in one place means training
data and inference see byte-identical instructions.
"""

from typing import Any, Dict, List

EV_SYSTEM_PROMPT = (
    "You are Overcut.ai's Principal Telemetry Intelligence Engineer. "
    "Analyze the supplied telemetry metrics and retrieved precedents. "
    "Return a single JSON object only: no markdown fences and no prose outside the object."
)

EV_OUTPUT_SCHEMA = (
    "{\n"
    '  "dtc_code": "P0A80 or null",\n'
    '  "title": "concise anomaly title",\n'
    '  "root_cause": "engineering explanation grounded in the metrics",\n'
    '  "severity": "LOW | MEDIUM | HIGH | CRITICAL",\n'
    '  "confidence_score": 0.0,\n'
    '  "key_evidence": [\n'
    '    {"channel": "Voltage", "observation": "...", "delta_value": "..."}\n'
    "  ],\n"
    '  "recommended_action": "specific corrective action",\n'
    '  "technical_notes": "optional supporting detail"\n'
    "}"
)

EV_NO_HISTORY = "No historical precedent found (novel telemetry signature)."


def build_ev_local_messages(
    metrics: Dict[str, Any], history_text: str | None = None
) -> List[Dict[str, str]]:
    """Builds the production system/user turns for the local EV tier."""
    metrics_text = (
        f"- Min voltage: {metrics.get('min_voltage', 'N/A')} V\n"
        f"- Max voltage: {metrics.get('max_voltage', 'N/A')} V\n"
        f"- Peak current: {metrics.get('peak_current', 'N/A')} A\n"
        f"- Max temperature: {metrics.get('max_temperature', 'N/A')} C\n"
        f"- Max cell imbalance: {metrics.get('max_cell_imbalance_mv', 'N/A')} mV\n"
        f"- Min state of charge: {metrics.get('min_soc', 'N/A')} %"
    )
    user = (
        "You are diagnosing an electric vehicle NMC Li-ion battery pack BMS.\n\n"
        f"QUANTITATIVE TELEMETRY METRICS:\n{metrics_text}\n\n"
        f"FAISS HISTORICAL INCIDENT PRECEDENTS:\n{history_text or EV_NO_HISTORY}\n\n"
        f"OUTPUT SCHEMA:\n{EV_OUTPUT_SCHEMA}\n\n"
        "RULES:\n"
        '1. Set "dtc_code" to a valid SAE J2012 code matching ^P0[0-9A-F]{3}$ '
        "when the metrics support one, otherwise null.\n"
        "2. severity must be one of LOW, MEDIUM, HIGH, CRITICAL.\n"
        "3. confidence_score must be a number between 0.0 and 1.0.\n"
        "4. key_evidence must contain at least one item whose metric values appear "
        "in the telemetry metrics above.\n"
        "5. Do not invent precedent sessions that are not listed."
    )
    return [
        {"role": "system", "content": EV_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def report_payload_from_labels(labels: Dict[str, Any]) -> Dict[str, Any]:
    """Maps a labelled sample to the DiagnosticReport JSON the local tier emits."""
    evidence = []
    for item in labels.get("quantitative_evidence") or []:
        metric = str(item.get("metric", ""))
        delta = item.get("delta")
        observation = f"{delta} at {metric}".strip() if delta else f"observed {metric}"
        evidence.append(
            {
                "channel": item.get("channel", "Telemetry"),
                "observation": observation,
                "delta_value": str(delta) if delta is not None else None,
            }
        )
    dtc = labels.get("dtc_code") or None
    return {
        "dtc_code": dtc,
        "title": labels.get("title", ""),
        "root_cause": labels.get("root_cause", ""),
        "severity": labels.get("severity", "LOW"),
        "confidence_score": 0.95 if dtc else 0.9,
        "key_evidence": evidence,
        "recommended_action": labels.get("recommended_action", ""),
        "technical_notes": f"Grounded in {len(evidence)} cited telemetry channels.",
    }
