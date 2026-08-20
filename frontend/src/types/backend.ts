// ── FreightPipe TypeScript types ─────────────────────────────────────────────
// Mirrors BACKEND.md §3.1 and §4.1 exactly.
// Every enum value is synced to the backend contract — compile-time drift = build error.

// ── Enums (BACKEND.md §3.1) ──────────────────────────────────────────────────

/** jobs.status — 12 values, §3.1 */
export enum JobStatus {
  QUEUED = "queued",
  CLASSIFYING = "classifying",
  SPLITTING = "splitting",
  EXTRACTING = "extracting",
  NORMALIZING = "normalizing",
  VALIDATING = "validating",
  MATCHING = "matching",
  SCORING = "scoring",
  NEEDS_REVIEW = "needs_review",
  COMPLETE = "complete",
  FAILED = "failed",
  NEEDS_LLM_CAPACITY = "needs_llm_capacity",
}

/** Mid-pipeline stages that collapse to "Processing" in the UI (§2.4) */
export const PROCESSING_STAGES: readonly JobStatus[] = [
  JobStatus.CLASSIFYING,
  JobStatus.SPLITTING,
  JobStatus.EXTRACTING,
  JobStatus.NORMALIZING,
  JobStatus.VALIDATING,
  JobStatus.MATCHING,
  JobStatus.SCORING,
] as const;

/** Terminal statuses — polling stops (§6) */
export const TERMINAL_STATUSES: readonly JobStatus[] = [
  JobStatus.COMPLETE,
  JobStatus.FAILED,
  JobStatus.NEEDS_REVIEW,
  JobStatus.NEEDS_LLM_CAPACITY,
] as const;

/** documents.doc_type — 5 values, §3.1 */
export enum DocType {
  RATE_CON = "rate_con",
  BOL = "bol",
  POD = "pod",
  INVOICE = "invoice",
  UNKNOWN = "unknown",
}

/** match_results.discrepancy_flag — 6 values, §3.1 */
export enum DiscrepancyFlag {
  NONE = "none",
  RATE_DELTA = "rate_delta",
  MISSING_ACCESSORIAL = "missing_accessorial",
  EXTRA_ACCESSORIAL = "extra_accessorial",
  WEIGHT_VARIANCE = "weight_variance",
  PIECES_VARIANCE = "pieces_variance",
}

/** review_queue.reason — 5 values, §3.1 */
export enum ReviewReason {
  LOW_CONFIDENCE = "low_confidence",
  DISCREPANCY = "discrepancy",
  CLASSIFICATION_FAILED = "classification_failed",
  NEEDS_LLM_CAPACITY = "needs_llm_capacity",
  VALIDATION_FAILED = "validation_failed",
}

/** review_queue.state — 4 values, §3.1 */
export enum ReviewState {
  PENDING = "pending",
  IN_REVIEW = "in_review",
  RESOLVED = "resolved",
  ESCALATED = "escalated",
}

/** extracted_fields.extraction_method — 4 values, §3.1 */
export enum ExtractionMethod {
  RULE = "rule",
  LLM_TEXT = "llm_text",
  LLM_VISION = "llm_vision",
  OCR = "ocr",
}

/** documents.extraction_method — document-level, §3.1 */
export enum DocExtractionMethod {
  TEXT = "text",
  OCR_TESSERACT = "ocr_tesseract",
  VISION_LLM = "vision_llm",
}

/** Webhook delivery status (§4.2) */
export enum WebhookStatus {
  DELIVERED = "delivered",
  PENDING = "pending",
  WEBHOOK_DELIVERY_FAILED = "webhook_delivery_failed",
}

/** Error codes (§4.3) */
export type ErrorCode =
  | "invalid_pdf"
  | "file_too_large"
  | "unauthorized"
  | "rate_limited"
  | "job_not_found"
  | "job_not_complete"
  | "idempotency_conflict"
  | "internal_error"
  | "llm_capacity_exhausted";

// ── Field & Extraction (§3.1 schema) ────────────────────────────────────────

/** Source bounding box — [x, y, w, h] in PDF points (§3.1) */
export type BBox = [number, number, number, number];

/** Source location for an extracted field */
export interface FieldSource {
  page: number;
  bbox: BBox;
}

/** Money type (§3.2 canonical schema) */
export interface Money {
  amount: number;
  currency: string;
}

/** A single extracted field value with confidence and source coordinates */
export interface ExtractedFieldValue {
  value: string | Money | null;
  confidence: number;
  source: FieldSource;
  extraction_method?: ExtractionMethod;
}

// ── Document (§3.1 documents table + §4.1 GET /result) ──────────────────────

/** Document summary (from GET /v1/jobs/{id}) */
export interface DocumentSummary {
  document_id: string;
  doc_type: DocType;
  page_start: number;
  page_end: number;
}

