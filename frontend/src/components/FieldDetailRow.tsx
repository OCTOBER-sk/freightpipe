// FieldDetailRow — FRONTEND.md §4.6
// Props: fieldName, value, confidence, sourcePage, sourceBbox, extractionMethod
// Monospace value, confidence badge, extraction method tag
import type { ExtractedFieldValue, ExtractionMethod } from "@/types/backend";
import ConfidenceBadge from "./ConfidenceBadge";
import styles from "./FieldDetailRow.module.css";

interface FieldDetailRowProps {
  fieldName: string;
  field: ExtractedFieldValue;
  highlight?: boolean;
  onClick?: () => void;
}

const METHOD_LABELS: Record<ExtractionMethod, string> = {
  rule: "rule",
  llm_text: "LLM",
  llm_vision: "vision",
  ocr: "OCR",
};

function formatValue(value: string | { amount: number; currency: string } | null): string {
  if (value === null || value === undefined) return "\u2014";
  if (typeof value === "string") return value;
  if (typeof value === "object" && "amount" in value) {
    return `$${value.amount.toLocaleString("en-US", { minimumFractionDigits: 2 })} ${value.currency}`;
  }
  return String(value);
}

export default function FieldDetailRow({
  fieldName,
  field,
  highlight = false,
  onClick,
}: FieldDetailRowProps) {
  const displayValue = formatValue(field.value);
  const method = field.extraction_method;

  return (
    <div
      className={`${styles.row} ${highlight ? styles.highlight : ""}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={`${fieldName}: ${displayValue}, confidence ${Math.round(field.confidence * 100)} percent${method ? `, extracted by ${method}` : ""}`}
    >
      <span className={styles.name} data-mono>{fieldName}</span>
      <span className={styles.value} data-mono>{displayValue}</span>
      <div className={styles.meta}>
        {method && (
          <span className={styles.method} data-mono>{METHOD_LABELS[method]}</span>
        )}
        <ConfidenceBadge value={field.confidence} scope="field" size="sm" />
      </div>
    </div>
  );
}
