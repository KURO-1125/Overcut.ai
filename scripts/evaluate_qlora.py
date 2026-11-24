"""Scores saved model predictions against a versioned evaluation set.

Usage:
    python scripts/evaluate_qlora.py
    python scripts/evaluate_qlora.py --dataset data/eval/golden_ev_v1.json
    python scripts/evaluate_qlora.py --predictions models/ev_qlora_adapter/predictions.jsonl

Without ``--predictions`` the script only reports dataset statistics and writes a
report marked ``"measured": false``. It never emits placeholder accuracy numbers.

Predictions file format (JSONL, one object per evaluation sample):

    {"id": "ev_golden_0001", "output": "<raw model text, expected strict JSON>",
     "latency_s": 0.64, "vram_gb": 3.4}

``latency_s`` and ``vram_gb`` are optional; when absent those metrics are omitted
rather than estimated. When a ``<dataset>.manifest.json`` file exists next to the
dataset, its recorded SHA-256 is verified before anything is scored.
"""

import argparse
import hashlib
import json
import logging
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
GOLDEN_FILE = BASE_DIR / "data" / "eval" / "golden_ev_v1.json"
LEGACY_EVAL_FILE = BASE_DIR / "data" / "qlora_dataset" / "ev_battery_eval.json"
REPORT_PATH = BASE_DIR / "models" / "ev_qlora_adapter" / "evaluation_benchmark.json"

REPORT_KEYS = {"dtc_code", "title", "severity", "root_cause", "recommended_action"}
EVIDENCE_KEYS = ("quantitative_evidence", "key_evidence")
EVIDENCE_TEXT_KEYS = ("metric", "delta", "delta_value", "observation")
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
ABSTAIN_SEVERITIES = {"LOW", "UNKNOWN"}


def default_dataset() -> Path:
    return GOLDEN_FILE if GOLDEN_FILE.exists() else LEGACY_EVAL_FILE


def manifest_path(dataset: Path) -> Path:
    return dataset.with_suffix(".manifest.json")


def load_eval_set(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"Evaluation dataset not found: {path}")
    samples = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(samples, list) or not samples:
        raise SystemExit(f"Evaluation dataset must be a non-empty list: {path}")
    return samples


def verify_manifest(dataset: Path) -> dict | None:
    """Verifies the dataset hash recorded by the golden-set generator."""
    path = manifest_path(dataset)
    if not path.exists():
        return None
    manifest = json.loads(path.read_text(encoding="utf-8"))
    actual = hashlib.sha256(dataset.read_bytes()).hexdigest()
    expected = manifest.get("dataset_sha256")
    if expected and expected != actual:
        raise SystemExit(
            f"Dataset hash mismatch for {dataset.name}: manifest says {expected[:12]}, file is {actual[:12]}."
        )
    manifest["verified_sha256"] = actual
    return manifest


def ground_truth(sample: dict) -> tuple[dict, str]:
    """Returns (expected labels, prompt text) for golden or legacy samples."""
    if isinstance(sample.get("expected"), dict):
        prompt = (sample.get("input") or {}).get("prompt", "")
        return sample["expected"], prompt

    conversations = sample.get("conversations") or []
    prompt = next((c.get("value", "") for c in conversations if c.get("from") == "human"), "")
    answer = next((c.get("value", "") for c in conversations if c.get("from") == "gpt"), "")
    try:
        expected = json.loads(answer)
    except json.JSONDecodeError:
        expected = {}
    return expected, prompt


def parse_output(output: str) -> dict | None:
    text = output.strip()
    # Tolerate markdown fences around the JSON object.
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def evidence_list(parsed: dict) -> list:
    for key in EVIDENCE_KEYS:
        value = parsed.get(key)
        if isinstance(value, list) and value:
            return value
    return []


def _decimals(number: str) -> int:
    return len(number.split(".", 1)[1]) if "." in number else 0


def _cited_number_in_prompt(cited: str, prompt_numbers: set[str], prompt_values: list[float]) -> bool:
    """Exact string match, or a rounding match (cited '3.2' grounds prompt 3.199)."""
    if cited in prompt_numbers:
        return True
    value = float(cited)
    places = _decimals(cited)
    return any(round(prompt_value, places) == round(value, places) for prompt_value in prompt_values)


def evidence_is_grounded(parsed: dict, prompt: str) -> bool:
    """True when every evidence item cites at least one metric value from the prompt.

    Supports both the golden ``quantitative_evidence`` shape (``metric``/``delta``)
    and the production ``key_evidence`` shape (``delta_value``/``observation``).
    A cited number grounds an item when it matches exactly or when it matches a
    prompt value after rounding to the cited number's precision.
    """
    prompt_numbers = set(NUMBER_RE.findall(prompt))
    prompt_values = [float(number) for number in prompt_numbers]
    evidence = evidence_list(parsed)
    if not evidence:
        return False
    for item in evidence:
        if not isinstance(item, dict):
            return False
        text = " ".join(str(item.get(key, "")) for key in EVIDENCE_TEXT_KEYS)
        cited_numbers = NUMBER_RE.findall(text)
        if not cited_numbers:
            return False
        if not any(
            _cited_number_in_prompt(cited, prompt_numbers, prompt_values)
            for cited in cited_numbers
        ):
            return False
    return True


