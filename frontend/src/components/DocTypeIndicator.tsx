// DocTypeIndicator — FRONTEND.md §4.3
// Text labels for all 5 doc types (BACKEND.md §3.1)
// Text label, not icon-only (rejects "generic SaaS" iconography per Hard Rules)
import { DocType } from "@/types/backend";
import styles from "./DocTypeIndicator.module.css";

interface DocTypeIndicatorProps {
  docType: DocType;
}

const DOC_TYPE_LABELS: Record<DocType, string> = {
  [DocType.RATE_CON]: "Rate Confirmation",
  [DocType.BOL]: "Bill of Lading",
  [DocType.POD]: "Proof of Delivery",
  [DocType.INVOICE]: "Carrier Invoice",
  [DocType.UNKNOWN]: "Unclassified",
};

const DOC_TYPE_ABBREVS: Record<DocType, string> = {
  [DocType.RATE_CON]: "RC",
  [DocType.BOL]: "BOL",
  [DocType.POD]: "POD",
  [DocType.INVOICE]: "INV",
  [DocType.UNKNOWN]: "---",
};

export default function DocTypeIndicator({ docType }: DocTypeIndicatorProps) {
  return (
    <span className={styles.indicator} data-doc-type={docType} aria-label={DOC_TYPE_LABELS[docType]}>
      <span className={styles.abbrev}>{DOC_TYPE_ABBREVS[docType]}</span>
      <span className={styles.label}>{DOC_TYPE_LABELS[docType]}</span>
    </span>
  );
}
