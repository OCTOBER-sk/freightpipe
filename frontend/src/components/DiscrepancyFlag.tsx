// DiscrepancyFlag — FRONTEND.md §4.2
// 6 enum values from BACKEND.md §3.1 match_results.discrepancy_flag
// none → gray dot + "No discrepancy"; non-none → red rail + plain English label
import { DiscrepancyFlag as DiscrepancyFlagEnum } from "@/types/backend";
import styles from "./DiscrepancyFlag.module.css";

interface DiscrepancyFlagProps {
  flag: DiscrepancyFlagEnum;
  amount?: number | null;
}

const FLAG_LABELS: Record<DiscrepancyFlagEnum, string> = {
  [DiscrepancyFlagEnum.NONE]: "No discrepancy",
  [DiscrepancyFlagEnum.RATE_DELTA]: "Rate delta",
  [DiscrepancyFlagEnum.MISSING_ACCESSORIAL]: "Missing accessorial",
  [DiscrepancyFlagEnum.EXTRA_ACCESSORIAL]: "Extra accessorial",
  [DiscrepancyFlagEnum.WEIGHT_VARIANCE]: "Weight variance",
  [DiscrepancyFlagEnum.PIECES_VARIANCE]: "Pieces variance",
};

function formatAmount(amount: number): string {
  return amount >= 0 ? `+$${amount.toFixed(2)}` : `-$${Math.abs(amount).toFixed(2)}`;
}

export default function DiscrepancyFlag({ flag, amount }: DiscrepancyFlagProps) {
  const isNone = flag === DiscrepancyFlagEnum.NONE;

  return (
    <span
      className={`${styles.flag} ${isNone ? styles.none : styles.alert}`}
      data-flag={flag}
      role="status"
      aria-label={FLAG_LABELS[flag]}
    >
      {!isNone && <span className={styles.rail} />}
      <span className={styles.label}>{FLAG_LABELS[flag]}</span>
      {amount != null && !isNone && (
        <span className={styles.amount} data-mono>
          {formatAmount(amount)}
        </span>
      )}
    </span>
  );
}
