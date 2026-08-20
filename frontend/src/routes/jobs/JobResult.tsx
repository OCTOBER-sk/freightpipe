import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getJobResult, getJob } from "@/api/jobs";
import { getConfidenceLevel } from "@/config/confidence";
import type { DocumentResult } from "@/types/backend";
import JobStatusPill from "@/components/JobStatusPill";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import FieldDetailRow from "@/components/FieldDetailRow";
import MatchResultRow from "@/components/MatchResultRow";
import styles from "./JobResult.module.css";

function DocumentCard({ doc }: { doc: DocumentResult }) {
  const [expanded, setExpanded] = useState(false);
  const level = getConfidenceLevel(doc.document_confidence, "document");
  const fieldEntries = Object.entries(doc.fields);

  return (
    <div className={styles.documentCard} data-confidence={level}>
      <div className={styles.docCardHeader}>
        <div>
          <span className={styles.docCardType}>{doc.doc_type}</span>
        </div>
        <div className={styles.docCardConfidence}>
          <ConfidenceBadge value={doc.document_confidence} scope="document" size="sm" />
        </div>
      </div>
      <button
        type="button"
        className={styles.expandBtn}
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        {expanded ? "▾ Collapse fields" : "▸ Expand fields"}
      </button>
      {expanded && (
        <div className={styles.fieldsList}>
          {fieldEntries.length === 0 ? (
            <p className={styles.noFields}>No fields extracted</p>
          ) : (
            fieldEntries.map(([name, field]) => (
              <FieldDetailRow key={name} fieldName={name} field={field} />
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function JobResult() {
  const { id } = useParams<{ id: string }>();

  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ["job", id],
    queryFn: () => getJob(id!),
    enabled: !!id,
  });

  const {
    data: result,
    isLoading: resultLoading,
    error,
  } = useQuery({
    queryKey: ["job-result", id],
    queryFn: () => getJobResult(id!),
    enabled: !!id,
    retry: (failureCount, err: Error) => {
      if (err.message?.includes("409")) return true;
      return failureCount < 2;
    },
  });

  if (resultLoading || jobLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <Link to="/jobs" className={styles.back}>{"< Jobs"}</Link>
          <h1 className={styles.title}>Loading...</h1>
        </div>
        <div className={styles.loading}>Loading result...</div>
      </div>
    );
  }

  if (error) {
    const is404 = error.message?.includes("404");
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
            <Link to="/jobs" className={styles.notFoundLink}>Back to Jobs</Link>
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
          <p className={styles.errorTitle}>Failed to load result</p>
          <p className={styles.errorMessage}>{error.message}</p>
        </div>
      </div>
    );
  }

  if (!result) return null;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Link to="/jobs" className={styles.back}>{"< Jobs"}</Link>
        <h1 className={styles.title}>Result: {result.job_id.slice(0, 12)}...</h1>
        {job && (
          <div className={styles.headerStatus}>
            <JobStatusPill status={job.status} showStage={false} />
          </div>
        )}
      </div>

      {/* Review banner */}
      {result.review_required && (
        <div className={styles.reviewBanner}>
          <span className={styles.reviewBannerText}>
            This job requires review
            {result.review_reasons.length > 0 && `: ${result.review_reasons[0]}`}
          </span>
          <Link
            to={`/review-queue/${result.job_id}`}
            className={styles.reviewBannerLink}
          >
            Review
          </Link>
        </div>
      )}

      {/* Documents */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>
          Documents ({result.documents.length})
        </h2>
        <div className={styles.documentsGrid}>
          {result.documents.map((doc) => (
            <DocumentCard key={doc.document_id} doc={doc} />
          ))}
        </div>
      </div>

      {/* 3-Way Match */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>3-Way Match</h2>
        {result.match_results.length === 0 ? (
          <p className={styles.noDiscrepancies}>No discrepancies found</p>
        ) : (
          <div className={styles.matchTable}>
            <div className={styles.matchHeader}>
              <span>Line item</span>
              <span>Rate Con</span>
              <span>BOL/POD</span>
              <span>Invoice</span>
              <span>Flag</span>
            </div>
            {result.match_results.map((match, i) => (
              <MatchResultRow key={`${match.line_item}-${i}`} result={match} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
