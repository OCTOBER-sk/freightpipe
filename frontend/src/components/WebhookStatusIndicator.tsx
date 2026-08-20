import type { Webhook } from "@/types/backend";
import styles from "./WebhookStatusIndicator.module.css";

interface WebhookStatusIndicatorProps {
  webhook: Webhook;
}

export default function WebhookStatusIndicator({ webhook }: WebhookStatusIndicatorProps) {
  const isHealthy = webhook.active && webhook.failure_count === 0;
  const isFailing = webhook.failure_count > 0;

  return (
    <span
      className={styles.indicator}
      data-status={isHealthy ? "healthy" : isFailing ? "failing" : "inactive"}
      title={
        isHealthy
          ? "Active and healthy"
          : isFailing
            ? `${webhook.failure_count} consecutive failures`
            : "Inactive"
      }
    >
      <span className={styles.dot} />
      {isHealthy ? "Healthy" : isFailing ? `${webhook.failure_count} failures` : "Inactive"}
    </span>
  );
}
