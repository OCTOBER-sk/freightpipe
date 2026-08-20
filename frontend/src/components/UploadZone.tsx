// UploadZone — FRONTEND.md §4.8
// maxSizeMb: 25 (BACKEND.md §4.1), accept: application/pdf
// 5 states: idle, dragover, file-selected, uploading, error
// No emoji (§1.6 Hard Rules)
import { useCallback, useState, useRef } from "react";
import styles from "./UploadZone.module.css";

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  file?: File | null;
  state?: "idle" | "dragover" | "file-selected" | "uploading" | "error";
  errorMessage?: string;
  maxSizeMb?: number;
  disabled?: boolean;
}

const MAX_SIZE_MB = 25;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

export default function UploadZone({
  onFileSelect,
  file = null,
  state: externalState,
  disabled = false,
}: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const computeState = useCallback((): string => {
    if (externalState) return externalState;
    if (error) return "error";
    if (file) return "file-selected";
    if (isDragging) return "dragover";
    return "idle";
  }, [externalState, error, file, isDragging]);

  const validateFile = useCallback((f: File): string | null => {
    if (f.type !== "application/pdf" && !f.name.toLowerCase().endsWith(".pdf")) {
      return "Only PDF files are accepted.";
    }
    if (f.size > MAX_SIZE_BYTES) {
      const sizeMb = (f.size / (1024 * 1024)).toFixed(0);
      return `This file is ${sizeMb}MB \u2014 FreightPipe accepts PDFs up to ${MAX_SIZE_MB}MB. Try splitting it into separate documents.`;
    }
    return null;
  }, []);

  const handleFile = useCallback(
    (f: File) => {
      setError(null);
      const validationError = validateFile(f);
      if (validationError) {
        setError(validationError);
        return;
      }
      onFileSelect(f);
    },
    [onFileSelect, validateFile],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (disabled) return;
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) handleFile(droppedFile);
    },
    [disabled, handleFile],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) handleFile(selected);
    },
    [handleFile],
  );

  const handleClear = useCallback(() => {
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  const currentState = computeState();

  return (
    <div
      className={`${styles.zone} ${styles[currentState] ?? ""}`}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      role="region"
      aria-label="File upload zone"
    >
      <label className={styles.label}>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          onChange={handleChange}
          disabled={disabled || currentState === "uploading"}
          className={styles.input}
        />
        {currentState === "file-selected" && file ? (
          <div className={styles.fileInfo}>
            <span className={styles.filename} data-mono>{file.name}</span>
            <span className={styles.filesize} data-mono>
              {(file.size / (1024 * 1024)).toFixed(1)}MB
            </span>
            <button
              type="button"
              className={styles.clear}
              onClick={(e) => { e.preventDefault(); handleClear(); }}
              aria-label="Remove selected file"
            >
              x
            </button>
          </div>
        ) : currentState === "uploading" ? (
          <span className={styles.text}>Uploading...</span>
        ) : (
          <>
            <span className={styles.text}>
              Drop a PDF here, or click to browse
            </span>
            <span className={styles.hint}>
              Max {MAX_SIZE_MB}MB &middot; rate confirmations, BOLs, PODs, invoices &mdash; merged files OK
            </span>
          </>
        )}
      </label>
      {error && (
        <div className={styles.error} role="alert">{error}</div>
      )}
    </div>
  );
}
