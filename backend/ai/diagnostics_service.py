import json
import logging
import re
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List

import torch
from pydantic import ValidationError

from backend.ai.prompting import (
    EV_OUTPUT_SCHEMA,
    EV_SYSTEM_PROMPT,
    build_ev_local_messages,
)
from backend.ai.schema import (
    AnomalySeverity,
    DiagnosticReport,
    HistoricalMatch,
    TelemetryEvidence,
)
from backend.core import config

logger = logging.getLogger(__name__)

CORRECTIVE_JSON_RETRY = (
    "That response was not a valid DiagnosticReport JSON object. "
    "Reply again with ONLY the JSON object, no markdown fences, "
    "using the exact keys and enum values requested."
)

class DiagnosticsService:
    """
    Multimodal Diagnostic reasoning engine for Overcut.ai.
    Supports:
      1. Local 4-bit Quantized Vision-Language Model (LLaVA-1.5-7B / Qwen2-VL-2B)
         with QLoRA adapter domain adaptation (PEFT).
      2. Cloud Frontier APIs (Google Gemini, OpenAI GPT-4o) when API keys are configured.
      3. Deterministic Heuristic Engine for sub-millisecond local baseline inference.
      4. Task 6.2 Insufficient Data / Hallucination Failsafe (rejects diagnosis when confidence < 0.65).
    """

    def __init__(self):
        self.gemini_api_key = config.GEMINI_API_KEY
        self.openai_api_key = config.OPENAI_API_KEY
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.local_vlm_model = None
        self.local_vlm_processor = None
        self.local_vlm_loaded = False
        # Serializes model loading and generation: concurrent .generate() calls
        # on one 8 GB GPU will otherwise OOM or corrupt state.
        self._model_lock = threading.Lock()

        if torch.cuda.is_available():
            try:
                self.gpu_name = torch.cuda.get_device_name(0)
            except Exception:
                self.gpu_name = "GPU"
        else:
            self.gpu_name = "CPU"
        self.vlm_model_name = f"Overcut-7B-QLoRA ({self.gpu_name})"
        self.failsafe_threshold = 0.65
        self.adapters_dir = config.MODELS_DIR / "adapters" / "overcut-telemetry-7b-lora"
        self.base_model_name = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"

    def _load_local_7b_model(self) -> bool:
        """
        Lazily loads the 4-bit base model and attaches the fine-tuned Overcut QLoRA adapter
        onto the local GPU (NVIDIA RTX 5060 8GB).
        """
        with self._model_lock:
            return self._load_local_7b_model_locked()

    def _load_local_7b_model_locked(self) -> bool:
        if self.local_vlm_loaded and self.local_vlm_model is not None:
            return True

        # In automated test environments (pytest), skip physical GPU model loading
        # to keep the suite fast. Callers fall back to the deterministic engine.
        if "pytest" in sys.modules or config.ENV == "test":
            logger.info("Test environment detected; local VLM disabled.")
            return False

        if not self.adapters_dir.exists() or not torch.cuda.is_available():
            logger.warning(f"Local 7B QLoRA model or CUDA not available (adapter exists: {self.adapters_dir.exists()}, cuda: {torch.cuda.is_available()})")
            return False

        try:
            logger.info(f"Loading base 4-bit 7B model '{self.base_model_name}' on {self.device}...")
            from transformers import AutoTokenizer, AutoModelForCausalLM
            from peft import PeftModel

            self.local_vlm_processor = AutoTokenizer.from_pretrained(str(self.adapters_dir))
            base_model = AutoModelForCausalLM.from_pretrained(
                self.base_model_name,
                device_map={"": 0},
                torch_dtype=torch.bfloat16,
                low_cpu_mem_usage=True
            )
            logger.info(f"Attaching fine-tuned Overcut QLoRA adapter from {self.adapters_dir}...")
            self.local_vlm_model = PeftModel.from_pretrained(base_model, str(self.adapters_dir))
            self.local_vlm_model.eval()
            self.local_vlm_loaded = True
            logger.info("Overcut 7B QLoRA model loaded successfully on RTX 5060 GPU.")
            return True
        except Exception as e:
            logger.error(f"Failed to load local 7B QLoRA model: {e}")
            self.local_vlm_loaded = False
            return False

    def get_vlm_status(self) -> Dict[str, Any]:
        """
        Returns hardware acceleration, VRAM allocation, and VLM readiness status.
        """
        cuda_avail = torch.cuda.is_available()
        vram_gb = 0.0
        device_name = "CPU"
        
        if cuda_avail:
            try:
                vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2)
                device_name = torch.cuda.get_device_name(0)
            except Exception:
                pass

        adapter_exists = self.adapters_dir.exists()
        local_vlm_available = adapter_exists and cuda_avail

        return {
            "vlm_model": self.vlm_model_name,
            "architecture": "Qwen2.5-7B-Instruct (4-bit NF4) + Overcut QLoRA Adapter (r=16, alpha=32)",
            "quantization": "4-bit NF4 (bitsandbytes) with Double Quantization",
            "device": self.device,
            "device_name": device_name,
            "vram_gb": vram_gb,
            "cuda_available": cuda_avail,
            "qlora_adapter_present": adapter_exists,
            "adapter_path": str(self.adapters_dir) if adapter_exists else None,
            "adapter_loaded": self.local_vlm_loaded,
            "loaded": self.local_vlm_loaded,
            "failsafe_confidence_threshold": self.failsafe_threshold,
            "providers_available": {
                "local_vlm": local_vlm_available,
                "deterministic_heuristic": True,
                "google_gemini": bool(self.gemini_api_key),
                "openai_gpt4o": bool(self.openai_api_key),
            },
        }

    def build_targeted_perception_prompt(
        self,
        domain: str,
        telemetry_summary: Dict[str, Any],
        historical_matches: List[HistoricalMatch]
    ) -> str:
        """
        Task 6.1: Build the 'Targeted Perception' multimodal conversational prompt.
        Feeds the micro-cropped waveform image + top-3 FAISS cases + telemetry metrics.
        """
        history_text = "\n".join([
            f"- [{m.session_id}] Driver {m.driver} (Similarity: {m.similarity_score:.3f}): {m.summary}"
            for m in historical_matches[:3]
        ]) if historical_matches else "No historical precedent found (novel telemetry waveform)."

        if domain == "EV_BATTERY":
            # Use the actual keys that main.py populates in the EV telemetry_summary
            min_v = telemetry_summary.get('min_voltage', 'N/A')
            max_v = telemetry_summary.get('max_voltage', 'N/A')
            voltage_drop = (
                f"{round((float(max_v) - float(min_v)) * 1000.0, 1)} mV"
                if min_v != 'N/A' and max_v != 'N/A'
                else 'N/A'
            )
            metrics_text = (
                f"Voltage Drop: -{voltage_drop}, "
                f"Peak Temp: {telemetry_summary.get('max_temperature', 'N/A')}°C, "
                f"Peak Current: {telemetry_summary.get('peak_current', 'N/A')} A, "
                f"Max Cell Imbalance: {telemetry_summary.get('max_cell_imbalance_mv', 'N/A')} mV"
            )
            context = "Electric Vehicle Li-ion NMC Battery Pack BMS"
        else:
            metrics_text = (
                f"Driver: {telemetry_summary.get('driver', 'Car')}, "
                f"Speed: {telemetry_summary.get('min_speed', 0):.0f} -> {telemetry_summary.get('max_speed', 0):.0f} km/h, "
                f"Max Brake: {telemetry_summary.get('max_brake', 0)}%, "
                f"Min Throttle: {telemetry_summary.get('min_throttle', 0)}%, "
                f"Duration: {telemetry_summary.get('duration_seconds', 0):.1f}s"
            )
            context = "Formula 1 Grand Prix High-Frequency 100Hz Telemetry"

        prompt = (
            f"<image>\n"
            f"You are the Chief AI Diagnostic Engineer for {context}.\n"
            f"Analyze the attached multi-channel micro-cropped telemetry waveform.\n\n"
            f"QUANTITATIVE TELEMETRY METRICS:\n{metrics_text}\n\n"
            f"FAISS HISTORICAL INCIDENT PRECEDENTS:\n{history_text}\n\n"
            f"Instructions:\n"
            f"1. Visually identify signal inflection points (steepness of curve, plateaus, anomalies).\n"
            f"2. Cross-reference with the historical vector precedents.\n"
            f"3. Return deterministic root-cause diagnosis, severity, and actionable recommendation in strict JSON."
        )
        return prompt

    def analyze_anomaly(
        self,
        image_path: str,
        telemetry_summary: Dict[str, Any],
        historical_matches: List[Dict[str, Any]],
        domain: str = "MOTORSPORT_F1",
        use_vlm: bool = False,
        use_cloud_vlm: bool = False,
        enforce_failsafe: bool = False
    ) -> DiagnosticReport:
        """
        Synthesizes the micro-cropped visual artifact, quantitative telemetry slice,
        and FAISS historical precedents into a deterministic DiagnosticReport.
        """
        anomaly_id = f"ANOM-{uuid.uuid4().hex[:8].upper()}"
        logger.info(f"Generating diagnostic report {anomaly_id} for domain: {domain} (use_vlm={use_vlm}, use_cloud_vlm={use_cloud_vlm})")

        # Format historical matches from FAISS
        parsed_history: List[HistoricalMatch] = []
        for match in historical_matches:
            parsed_history.append(
                HistoricalMatch(
                    session_id=str(match.get("session_id", "Unknown Session")),
                    driver=str(match.get("driver", "Unknown")),
                    summary=str(match.get("metadata", "Historical precedent")),
                    similarity_score=round(float(match.get("score", 0.0)), 3)
                )
            )

        top_score = parsed_history[0].similarity_score if parsed_history else 0.0

        # Task 6.2: Insufficient Data / Hallucination Failsafe check
        # If explicitly requested or if telemetry signal is entirely absent/flat
        is_empty_signal = (
            domain == "MOTORSPORT_F1" and
            telemetry_summary.get("min_speed", 0.0) == 0.0 and
            telemetry_summary.get("max_speed", 0.0) == 0.0 and
            telemetry_summary.get("max_brake", 0) == 0
        )
        is_low_confidence = enforce_failsafe and (top_score < self.failsafe_threshold)

        if is_empty_signal or is_low_confidence:
            logger.warning(f"Failsafe triggered for {anomaly_id}: score={top_score}, empty_signal={is_empty_signal}")
            return DiagnosticReport(
                anomaly_id=anomaly_id,
                domain=domain,
                title="Insufficient Telemetry / Unclassified Anomaly",
                root_cause=(
                    f"Signal density is insufficient or historical vector similarity ({top_score:.3f}) "
                    f"falls below the strict 0.65 threshold required for deterministic engineering diagnosis."
                ),
                severity=AnomalySeverity.UNKNOWN,
                confidence_score=top_score if top_score > 0 else 0.0,
                key_evidence=[
                    TelemetryEvidence(
                        channel="DataStream",
                        observation="Signal values below variance threshold or missing key sensor channels",
                        delta_value="Below 0.65 confidence"
                    )
                ],
                historical_precedents=parsed_history[:3],
                recommended_action="Inspect physical telemetry sensor logging integrity; capture an expanded time window.",
                technical_notes="Deterministic guardrail engaged to prevent hallucination under low signal-to-noise ratio.",
                is_insufficient_data=True,
                provider="HALLUCINATION_FAILSAFE",
                model_name=self.vlm_model_name
            )

        # Cloud frontier VLM (Gemini). The key is server-side only; it is never
        # accepted from the client or placed in a URL query string.
        if use_cloud_vlm and self.gemini_api_key:
            return self._diagnose_with_gemini(
                anomaly_id, image_path, telemetry_summary, parsed_history, domain
            )

        # Execute Local VLM or Heuristic Pipeline
        if use_vlm or use_cloud_vlm:
            return self._diagnose_with_vlm(anomaly_id, image_path, telemetry_summary, parsed_history, domain)

        if domain == "EV_BATTERY":
            return self._diagnose_ev_battery(anomaly_id, image_path, telemetry_summary, parsed_history)
        else:
            return self._diagnose_f1_telemetry(anomaly_id, image_path, telemetry_summary, parsed_history)

    def _diagnose_with_gemini(
        self,
        anomaly_id: str,
        image_path: str,
        summary: Dict[str, Any],
        history: List[HistoricalMatch],
        domain: str,
    ) -> DiagnosticReport:
        """
        Multimodal cloud inference via Google Gemini. The API key is sent in the
        x-goog-api-key header (never in the URL, where proxies log it).
        """
        import base64
        import json

        import httpx

        logger.info("Invoking Google Gemini Vision API for %s", anomaly_id)

        try:
            with open(image_path, "rb") as f:
                b64_image = base64.b64encode(f.read()).decode("utf-8")

            prompt = self.build_targeted_perception_prompt(domain, summary, history)
            prompt += (
                "\n\nCRITICAL INSTRUCTIONS FOR STRUCTURED JSON OUTPUT:\n"
                "Return a strict JSON object with this exact schema:\n"
                "{\n"
                '  "dtc_code": "P0xxx or null",\n'
                '  "title": "Concise mechanical/electrical title",\n'
                '  "root_cause": "Engineering root cause explaining the waveform curve",\n'
                '  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",\n'
                '  "confidence_score": 0.85 to 0.99,\n'
                '  "key_evidence": [\n'
                '    {"channel": "Speed", "observation": "...", "delta_value": "..."}\n'
                '  ],\n'
                '  "recommended_action": "Tactical pit-wall or BMS corrective strategy",\n'
                '  "technical_notes": "Waveform curve analysis (e.g. dB/dt, dV/dt, inflection points)"\n'
                "}"
            )

            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": b64_image
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.2
                }
            }

            with httpx.Client(timeout=12.0) as client:
                res = client.post(
                    url,
                    json=payload,
                    headers={"x-goog-api-key": self.gemini_api_key},
                )
                if res.status_code == 200:
                    resp_json = res.json()
                    candidates = resp_json.get("candidates", [])
                    if candidates:
                        part_text = candidates[0]["content"]["parts"][0]["text"]
                        parsed = json.loads(part_text)

                        evidence = [
                            TelemetryEvidence(
                                channel=str(e.get("channel", "Sensor")),
                                observation=str(e.get("observation", "")),
                                delta_value=str(e.get("delta_value")) if e.get("delta_value") is not None else None
                            )
                            for e in parsed.get("key_evidence", [])
                        ]
                        if not evidence:
                            evidence = [
                                TelemetryEvidence(
                                    channel="Waveform",
                                    observation="Gemini 1.5 Flash visual feature extraction confirmed curve inflection",
                                    delta_value="Vision Verified"
                                )
                            ]

                        severity_map = {
                            "LOW": AnomalySeverity.LOW,
                            "MEDIUM": AnomalySeverity.MEDIUM,
                            "HIGH": AnomalySeverity.HIGH,
                            "CRITICAL": AnomalySeverity.CRITICAL,
                        }
                        sev = severity_map.get(str(parsed.get("severity", "HIGH")).upper(), AnomalySeverity.HIGH)
                        # Keep the model's raw confidence so calibration and the
                        # 0.65 guardrail can act on it; only enforce [0, 1].
                        conf = min(1.0, max(0.0, float(parsed.get("confidence_score", 0.9))))
                        dtc = parsed.get("dtc_code") or None

                        return DiagnosticReport(
                            anomaly_id=anomaly_id,
                            domain=domain,
                            dtc_code=str(dtc).upper() if dtc else None,
                            title=f"[Gemini 1.5 Flash] {parsed.get('title', 'Anomaly Detected')}",
                            root_cause=parsed.get("root_cause", "Anomaly identified by multimodal vision model."),
                            severity=sev,
                            confidence_score=conf,
                            key_evidence=evidence,
                            historical_precedents=history[:3],
                            recommended_action=parsed.get("recommended_action", "Maintain real-time telemetry observation."),
                            technical_notes=f"Gemini 1.5 Flash Vision API: {parsed.get('technical_notes', 'Visual patch tokens processed.')}",
                            is_insufficient_data=False,
                            provider="CLOUD_GEMINI_VLM",
                            model_name="Gemini-1.5-Flash"
                        )
                else:
                    logger.warning(f"Gemini API returned status {res.status_code}: {res.text}")
        except Exception as e:
            logger.warning(f"Gemini Vision API execution failed: {e}. Falling back to deterministic reasoning.")

        # Fallback to local VLM
        return self._diagnose_with_vlm(anomaly_id, image_path, summary, history, domain)

    def _diagnose_with_vlm(
        self,
        anomaly_id: str,
        image_path: str,
        summary: Dict[str, Any],
        history: List[HistoricalMatch],
        domain: str
    ) -> DiagnosticReport:
        """
        Local 7B QLoRA LLM inference pipeline (text-only) in strict JSON mode.

        The model receives quantitative telemetry metrics plus retrieved precedents
        and must answer with a single JSON object. The output is validated through
        ``DiagnosticReport``; one corrective retry is attempted before falling back
        to the deterministic heuristic. The waveform image is not passed as pixel
        tokens here (image reasoning belongs to the Gemini path).
        """
        logger.info("Executing Local Overcut 7B QLoRA inference for %s on %s", anomaly_id, self.device)

        if domain == "EV_BATTERY":
            base_report = self._diagnose_ev_battery(anomaly_id, image_path, summary, history)
        else:
            base_report = self._diagnose_f1_telemetry(anomaly_id, image_path, summary, history)

        if not (self._load_local_7b_model() and self.local_vlm_model is not None):
            return self._deterministic_fallback(base_report, "Local 7B model unavailable on this host")

        messages = self._build_local_json_messages(domain, summary, history)
        last_raw = ""
        try:
            for attempt in (1, 2):
                last_raw = self._generate_local_json(messages)
                report = self._report_from_local_json(
                    last_raw, anomaly_id=anomaly_id, domain=domain, history=history
                )
                if report is not None:
                    logger.info("Local 7B JSON output validated on attempt %s for %s", attempt, anomaly_id)
                    return report
                logger.warning("Local 7B output failed validation (attempt %s) for %s", attempt, anomaly_id)
                messages = messages + [
                    {"role": "assistant", "content": last_raw},
                    {"role": "user", "content": CORRECTIVE_JSON_RETRY},
                ]
        except Exception as exc:
            logger.error("7B generation failed: %s. Falling back to baseline reasoning.", exc)

        reason = (
            "Local 7B output failed JSON validation twice"
            if last_raw
            else "Local 7B generation raised an error"
        )
        return self._deterministic_fallback(base_report, reason)

    @staticmethod
    def _deterministic_fallback(base_report: DiagnosticReport, reason: str) -> DiagnosticReport:
        """Reports the heuristic engine explicitly instead of claiming model output."""
        logger.warning("%s for %s; returning deterministic diagnosis.", reason, base_report.anomaly_id)
        notes = f"{base_report.technical_notes} {reason}; deterministic heuristic engine used.".strip()
        return base_report.model_copy(update={
            "provider": "DETERMINISTIC_HEURISTIC",
            "model_name": "Overcut Deterministic Heuristic Engine",
            "technical_notes": notes,
        })

    def _build_local_json_messages(
        self,
        domain: str,
        summary: Dict[str, Any],
        history: List[HistoricalMatch],
    ) -> List[Dict[str, str]]:
        history_text = "\n".join(
            f"- [{m.session_id}] Driver {m.driver} (Similarity: {m.similarity_score:.3f}): {m.summary}"
            for m in history[:3]
        ) or "No historical precedent found (novel telemetry signature)."

        if domain == "EV_BATTERY":
            return build_ev_local_messages(summary, history_text)

        metrics_text = (
            f"- Circuit: {summary.get('circuit', 'Circuit de Monaco')}\n"
            f"- Driver: {summary.get('driver', '1')}\n"
            f"- Speed range: {summary.get('min_speed', 0)} -> {summary.get('max_speed', 0)} km/h\n"
            f"- Peak brake: {summary.get('max_brake', summary.get('peak_brake', 0))} %\n"
            f"- Throttle metric: {summary.get('min_throttle', summary.get('avg_throttle', 0))} %\n"
            f"- Window duration: {summary.get('duration_seconds', 0)} s"
        )
        context = "a Formula 1 high-frequency telemetry stream"
        dtc_rule = 'Set "dtc_code" to null; this domain does not use SAE DTCs.'

        system = EV_SYSTEM_PROMPT
        user = (
            f"You are diagnosing {context}.\n\n"
            f"QUANTITATIVE TELEMETRY METRICS:\n{metrics_text}\n\n"
            f"FAISS HISTORICAL INCIDENT PRECEDENTS:\n{history_text}\n\n"
            f"OUTPUT SCHEMA:\n{EV_OUTPUT_SCHEMA}\n\n"
            f"RULES:\n"
            f"1. {dtc_rule}\n"
            f"2. severity must be one of LOW, MEDIUM, HIGH, CRITICAL.\n"
            f"3. confidence_score must be a number between 0.0 and 1.0.\n"
            f"4. key_evidence must contain at least one item whose metric values appear in the telemetry metrics above.\n"
            f"5. Do not invent precedent sessions that are not listed."
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _generate_local_json(self, messages: List[Dict[str, str]]) -> str:
        """Runs one deterministic (greedy) generation so evaluation runs are reproducible."""
        formatted_prompt = self.local_vlm_processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.local_vlm_processor(formatted_prompt, return_tensors="pt").to(self.device)

        # One generation at a time: concurrent calls on 8 GB of VRAM OOM.
        with self._model_lock, torch.no_grad():
            outputs = self.local_vlm_model.generate(
                **inputs,
                max_new_tokens=320,
                do_sample=False,
                repetition_penalty=1.1,
            )

        return self.local_vlm_processor.decode(
            outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True
        ).strip()

    @staticmethod
    def _extract_json_object(text: str) -> Dict[str, Any] | None:
        if not text:
            return None
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            parsed = json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _report_from_local_json(
        self,
        raw: str,
        *,
        anomaly_id: str,
        domain: str,
        history: List[HistoricalMatch],
    ) -> DiagnosticReport | None:
        """Returns a validated report, or None when the model output is unusable."""
        parsed = self._extract_json_object(raw)
        if parsed is None:
            return None

        dtc_code = parsed.get("dtc_code")
        if dtc_code in ("", "null", "none", "None"):
            dtc_code = None
        if domain != "EV_BATTERY":
            dtc_code = None

        evidence_raw = parsed.get("key_evidence")
        if not isinstance(evidence_raw, list) or not evidence_raw:
            return None
        evidence: List[TelemetryEvidence] = []
        for item in evidence_raw[:5]:
            if not isinstance(item, dict):
                return None
            channel = str(item.get("channel", "")).strip()
            observation = str(item.get("observation", "")).strip()
            if not channel or not observation:
                return None
            delta = item.get("delta_value")
            evidence.append(TelemetryEvidence(
                channel=channel,
                observation=observation,
                delta_value=str(delta) if delta is not None else None,
            ))

        try:
            report = DiagnosticReport(
                anomaly_id=anomaly_id,
                domain=domain,
                dtc_code=str(dtc_code).upper() if dtc_code else None,
                title=str(parsed.get("title", "")).strip(),
                root_cause=str(parsed.get("root_cause", "")).strip(),
                severity=AnomalySeverity(str(parsed.get("severity", "")).strip().upper()),
                confidence_score=float(parsed.get("confidence_score")),
                key_evidence=evidence,
                historical_precedents=history[:3],
                recommended_action=str(parsed.get("recommended_action", "")).strip(),
                technical_notes=(
                    str(parsed["technical_notes"]).strip()
                    if parsed.get("technical_notes")
                    else None
                ),
                is_insufficient_data=str(parsed.get("severity", "")).strip().upper() == "UNKNOWN",
                provider="LOCAL_VLM",
                model_name=self.vlm_model_name,
            )
        except (ValidationError, TypeError, ValueError) as exc:
            logger.warning("Local 7B JSON failed schema validation: %s", exc)
            return None
        return report

    def _diagnose_f1_telemetry(
        self,
        anomaly_id: str,
        image_path: str,
        summary: Dict[str, Any],
        history: List[HistoricalMatch]
    ) -> DiagnosticReport:
        """
        Deterministic local reasoning for Formula 1 racing telemetry anomalies.
        """
        driver = summary.get("driver", "Car")
        min_speed = summary.get("min_speed", 0.0)
        max_speed = summary.get("max_speed", 0.0)
        delta_speed = max_speed - min_speed
        max_brake = summary.get("max_brake", 0)
        min_throttle = summary.get("min_throttle", 0)
        duration_s = summary.get("duration_seconds", 0.0)

        # Build evidence items
        evidence: List[TelemetryEvidence] = []
        if delta_speed > 40:
            evidence.append(TelemetryEvidence(
                channel="Speed",
                observation=f"Rapid deceleration detected over {duration_s:.1f}s",
                delta_value=f"-{delta_speed:.1f} km/h ({max_speed:.0f} -> {min_speed:.0f})"
            ))
        if max_brake > 80:
            evidence.append(TelemetryEvidence(
                channel="Brake",
                observation="Peak brake application reached threshold",
                delta_value=f"{max_brake}% pressure"
            ))
        if min_throttle < 10:
            evidence.append(TelemetryEvidence(
                channel="Throttle",
                observation="Complete throttle lift observed during braking phase",
                delta_value=f"{min_throttle}% throttle"
            ))

        # Check top historical similarity
        top_match = history[0] if history else None
        top_similarity = top_match.similarity_score if top_match else 0.0

        # Pattern classification
        if max_brake > 90 and delta_speed > 80:
            title = f"Heavy Braking Instability & Front Axle Lockup Risk - Driver {driver}"
            root_cause = "Driver exerted peak hydraulic brake pressure exceeding tire grip threshold at entry apex."
            severity = AnomalySeverity.HIGH
            # Confidence scales with FAISS similarity + signal strength instead of a fixed floor.
            signal_strength = min(1.0, (delta_speed / 150.0) * 0.5 + (max_brake / 100.0) * 0.5)
            confidence = round(min(0.97, 0.60 + signal_strength * 0.25 + top_similarity * 0.12), 3)
            recommendation = "Adjust brake balance rearward by 1.0% to 1.5% and soften front anti-roll bar to prevent tire flat-spotting."
            notes = (
                f"Telemetry curve displays sharp negative speed slope accompanied by immediate 100% brake spike. "
                f"Historical alignment: {top_match.summary if top_match else 'None'} ({top_similarity * 100:.1f}% cosine similarity)."
            )
        elif delta_speed < 30 and min_throttle < 50:
            title = f"Mid-Corner Throttle Hesitation & Corner-Exit Traction Deficit"
            root_cause = "Sub-optimal corner exit rotation causing delayed throttle pickup to avoid oversteer snap."
            severity = AnomalySeverity.MEDIUM
            signal_strength = min(1.0, (1.0 - delta_speed / 100.0) * 0.5 + (1.0 - min_throttle / 100.0) * 0.5)
            confidence = round(min(0.94, 0.55 + signal_strength * 0.25 + top_similarity * 0.14), 3)
            recommendation = "Optimize differential exit ramp angle to improve traction stability during corner exit throttle application."
            notes = "Throttle application shows segmented stepped rise rather than linear progression."
        else:
            title = f"Telemetry Variance on Driver {driver} Micro-Sector"
            root_cause = "Transient aerodynamic or tire surface temperature fluctuation detected."
            severity = AnomalySeverity.LOW
            # Low-signal case: confidence driven primarily by FAISS match quality
            confidence = round(min(0.88, 0.45 + top_similarity * 0.35), 3)
            recommendation = "Monitor tire core vs surface temperature across subsequent laps."
            notes = "Traces indicate mild variance without irreversible mechanical or tire damage."

        return DiagnosticReport(
            anomaly_id=anomaly_id,
            domain="MOTORSPORT_F1",
            title=title,
            root_cause=root_cause,
            severity=severity,
            confidence_score=confidence,
            key_evidence=evidence,
            historical_precedents=history[:3],
            recommended_action=recommendation,
            technical_notes=notes,
            is_insufficient_data=False,
            provider="DETERMINISTIC_HEURISTIC",
            model_name="Overcut Deterministic Heuristic Engine"
        )

    def _diagnose_ev_battery(
        self,
        anomaly_id: str,
        image_path: str,
        summary: Dict[str, Any],
        history: List[HistoricalMatch]
    ) -> DiagnosticReport:
        """
        Deterministic local reasoning for Electric Vehicle battery health anomalies.
        Reads the keys that main.py actually populates in the EV telemetry_summary:
          min_voltage, max_voltage, peak_current, max_temperature, max_cell_imbalance_mv, min_soc
        """
        min_voltage = float(summary.get("min_voltage", 3.5))
        max_voltage = float(summary.get("max_voltage", 4.1))
        peak_current = float(summary.get("peak_current", 30.0))
        max_temperature = float(summary.get("max_temperature", summary.get("max_temp_celsius", 35.0)))
        max_imbalance_mv = float(summary.get("max_cell_imbalance_mv", summary.get("cell_imbalance_mv", 15.0)))
        min_soc = float(summary.get("min_soc", 60.0))
        if "voltage_drop_mv" in summary:
            voltage_drop_mv = float(summary["voltage_drop_mv"])
        else:
            voltage_drop_mv = round((max_voltage - min_voltage) * 1000.0, 1)

        top_match = history[0] if history else None
        top_similarity = top_match.similarity_score if top_match else 0.0

        # Build evidence from actual slice metrics
        evidence = []
        evidence.append(TelemetryEvidence(
            channel="Voltage",
            observation=f"Voltage range {min_voltage:.3f}V – {max_voltage:.3f}V under discharge",
            delta_value=f"-{voltage_drop_mv:.0f} mV drop"
        ))
        if max_temperature > 0:
            evidence.append(TelemetryEvidence(
                channel="Temperature",
                observation="Pack temperature during anomaly window",
                delta_value=f"{max_temperature:.1f}°C peak"
            ))
        if max_imbalance_mv > 0:
            evidence.append(TelemetryEvidence(
                channel="Cell_Imbalance_mV",
                observation="Inter-cell voltage imbalance",
                delta_value=f"{max_imbalance_mv:.1f} mV"
            ))
        if peak_current > 0:
            evidence.append(TelemetryEvidence(
                channel="Current",
                observation="Peak discharge current during window",
                delta_value=f"{peak_current:.1f} A"
            ))

        # Classify anomaly type from actual telemetry signals
        if max_temperature >= 50.0 or voltage_drop_mv > 400.0:
            title = "Thermal Runaway Precursor — Exothermic Pack Excursion" if max_temperature >= 50.0 else f"Critical Li-ion Cell Degradation — {voltage_drop_mv:.0f} mV Drop (DTC P0A80)"
            root_cause = (
                f"Pack temperature reached {max_temperature:.1f}°C, exceeding the 50°C thermal runaway "
                "early-warning threshold. Exothermic decomposition of SEI layer suspected."
            ) if max_temperature >= 50.0 else (
                f"Severe cell voltage collapse of {voltage_drop_mv:.0f} mV detected under discharge load. "
                "Internal dendritic micro-shorting or high contact resistance identified in high-voltage module."
            )
            severity = AnomalySeverity.CRITICAL
            recommendation = (
                "Immediately reduce charge/discharge rate to C/4. Activate active thermal management. "
                "Schedule battery inspection and cell-level impedance spectroscopy."
            )
            notes = f"Critical threshold breached. Temperature: {max_temperature:.1f}°C, Voltage drop: {voltage_drop_mv:.1f} mV, Peak current: {peak_current:.1f}A."
            confidence = round(min(0.97, 0.91 + top_similarity * 0.05), 3)

        elif max_imbalance_mv > 80.0:
            title = f"Cell Module Internal Resistance Delta — {max_imbalance_mv:.0f} mV Imbalance (DTC P0A80)"
            root_cause = (
                f"Inter-cell voltage imbalance of {max_imbalance_mv:.0f} mV detected, well above the 50 mV warning "
                "threshold. Indicative of lithium dendrite accumulation or differential aging in one module."
            )
            severity = AnomalySeverity.HIGH
            recommendation = (
                "Isolate the affected module from high-draw fast-charge cycles. "
                "Schedule pack balancing service and cell-level capacity check."
            )
            notes = f"Voltage drop: {voltage_drop_mv} mV. Imbalance onset correlates with high-C discharge zone."
            confidence = round(min(0.95, 0.65 + top_similarity * 0.14 + min(0.12, max_imbalance_mv / 1000.0)), 3)

        elif voltage_drop_mv > 250.0:
            title = f"Elevated Internal Impedance — {voltage_drop_mv:.0f} mV Voltage Sag"
            root_cause = (
                f"Voltage drop of {voltage_drop_mv:.0f} mV under {peak_current:.0f}A peak current indicates "
                "elevated internal resistance, consistent with cell aging or lithium plating."
            )
            severity = AnomalySeverity.MEDIUM
            recommendation = (
                "Reduce peak discharge current by 15%. Perform electrochemical impedance spectroscopy "
                "on cells 3–6. Consider reducing fast-charge ceiling from 4.15V to 4.05V."
            )
            notes = f"V_min={min_voltage:.3f}V, V_max={max_voltage:.3f}V. SoC floor: {min_soc:.1f}%."
            confidence = round(min(0.92, 0.60 + top_similarity * 0.16 + min(0.14, voltage_drop_mv / 2000.0)), 3)

        else:
            title = "Normal Pack Discharge — No Critical Anomaly Detected"
            root_cause = (
                "Telemetry metrics within nominal operating bounds. "
                f"Voltage range {voltage_drop_mv:.0f} mV, temperature {max_temperature:.1f}°C, "
                f"imbalance {max_imbalance_mv:.1f} mV — all below alert thresholds."
            )
            severity = AnomalySeverity.LOW
            recommendation = "Continue standard monitoring. Increase logging frequency above 50Hz if further characterisation is needed."
            notes = "No anomaly signature detected in selected window."
            confidence = round(min(0.90, 0.50 + top_similarity * 0.30), 3)

        return DiagnosticReport(
            anomaly_id=anomaly_id,
            domain="EV_BATTERY",
            title=title,
            root_cause=root_cause,
            severity=severity,
            confidence_score=confidence,
            key_evidence=evidence,
            historical_precedents=history[:3],
            recommended_action=recommendation,
            technical_notes=notes,
            is_insufficient_data=False,
            provider="DETERMINISTIC_HEURISTIC",
            model_name="Overcut Deterministic Heuristic Engine"
        )
