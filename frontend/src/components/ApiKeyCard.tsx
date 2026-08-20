import type { ApiKey } from "@/types/backend";
import styles from "./ApiKeyCard.module.css";

interface ApiKeyCardProps {
  apiKey: ApiKey;
  onRevoke?: (keyId: string) => void;
}

export default function ApiKeyCard({ apiKey, onRevoke }: ApiKeyCardProps) {
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={styles.name}>{apiKey.name}</span>
        <span className={styles.prefix} data-mono>{apiKey.key_prefix}••••••••</span>
      </div>
      <div className={styles.meta}>
        <span>Created {new Date(apiKey.created_at).toLocaleDateString()}</span>
        {apiKey.last_used_at && (
          <span>Last used {new Date(apiKey.last_used_at).toLocaleDateString()}</span>
        )}
        {apiKey.expires_at && (
          <span>Expires {new Date(apiKey.expires_at).toLocaleDateString()}</span>
        )}
      </div>
      {onRevoke && (
        <button
          className={styles.revoke}
          onClick={() => onRevoke(apiKey.id)}
          type="button"
        >
          Revoke
        </button>
      )}
    </div>
  );
}
