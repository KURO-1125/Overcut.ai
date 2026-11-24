"""Runs the local QLoRA diagnostic tier over the golden set and saves predictions.

Every sample is rendered with the production prompt and schema
(``DiagnosticsService._build_local_json_messages``), decoded greedily with the
production settings, validated through ``DiagnosticReport`` with the same single
corrective retry, and recorded as the serialised report — or as the labelled
deterministic fallback when both attempts fail. The output file is directly
consumable by ``scripts/evaluate_qlora.py``.

Retrieval precedents are intentionally omitted (empty history) so the benchmark
isolates the adapter's reasoning over the labelled metrics instead of mixing in
the unlabelled contents of the FAISS index.

Usage:
    python scripts/run_golden_inference.py
    python scripts/run_golden_inference.py --limit 20 --batch-size 2

Decoding is batched for throughput; per-sample ``latency_s`` is the batch wall
time divided by the number of sequences in that batch.
"""

import argparse
import hashlib
import json
import logging
import time
from pathlib import Path

import torch

from backend.ai.diagnostics_service import CORRECTIVE_JSON_RETRY, DiagnosticsService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("golden_inference")

BASE_DIR = Path(__file__).resolve().parent.parent
GOLDEN_FILE = BASE_DIR / "data" / "eval" / "golden_ev_v1.json"
DEFAULT_OUTPUT = BASE_DIR / "models" / "ev_qlora_adapter" / "predictions.jsonl"

