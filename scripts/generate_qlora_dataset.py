"""Generates the deterministic, product-aligned EV QLoRA training set.

Each sample is rendered with the runtime's exact EV system/user prompt and its
target is the DiagnosticReport JSON the local tier must emit (``key_evidence``,
SAE DTC codes, lowercase-null nominal handling). Five classes — four failure
modes plus nominal cycles — are balanced so the adapter also learns abstention.

The signal and label rules are shared with ``build_golden_set.py``; the seed
(2027) and image prefix differ, and ``tests/test_eval_golden.py`` verifies the
training and golden crops never share an image hash.

Usage:
    python scripts/generate_qlora_dataset.py
"""

import json
import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_golden_set import FAILURE_MODES, _signals  # noqa: E402
from backend.ai.prompting import build_ev_local_messages, report_payload_from_labels  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = BASE_DIR / "data" / "qlora_dataset"
CROPS_DIR = DATA_DIR / "images"
TRAIN_PATH = DATA_DIR / "ev_battery_train.json"
EVAL_PATH = DATA_DIR / "ev_battery_eval.json"

SEED = 2027
SAMPLES_PER_MODE = 30
TRAIN_FRACTION = 0.85


def render_crop(path: Path, t, voltage, current, temp) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(6, 5), sharex=True)
    fig.patch.set_facecolor("black")
    for ax, data, label, color in zip(
        axes,
        (voltage, current, temp),
        ("Voltage (V)", "Current (A)", "Temperature (°C)"),
        ("#00FFFF", "#FFFF00", "#FF4500"),
    ):
        ax.plot(t, data, color=color, linewidth=1.6)
        ax.set_ylabel(label, color=color, fontsize=8, fontweight="bold")
        ax.set_facecolor("black")
        ax.tick_params(colors="white", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#333333")
        ax.grid(True, color="#222222", linestyle="--", alpha=0.7)
    axes[-1].set_xlabel("Time (s)", color="white", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, facecolor="black", dpi=100)
    plt.close(fig)


def _sample(index: int, mode: dict, rng: np.random.Generator) -> dict:
    t, voltage, current, temp = _signals(mode["type"], rng)
    filename = f"ev_train_{index:04d}_{mode['type']}.png"
    image_path = CROPS_DIR / filename
    render_crop(image_path, t, voltage, current, temp)

    min_v = round(float(voltage.min()), 3)
    max_v = round(float(voltage.max()), 3)
    peak_a = round(float(current.max()), 1)
    temp_c = round(float(temp.max()), 1)
    imbalance_mv = round(float(rng.uniform(*mode["imbalance_mv"])), 1)
    soc = round(float(rng.uniform(*mode["soc"])), 1)
    sag_mv = int(round((max_v - min_v) * 1000))
    module = (index % 4) + 1

    metrics = {
        "min_voltage": min_v,
        "max_voltage": max_v,
        "peak_current": peak_a,
        "max_temperature": temp_c,
        "max_cell_imbalance_mv": imbalance_mv,
        "min_soc": soc,
    }
    labels = {
        "dtc_code": mode["dtc_code"],
        "abstain": mode["dtc_code"] is None,
        "title": mode["title"],
        "severity": mode["severity"],
        "root_cause": mode["root_cause"].format(
            module=module, sag_mv=sag_mv, peak_a=peak_a, temp_c=temp_c
        ),
        "quantitative_evidence": [
            {"channel": "Voltage", "metric": f"{min_v}V", "delta": f"-{sag_mv}mV"},
            {"channel": "Temperature", "metric": f"{temp_c}°C", "delta": "peak pack temperature"},
            {"channel": "Cell_Imbalance_mV", "metric": f"{imbalance_mv}mV", "delta": "max module imbalance"},
        ],
        "recommended_action": mode["action"].format(module=module),
    }
    target = report_payload_from_labels(labels)
    user_prompt = build_ev_local_messages(metrics)[1]["content"]
    flat_prompt = (
        "<image>\n"
        "Analyze this 3-channel EV battery pack telemetry micro-crop. "
        f"Telemetry metrics: Min Voltage: {min_v}V, Max Voltage: {max_v}V, "
        f"Peak Current: {peak_a}A, Max Temp: {temp_c}°C, "
        f"Max Cell Imbalance: {imbalance_mv}mV, Min SoC: {soc}%. "
        "Provide diagnostic root cause, DTC fault code, and corrective action in strict JSON."
    )

    return {
        "id": f"ev_train_{index:04d}",
        "image": str(image_path.relative_to(BASE_DIR)),
        "input": {
            "domain": "EV_BATTERY",
            "anomaly_type": mode["type"],
            "metrics": metrics,
            "prompt": flat_prompt,
        },
        "expected": labels,
        "conversations": [
            {"from": "human", "value": user_prompt},
            {"from": "gpt", "value": json.dumps(target, indent=2)},
        ],
    }


def build() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CROPS_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    samples = []
    for index in range(SAMPLES_PER_MODE * len(FAILURE_MODES)):
        mode = FAILURE_MODES[index % len(FAILURE_MODES)]
        samples.append(_sample(index + 1, mode, rng))

    split = int(TRAIN_FRACTION * len(samples))
    train, held_out = samples[:split], samples[split:]

    TRAIN_PATH.write_text(json.dumps(train, indent=2) + "\n", encoding="utf-8")
    EVAL_PATH.write_text(json.dumps(held_out, indent=2) + "\n", encoding="utf-8")
    logger.info("Train: %d samples -> %s", len(train), TRAIN_PATH)
    logger.info("Held-out: %d samples -> %s", len(held_out), EVAL_PATH)


if __name__ == "__main__":
    build()
