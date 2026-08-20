"""Pydantic models — mirrors BACKEND.md §3.1 exactly."""
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field

class JobStatus(str, Enum):
    QUEUED = "queued"
    CLASSIFYING = "classifying"
    SPLITTING = "splitting"
    EXTRACTING = "extracting"
    NORMALIZING = "normalizing"
    VALIDATING = "validating"
    MATCHING = "matching"
    SCORING = "scoring"
    NEEDS_REVIEW = "needs_review"
    COMPLETE = "complete"
    FAILED = "failed"
    NEEDS_LLM_CAPACITY = "needs_llm_capacity"

class DocType(str, Enum):
    RATE_CON = "rate_con"
    BOL = "bol"
    POD = "pod"
    INVOICE = "invoice"
    UNKNOWN = "unknown"

class DiscrepancyFlag(str, Enum):
    NONE = "none"
    RATE_DELTA = "rate_delta"
    MISSING_ACCESSORIAL = "missing_accessorial"
    EXTRA_ACCESSORIAL = "extra_accessorial"
    WEIGHT_VARIANCE = "weight_variance"
    PIECES_VARIANCE = "pieces_variance"

class ReviewReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    DISCREPANCY = "discrepancy"
    CLASSIFICATION_FAILED = "classification_failed"
    NEEDS_LLM_CAPACITY = "needs_llm_capacity"
    VALIDATION_FAILED = "validation_failed"

class ReviewState(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"

class Job(BaseModel):
    id: UUID
    account_id: UUID
    idempotency_key: str | None = None
    status: JobStatus = JobStatus.QUEUED
    source_r2_key: str
    shipment_id: UUID | None = None
    webhook_url: str | None = None
    error: dict | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

class Document(BaseModel):
    id: UUID
    job_id: UUID
    doc_type: DocType | None = None
    page_start: int
    page_end: int
    r2_key: str
    extraction_method: str | None = None
    raw_text: str | None = None
    classification_confidence: float | None = None
    created_at: datetime

class ExtractedField(BaseModel):
    id: UUID
    document_id: UUID
    field_name: str
    field_value: str | None = None
    confidence: float
    source_page: int | None = None
    source_bbox: dict | None = None
    extraction_method: str | None = None
    created_at: datetime

class MatchResult(BaseModel):
    id: UUID
    shipment_id: UUID
    line_item: str
    rate_con_value: str | None = None
    bol_pod_value: str | None = None
    invoice_value: str | None = None
    discrepancy_flag: DiscrepancyFlag = DiscrepancyFlag.NONE
    discrepancy_amount: float | None = None
    created_at: datetime

class ReviewQueueItem(BaseModel):
    id: UUID
    job_id: UUID
    reason: ReviewReason
    state: ReviewState = ReviewState.PENDING
    assigned_to: str | None = None
    resolution_notes: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