MAX_NEW_TOKENS = 320
BATCH_SIZE = 4


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_sha256(dataset: Path) -> str | None:
    manifest = dataset.with_suffix(".manifest.json")
    if not manifest.exists():
        return None
    return json.loads(manifest.read_text(encoding="utf-8")).get("dataset_sha256")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=GOLDEN_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--adapter", type=Path, default=None,
                        help="Adapter directory (default: the service's configured adapter)")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N samples")
    args = parser.parse_args()

    dataset = args.dataset.resolve()
    if not dataset.exists():
        raise SystemExit(f"Dataset not found: {dataset}")
    actual_sha = _sha256(dataset)
    manifest_sha = _manifest_sha256(dataset)
    if manifest_sha and manifest_sha != actual_sha:
        raise SystemExit(
            f"Dataset hash mismatch: manifest says {manifest_sha[:12]}, file is {actual_sha[:12]}."
        )

    samples = json.loads(dataset.read_text(encoding="utf-8"))
    if args.limit:
        samples = samples[: args.limit]
    logger.info("Running %d samples from %s", len(samples), dataset)

    service = DiagnosticsService()
    if args.adapter is not None:
        adapter = args.adapter.resolve()
        if not adapter.exists():
            raise SystemExit(f"Adapter directory not found: {adapter}")
        service.adapters_dir = adapter
        logger.info("Using adapter override: %s", adapter)
    if not service._load_local_7b_model():
        raise SystemExit(
            "Local 7B QLoRA model could not be loaded (adapter or CUDA unavailable). "
            "No predictions were generated."
        )

    tokenizer = service.local_vlm_processor
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    vram_gb = round(torch.cuda.max_memory_allocated() / 1024 ** 3, 2)
    logger.info("Model loaded on %s (resident weights: %.2f GB)", service.gpu_name, vram_gb)

    state = {}
    for sample in samples:
        state[sample["id"]] = {
            "sample": sample,
            "messages": service._build_local_json_messages(
                "EV_BATTERY", sample["input"]["metrics"], []
            ),
            "attempts": 0,
            "raw_first": None,
            "latency_s": 0.0,
        }

    output: Path = args.output.resolve()
    partial = output.with_suffix(".partial.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)

    pending = list(samples)
    written = 0
    retries = 0
    first_attempt_valid = 0
    provider_counts: dict[str, int] = {}
    started = time.time()

    with partial.open("w", encoding="utf-8") as sink:
        while pending:
            batch = pending[: args.batch_size]
            pending = pending[args.batch_size :]

            prompts = [
                tokenizer.apply_chat_template(
                    state[s["id"]]["messages"], tokenize=False, add_generation_prompt=True
                )
                for s in batch
            ]
            inputs = tokenizer(prompts, return_tensors="pt", padding=True).to(service.device)

            t0 = time.time()
            with service._model_lock, torch.no_grad():
                generated = service.local_vlm_model.generate(
                    **inputs,
                    max_new_tokens=MAX_NEW_TOKENS,
                    do_sample=False,
                    repetition_penalty=1.1,
                )
            wall = time.time() - t0
            new_tokens = generated[:, inputs["input_ids"].shape[1] :]
            texts = tokenizer.batch_decode(new_tokens, skip_special_tokens=True)

            for sample, raw in zip(batch, texts):
                entry = state[sample["id"]]
                entry["attempts"] += 1
                entry["latency_s"] += wall / len(batch)
                if entry["raw_first"] is None:
                    entry["raw_first"] = raw.strip()

                report = service._report_from_local_json(
                    raw, anomaly_id=sample["id"], domain="EV_BATTERY", history=[]
                )
                if report is None and entry["attempts"] < 2:
                    entry["messages"] = entry["messages"] + [
                        {"role": "assistant", "content": raw},
                        {"role": "user", "content": CORRECTIVE_JSON_RETRY},
                    ]
                    pending.append(sample)
                    retries += 1
                    logger.warning("%s: attempt %d invalid; queued corrective retry", sample["id"], entry["attempts"])
                    continue
                if report is None:
                    base = service._diagnose_ev_battery(
                        sample["id"], sample.get("image", ""), sample["input"]["metrics"], []
                    )
                    report = service._deterministic_fallback(
                        base, "Local 7B output failed JSON validation twice"
                    )
                else:
                    if entry["attempts"] == 1:
                        first_attempt_valid += 1

                provider_counts[report.provider] = provider_counts.get(report.provider, 0) + 1
                sink.write(
                    json.dumps(
                        {
                            "id": sample["id"],
                            "output": json.dumps(report.model_dump(mode="json"), ensure_ascii=False),
                            "provider": report.provider,
                            "attempts": entry["attempts"],
                            "latency_s": round(entry["latency_s"], 3),
                            "vram_gb": vram_gb,
                            "raw_first": entry["raw_first"],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                sink.flush()
                written += 1

            elapsed = time.time() - started
            logger.info(
                "batch complete: %d/%d samples | %.1fs wall (%.1fs/sample amortised) | %.1f min elapsed",
                written,
                len(samples),
                wall,
                wall / len(batch),
                elapsed / 60,
            )

    partial.replace(output)

    def rel(path: Path) -> str:
        return str(path.relative_to(BASE_DIR)) if path.is_relative_to(BASE_DIR) else str(path)

    meta = {
        "dataset": rel(dataset),
        "dataset_sha256": actual_sha,
        "manifest_sha256": manifest_sha,
        "samples": len(samples),
        "output": rel(output),
        "batch_size": args.batch_size,
        "max_new_tokens": MAX_NEW_TOKENS,
        "decoding": "greedy (do_sample=false, repetition_penalty=1.1)",
        "history": "none (retrieval excluded to isolate model reasoning)",
        "model_name": service.vlm_model_name,
        "adapter": rel(service.adapters_dir),
        "base_model": service.base_model_name,
        "gpu": service.gpu_name,
        "vram_gb": vram_gb,
        "wall_time_s": round(time.time() - started, 1),
        "first_attempt_valid": first_attempt_valid,
        "corrective_retries": retries,
        "provider_distribution": dict(sorted(provider_counts.items())),
    }
    meta_path = output.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    logger.info("Predictions written to %s", output)
    logger.info("Run metadata written to %s", meta_path)


if __name__ == "__main__":
    main()
