import { useState, useCallback, useMemo } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getReviewItem } from "@/api/reviewQueue";
import { getJobResult, getDocumentPdfUrl } from "@/api/jobs";
import { useReviewResolve } from "@/hooks/useReviewResolve";
import { ApiClientError } from "@/api/client";
import type { ExtractedFieldValue, Money } from "@/types/backend";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import PdfViewerWithOverlay from "@/components/PdfViewerWithOverlay";
import styles from "./ReviewItemDetail.module.css";

function formatValue(value: string | Money | null): string {
  if (value === null || value === undefined) return "\u2014";
  if (typeof value === "string") return value;
  if (typeof value === "object" && "amount" in value) {
    return `$${value.amount.toLocaleString("en-US", { minimumFractionDigits: 2 })} ${value.currency}`;
  }
  return String(value);
}

export default function ReviewItemDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [notes, setNotes] = useState("");
  const [correctedFields, setCorrectedFields] = useState<Record<string, unknown>>({});
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [resolveError, setResolveError] = useState<string | null>(null);

  // Fetch review item
  const {
    data: reviewItem,
    isLoading: itemLoading,
    error: itemError,
  } = useQuery({
    queryKey: ["review-item", id],
    queryFn: () => getReviewItem(id!),
    enabled: !!id,
  });

  // Fetch job result for field data
  const { data: jobResult, isLoading: resultLoading } = useQuery({
    queryKey: ["job-result", reviewItem?.job_id],
    queryFn: () => getJobResult(reviewItem!.job_id),
    enabled: !!reviewItem?.job_id,
  });

  // Fetch PDF URL for the first document
  const firstDocId = jobResult?.documents?.[0]?.document_id;
  const { data: pdfData, isLoading: pdfLoading } = useQuery({
    queryKey: ["document-pdf", firstDocId],
    queryFn: () => getDocumentPdfUrl(firstDocId!),
    enabled: !!firstDocId,
  });

  // Resolve mutation
  const resolveMutation = useReviewResolve({
    onSuccess: () => {
      navigate("/review-queue");
    },
    onError: (err: Error) => {
      if (err instanceof ApiClientError) {
        setResolveError(err.error.message);
      } else {
        setResolveError("Failed to resolve. Please try again.");
      }
    },
  });

  const isLoading = itemLoading || resultLoading;

  // Build highlights from fields
  const highlights = useMemo(() => {
    if (!jobResult?.documents?.[0]?.fields) return [];
    const fields = jobResult.documents[0].fields;
    return Object.entries(fields)
      .filter(([, f]) => f.source?.bbox)
      .map(([name, f]) => ({
        fieldName: name,
        page: f.source.page,
        bbox: f.source.bbox,
        confidence: f.confidence,
      }));
  }, [jobResult]);

  const fields = jobResult?.documents?.[0]?.fields ?? {};
  const fieldEntries = Object.entries(fields);

  const handleStartEdit = useCallback(
    (fieldName: string, currentValue: ExtractedFieldValue) => {
      setEditingField(fieldName);
      setEditValue(
        typeof currentValue.value === "string"
          ? currentValue.value
          : currentValue.value
            ? JSON.stringify(currentValue.value)
            : "",
      );
    },
    [],
  );

  const handleSaveEdit = useCallback(() => {
    if (editingField) {
      setCorrectedFields((prev) => ({ ...prev, [editingField]: editValue }));
      setEditingField(null);
      setEditValue("");
    }
  }, [editingField, editValue]);

  const handleCancelEdit = useCallback(() => {
    setEditingField(null);
    setEditValue("");
  }, []);

  const handleApprove = useCallback(() => {
    if (!id) return;
    setResolveError(null);
    resolveMutation.mutate({
      itemId: id,
      data: { resolution: "approved", notes: notes || undefined },
    });
  }, [id, notes, resolveMutation]);

  const handleCorrect = useCallback(() => {
    if (!id) return;
    setResolveError(null);
    resolveMutation.mutate({
      itemId: id,
      data: {
        resolution: "corrected",
        corrected_fields: correctedFields,
        notes: notes || undefined,
      },
    });
  }, [id, correctedFields, notes, resolveMutation]);

  const handleEscalate = useCallback(() => {
    if (!id) return;
    setResolveError(null);
    resolveMutation.mutate({
      itemId: id,
      data: { resolution: "escalated", notes: notes || undefined },
    });
  }, [id, notes, resolveMutation]);

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <Link to="/review-queue" className={styles.back}>{"< Review Queue"}</Link>
        </div>
        <div className={styles.loading}>Loading review item...</div>
      </div>
    );
  }

  if (itemError) {
    const is404 = itemError.message?.includes("404");
    if (is404) {
      return (
        <div className={styles.page}>
          <div className={styles.header}>
            <Link to="/review-queue" className={styles.back}>{"< Review Queue"}</Link>
          </div>
          <div className={styles.notFound}>
            <p className={styles.notFoundText}>
              This review item doesn't exist or you don't have access to it.
            </p>
            <Link to="/review-queue" className={styles.notFoundLink}>
              Back to Review Queue
            </Link>
          </div>
        </div>
      );
    }
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <Link to="/review-queue" className={styles.back}>{"< Review Queue"}</Link>
        </div>
        <div className={styles.error}>{itemError.message}</div>
      </div>
    );
  }

  if (!reviewItem) return null;

  const isResolving = resolveMutation.isPending;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Link to="/review-queue" className={styles.back}>{"< Review Queue"}</Link>
        <h1 className={styles.title}>
          {reviewItem.job_id.slice(0, 12)}...
          {jobResult?.documents?.[0] && (
            <span className={styles.docType}>
              &mdash; {jobResult.documents[0].doc_type}
            </span>
          )}
        </h1>
      </div>

      {/* Review reason */}
      <div className={styles.reason}>
        Review reason: {reviewItem.reason}
      </div>

      {resolveError && (
        <div className={styles.error} role="alert">{resolveError}</div>
      )}

      {/* Two-pane layout */}
      <div className={styles.panes}>
        {/* PDF viewer */}
        <div className={`${styles.pane} ${styles.pdfPane}`}>
          <div className={styles.paneTitle}>Source Document</div>
          {pdfLoading ? (
            <div className={styles.loading}>Loading PDF...</div>
          ) : pdfData?.url ? (
            <PdfViewerWithOverlay
              url={pdfData.url}
              highlights={highlights}
              activeField={editingField}
              onFieldClick={(fieldName) => {
                const field = fields[fieldName];
                if (field) handleStartEdit(fieldName, field);
              }}
            />
          ) : (
            <div className={styles.loading}>PDF not available</div>
          )}
        </div>

        {/* Fields pane */}
        <div className={`${styles.pane} ${styles.fieldsPane}`}>
          <div className={styles.paneTitle}>Extracted Fields</div>
          <div className={styles.fieldsList}>
            {fieldEntries.length === 0 ? (
              <div className={styles.loading}>No fields extracted</div>
            ) : (
              fieldEntries.map(([name, field]) => {
                const isEditing = editingField === name;
                const hasCorrection = name in correctedFields;
                const displayValue = hasCorrection
                  ? String(correctedFields[name])
                  : formatValue(field.value);

                return (
                  <div key={name} className={styles.fieldRow}>
                    <span className={styles.fieldName} data-mono>{name}</span>
                    {isEditing ? (
                      <input
                        className={styles.editInput}
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveEdit();
                          if (e.key === "Escape") handleCancelEdit();
                        }}
                        autoFocus
                      />
                    ) : (
                      <span
                        className={styles.fieldValue}
                        data-mono
                        style={hasCorrection ? { color: "var(--accent)" } : undefined}
                      >
                        {displayValue}
                      </span>
                    )}
                    <div className={styles.fieldMeta}>
                      {isEditing ? (
                        <>
                          <button
                            type="button"
                            className={styles.editBtn}
                            onClick={handleSaveEdit}
                            aria-label="Save edit"
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            className={styles.editBtn}
                            onClick={handleCancelEdit}
                            aria-label="Cancel edit"
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <ConfidenceBadge value={field.confidence} scope="field" size="sm" />
                          <button
                            type="button"
                            className={styles.editBtn}
                            onClick={() => handleStartEdit(name, field)}
                            aria-label={`Edit ${name}`}
                          >
                            Edit
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Notes */}
      <div className={styles.notes}>
        <label className={styles.notesLabel} htmlFor="review-notes">
          Notes (optional)
        </label>
        <textarea
          id="review-notes"
          className={styles.notesInput}
          placeholder="Add notes about this review..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          disabled={isResolving}
        />
      </div>

      {/* Actions */}
      <div className={styles.actions}>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnEscalate}`}
          onClick={handleEscalate}
          disabled={isResolving}
        >
          {isResolving ? <span className={styles.spinner} /> : null}
          Escalate
        </button>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnApprove}`}
          onClick={handleApprove}
          disabled={isResolving}
        >
          {isResolving ? <span className={styles.spinner} /> : null}
          Approve as-is
        </button>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnCorrect}`}
          onClick={handleCorrect}
          disabled={isResolving || Object.keys(correctedFields).length === 0}
        >
          {isResolving ? <span className={styles.spinner} /> : null}
          Save corrections
        </button>
      </div>
    </div>
  );
}
