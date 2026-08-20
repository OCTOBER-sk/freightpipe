import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { listReviewItems } from "@/api/reviewQueue";
import { ReviewReason } from "@/types/backend";
import type { ReviewItem } from "@/types/backend";
import styles from "./ReviewQueueList.module.css";

const REASON_OPTIONS: { label: string; value: string | null }[] = [
  { label: "All reasons", value: null },
  { label: "Low confidence", value: ReviewReason.LOW_CONFIDENCE },
  { label: "Discrepancy", value: ReviewReason.DISCREPANCY },
  { label: "Classification failed", value: ReviewReason.CLASSIFICATION_FAILED },
  { label: "Capacity limited", value: ReviewReason.NEEDS_LLM_CAPACITY },
  { label: "Validation failed", value: ReviewReason.VALIDATION_FAILED },
];

const REASON_LABELS: Record<ReviewReason, string> = {
  [ReviewReason.LOW_CONFIDENCE]: "Low confidence",
  [ReviewReason.DISCREPANCY]: "Discrepancy",
  [ReviewReason.CLASSIFICATION_FAILED]: "Classification failed",
  [ReviewReason.NEEDS_LLM_CAPACITY]: "Capacity limited",
  [ReviewReason.VALIDATION_FAILED]: "Validation failed",
};

function formatAge(createdAt: string): string {
  const diff = Date.now() - new Date(createdAt).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr`;
  const days = Math.floor(hours / 24);
  return `${days} d`;
}

function SkeletonRows({ count = 5 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={styles.skeletonRow}>
          <div className={styles.skeletonRail} />
          <div className={styles.skeletonBlock} style={{ width: `${50 + Math.random() * 40}%` }} />
          <div className={styles.skeletonBlock} style={{ width: "120px" }} />
          <div className={styles.skeletonBlock} style={{ width: "60px" }} />
          <div />
        </div>
      ))}
    </>
  );
}

export default function ReviewQueueList() {
  const navigate = useNavigate();
  const [reasonFilter, setReasonFilter] = useState<string | null>(null);
  const [cursors, setCursors] = useState<string[]>([]);

  const currentCursor = cursors.length > 0 ? cursors[cursors.length - 1] : undefined;

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["review-queue", reasonFilter, currentCursor],
    queryFn: () =>
      listReviewItems({
        state: "pending",
        limit: 50,
        cursor: currentCursor,
      }),
  });

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
  const filteredItems = reasonFilter
    ? items.filter((item) => item.reason === reasonFilter)
    : items;

  // Sort oldest-first (FIFO)
  const sortedItems = [...filteredItems].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>
          Review Queue
          {data && <span className={styles.count}>({data.items.length} pending)</span>}
        </h1>
      </div>

      <div className={styles.controls}>
        <div className={styles.controlGroup}>
          <span className={styles.controlLabel}>Filter:</span>
          <select
            className={styles.select}
            value={reasonFilter ?? ""}
            onChange={(e) => {
              setReasonFilter(e.target.value || null);
              setCursors([]);
            }}
            aria-label="Filter by reason"
          >
            {REASON_OPTIONS.map((opt) => (
              <option key={opt.label} value={opt.value ?? ""}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className={styles.errorBanner} role="alert">
          <span>Failed to load review queue. Please try again.</span>
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
            <span>Reason</span>
            <span>Age</span>
            <span />
          </div>
          <SkeletonRows />
        </div>
      ) : sortedItems.length === 0 && !error ? (
        <div className={styles.empty}>
          <p className={styles.emptyText}>
            All clear &mdash; no items need review.
          </p>
        </div>
      ) : (
        <>
          <div className={styles.tableHeader}>
            <span />
            <span>Job</span>
            <span>Reason</span>
            <span>Age</span>
            <span />
          </div>
          {sortedItems.map((item: ReviewItem) => (
            <Link
              key={item.id}
              to={`/review-queue/${item.id}`}
              className={styles.row}
              aria-label={`Review item ${item.job_id.slice(0, 8)}: ${REASON_LABELS[item.reason]}, age ${formatAge(item.created_at)}`}
            >
              <div className={styles.rail} data-reason={item.reason} />
              <span className={styles.jobId} data-mono>
                {item.job_id.slice(0, 12)}...
              </span>
              <span className={styles.reason}>{REASON_LABELS[item.reason]}</span>
              <span className={styles.age}>{formatAge(item.created_at)}</span>
              <div className={styles.actions}>
                <span className={styles.reviewLink}>Review</span>
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
