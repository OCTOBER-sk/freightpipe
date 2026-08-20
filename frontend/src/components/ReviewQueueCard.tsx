import type { ReviewItem } from "@/types/backend";
import JobStatusPill from "./JobStatusPill";
import DiscrepancyFlag from "./DiscrepancyFlag";
import styles from "./ReviewQueueCard.module.css";

interface ReviewQueueCardProps {
  item: ReviewItem;
  onClick?: (item: ReviewItem) => void;
}

export default function ReviewQueueCard({ item, onClick }: ReviewQueueCardProps) {
  return (
    <button
      className={styles.card}
      onClick={() => onClick?.(item)}
      type="button"
    >
      <div className={styles.header}>
        <span className={styles.jobId} data-mono>{item.job_id.slice(0, 8)}</span>
        <span className={styles.time}>
          {new Date(item.created_at).toLocaleString()}
        </span>
      </div>
      <p className={styles.description}>{item.description}</p>
      <div className={styles.footer}>
        {item.field && (
          <span className={styles.field} data-mono>{item.field}</span>
        )}
        {item.resolved && <span className={styles.resolved}>Resolved</span>}
      </div>
    </button>
  );
}