def score(evals: list[dict], predictions: dict[str, dict]) -> dict:
    matched = [s for s in evals if s.get("id") in predictions]
    if not matched:
        raise SystemExit("No prediction ids matched the evaluation set.")

    dtc_total = dtc_hits = sev_total = sev_hits = 0
    negative_total = negative_hits = 0
    schema_hits = grounded_hits = parse_hits = 0
    per_code: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    latencies, vrams = [], []
    providers: Counter[str] = Counter()

    for sample in matched:
        expected, prompt = ground_truth(sample)
        record = predictions[sample["id"]]
        parsed = parse_output(str(record.get("output", "")))

        expected_dtc = expected.get("dtc_code")
        expected_severity = str(expected.get("severity", "")).upper()
        abstain_expected = bool(expected.get("abstain"))

        predicted_dtc = None
        predicted_severity = ""
        if parsed is not None:
            parse_hits += 1
            predicted_dtc = parsed.get("dtc_code") or None
            predicted_severity = str(parsed.get("severity", "")).strip().upper()
            if REPORT_KEYS.issubset(parsed) and evidence_list(parsed):
                schema_hits += 1
            if evidence_is_grounded(parsed, prompt):
                grounded_hits += 1

        if expected_dtc:
            dtc_total += 1
            per_code[expected_dtc][1] += 1
            if predicted_dtc == expected_dtc:
                dtc_hits += 1
                per_code[expected_dtc][0] += 1

        if expected_severity:
            sev_total += 1
            if predicted_severity == expected_severity:
                sev_hits += 1

        if abstain_expected:
            negative_total += 1
            if parsed is not None and not predicted_dtc and predicted_severity in ABSTAIN_SEVERITIES:
                negative_hits += 1

        if isinstance(record.get("latency_s"), (int, float)):
            latencies.append(float(record["latency_s"]))
        if isinstance(record.get("vram_gb"), (int, float)):
            vrams.append(float(record["vram_gb"]))
        if isinstance(record.get("provider"), str):
            providers[record["provider"]] += 1

    total = len(matched)
    report = {
        "measured": True,
        "predictions_evaluated": total,
        "evaluation_set_size": len(evals),
        "json_parse_rate": round(parse_hits / total, 4),
        "json_schema_compliance": round(schema_hits / total, 4),
        "evidence_groundedness": round(grounded_hits / total, 4),
    }
    if dtc_total:
        report["dtc_code_accuracy"] = round(dtc_hits / dtc_total, 4)
        report["dtc_accuracy_by_code"] = {
            code: round(hits / count, 4) for code, (hits, count) in sorted(per_code.items())
        }
    if sev_total:
        report["severity_accuracy"] = round(sev_hits / sev_total, 4)
    if negative_total:
        report["negative_specificity"] = round(negative_hits / negative_total, 4)
    if latencies:
        report["mean_latency_s"] = round(statistics.fmean(latencies), 3)
    if vrams:
        report["mean_vram_gb"] = round(statistics.fmean(vrams), 3)
    if providers:
        report["provider_distribution"] = dict(sorted(providers.items()))
    return report


def dataset_stats(evals: list[dict]) -> dict:
    dtc_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    negatives = 0
    for sample in evals:
        expected, _ = ground_truth(sample)
        dtc = expected.get("dtc_code") or "NOMINAL"
        dtc_counts[dtc] = dtc_counts.get(dtc, 0) + 1
        severity = str(expected.get("severity", "MISSING")).upper()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if expected.get("abstain"):
            negatives += 1
    return {
        "measured": False,
        "status": "not_evaluated",
        "evaluation_set_size": len(evals),
        "ground_truth_dtc_distribution": dict(sorted(dtc_counts.items())),
        "ground_truth_severity_distribution": dict(sorted(severity_counts.items())),
        "negative_samples": negatives,
        "note": (
            "Run with --predictions <jsonl> to score model outputs. "
            "No accuracy numbers are reported until predictions have been measured."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=None, help="Evaluation JSON (defaults to the golden set)")
    parser.add_argument("--predictions", type=Path, help="JSONL file of model outputs keyed by sample id")
    args = parser.parse_args()

    dataset = args.dataset or default_dataset()
    evals = load_eval_set(dataset)
    manifest = verify_manifest(dataset)
    logger.info("Evaluation set: %d samples from %s", len(evals), dataset)
    if manifest:
        logger.info("Manifest verified (sha256 %s...)", manifest["verified_sha256"][:12])

    if args.predictions:
        if not args.predictions.exists():
            raise SystemExit(f"Predictions file not found: {args.predictions}")
        records = {}
        for line in args.predictions.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if "id" not in record:
                raise SystemExit("Every prediction record needs an 'id' field.")
            records[str(record["id"])] = record
        report = score(evals, records)
        meta_path = args.predictions.with_suffix(".meta.json")
        if meta_path.exists():
            report["run"] = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        report = dataset_stats(evals)
        logger.info("No --predictions supplied; writing an unmeasured status report.")

    report["dataset"] = str(dataset.relative_to(BASE_DIR)) if dataset.is_relative_to(BASE_DIR) else str(dataset)
    if manifest:
        report["dataset_sha256"] = manifest["verified_sha256"]

    logger.info(json.dumps(report, indent=2))
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    logger.info("Report saved to %s", REPORT_PATH)


if __name__ == "__main__":
    main()
