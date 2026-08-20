// JobStatusPill — FRONTEND.md §4.4
// Full 12-value enum from BACKEND.md §3.1 jobs.status
// Collapses 7 mid-pipeline stages to "Processing" with stage name subtext (§2.4)
import { JobStatus, PROCESSING_STAGES } from "@/types/backend";
import styles from "./JobStatusPill.module.css";

interface JobStatusPillProps {
  status: JobStatus;
  /** Show the specific stage name as subtext when collapsed to "Processing" */
  showStage?: boolean;
}

const STATUS_LABELS: Record<JobStatus, string> = {
  [JobStatus.QUEUED]: "Queued",
  [JobStatus.CLASSIFYING]: "Processing",
  [JobStatus.SPLITTING]: "Processing",
  [JobStatus.EXTRACTING]: "Processing",
  [JobStatus.NORMALIZING]: "Processing",
  [JobStatus.VALIDATING]: "Processing",
  [JobStatus.MATCHING]: "Processing",
  [JobStatus.SCORING]: "Processing",
  [JobStatus.NEEDS_REVIEW]: "Needs Review",
  [JobStatus.COMPLETE]: "Complete",
  [JobStatus.FAILED]: "Failed",
  [JobStatus.NEEDS_LLM_CAPACITY]: "Capacity Limited",
};

/** Map status to rail state for color (§2.4) */
function getRailState(status: JobStatus): string {
  if (status === JobStatus.QUEUED) return "queued";
  if (PROCESSING_STAGES.includes(status)) return "processing";
  if (status === JobStatus.NEEDS_REVIEW) return "needs_review";
  if (status === JobStatus.COMPLETE) return "complete";
  if (status === JobStatus.FAILED) return "failed";
  if (status === JobStatus.NEEDS_LLM_CAPACITY) return "needs_llm_capacity";
  return "queued";
}

export default function JobStatusPill({ status, showStage = true }: JobStatusPillProps) {
  const isProcessing = PROCESSING_STAGES.includes(status);
  const railState = getRailState(status);

  return (
    <span
      className={styles.pill}
      data-rail-state={railState}
      role="status"
      aria-label={`Job status: ${STATUS_LABELS[status]}${isProcessing ? `, stage: ${status}` : ""}`}
    >
      <span className={styles.dot} />
      <span className={styles.text}>
        {STATUS_LABELS[status]}
        {isProcessing && showStage && (
          <span className={styles.stage} data-mono>{status}</span>
        )}
      </span>
    </span>
  );
}
