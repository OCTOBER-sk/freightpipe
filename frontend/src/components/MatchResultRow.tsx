// MatchResultRow — FRONTEND.md §4.7
// 5 columns: lineItem, rateConValue, bolPodValue, invoiceValue, discrepancyFlag
// Plus discrepancy amount when present
import type { MatchResult } from "@/types/backend";
import DiscrepancyFlag from "./DiscrepancyFlag";
import styles from "./MatchResultRow.module.css";

interface MatchResultRowProps {
  result: MatchResult;
}

function formatCell(value: string | null): string {
  return value ?? "\u2014";
}

export default function MatchResultRow({ result }: MatchResultRowProps) {
  return (
    <div
      className={styles.row}
      data-flag={result.discrepancy_flag}
      aria-label={`${result.line_item}: rate con ${formatCell(result.rate_con_value)}, BOL/POD ${formatCell(result.bol_pod_value)}, invoice ${formatCell(result.invoice_value)}, ${result.discrepancy_flag}`}
    >
      <span className={styles.lineItem} data-mono>{result.line_item}</span>
      <span className={styles.cell} data-mono>{formatCell(result.rate_con_value)}</span>
      <span className={styles.cell} data-mono>{formatCell(result.bol_pod_value)}</span>
      <span className={styles.cell} data-mono>{formatCell(result.invoice_value)}</span>
      <DiscrepancyFlag flag={result.discrepancy_flag} amount={result.discrepancy_amount} />
    </div>
  );
}
