import type { DocType } from "@/types/backend";
import styles from "./DocTypeIndicator.module.css";

interface DocTypeIndicatorProps {
  docType: DocType;
  showLabel?: boolean;
}

const DOC_TYPE_LABELS: Record<DocType, string> = {
  bill_of_lading: "Bill of Lading",
  commercial_invoice: "Commercial Invoice",
  packing_list: "Packing List",
  certificate_of_origin: "Certificate of Origin",
  customs_declaration: "Customs Declaration",
  delivery_order: "Delivery Order",
  other: "Other",
};

const DOC_TYPE_ABBREVS: Record<DocType, string> = {
  bill_of_lading: "BOL",
  commercial_invoice: "CI",
  packing_list: "PL",
  certificate_of_origin: "COO",
  customs_declaration: "CD",
  delivery_order: "DO",
  other: "DOC",
};

export default function DocTypeIndicator({ docType, showLabel = true }: DocTypeIndicatorProps) {
  return (
    <span className={styles.indicator} data-doc-type={docType}>
      <span className={styles.abbrev}>{DOC_TYPE_ABBREVS[docType]}</span>
      {showLabel && <span className={styles.label}>{DOC_TYPE_LABELS[docType]}</span>}
    </span>
  );
}
