import { apiGet, apiPost, apiFetch } from "./client";
import type { Job, JobListResponse, DocType } from "@/types/backend";

export function listJobs(page = 1, pageSize = 20): Promise<JobListResponse> {
  return apiGet<JobListResponse>(`/jobs?page=${page}&page_size=${pageSize}`);
}

export function getJob(jobId: string): Promise<Job> {
  return apiGet<Job>(`/jobs/${jobId}`);
}

export function submitJob(params: {
  sourceFile: File;
  targetFile: File;
  sourceDocType?: DocType;
  targetDocType?: DocType;
}): Promise<Job> {
  const formData = new FormData();
  formData.append("source_file", params.sourceFile);
  formData.append("target_file", params.targetFile);
  if (params.sourceDocType) formData.append("source_doc_type", params.sourceDocType);
  if (params.targetDocType) formData.append("target_doc_type", params.targetDocType);

  return apiPost<Job>("/jobs", formData);
}

export function deleteJob(jobId: string): Promise<void> {
  return apiFetch<void>(`/jobs/${jobId}`, { method: "DELETE" });
}
