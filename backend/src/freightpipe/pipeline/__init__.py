"""Pipeline stages — FreightPipe document processing pipeline."""
from freightpipe.pipeline.classify import classify_document, ClassificationResult
from freightpipe.pipeline.split import split_merged_pdf, SplitResult, PageSplit
from freightpipe.pipeline.extract import extract_document, ExtractionResult, ExtractedFieldValue
from freightpipe.pipeline.normalize import (
    normalize_date,
    normalize_money,
    normalize_weight,
    normalize_accessorial,
    normalize_extracted_fields,
)
from freightpipe.pipeline.validate import (
    validate_document,
    validate_job_documents,
    ValidationResult,
    ValidationIssue,
)
from freightpipe.pipeline.ingest import (
    create_job,
    validate_pdf,
    PDFValidationError,
    IdempotencyConflictError,
)
from freightpipe.pipeline.match import (
    match_shipment,
    MatchLineItem,
    has_discrepancies,
    match_results_to_dicts,
    MONEY_TOLERANCE,
)
from freightpipe.pipeline.confidence import (
    score_field_confidence,
    score_document_confidence,
    should_route_to_hitl,
    verify_field_with_llm,
    FieldConfidence,
    DocumentConfidence,
    HITLDecision,
    DOCUMENT_CONFIDENCE_THRESHOLD,
    FIELD_CONFIDENCE_THRESHOLD,
)
from freightpipe.pipeline.review import (
    ReviewItem,
    ResolutionResult,
    can_transition,
    transition_to_in_review,
    resolve_approved,
    resolve_corrected,
    resolve_escalated,
    classify_review_reason,
    build_field_corrections,
)

__all__ = [
    "classify_document",
    "ClassificationResult",
    "split_merged_pdf",
    "SplitResult",
    "PageSplit",
    "extract_document",
    "ExtractionResult",
    "ExtractedFieldValue",
    "normalize_date",
    "normalize_money",
    "normalize_weight",
    "normalize_accessorial",
    "normalize_extracted_fields",
    "validate_document",
    "validate_job_documents",
    "ValidationResult",
    "ValidationIssue",
    "create_job",
    "validate_pdf",
    "PDFValidationError",
    "IdempotencyConflictError",
    "match_shipment",
    "MatchLineItem",
    "has_discrepancies",
    "match_results_to_dicts",
    "MONEY_TOLERANCE",
    "score_field_confidence",
    "score_document_confidence",
    "should_route_to_hitl",
    "verify_field_with_llm",
    "FieldConfidence",
    "DocumentConfidence",
    "HITLDecision",
    "DOCUMENT_CONFIDENCE_THRESHOLD",
    "FIELD_CONFIDENCE_THRESHOLD",
    "ReviewItem",
    "ResolutionResult",
    "can_transition",
    "transition_to_in_review",
    "resolve_approved",
    "resolve_corrected",
    "resolve_escalated",
    "classify_review_reason",
    "build_field_corrections",
]
