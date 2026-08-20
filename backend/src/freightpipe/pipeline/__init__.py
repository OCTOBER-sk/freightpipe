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
    upload_to_r2,
    PDFValidationError,
    IdempotencyConflictError,
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
    "upload_to_r2",
    "PDFValidationError",
    "IdempotencyConflictError",
]
