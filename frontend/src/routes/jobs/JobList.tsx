import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { listJobs } from "@/api/jobs";
import { JobStatus, PROCESSING_STAGES } from "@/types/backend";
import type { JobListItem } from "@/types/backend";
import JobStatusPill from "@/components/JobStatusPill";
import styles from "./JobList.module.css";

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

function SkeletonRows({ count = 5 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={styles.skeletonRow}>
          <div className={styles.skeletonRail} />
          <div className={styles.skeletonBlock} style={{ width: `${60 + Math.random() * 30}%` }} />
          <div className={styles.skeletonBlock} style={{ width: "24px" }} />
          <div className={styles.skeletonBlock} style={{ width: "100px" }} />
          <div className={styles.skeletonBlock} style={{ width: "80px" }} />
          <div />
        </div>
      ))}
    </>
  );
}

export default function JobList() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [cursors, setCursors] = useState<string[]>([]);

  const statusParam = statusFilter === "processing" ? undefined : statusFilter ?? undefined;
  const currentCursor = cursors.length > 0 ? cursors[cursors.length - 1] : undefined;

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["jobs", statusFilter, currentCursor],
    queryFn: () =>
      listJobs({
        status: statusParam,
        limit: 50,
        cursor: currentCursor,
      }),
  });

  const handleFilterChange = useCallback((value: string | null) => {
    setStatusFilter(value);
    setCursors([]);
  }, []);

  const handleLoadMore = useCallback(() => {
    if (data?.next_cursor) {
      setCursors((prev) => [...prev, data.next_cursor!]);
    }
  }, [data?.next_cursor]);

  const handleGoBack = useCallback(() => {
    if (cursors.length > 0) {
      setCursors((prev) => prev.slice(0, -1));
    }
  }, [cursors.length]);

  const items = data?.items ?? [];
  const filteredItems =
    statusFilter === "processing"
      ? items.filter((item) => PROCESSING_STAGES.includes(item.status))
      : items;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Jobs</h1>
        <Link to="/jobs/new" className={styles.submitBtn}>
          + Submit document
        </Link>
      </div>

      <div className={styles.filters} role="tablist" aria-label="Filter jobs by status">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.label}
            type="button"
            className={styles.filterBtn}
            data-active={statusFilter === opt.value}
            onClick={() => handleFilterChange(opt.value)}
            role="tab"
            aria-selected={statusFilter === opt.value}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {error && (
        <div className={styles.errorBanner} role="alert">
          <span>Failed to load jobs. Please try again.</span>
          <button type="button" className={styles.retryBtn} onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      {isLoading ? (
        <div>
          <div className={styles.tableHeader}>
            <span />
            <span>Job</span>
            <span>Docs</span>
            <span>Status</span>
            <span>Submitted</span>
            <span />
          </div>
          <SkeletonRows />
        </div>
      ) : filteredItems.length === 0 && !error ? (
        <div className={styles.empty}>
          <p className={styles.emptyText}>
            No jobs yet. Submit your first document to get started.
          </p>
          <Link to="/jobs/new" className={styles.emptyCta}>
            + Submit document
          </Link>
        </div>
      ) : (
        <>
          <div className={styles.tableHeader}>
            <span />
            <span>Job</span>
            <span>Docs</span>
            <span>Status</span>
            <span>Submitted</span>
            <span />
          </div>
          {filteredItems.map((job: JobListItem) => (
            <Link
              key={job.job_id}
              to={
                job.status === JobStatus.COMPLETE
                  ? `/jobs/${job.job_id}/result`
                  : job.status === JobStatus.NEEDS_REVIEW
                    ? `/review-queue/${job.job_id}`
                    : `/jobs/${job.job_id}`
              }
              className={styles.row}
              aria-label={`Job ${job.job_id.slice(0, 8)}: ${job.document_count} documents, status ${job.status}, submitted ${formatRelativeTime(job.created_at)}`}
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
                {job.review_required && job.review_reasons.length > 0 && (
                  <span className={styles.reviewReason}>
                    {job.review_reasons[0]}
                  </span>
                )}
              </div>
              <span className={styles.submitted}>
                {formatRelativeTime(job.created_at)}
              </span>
              <div className={styles.actions}>
                {job.status === JobStatus.NEEDS_REVIEW && (
                  <span className={styles.reviewLink}>Review</span>
                )}
              </div>
            </Link>
          ))}

          {(data?.next_cursor || cursors.length > 0) && (
            <div className={styles.pagination}>
              {cursors.length > 0 && (
                <button
                  type="button"
                  className={styles.loadMore}
                  onClick={handleGoBack}
                >
                  Previous
                </button>
              )}
              {data?.next_cursor && (
                <button
                  type="button"
                  className={styles.loadMore}
                  onClick={handleLoadMore}
                >
                  Load more
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