/** Document with full extracted fields (from GET /v1/jobs/{id}/result) */
export interface DocumentResult {
  document_id: string;
  doc_type: DocType;
  fields: Record<string, ExtractedFieldValue>;
  document_confidence: number;
}

// ── Match Results (§3.1 match_results table) ────────────────────────────────

export interface MatchResult {
  line_item: string;
  rate_con_value: string | null;
  bol_pod_value: string | null;
  invoice_value: string | null;
  discrepancy_flag: DiscrepancyFlag;
  discrepancy_amount?: number | null;
}

// ── Job (§3.1 jobs table + §4.1 endpoints) ──────────────────────────────────

/** Job list item (from GET /v1/jobs) */
export interface JobListItem {
  job_id: string;
  status: JobStatus;
  shipment_id: string | null;
  document_count: number;
  review_required: boolean;
  review_reasons: string[];
  created_at: string;
  completed_at: string | null;
}

/** Job detail (from GET /v1/jobs/{id}) */
export interface JobDetail {
  job_id: string;
  status: JobStatus;
  shipment_id: string | null;
  documents: DocumentSummary[];
  created_at: string;
  completed_at: string | null;
  webhook_status?: WebhookStatus;
  error?: ErrorEnvelope;
}

/** Job result (from GET /v1/jobs/{id}/result) */
export interface JobResult {
  job_id: string;
  shipment_id: string;
  documents: DocumentResult[];
  match_results: MatchResult[];
  review_required: boolean;
  review_reasons: string[];
}

/** Paginated job list response */
export interface JobListResponse {
  items: JobListItem[];
  next_cursor: string | null;
}

/** POST /v1/documents 202 response */
export interface JobSubmitResponse {
  job_id: string;
  status: JobStatus;
  created_at: string;
  idempotent_replay?: boolean;
}

// ── Review Queue (§3.1 review_queue table + §4.1) ───────────────────────────

/** Review queue item */
export interface ReviewItem {
  id: string;
  job_id: string;
  reason: ReviewReason;
  state: ReviewState;
  assigned_to: string | null;
  resolution_notes: string | null;
  created_at: string;
  resolved_at: string | null;
}

/** Paginated review queue response */
export interface ReviewQueueResponse {
  items: ReviewItem[];
  next_cursor: string | null;
}

/** POST /v1/review-queue/{id}/resolve request (§4.1) */
export interface ReviewResolveRequest {
  resolution: "approved" | "corrected" | "escalated";
  corrected_fields?: Record<string, unknown>;
  notes?: string;
}

// ── API Keys (§3.1 api_keys table + §4.1) ───────────────────────────────────

/** API key list item (key is masked — key_prefix only) */
export interface ApiKeyItem {
  id: string;
  label: string;
  key_prefix: string;
  created_at: string;
  revoked_at: string | null;
}

/** POST /v1/api-keys 201 response — raw key shown once */
export interface ApiKeyCreateResponse {
  id: string;
  label: string;
  key: string;
  created_at: string;
}

/** Paginated API keys response */
export interface ApiKeyListResponse {
  items: ApiKeyItem[];
}

/** DELETE /v1/api-keys/{id} response */
export interface ApiKeyRevokeResponse {
  id: string;
  revoked_at: string;
}

// ── Webhooks / Settings (§4.1) ──────────────────────────────────────────────

/** Account-level webhook config (GET /v1/settings/webhook) */
export interface WebhookConfig {
  webhook_url: string;
  webhook_secret: string;
  updated_at: string;
}

/** PUT /v1/settings/webhook request */
export interface WebhookConfigUpdate {
  webhook_url: string;
}

/** POST /v1/webhooks/test response */
export interface WebhookTestResponse {
  delivered: boolean;
  status_code?: number;
  error?: string;
}

// ── Analytics (§4.1 GET /v1/analytics/usage) ────────────────────────────────

export interface AnalyticsUsageResponse {
  period: string;
  jobs: {
    total: number;
    completed: number;
    needs_review: number;
    failed: number;
  };
  documents: {
    total: number;
    by_type: Record<string, number>;
  };
  accuracy: {
    avg_confidence: number;
    review_rate: number;
    correction_rate: number;
  };
  processing_time: {
    p50_seconds: number;
    p90_seconds: number;
    p99_seconds: number;
  };
  llm_usage: {
    total_calls: number;
    cache_hit_rate: number;
    by_provider: Record<string, number>;
  };
}

// ── Error Envelope (§4.3) ───────────────────────────────────────────────────

export interface ErrorEnvelope {
  code: ErrorCode;
  message: string;
  request_id: string;
}

// ── Health (§4.1 GET /v1/health) ────────────────────────────────────────────

export interface HealthResponse {
  worker: "ok";
  processor: "ok" | "cold_starting" | "unreachable";
}
