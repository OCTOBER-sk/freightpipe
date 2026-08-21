import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listJobs, submitDocument } from "@/api/jobs";
import { ApiClientError } from "@/api/client";
import { JobStatus, PROCESSING_STAGES } from "@/types/backend";
import type { JobListItem } from "@/types/backend";
import UploadZone from "@/components/UploadZone";
import JobStatusPill from "@/components/JobStatusPill";
import styles from "./Documents.module.css";

const FILTER_OPTIONS: { label: string; value: string | null }[] = [
  { label: "All", value: null },
  { label: "Queued", value: JobStatus.QUEUED },
  { label: "Processing", value: "processing" },
  { label: "Needs Review", value: JobStatus.NEEDS_REVIEW },
  { label: "Complete", value: JobStatus.COMPLETE },
  { label: "Failed", value: JobStatus.FAILED },
];

function getRailState(status: JobStatus): string {
  if (status === JobStatus.QUEUED) return "queued";
  if (PROCESSING_STAGES.includes(status)) return "processing";
  if (status === JobStatus.NEEDS_REVIEW) return "needs_review";
  if (status === JobStatus.COMPLETE) return "complete";
  if (status === JobStatus.FAILED) return "failed";
  if (status === JobStatus.NEEDS_LLM_CAPACITY) return "needs_llm_capacity";
  return "queued";
}

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.floor(hours / 24);
  return `${days} d ago`;
}

export default function Documents() {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["documents-list"],
    queryFn: () => listJobs({ limit: 100 }),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => submitDocument({ file }),
    onSuccess: (res) => {
      setSelectedFile(null);
      setUploadError(null);
      setUploadSuccess(`Document submitted. Job: ${res.job_id.slice(0, 12)}...`);
      queryClient.invalidateQueries({ queryKey: ["documents-list"] });
      setTimeout(() => setUploadSuccess(null), 5000);
    },
    onError: (err: Error) => {
      if (err instanceof ApiClientError) {
        if (err.error.code === "file_too_large") {
          setUploadError("File exceeds 25MB limit. Split it into separate documents.");
        } else if (err.error.code === "invalid_pdf") {
          setUploadError("Could not read this file as a PDF. Check it is not corrupted.");
        } else {
          setUploadError(err.error.message);
        }
      } else {
        setUploadError("Upload failed. The backend may be starting up.");
      }
    },
  });

  const handleFile = useCallback((file: File) => {
    setSelectedFile(file);
    setUploadError(null);
    setUploadSuccess(null);
  }, []);

  const handleSubmit = useCallback(() => {
    if (!selectedFile) return;
    setUploadError(null);
    uploadMutation.mutate(selectedFile);
  }, [selectedFile, uploadMutation]);

  const items = data?.items ?? [];
  const filteredItems =
    statusFilter === "processing"
      ? items.filter((item) => PROCESSING_STAGES.includes(item.status))
      : statusFilter
        ? items.filter((item) => item.status === statusFilter)
        : items;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Documents</h1>
      </div>

      <div className={styles.uploadSection}>
        <UploadZone onFileSelect={handleFile} />
        {selectedFile && (
          <div className={styles.uploadForm}>
            <span className={styles.fileName}>
              {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(1)} MB)
            </span>
            <div className={styles.uploadActions}>
              <button
                type="button"
                className={styles.submitBtn}
                onClick={handleSubmit}
                disabled={uploadMutation.isPending}
              >
                {uploadMutation.isPending ? "Submitting..." : "Submit Document"}
              </button>
              <button
                type="button"
                className={styles.clearBtn}
                onClick={() => setSelectedFile(null)}
                disabled={uploadMutation.isPending}
              >
                Clear
              </button>
            </div>
          </div>
        )}
        {uploadError && <div className={styles.errorBanner}>{uploadError}</div>}
        {uploadSuccess && <div className={styles.success}>{uploadSuccess}</div>}
      </div>

      <div className={styles.filters} role="tablist" aria-label="Filter documents by status">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.label}
            type="button"
            className={styles.filterBtn}
            data-active={statusFilter === opt.value}
            onClick={() => setStatusFilter(opt.value)}
            role="tab"
            aria-selected={statusFilter === opt.value}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {error && (
        <div className={styles.errorBanner} role="alert">
          <span>Failed to load documents. Please try again.</span>
          <button type="button" className={styles.retryBtn} onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      {isLoading ? (
        <div className={styles.loading}>Loading documents...</div>
      ) : filteredItems.length === 0 && !error ? (
        <div className={styles.empty}>
          <p className={styles.emptyText}>
            No documents yet. Upload your first PDF to get started.
          </p>
        </div>
      ) : (
        <>
          <div className={styles.tableHeader}>
            <span />
            <span>Job</span>
            <span>Docs</span>
            <span>Status</span>
            <span>Submitted</span>
          </div>
          {filteredItems.map((job: JobListItem) => (
            <Link
              key={job.job_id}
              to={
                job.status === JobStatus.COMPLETE
                  ? `/jobs/${job.job_id}/result`
                  : job.status === JobStatus.NEEDS_REVIEW
                    ? `/review-queue/${job.job_id}`
                    : `/documents`
              }
              className={styles.row}
              aria-label={`Job ${job.job_id.slice(0, 8)}: ${job.document_count} documents, status ${job.status}`}
            >
              <div className={styles.rail} data-state={getRailState(job.status)} />
              <span className={styles.jobId} data-mono>
                {job.job_id.slice(0, 12)}...
              </span>
              <span className={styles.docs} data-mono>
                {job.document_count > 0 ? job.document_count : "\u2014"}
              </span>
              <div className={styles.statusCell}>
                <JobStatusPill status={job.status} showStage={false} />
              </div>
              <span className={styles.submitted}>
                {formatRelativeTime(job.created_at)}
              </span>
            </Link>
          ))}
        </>
      )}
    </div>
  );
}
