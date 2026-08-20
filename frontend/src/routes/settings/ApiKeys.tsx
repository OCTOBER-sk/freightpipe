import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listApiKeys, createApiKey, revokeApiKey } from "@/api/settings";
import { ApiClientError } from "@/api/client";
import ApiKeyCard from "@/components/ApiKeyCard";
import styles from "./ApiKeys.module.css";

export default function ApiKeys() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [label, setLabel] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: listApiKeys,
  });

  const createMutation = useMutation({
    mutationFn: (label: string) => createApiKey(label),
    onSuccess: (res) => {
      setNewKey(res.key);
      setLabel("");
      setShowCreate(false);
      setCopied(false);
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (err: Error) => {
      if (err instanceof ApiClientError) {
        setError(err.error.message);
      } else {
        setError("Failed to create API key");
      }
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (keyId: string) => revokeApiKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (err: Error) => {
      if (err instanceof ApiClientError) {
        setError(err.error.message);
      } else {
        setError("Failed to revoke API key");
      }
    },
  });

  const handleCreate = useCallback(() => {
    if (!label.trim()) return;
    setError(null);
    createMutation.mutate(label.trim());
  }, [label, createMutation]);

  const handleCopy = useCallback(async () => {
    if (!newKey) return;
    try {
      await navigator.clipboard.writeText(newKey);
      setCopied(true);
    } catch {
      // Fallback for non-secure contexts
      const textarea = document.createElement("textarea");
      textarea.value = newKey;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
    }
  }, [newKey]);

  const handleRevoke = useCallback(
    (keyId: string) => {
      setError(null);
      revokeMutation.mutate(keyId);
    },
    [revokeMutation],
  );

  const keys = data?.items ?? [];

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>API Keys</h1>
        <button
          type="button"
          className={styles.createBtn}
          onClick={() => setShowCreate((v) => !v)}
          disabled={createMutation.isPending}
        >
          + New API Key
        </button>
      </div>

      {error && (
        <div className={styles.error} role="alert">{error}</div>
      )}

      {/* New key display */}
      {newKey && (
        <div className={styles.newKeyDisplay}>
          <p className={styles.newKeyTitle}>API Key Created</p>
          <p className={styles.newKeyWarning}>
            This key will only be shown once. Copy it now and store it securely.
          </p>
          <div className={styles.newKeyValue}>
            <span style={{ flex: 1 }} data-mono>{newKey}</span>
            <button
              type="button"
              className={styles.copyBtn}
              onClick={handleCopy}
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <button
            type="button"
            className={styles.dismissBtn}
            onClick={() => {
              setNewKey(null);
              setCopied(false);
            }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <div className={styles.createForm}>
          <p className={styles.createFormTitle}>Create New API Key</p>
          <div className={styles.createFormRow}>
            <div className={styles.createField}>
              <label className={styles.createLabel} htmlFor="key-label">
                Label
              </label>
              <input
                id="key-label"
                type="text"
                className={styles.createInput}
                placeholder="e.g. Production, Test/staging"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCreate();
                }}
                disabled={createMutation.isPending}
                autoFocus
              />
            </div>
            <div className={styles.createActions}>
              <button
                type="button"
                className={styles.createSubmit}
                onClick={handleCreate}
                disabled={!label.trim() || createMutation.isPending}
              >
                {createMutation.isPending ? "Creating..." : "Create"}
              </button>
              <button
                type="button"
                className={styles.createCancel}
                onClick={() => {
                  setShowCreate(false);
                  setLabel("");
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Key list */}
      {isLoading ? (
        <div className={styles.loading}>Loading API keys...</div>
      ) : keys.length === 0 ? (
        <div className={styles.empty}>
          <p className={styles.emptyText}>No API keys yet.</p>
        </div>
      ) : (
        <div className={styles.keyList}>
          {keys.map((key) => (
            <ApiKeyCard
              key={key.id}
              label={key.label}
              maskedKey={key.key_prefix}
              createdAt={key.created_at}
              revokedAt={key.revoked_at}
              onRevoke={
                key.revoked_at
                  ? undefined
                  : () => handleRevoke(key.id)
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
