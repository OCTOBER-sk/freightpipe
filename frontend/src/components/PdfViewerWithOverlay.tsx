import type { ExtractedField, Discrepancy } from "@/types/backend";
import styles from "./PdfViewerWithOverlay.module.css";

interface PdfViewerWithOverlayProps {
  url: string;
  fields?: ExtractedField[];
  discrepancies?: Discrepancy[];
  activeField?: string | null;
  onFieldClick?: (field: ExtractedField) => void;
}

export default function PdfViewerWithOverlay({
  url,
  fields = [],
  discrepancies = [],
  activeField = null,
  onFieldClick,
}: PdfViewerWithOverlayProps) {
  const discrepancyFields = new Set(discrepancies.map((d) => d.field));

  return (
    <div className={styles.container}>
      <div className={styles.viewer}>
        {/* PDF rendering will use react-pdf Document/Page */}
        <iframe src={url} className={styles.iframe} title="Document preview" />
      </div>
      {fields.length > 0 && (
        <div className={styles.overlay}>
          {fields.map((field) => (
            <div
              key={field.name}
              className={`${styles.fieldMarker} ${
                field.name === activeField ? styles.active : ""
              } ${discrepancyFields.has(field.name) ? styles.discrepancy : ""}`}
              style={{
                left: `${field.bbox[0]}%`,
                top: `${field.bbox[1]}%`,
                width: `${field.bbox[2] - field.bbox[0]}%`,
                height: `${field.bbox[3] - field.bbox[1]}%`,
              }}
              onClick={() => onFieldClick?.(field)}
              title={`${field.name}: ${field.value} (${(field.confidence * 100).toFixed(0)}%)`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
