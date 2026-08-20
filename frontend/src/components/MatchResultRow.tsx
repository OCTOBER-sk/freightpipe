import type { MatchResult } from "@/types/backend";
import ConfidenceBadge from "./ConfidenceBadge";
import styles from "./MatchResultRow.module.css";

interface MatchResultRowProps {
  result: MatchResult;
}

export default function MatchResultRow({ result }: MatchResultRowProps) {
  return (
    <div className={styles.row} data-match={result.match}>
      <span className={styles.field} data-mono>{result.field}</span>
      <div className={styles.values}>
        <span className={styles.source} data-mono>{result.source_value}</span>
        <span className={styles.arrow}>{result.match ? "=" : "≠"}</span>
        <span className={styles.target} data-mono>{result.target_value}</span>
      </div>
      <ConfidenceBadge score={result.confidence} size="sm" />
    </div>
  );
}
