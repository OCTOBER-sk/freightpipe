// WebhookStatusIndicator — FRONTEND.md §4.9
// 3 states: delivered | pending | webhook_delivery_failed
// Per BACKEND.md §4.2 retry schedule and terminal failure state
import { WebhookStatus } from "@/types/backend";
import styles from "./WebhookStatusIndicator.module.css";

interface WebhookStatusIndicatorProps {
  status: WebhookStatus;
}

const STATUS_LABELS: Record<WebhookStatus, string> = {
  [WebhookStatus.DELIVERED]: "Delivered",
  [WebhookStatus.PENDING]: "Pending",
  [WebhookStatus.WEBHOOK_DELIVERY_FAILED]: "Failed",
};

export default function WebhookStatusIndicator({ status }: WebhookStatusIndicatorProps) {
  return (
    <span
      className={styles.indicator}
      data-status={status}
      role="status"
      aria-label={`Webhook: ${STATUS_LABELS[status]}`}
    >
      <span className={styles.dot} />
      <span className={styles.label}>{STATUS_LABELS[status]}</span>
    </span>
  );
}
