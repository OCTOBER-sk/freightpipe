// ── Enums ──────────────────────────────────────────────────────────────────────

export enum JobStatus {
  QUEUED = "queued",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
  REVIEW_REQUIRED = "review_required",
}

export enum DocType {
  BILL_OF_LADING = "bill_of_lading",
  COMMERCIAL_INVOICE = "commercial_invoice",
  PACKING_LIST = "packing_list",
  CERTIFICATE_OF_ORIGIN = "certificate_of_origin",
  CUSTOMS_DECLARATION = "customs_declaration",
  DELIVERY_ORDER = "delivery_order",
  OTHER = "other",
}

export enum DiscrepancyFlag {
  MISMATCH = "mismatch",
  MISSING = "missing",
  EXTRA = "extra",
  FORMAT_ERROR = "format_error",
  LOW_CONFIDENCE = "low_confidence",
}

export enum ReviewReason {
  LOW_CONFIDENCE = "low_confidence",
  DISCREPANCY = "discrepancy",
  MISSING_FIELD = "missing_field",
  MANUAL_FLAG = "manual_flag",
}

// ── Field & Extraction ─────────────────────────────────────────────────────────

export interface ExtractedField {
  name: string;
  value: string;
  confidence: number;
  page: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
}

export interface Discrepancy {
  field: string;
  flag: DiscrepancyFlag;
  expected?: string;
  actual?: string;
  description: string;
}

export interface MatchResult {
  field: string;
  source_value: string;
  target_value: string;
  match: boolean;
  confidence: number;
}

// ── Document ───────────────────────────────────────────────────────────────────

export interface Document {
  id: string;
  job_id: string;
  filename: string;
  doc_type: DocType;
  confidence: number;
  page_count: number;
  fields: ExtractedField[];
  discrepancies: Discrepancy[];
  created_at: string;
}

// ── Job ────────────────────────────────────────────────────────────────────────

export interface Job {
  id: string;
  status: JobStatus;
  source_doc: Document | null;
  target_doc: Document | null;
  match_results: MatchResult[];
  overall_confidence: number;
  review_reasons: ReviewReason[];
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobSubmitRequest {
  source_file: File;
  target_file: File;
  source_doc_type?: DocType;
  target_doc_type?: DocType;
}

// ── Review Queue ───────────────────────────────────────────────────────────────

export interface ReviewItem {
  id: string;
  job_id: string;
  reason: ReviewReason;
  field: string | null;
  description: string;
  resolved: boolean;
  resolved_by: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface ReviewQueueResponse {
  items: ReviewItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ReviewResolveRequest {
  resolution: "accept_source" | "accept_target" | "manual_override";
  override_value?: string;
  notes?: string;
}

// ── Webhooks ───────────────────────────────────────────────────────────────────

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  secret: string;
  created_at: string;
  last_triggered_at: string | null;
  failure_count: number;
}

export interface WebhookCreateRequest {
  url: string;
  events: string[];
  active?: boolean;
}

// ── API Keys ───────────────────────────────────────────────────────────────────

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
}

export interface ApiKeyCreateRequest {
  name: string;
  expires_in_days?: number;
}

export interface ApiKeyCreateResponse {
  key: string;
  key_info: ApiKey;
}

// ── Analytics ──────────────────────────────────────────────────────────────────

export interface AnalyticsSummary {
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  review_required: number;
  avg_confidence: number;
  avg_processing_time_ms: number;
  doc_type_breakdown: Record<DocType, number>;
  discrepancy_rate: number;
}

export interface AnalyticsTimeSeries {
  date: string;
  jobs: number;
  avg_confidence: number;
  discrepancies: number;
}

export interface AnalyticsResponse {
  summary: AnalyticsSummary;
  time_series: AnalyticsTimeSeries[];
}

// ── Generic API ────────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string;
  status_code: number;
}
