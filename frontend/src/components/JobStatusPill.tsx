import type { JobStatus } from "@/types/backend";
import styles from "./JobStatusPill.module.css";

interface JobStatusPillProps {
  status: JobStatus;
}

const STATUS_LABELS: Record<JobStatus, string> = {
  queued: "Queued",
  processing: "Processing",
  completed: "Completed",
  failed: "Failed",
  review_required: "Review Required",
};

export default function JobStatusPill({ status }: JobStatusPillProps) {
  return (
    <span className={styles.pill} data-status={status}>
      <span className={styles.dot} />
      {STATUS_LABELS[status]}
    </span>
  );
}
