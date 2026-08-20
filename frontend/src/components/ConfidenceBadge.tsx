// ConfidenceBadge — FRONTEND.md §4.1
// Green (≥threshold), amber (≥threshold-0.10), red (below)
// Always shows numeric + text label. WCAG aria-label.
import {
  getConfidenceLevel,
  getConfidenceColor,
  getConfidenceLabel,
  type ConfidenceScope,
} from "@/config/confidence";
import styles from "./ConfidenceBadge.module.css";

interface ConfidenceBadgeProps {
  value: number;
  scope?: ConfidenceScope;
  size?: "sm" | "md" | "lg";
}

export default function ConfidenceBadge({
  value,
  scope = "field",
  size = "md",
}: ConfidenceBadgeProps) {
  const level = getConfidenceLevel(value, scope);
  const color = getConfidenceColor(level);
  const label = getConfidenceLabel(level);
  const pct = Math.round(value * 100);

  return (
    <span
      className={`${styles.badge} ${styles[size]}`}
      style={{ borderColor: color, color }}
      aria-label={`Confidence: ${pct} percent, ${label}`}
    >
      <span className={styles.value}>{pct}%</span>
      <span className={styles.label}>{label}</span>
    </span>
  );
}
