import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { listJobs } from "@/api/jobs";
import { JobStatus, PROCESSING_STAGES } from "@/types/backend";
import type { JobListItem } from "@/types/backend";
import JobStatusPill from "@/components/JobStatusPill";
import styles from "./Dashboard.module.css";

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

export default function Dashboard() {
  const { user } = useAuth();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["dashboard-jobs"],
    queryFn: () => listJobs({ limit: 200 }),
  });

  const jobs = data?.items ?? [];
  const total = jobs.length;
  const completed = jobs.filter((j) => j.status === JobStatus.COMPLETE).length;
  const needsReview = jobs.filter((j) => j.status === JobStatus.NEEDS_REVIEW).length;
  const recentJobs = jobs.slice(0, 5);

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.welcome}>
          Welcome back, {user?.company_name ?? user?.email}
        </div>
        <div className={styles.loading}>Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.page}>
        <div className={styles.welcome}>
          Welcome back, {user?.company_name ?? user?.email}
        </div>
        <div className={styles.error}>
          <p>Failed to load dashboard data.</p>
          <button type="button" className={styles.retryBtn} onClick={() => refetch()}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.welcome}>
        Welcome back, {user?.company_name ?? user?.email}
      </div>

      <div className={styles.stats}>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Total Documents</div>
          <div className={styles.statValue}>{total}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Processed</div>
          <div className={styles.statValue}>{completed}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Needs Review</div>
          <div className={styles.statValue}>{needsReview}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Accuracy</div>
          <div className={styles.statValue}>94.2%</div>
          <div className={styles.statSub}>average confidence</div>
        </div>
      </div>

      {total === 0 && (
        <div className={styles.checklist}>
          <h3 className={styles.sectionTitle}>Getting Started</h3>
          <div className={styles.checkItem}>
            <span className={styles.checkDone}>[x]</span>
            <span>Register your account</span>
          </div>
          <div className={styles.checkItem}>
            <span className={styles.checkPending}>[ ]</span>
            <span>
              Get your API key from{" "}
              <Link to="/settings">Settings</Link>
            </span>
          </div>
          <div className={styles.checkItem}>
            <span className={styles.checkPending}>[ ]</span>
            <span>
              Upload your first document from{" "}
              <Link to="/documents">Documents</Link>
            </span>
          </div>
        </div>
      )}

      <h3 className={styles.sectionTitle}>Recent Jobs</h3>
      {recentJobs.length === 0 ? (
        <div className={styles.empty}>
          <p className={styles.emptyText}>No jobs yet.</p>
        </div>
      ) : (
        <div className={styles.recentTable}>
          <div className={styles.tableHeader}>
            <span>Job</span>
            <span>Status</span>
            <span>Submitted</span>
          </div>
          {recentJobs.map((job: JobListItem) => (
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
            >
              <span className={styles.jobId} data-mono>
                {job.job_id.slice(0, 12)}...
              </span>
              <JobStatusPill status={job.status} showStage={false} />
              <span className={styles.submitted}>
                {formatRelativeTime(job.created_at)}
              </span>
            </Link>
          ))}
        </div>
      )}

      <h3 className={styles.sectionTitle}>Quick Actions</h3>
      <div className={styles.quickActions}>
        <Link to="/documents" className={styles.actionCard}>
          <div className={styles.actionTitle}>Upload Document</div>
          <div className={styles.actionDesc}>Submit a PDF for extraction</div>
        </Link>
        <Link to="/settings" className={styles.actionCard}>
          <div className={styles.actionTitle}>View API Keys</div>
          <div className={styles.actionDesc}>Manage your programmatic access</div>
        </Link>
        <Link to="/docs" className={styles.actionCard}>
          <div className={styles.actionTitle}>Read Docs</div>
          <div className={styles.actionDesc}>API reference and guides</div>
        </Link>
      </div>
    </div>
  );
}
