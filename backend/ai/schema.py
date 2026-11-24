from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class AnomalySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"

class TelemetryEvidence(BaseModel):
    channel: str = Field(..., description="The telemetry channel (e.g., Speed, Brake, Throttle, Voltage)")
    observation: str = Field(..., description="Observed anomaly behavior on this channel")
    delta_value: Optional[str] = Field(None, description="Quantitative change or extreme value observed")

class HistoricalMatch(BaseModel):
    session_id: str
    driver: str
    summary: str
    similarity_score: float

class DiagnosticReport(BaseModel):
    anomaly_id: str = Field(..., description="Unique identifier for the diagnosed incident")
    domain: str = Field(default="MOTORSPORT_F1", description="Diagnostic domain: MOTORSPORT_F1 or EV_BATTERY")
    dtc_code: Optional[str] = Field(
        None,
        pattern=r"^P0[0-9A-F]{3}$",
        description="SAE J2012 diagnostic trouble code (EV battery domain only), e.g. P0A80",
    )
    title: str = Field(..., min_length=1, description="Concise editorial summary of the anomaly")
    root_cause: str = Field(..., min_length=1, description="Primary engineering or driver root cause")
    severity: AnomalySeverity = Field(..., description="Operational severity classification")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Unclamped model confidence score between 0.0 and 1.0")
    key_evidence: List[TelemetryEvidence] = Field(default_factory=list, description="Telemetry channel evidence citations")
    historical_precedents: List[HistoricalMatch] = Field(default_factory=list, description="Top historical matches from vector search")
    recommended_action: str = Field(..., min_length=1, description="Actionable strategy or engineering recommendation")
    technical_notes: Optional[str] = Field(None, description="Detailed domain analysis of the curve geometry")
    is_insufficient_data: bool = Field(default=False, description="Flag indicating insufficient telemetry or confidence below 0.65 threshold")
    provider: str = Field(default="DETERMINISTIC_HEURISTIC", description="Inference engine provider: LOCAL_VLM, CLOUD_GEMINI_VLM, DETERMINISTIC_HEURISTIC, or HALLUCINATION_FAILSAFE")
    model_name: Optional[str] = Field(default="Qwen2.5-7B-Instruct (4-bit QLoRA)", description="Name of the underlying reasoning model")
