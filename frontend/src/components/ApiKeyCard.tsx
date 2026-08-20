// ApiKeyCard — FRONTEND.md §4.10
// Props: label, maskedKey, createdAt, revokedAt?
// Masked key display, create/revoke actions
import styles from "./ApiKeyCard.module.css";

interface ApiKeyCardProps {
  label: string;
  maskedKey: string;
  createdAt: string;
  revokedAt?: string | null;
  onRevoke?: () => void;
}

export default function ApiKeyCard({
  label,
  maskedKey,
  createdAt,
  revokedAt,
  onRevoke,
}: ApiKeyCardProps) {
  const isRevoked = revokedAt != null;

  return (
    <div
      className={styles.card}
      data-revoked={isRevoked}
      aria-label={`API key ${label}: ${isRevoked ? "revoked" : "active"}`}
    >
      <div className={styles.header}>
        <span className={styles.label}>{label}</span>
        <span className={styles.key} data-mono>{maskedKey}</span>
      </div>
      <div className={styles.meta}>
        <span className={styles.date}>
          Created {new Date(createdAt).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
        </span>
        {isRevoked && (
          <span className={styles.revoked}>
            Revoked {new Date(revokedAt!).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
          </span>
        )}
      </div>
      {!isRevoked && onRevoke && (
        <button
          className={styles.revoke}
          onClick={onRevoke}
          type="button"
          aria-label={`Revoke API key ${label}`}
        >
          Revoke
        </button>
      )}
    </div>
  );
}
