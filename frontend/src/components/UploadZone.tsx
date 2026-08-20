import { useCallback, useState } from "react";
import styles from "./UploadZone.module.css";

interface UploadZoneProps {
  label: string;
  accept?: string;
  onFileSelect: (file: File) => void;
  file?: File | null;
  disabled?: boolean;
}

export default function UploadZone({
  label,
  accept = ".pdf,.png,.jpg,.jpeg,.tiff",
  onFileSelect,
  file = null,
  disabled = false,
}: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (disabled) return;
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) onFileSelect(droppedFile);
    },
    [disabled, onFileSelect],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) onFileSelect(selected);
    },
    [onFileSelect],
  );

  return (
    <div
      className={`${styles.zone} ${isDragging ? styles.dragging : ""} ${disabled ? styles.disabled : ""}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <label className={styles.label}>
        <input
          type="file"
          accept={accept}
          onChange={handleChange}
          disabled={disabled}
          className={styles.input}
        />
        {file ? (
          <span className={styles.filename} data-mono>{file.name}</span>
        ) : (
          <>
            <span className={styles.icon}>📄</span>
            <span className={styles.text}>{label}</span>
            <span className={styles.hint}>Drop file or click to browse</span>
          </>
        )}
      </label>
    </div>
  );
}
