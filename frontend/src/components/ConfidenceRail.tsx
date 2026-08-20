import type { ExtractedField } from "@/types/backend";
import ConfidenceBadge from "./ConfidenceBadge";
import styles from "./ConfidenceRail.module.css";

interface ConfidenceRailProps {
  fields: ExtractedField[];
  threshold?: number;
}

export default function ConfidenceRail({
  fields,
  threshold = 0.7,
}: ConfidenceRailProps) {
  const sorted = [...fields].sort((a, b) => a.confidence - b.confidence);

  return (
    <div className={styles.rail}>
      <div className={styles.header}>
        <span>Field Confidence</span>
        <span className={styles.count}>
          {sorted.filter((f) => f.confidence < threshold).length} below threshold
        </span>
      </div>
      <div className={styles.list}>
        {sorted.map((field) => (
          <div
            key={field.name}
            className={styles.row}
            data-below={field.confidence < threshold}
          >
            <span className={styles.fieldName}>{field.name}</span>
            <ConfidenceBadge score={field.confidence} size="sm" />
          </div>
        ))}
      </div>
    </div>
  );
}
