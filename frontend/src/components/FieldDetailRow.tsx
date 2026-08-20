import type { ExtractedField } from "@/types/backend";
import ConfidenceBadge from "./ConfidenceBadge";
import styles from "./FieldDetailRow.module.css";

interface FieldDetailRowProps {
  field: ExtractedField;
  highlight?: boolean;
  onClick?: (field: ExtractedField) => void;
}

export default function FieldDetailRow({
  field,
  highlight = false,
  onClick,
}: FieldDetailRowProps) {
  return (
    <div
      className={`${styles.row} ${highlight ? styles.highlight : ""}`}
      onClick={() => onClick?.(field)}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <span className={styles.name} data-mono>{field.name}</span>
      <span className={styles.value} data-mono>{field.value}</span>
      <div className={styles.meta}>
        <span className={styles.page}>p.{field.page}</span>
        <ConfidenceBadge score={field.confidence} size="sm" />
      </div>
    </div>
  );
}
