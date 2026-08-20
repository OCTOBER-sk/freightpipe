// Jobs API — BACKEND.md §4.1
import { apiGet, apiPost, apiFetch } from "./client";
import type {
  JobListResponse,
  JobDetail,
  JobResult,
  JobSubmitResponse,
} from "@/types/backend";

/**
 * GET /v1/jobs — list jobs (paginated, cursor-based)
 * §4.1: query params status, limit (default 50, max 200), cursor
 */
export function listJobs(params?: {
  status?: string;
  limit?: number;
  cursor?: string;
}): Promise<JobListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.cursor) searchParams.set("cursor", params.cursor);
  const qs = searchParams.toString();
  return apiGet<JobListResponse>(`/jobs${qs ? `?${qs}` : ""}`);
}

/**
 * GET /v1/jobs/{job_id} — poll job status
 * §4.1: returns job_id, status, shipment_id, documents[], created_at, completed_at
 */
export function getJob(jobId: string): Promise<JobDetail> {
  return apiGet<JobDetail>(`/jobs/${jobId}`);
}

/**
 * GET /v1/jobs/{job_id}/result — full structured output
 * §4.1: only meaningful once status is complete or needs_review
 * Returns 409 if job not yet complete
 */
export function getJobResult(jobId: string): Promise<JobResult> {
  return apiGet<JobResult>(`/jobs/${jobId}/result`);
}

/**
 * POST /v1/documents — submit a document for processing (async)
 * §4.1: multipart/form-data with file (PDF), optional webhook_url
 * Optional Idempotency-Key header
 * Returns 202 Accepted
 */
export function submitDocument(params: {
  file: File;
  webhookUrl?: string;
  idempotencyKey?: string;
}): Promise<JobSubmitResponse> {
  const formData = new FormData();
  formData.append("file", params.file);
  if (params.webhookUrl) formData.append("webhook_url", params.webhookUrl);

  const headers: Record<string, string> = {};
  if (params.idempotencyKey) {
    headers["Idempotency-Key"] = params.idempotencyKey;
  }

  return apiPost<JobSubmitResponse>("/documents", formData, headers);
}

/**
 * GET /v1/documents/{document_id}/pdf — get signed URL for original PDF
 * §4.1: returns signed R2 URL, valid for 5 minutes (300s)
 */
export function getDocumentPdfUrl(documentId: string): Promise<{ url: string; expires_in: number }> {
  return apiGet<{ url: string; expires_in: number }>(`/documents/${documentId}/pdf`);
}

/**
 * GET /v1/health — unauthenticated liveness check
 * §4.1
 */
export function getHealth(): Promise<{ worker: string; processor: string }> {
  return apiFetch<{ worker: string; processor: string }>("/health", {
    method: "GET",
    headers: { "Accept": "application/json" },
  });
}
