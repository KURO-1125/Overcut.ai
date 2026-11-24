"""
Verification Inference Script for Fine-Tuned Overcut 7B QLoRA Adapter
Tests live diagnostic generation on NVIDIA GeForce RTX 5060 Laptop GPU.
"""

import time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

ADAPTER_DIR = "models/adapters/overcut-telemetry-7b-lora"
BASE_MODEL = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"

def main():
    print("=" * 70)
    print("  OVERCUT 7B QLoRA INFERENCE BENCHMARK (RTX 5060 8GB)")
    print("=" * 70)

    print("[1/3] Loading Base 4-Bit 7B Model...")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_DIR)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        device_map={"": 0},
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True
    )
    print(f"      Base model loaded in {time.time() - t0:.1f}s.")

    print("[2/3] Attaching Overcut Fine-Tuned LoRA Adapter...")
    t1 = time.time()
    model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
    model.eval()
    print(f"      Adapter attached in {time.time() - t1:.1f}s.")

    vram_alloc = torch.cuda.memory_allocated() / (1024 ** 2)
    print(f"      Inference VRAM Footprint: {vram_alloc:.1f} MB ({vram_alloc / 1024:.2f} GB / 8.0 GB)")

    prompt = (
        "Circuit: Circuit de Monaco\n"
        "Sector / Anomaly Zone: Turn 1 (Sainte Dévote)\n"
        "Session Lap: Q3 Pole Flyer\n"
        "Telemetry Crop Window: [3.40s - 5.80s]\n"
        "- Primary Car: #44 HAM (Ferrari SF-25)\n"
        "- Ghost Reference Car: #4 NOR (McLaren MCL39)\n"
        "- Kinematic Metrics:\n"
        "  * Entry Speed: 288 km/h -> 78 km/h\n"
        "  * Peak Brake Pressure: 100% (onset at 3.52s)\n"
        "  * Throttle Pickup: Delayed by 0.28s past apex\n"
        "  * Delta-T Swing: Lost 0.330s to ghost\n"
        "  * Apex Minimum Speed: 74 km/h vs Ghost 82 km/h\n\n"
        "Diagnose this telemetry anomaly window, identify primary root cause, kinematic loss mechanism, and recommended engineering countermeasure."
    )

    messages = [
        {"role": "system", "content": "You are Overcut.ai's Principal Telemetry Intelligence Engineer. Analyze the input high-frequency telemetry slice and provide a deterministic diagnostic breakdown."},
        {"role": "user", "content": prompt}
    ]

    print("\n[3/3] Generating Telemetry Anomaly Diagnosis...")
    formatted_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(formatted_prompt, return_tensors="pt").to(0)

    t_gen_start = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.2,
            top_p=0.9,
            repetition_penalty=1.1
        )
    gen_duration = time.time() - t_gen_start
    num_tokens = len(outputs[0]) - len(inputs["input_ids"][0])
    tokens_per_sec = num_tokens / max(gen_duration, 0.01)

    response_text = tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)

    print("\n" + "*" * 70)
    print("  MODEL GENERATION RESULT:")
    print("*" * 70)
    print(response_text)
    print("*" * 70)
    print(f"Generated {num_tokens} tokens in {gen_duration:.2f}s ({tokens_per_sec:.1f} tokens/sec).")
    print("=" * 70)

if __name__ == "__main__":
    main()

