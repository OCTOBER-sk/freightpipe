import { getConfidenceLevel, getConfidenceColor } from "@/config/confidence";
import styles from "./ConfidenceBadge.module.css";

interface ConfidenceBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export default function ConfidenceBadge({
  score,
  size = "md",
  showLabel = false,
}: ConfidenceBadgeProps) {
  const level = getConfidenceLevel(score);
  const color = getConfidenceColor(level);

  return (
    <span
      className={`${styles.badge} ${styles[size]}`}
      style={{ borderColor: color, color }}
      title={`Confidence: ${(score * 100).toFixed(1)}%`}
    >
      {(score * 100).toFixed(0)}%
      {showLabel && <span className={styles.label}>{level}</span>}
    </span>
  );
}
