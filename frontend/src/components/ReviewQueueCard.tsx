// ReviewQueueCard — FRONTEND.md §4.5
// Props: reason, age, jobId, docType
// Used in §3.5's review queue list
import { ReviewReason, DocType } from "@/types/backend";
import DocTypeIndicator from "./DocTypeIndicator";
import styles from "./ReviewQueueCard.module.css";

interface ReviewQueueCardProps {
  reason: ReviewReason;
  jobId: string;
  docType?: DocType;
  createdAt: string;
  onClick?: () => void;
}

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

export default function ReviewQueueCard({
  reason,
  jobId,
  docType,
  createdAt,
  onClick,
}: ReviewQueueCardProps) {
  const isDiscrepancy = reason === ReviewReason.DISCREPANCY;
  const isCapacity = reason === ReviewReason.NEEDS_LLM_CAPACITY;

  return (
    <button
      className={styles.card}
      data-rail-state={isCapacity ? "needs_review" : isDiscrepancy ? "failed" : "needs_review"}
      onClick={onClick}
      type="button"
      aria-label={`Review item ${jobId.slice(0, 8)}: ${REASON_LABELS[reason]}, age ${formatAge(createdAt)}`}
    >
      <div className={styles.row}>
        <span className={styles.jobId} data-mono>{jobId.slice(0, 12)}...</span>
        <span className={styles.reason}>{REASON_LABELS[reason]}</span>
        <span className={styles.age}>{formatAge(createdAt)}</span>
      </div>
      {docType && (
        <div className={styles.docType}>
          <DocTypeIndicator docType={docType} />
        </div>
      )}
    </button>
  );
}
