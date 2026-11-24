import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts.evaluate_qlora import (
    GOLDEN_FILE,
    evidence_is_grounded,
    ground_truth,
    load_eval_set,
    score,
    verify_manifest,
)

BASE_DIR = Path(__file__).resolve().parent.parent
TRAIN_FILE = BASE_DIR / "data" / "qlora_dataset" / "ev_battery_train.json"
DTC_RE = re.compile(r"^P0[0-9A-F]{3}$")
SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"}


@pytest.fixture(scope="module")
def golden():
    if not GOLDEN_FILE.exists():
        pytest.skip("Golden set not generated; run scripts/build_golden_set.py")
    return load_eval_set(GOLDEN_FILE)


def test_manifest_hash_matches_dataset():
    if not GOLDEN_FILE.exists():
        pytest.skip("Golden set not generated")
    manifest = verify_manifest(GOLDEN_FILE)
    assert manifest is not None
    assert manifest["verified_sha256"] == hashlib.sha256(GOLDEN_FILE.read_bytes()).hexdigest()


def test_golden_set_is_balanced_and_large_enough(golden):
    manifest = json.loads(GOLDEN_FILE.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    assert len(golden) >= 150
    assert manifest["counts"]["total"] == len(golden)
    assert manifest["counts"]["negatives"] >= 20
    assert len(manifest["counts"]["by_dtc"]) >= 4


def test_labels_are_well_formed(golden):
    ids = set()
    for sample in golden:
        expected, prompt = ground_truth(sample)
        assert sample["id"] not in ids
        ids.add(sample["id"])
        assert expected["severity"] in SEVERITIES
        if expected["dtc_code"] is not None:
            assert DTC_RE.match(expected["dtc_code"])
        assert expected["recommended_action"]
        assert prompt
        for metric, value in sample["input"]["metrics"].items():
            assert str(value) in prompt, f"{sample['id']} prompt is missing {metric}"


def test_golden_images_do_not_overlap_training_images(golden):
    if not TRAIN_FILE.exists():
        pytest.skip("Training split not present")

    def digest(relative_path: str) -> str:
        return hashlib.sha256((BASE_DIR / relative_path).read_bytes()).hexdigest()

    golden_hashes = {
        digest(sample["image"]) for sample in golden
        if (BASE_DIR / sample["image"]).exists()
    }
    train_samples = json.loads(TRAIN_FILE.read_text(encoding="utf-8"))
    train_hashes = {
        digest(sample["image"]) for sample in train_samples
        if (BASE_DIR / sample["image"]).exists()
    }
    assert golden_hashes
    assert golden_hashes.isdisjoint(train_hashes), "Golden images overlap the training split"


def test_perfect_predictions_score_one(golden):
    predictions = {}
    for sample in golden:
        expected, _ = ground_truth(sample)
        predictions[sample["id"]] = {"id": sample["id"], "output": json.dumps(expected)}

    report = score(golden, predictions)

    assert report["json_parse_rate"] == 1.0
    assert report["json_schema_compliance"] == 1.0
    assert report["evidence_groundedness"] == 1.0
    assert report["dtc_code_accuracy"] == 1.0
    assert report["severity_accuracy"] == 1.0
    assert report["negative_specificity"] == 1.0


def test_product_key_evidence_shape_is_grounded(golden):
    predictions = {}
    for sample in golden:
        expected, _ = ground_truth(sample)
        output = {k: v for k, v in expected.items() if k != "quantitative_evidence"}
        output["key_evidence"] = [
            {"channel": item["channel"], "observation": "observed", "delta_value": item["metric"]}
            for item in expected["quantitative_evidence"]
        ]
        predictions[sample["id"]] = {
            "id": sample["id"],
            "output": json.dumps(output),
            "provider": "LOCAL_VLM",
        }

    report = score(golden, predictions)

    assert report["evidence_groundedness"] == 1.0
    assert report["provider_distribution"] == {"LOCAL_VLM": len(golden)}


def test_grounding_accepts_rounded_citations():
    prompt = "Min Voltage: 3.199V, Peak Current: 52.1A"
    rounded = {
        "key_evidence": [
            {"channel": "Voltage", "observation": "sag", "delta_value": "3.2 V"},
            {"channel": "Current", "observation": "peak draw", "delta_value": "52 A"},
        ]
    }
    invented = {
        "key_evidence": [
            {"channel": "Voltage", "observation": "sag", "delta_value": "3.7 V"},
        ]
    }

    assert evidence_is_grounded(rounded, prompt)
    assert not evidence_is_grounded(invented, prompt)


def test_malformed_output_scores_zero_but_does_not_crash(golden):
    predictions = {
        sample["id"]: {"id": sample["id"], "output": "the battery looks warm"}
        for sample in golden
    }

    report = score(golden, predictions)

    assert report["json_parse_rate"] == 0.0
    assert report["json_schema_compliance"] == 0.0
    assert report["dtc_code_accuracy"] == 0.0
    assert report["negative_specificity"] == 0.0


def test_negative_samples_require_abstention(golden):
    negatives = [s for s in golden if ground_truth(s)[0].get("abstain")]
    assert negatives, "Golden set must contain nominal samples"

    # A confident CRITICAL diagnosis of a nominal pack must lose specificity.
    predictions = {}
    for sample in golden:
        expected, _ = ground_truth(sample)
        output = dict(expected)
        if expected.get("abstain"):
            output["dtc_code"] = "P0A80"
            output["severity"] = "CRITICAL"
        predictions[sample["id"]] = {"id": sample["id"], "output": json.dumps(output)}

    report = score(golden, predictions)

    assert report["negative_specificity"] == 0.0
    assert report["dtc_code_accuracy"] == 1.0  # DTC accuracy ignores nominal samples
