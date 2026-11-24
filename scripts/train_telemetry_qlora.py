"""
Overcut.ai 4-bit QLoRA Telemetry Fine-Tuning Pipeline
Specifically tailored for 8GB VRAM (NVIDIA RTX 5060 Laptop GPU).
Directly tests 7B model fine-tuning with NF4 quantization, double quantization,
and paged 8-bit AdamW optimizer.
"""

import os
import sys
import time
import json
import argparse
import traceback

def get_vram_usage():
    import torch
    if not torch.cuda.is_available():
        return "CUDA Unavailable"
    allocated = torch.cuda.memory_allocated() / (1024 ** 2)
    reserved = torch.cuda.memory_reserved() / (1024 ** 2)
    max_alloc = torch.cuda.max_memory_allocated() / (1024 ** 2)
    return f"Allocated: {allocated:.1f} MB | Reserved: {reserved:.1f} MB | Peak: {max_alloc:.1f} MB"

def main():
    parser = argparse.ArgumentParser(description="Overcut 7B QLoRA Fine-Tuning Pipeline")
    parser.add_argument("--model_name", type=str, default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit", help="HuggingFace 7B model ID")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs")
    parser.add_argument("--max_seq_len", type=int, default=512, help="Context token length")
    parser.add_argument("--batch_size", type=int, default=1, help="Per-device batch size (keep 1 for 8GB VRAM)")
    parser.add_argument("--grad_accum", type=int, default=8, help="Gradient accumulation steps")
    parser.add_argument("--lr", type=float, default=2e-4, help="Peak learning rate")
    parser.add_argument("--output_dir", type=str, default="models/adapters/overcut-telemetry-7b-lora", help="Adapter destination")
    parser.add_argument("--max_steps", type=int, default=10, help="Number of training optimization steps for verification")
    args = parser.parse_args()

    print("=" * 78)
    print("  OVERCUT.AI 7B QLoRA TELEMETRY FINE-TUNING BENCHMARK")
    print("=" * 78)

    import torch
    if not torch.cuda.is_available():
        print("[ERROR] CUDA is not available to PyTorch. Please verify CUDA PyTorch installation.")
        sys.exit(1)

    gpu_name = torch.cuda.get_device_name(0)
    total_vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 2)
    print(f"[HARDWARE] GPU: {gpu_name}")
    print(f"[HARDWARE] Total VRAM: {total_vram_mb:.0f} MB ({total_vram_mb / 1024:.2f} GB)")
    print(f"[HARDWARE] PyTorch CUDA Version: {torch.version.cuda}")
    print(f"[BENCHMARK] Target Model: {args.model_name} (7 Billion Parameters)")
    print(f"[MEMORY] Initial State: {get_vram_usage()}")
    print("-" * 78)

    # 1. Verify Dataset
    train_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fine_tuning", "telemetry_anomalies_train.jsonl")
    if not os.path.exists(train_file):
        print(f"[DATASET] Generating training dataset at {train_file}...")
        from generate_telemetry_dataset import generate_synthetic_variations
        generate_synthetic_variations()

    with open(train_file, "r", encoding="utf-8") as f:
        samples = [json.loads(line) for line in f]
    print(f"[DATASET] Loaded {len(samples)} instruction-tuning telemetry samples.")

    # 2. Configure 4-bit NormalFloat (NF4) Quantization
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    print("\n[STEP 1/4] Configuring 4-Bit NF4 Quantization & Memory Offloading...")
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    print(f"           - Compute Dtype: {compute_dtype}")
    print("           - Double Quantization (bnb_4bit_use_double_quant): True")
    print("           - Quant Type: NormalFloat4 (nf4)")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True
    )

    try:
        print(f"\n[STEP 2/4] Loading Tokenizer & 7B Base Weights from HuggingFace ({args.model_name})...")
        t0 = time.time()
        tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        is_pre_quantized = "bnb-4bit" in args.model_name or "4bit" in args.model_name.lower()
        if is_pre_quantized:
            model = AutoModelForCausalLM.from_pretrained(
                args.model_name,
                device_map={"": 0},
                torch_dtype=compute_dtype,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
        else:
            model = AutoModelForCausalLM.from_pretrained(
                args.model_name,
                quantization_config=bnb_config,
                device_map={"": 0},
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
        load_sec = time.time() - t0
        print(f"           Model loaded in {load_sec:.1f}s.")
        print(f"           VRAM after 4-bit model load: {get_vram_usage()}")

    except torch.cuda.OutOfMemoryError as oom:
        print("\n" + "!" * 78)
        print("  [7B FAILED: CUDA OUT OF MEMORY DURING INITIAL MODEL LOAD]")
        print("!" * 78)
        print(f"Peak VRAM reached: {torch.cuda.max_memory_allocated() / (1024**2):.1f} MB / {total_vram_mb:.0f} MB")
        print("The 7B base weights + quantization buffers could not fit in the 8GB VRAM envelope.")
        print("As instructed: 7B model is ABANDONED. Ready to transition to 2B model.")
        sys.exit(2)
    except Exception as e:
        print(f"[ERROR] Failed to load 7B base model: {e}")
        traceback.print_exc()
        sys.exit(1)

    # 3. Configure LoRA Adapter
    print("\n[STEP 3/4] Preparing Model for K-Bit Training & Attaching LoRA Adapters...")
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    print(f"           VRAM after attaching LoRA: {get_vram_usage()}")

    # 4. Tokenize Dataset
    print("\n[STEP 4/4] Formatting Telemetry ChatML Prompts...")
    tokenized_inputs = []
    for s in samples:
        text = tokenizer.apply_chat_template(s["messages"], tokenize=False, add_generation_prompt=False)
        enc = tokenizer(text, max_length=args.max_seq_len, truncation=True, padding="max_length", return_tensors="pt")
        input_ids = enc["input_ids"].to(0)
        attention_mask = enc["attention_mask"].to(0)
        labels = input_ids.clone()
        labels[labels == tokenizer.pad_token_id] = -100
        tokenized_inputs.append((input_ids, attention_mask, labels))

    print(f"           Ready with {len(tokenized_inputs)} tokenized sequences (seq_len={args.max_seq_len}).")

    # 5. Optimizer & Execution
    print("\n" + "=" * 78)
    print("  LAUNCHING 7B QLoRA TRAINING ON NVIDIA RTX 5060 (8GB)")
    print(f"  Configuration: batch_size={args.batch_size}, grad_accum={args.grad_accum}, lr={args.lr}")
    print("=" * 78)

    import bitsandbytes as bnb
    optimizer = bnb.optim.PagedAdamW8bit(model.parameters(), lr=args.lr)

    model.train()
    step = 0
    total_loss = 0.0
    start_train_time = time.time()

    try:
        for epoch in range(args.epochs):
            print(f"\n--- Epoch {epoch + 1}/{args.epochs} ---")
            for i, (input_ids, attention_mask, labels) in enumerate(tokenized_inputs):
                outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                loss = outputs.loss / args.grad_accum
                loss.backward()

                total_loss += loss.item() * args.grad_accum

                if (i + 1) % args.grad_accum == 0 or (i + 1) == len(tokenized_inputs):
                    optimizer.step()
                    optimizer.zero_grad()
                    step += 1
                    current_vram = get_vram_usage()
                    print(f"  Step {step:02d} | Sample {i+1:02d}/{len(tokenized_inputs)} | Loss: {loss.item() * args.grad_accum:.4f} | {current_vram}")

                    if step >= args.max_steps:
                        print(f"\n[BENCHMARK] Completed {args.max_steps} optimization steps successfully!")
                        break

            if step >= args.max_steps:
                break

        train_duration = time.time() - start_train_time
        peak_vram_mb = torch.cuda.max_memory_allocated() / (1024 ** 2)
        print("\n" + "*" * 78)
        print("  [SUCCESS] 7B MODEL COMPLETED TRAINING WITHOUT OUT-OF-MEMORY!")
        print("*" * 78)
        print(f"  - Total Training Duration: {train_duration:.2f} seconds")
        print(f"  - Peak VRAM Consumption:   {peak_vram_mb:.1f} MB ({peak_vram_mb / 1024:.2f} GB / {total_vram_mb / 1024:.2f} GB)")
        print(f"  - Headroom Remaining:      {(total_vram_mb - peak_vram_mb):.1f} MB ({(total_vram_mb - peak_vram_mb) / 1024:.2f} GB)")
        print(f"  - Average Loss:            {total_loss / max(1, step):.4f}")

        os.makedirs(args.output_dir, exist_ok=True)
        model.save_pretrained(args.output_dir)
        tokenizer.save_pretrained(args.output_dir)
        print(f"  - LoRA Adapter Saved To:   {args.output_dir}")
        print("*" * 78)

    except torch.cuda.OutOfMemoryError as oom:
        print("\n" + "!" * 78)
        print("  [7B FAILED: CUDA OUT OF MEMORY DURING BACKWARD PASS]")
        print("!" * 78)
        peak_mb = torch.cuda.max_memory_allocated() / (1024 ** 2)
        print(f"Peak VRAM reached: {peak_mb:.1f} MB / {total_vram_mb:.0f} MB ({peak_mb / 1024:.2f} GB / 8.0 GB)")
        print("Activation cache or optimizer state spiked beyond the 8GB physical memory limit.")
        print("-" * 78)
        print(">>> AS INSTRUCTED: The 7B model has failed. We will ABANDON IT and proceed to the 2B model.")
        print("-" * 78)
        sys.exit(2)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error during training: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
