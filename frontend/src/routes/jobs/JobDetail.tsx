import { useEffect, useRef } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useJobPolling } from "@/hooks/useJobPolling";
import {
  JobStatus,
  PROCESSING_STAGES,
  TERMINAL_STATUSES,
} from "@/types/backend";
import JobStatusPill from "@/components/JobStatusPill";
import styles from "./JobDetail.module.css";

const ALL_STAGES = [
  JobStatus.QUEUED,
  JobStatus.CLASSIFYING,
  JobStatus.SPLITTING,
  JobStatus.EXTRACTING,
  JobStatus.NORMALIZING,
  JobStatus.VALIDATING,
  JobStatus.MATCHING,
  JobStatus.SCORING,
  JobStatus.COMPLETE,
];

function getStageState(
  stage: JobStatus,
  currentStatus: JobStatus,
): "completed" | "current" | "pending" {
  if (currentStatus === JobStatus.COMPLETE && stage === JobStatus.COMPLETE) {
    return "current";
  }
  if (currentStatus === JobStatus.FAILED || currentStatus === JobStatus.NEEDS_LLM_CAPACITY) {
    const currentIdx = ALL_STAGES.indexOf(JobStatus.SCORING);
    const stageIdx = ALL_STAGES.indexOf(stage);
    if (stageIdx <= currentIdx) return "completed";
    return "pending";
  }
  const currentIdx = ALL_STAGES.indexOf(currentStatus);
  const stageIdx = ALL_STAGES.indexOf(stage);
  if (stageIdx < currentIdx) return "completed";
  if (stageIdx === currentIdx) return "current";
  return "pending";
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

export default function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: job, isLoading, error } = useJobPolling(id!);
  const redirectedRef = useRef(false);

  // Auto-redirect on terminal status
  useEffect(() => {
    if (!job || redirectedRef.current) return;
    if (job.status === JobStatus.COMPLETE) {
      redirectedRef.current = true;
      navigate(`/jobs/${job.job_id}/result`, { replace: true });
    } else if (job.status === JobStatus.NEEDS_REVIEW) {
      redirectedRef.current = true;
      navigate(`/review-queue/${job.job_id}`, { replace: true });
    }
  }, [job, navigate]);

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <Link to="/jobs" className={styles.back}>{"< Jobs"}</Link>
          <h1 className={styles.title}>Loading...</h1>
        </div>
        <div className={styles.loading}>Loading job details...</div>
      </div>
    );
  }

  if (error) {
    const is404 = error.message?.includes("404") || error.message?.includes("not found");
    if (is404) {
      return (
        <div className={styles.page}>
          <div className={styles.header}>
            <Link to="/jobs" className={styles.back}>{"< Jobs"}</Link>
          </div>
          <div className={styles.notFound}>
            <p className={styles.notFoundText}>
              This job doesn't exist or you don't have access to it.
            </p>
            <Link to="/jobs" className={styles.notFoundLink}>
              Back to Jobs
            </Link>
          </div>
        </div>
      );
    }
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <Link to="/jobs" className={styles.back}>{"< Jobs"}</Link>
          <h1 className={styles.title}>Error</h1>
        </div>
        <div className={styles.error}>
          <p className={styles.errorTitle}>Failed to load job</p>
          <p className={styles.errorMessage}>{error.message}</p>
        </div>
      </div>
    );
  }

  if (!job) return null;

  const isTerminal = TERMINAL_STATUSES.includes(job.status);
  const isFailed = job.status === JobStatus.FAILED;
  const isCapacity = job.status === JobStatus.NEEDS_LLM_CAPACITY;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Link to="/jobs" className={styles.back}>{"< Jobs"}</Link>
        <h1 className={styles.title}>Job {job.job_id.slice(0, 12)}...</h1>
        <div className={styles.headerStatus}>
          <JobStatusPill status={job.status} />
        </div>
      </div>

      <div className={styles.meta}>
        <div className={styles.metaRow}>
          Stage: <span>{isTerminal ? job.status : (PROCESSING_STAGES.includes(job.status) ? job.status : "queued")}</span>
        </div>
        <div className={styles.metaRow}>
          Submitted <span>{formatRelativeTime(job.created_at)}</span>
        </div>
      </div>

      {/* Stage progress track */}
      <div className={styles.stageTrack} role="progressbar" aria-label="Pipeline progress">
        {ALL_STAGES.map((stage, i) => {
          const state = getStageState(stage, job.status);
          return (
            <div key={stage} className={styles.stage}>
              {i > 0 && <span className={styles.stageArrow}>{"->"}</span>}
              <span
                className={styles.stageLabel}
                data-state={state}
              >
                {stage}
              </span>
            </div>
          );
        })}
      </div>

      {/* Cold-start advisory */}
      {!isTerminal && (
        <div className={styles.advisory}>
          If this is a cold-start pickup, initial polling may take longer than usual
          &mdash; this is expected, not an error.
        </div>
      )}

      {/* Failed / capacity error */}
      {isFailed && job.error && (
        <div className={styles.error}>
          <p className={styles.errorTitle}>Job failed</p>
          <p className={styles.errorMessage}>{job.error.message}</p>
        </div>
      )}

      {isCapacity && (
        <div className={styles.error} style={{ borderColor: "var(--rail-capacity)", background: "rgba(217, 132, 65, 0.08)" }}>
          <p className={styles.errorTitle} style={{ color: "var(--rail-capacity)" }}>
            Capacity Limited
          </p>
          <p className={styles.errorMessage}>
            Free-tier processing capacity is temporarily exhausted for today. This job will
            resume automatically, or add your own API key in Settings to bypass the limit.
          </p>
        </div>
      )}

      {/* Documents detected */}
      {job.documents && job.documents.length > 0 && (
        <div className={styles.documents}>
          <h2 className={styles.documentsTitle}>
            Documents detected so far: {job.documents.length}
          </h2>
          {job.documents.map((doc) => (
            <div key={doc.document_id} className={styles.documentItem}>
              <span className={styles.docType}>{doc.doc_type}</span>
              <span className={styles.docPages}>
                pages {doc.page_start}
                {doc.page_end !== doc.page_start ? `\u2013${doc.page_end}` : ""}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Timeout notice */}
      {!isTerminal && (
        <div className={styles.timeout}>
          Still processing &mdash; this is taking longer than usual.
          <br />
          <button
            type="button"
            className={styles.refreshBtn}
            onClick={() => window.location.reload()}
          >
            Refresh
          </button>
        </div>
      )}
    </div>
  );
}
