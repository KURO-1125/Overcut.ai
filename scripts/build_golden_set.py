"""Builds the versioned EV battery golden evaluation set.

The set is fully synthetic and deterministically seeded: every label is derived
from the known failure mode and the generated metrics, so it can be regenerated
byte-for-byte. It intentionally uses an independent renderer from the QLoRA
training generator and a different prompt wording, so evaluation is not just a
replay of the training set.

Usage:
    python scripts/build_golden_set.py
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "eval"
IMAGES_DIR = OUTPUT_DIR / "images"
DATASET_PATH = OUTPUT_DIR / "golden_ev_v1.json"
MANIFEST_PATH = OUTPUT_DIR / "golden_ev_v1.manifest.json"

SEED = 1337
SAMPLES_PER_MODE = 40
VERSION = 1

FAILURE_MODES = [
    {
        "type": "cell_internal_resistance",
        "dtc_code": "P0A80",
        "title": "Hybrid/EV Battery Pack Cell Module Degraded",
        "severity": "HIGH",
        "root_cause": "Elevated internal resistance in module {module} causes a {sag_mv} mV voltage depression at {peak_a} A.",
        "action": "Isolate module {module}; run cell capacity testing and pack rebalancing.",
        "imbalance_mv": (115.0, 155.0),
        "soc": (20.0, 45.0),
    },
    {
        "type": "thermal_runaway_early",
        "dtc_code": "P0A7F",
        "title": "Severe Exothermic Thermal Gradient Excursion",
        "severity": "CRITICAL",
        "root_cause": "Exothermic separator breakdown drives {temp_c} C at negative dV/dt slope.",
        "action": "Open the HV contactors, run the coolant loop at 100% flow, and stop the vehicle.",
        "imbalance_mv": (25.0, 60.0),
        "soc": (30.0, 60.0),
    },
    {
        "type": "lithium_plating",
        "dtc_code": "P0B3C",
        "title": "Fast-Charge Anode Metallic Lithium Plating Risk",
        "severity": "HIGH",
        "root_cause": "Low-temperature fast charging ({temp_c} C) promotes SEI lithium dendrite growth.",
        "action": "De-rate DC fast charging to C/3 and enable pack pre-conditioning heaters.",
        "imbalance_mv": (18.0, 45.0),
        "soc": (40.0, 70.0),
    },
    {
        "type": "parasitic_drain",
        "dtc_code": "P0A1F",
        "title": "Static Key-Off HV Parasitic Phantom Drain",
        "severity": "MEDIUM",
        "root_cause": "Uncommanded DC-DC leakage draws {peak_a} A while the vehicle is in key-off sleep.",
        "action": "Isolate the auxiliary DC-DC gate driver and update BMS sleep firmware.",
        "imbalance_mv": (5.0, 14.0),
        "soc": (25.0, 55.0),
    },
    {
        "type": "nominal",
        "dtc_code": None,
        "title": "Nominal Pack Discharge — No Anomaly Detected",
        "severity": "LOW",
        "root_cause": "Voltage, current, temperature and imbalance remain inside nominal operating bounds.",
        "action": "Continue standard monitoring.",
        "imbalance_mv": (4.0, 10.0),
        "soc": (55.0, 80.0),
    },
]


def _signals(mode_type: str, rng: np.random.Generator):
    t = np.linspace(0.0, 5.0, 200)
    if mode_type == "cell_internal_resistance":
        sag = rng.uniform(0.55, 0.95)
        voltage = 4.10 - sag / (1 + np.exp(-3 * (t - 1.2)))
        current = np.where(t > 1.0, rng.uniform(40.0, 60.0), 8.0)
        temp = 25.0 + 3.5 * t + rng.normal(0, 0.15, t.size)
    elif mode_type == "thermal_runaway_early":
        voltage = 3.9 - 0.8 / (1 + np.exp(-2 * (t - 1.8)))
        current = np.where(t < 2.5, 45.0, 12.0)
        temp = 30.0 + rng.uniform(6.0, 8.5) * t ** 1.3
    elif mode_type == "lithium_plating":
        voltage = 4.05 + 0.25 / (1 + np.exp(-3 * (t - 1.0)))
        current = np.where(t > 1.0, -rng.uniform(35.0, 55.0), -5.0)
        temp = rng.uniform(2.0, 8.0) + 1.2 * t
    elif mode_type == "parasitic_drain":
        voltage = 3.72 - 0.04 * (t / 5.0)
        current = np.full_like(t, rng.uniform(1.8, 4.0))
        temp = 22.0 + 0.3 * np.sin(t)
    else:  # nominal
        voltage = 4.00 - 0.10 * (t / 5.0) + 0.01 * np.sin(2 * t)
        current = 12.0 + 3.0 * np.sin(t)
        temp = 25.0 + 0.6 * t + rng.normal(0, 0.1, t.size)
    return t, voltage, current, temp


def _render(path: Path, t, voltage, current, temp):
    fig, axes = plt.subplots(3, 1, figsize=(6, 5), sharex=True)
    fig.patch.set_facecolor("black")
    for ax, data, label, color in zip(
        axes,
        (voltage, current, temp),
        ("Voltage (V)", "Current (A)", "Temperature (C)"),
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
    filename = f"ev_golden_{index:04d}_{mode['type']}.png"
    _render(IMAGES_DIR / filename, t, voltage, current, temp)

    min_v = round(float(voltage.min()), 3)
    max_v = round(float(voltage.max()), 3)
    peak_a = round(float(current.max()), 1)
    temp_c = round(float(temp.max()), 1)
    imbalance_mv = round(float(rng.uniform(*mode["imbalance_mv"])), 1)
    soc = round(float(rng.uniform(*mode["soc"])), 1)
    sag_mv = int(round((max_v - min_v) * 1000))
    module = (index % 4) + 1

    evidence = [
        {"channel": "Voltage", "metric": f"{min_v}V", "delta": f"-{sag_mv}mV"},
        {"channel": "Temperature", "metric": f"{temp_c}°C", "delta": "peak pack temperature"},
        {"channel": "Cell_Imbalance_mV", "metric": f"{imbalance_mv}mV", "delta": "max module imbalance"},
    ]
    abstain = mode["dtc_code"] is None

    reference = {
        "dtc_code": mode["dtc_code"],
        "abstain": abstain,
        "title": mode["title"],
        "severity": mode["severity"],
        "root_cause": mode["root_cause"].format(
            module=module, sag_mv=sag_mv, peak_a=peak_a, temp_c=temp_c
        ),
        "quantitative_evidence": evidence,
        "recommended_action": mode["action"].format(module=module),
    }

    prompt = (
        "<image>\n"
        "Analyze this 3-channel EV battery pack telemetry micro-crop. "
        f"Telemetry metrics: Min Voltage: {min_v}V, Max Voltage: {max_v}V, "
        f"Peak Current: {peak_a}A, Max Temp: {temp_c}°C, "
        f"Max Cell Imbalance: {imbalance_mv}mV, Min SoC: {soc}%. "
        "Provide diagnostic root cause, DTC fault code, and corrective action in strict JSON."
    )

    return {
        "id": f"ev_golden_{index:04d}",
        "image": str((IMAGES_DIR / filename).relative_to(BASE_DIR)),
        "input": {
            "domain": "EV_BATTERY",
            "anomaly_type": mode["type"],
            "metrics": {
                "min_voltage": min_v,
                "max_voltage": max_v,
                "peak_current": peak_a,
                "max_temperature": temp_c,
                "max_cell_imbalance_mv": imbalance_mv,
                "min_soc": soc,
            },
            "prompt": prompt,
        },
        "expected": reference,
        # Kept in the training-compatible shape so the existing scorer can read it.
        "conversations": [
            {"from": "human", "value": prompt},
            {"from": "gpt", "value": json.dumps(reference, indent=2)},
        ],
    }


def build() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    samples = []
    for index in range(SAMPLES_PER_MODE * len(FAILURE_MODES)):
        mode = FAILURE_MODES[index % len(FAILURE_MODES)]
        samples.append(_sample(index + 1, mode, rng))

    DATASET_PATH.write_text(json.dumps(samples, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest()

    dtc_counts = {}
    severity_counts = {}
    for sample in samples:
        expected = sample["expected"]
        key = expected["dtc_code"] or "NOMINAL"
        dtc_counts[key] = dtc_counts.get(key, 0) + 1
        severity_counts[expected["severity"]] = severity_counts.get(expected["severity"], 0) + 1

    manifest = {
        "name": "overcut-golden-ev",
        "version": VERSION,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "scripts/build_golden_set.py",
        "seed": SEED,
        "dataset_sha256": digest,
        "dataset": str(DATASET_PATH.relative_to(BASE_DIR)),
        "counts": {
            "total": len(samples),
            "by_dtc": dict(sorted(dtc_counts.items())),
            "by_severity": dict(sorted(severity_counts.items())),
            "negatives": sum(1 for s in samples if s["expected"]["abstain"]),
        },
        "label_schema": {
            "dtc_code": "SAE J2012 P0xxx or null for nominal cycles",
            "severity": "LOW | MEDIUM | HIGH | CRITICAL",
            "abstain": "true when the correct behavior is to report no critical anomaly",
        },
        "known_gaps": [
            "No F1 golden set yet: labeled F1 windows require expert review of real FastF1 slices.",
            "Images come from the same synthetic renderer family as the training data; treat visual scores as internal consistency, not real-world generality.",
            "Labels are derived from generated failure modes, not from physical cell measurements.",
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    logger.info("Wrote %d golden samples to %s", len(samples), DATASET_PATH)
    logger.info("Dataset sha256: %s", digest)
    return manifest


if __name__ == "__main__":
    build()
