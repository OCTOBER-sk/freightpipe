import type { DiscrepancyFlag as DiscrepancyFlagType } from "@/types/backend";
import styles from "./DiscrepancyFlag.module.css";

interface DiscrepancyFlagProps {
  flag: DiscrepancyFlagType;
  compact?: boolean;
}

const FLAG_LABELS: Record<DiscrepancyFlagType, string> = {
  mismatch: "Mismatch",
  missing: "Missing",
  extra: "Extra",
  format_error: "Format Error",
  low_confidence: "Low Confidence",
};

const FLAG_ICONS: Record<DiscrepancyFlagType, string> = {
  mismatch: "≠",
  missing: "∅",
  extra: "+",
  format_error: "⚠",
  low_confidence: "↓",
};

export default function DiscrepancyFlag({ flag, compact = false }: DiscrepancyFlagProps) {
  return (
    <span className={styles.flag} data-flag={flag}>
      <span className={styles.icon}>{FLAG_ICONS[flag]}</span>
      {!compact && <span>{FLAG_LABELS[flag]}</span>}
    </span>
  );
}
