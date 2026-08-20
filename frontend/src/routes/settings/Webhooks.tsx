import { useState, useCallback, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getWebhookConfig, updateWebhookConfig } from "@/api/settings";
import { testWebhook } from "@/api/webhooks";
import { ApiClientError } from "@/api/client";
import styles from "./Webhooks.module.css";

export default function Webhooks() {
  const queryClient = useQueryClient();
  const [webhookUrl, setWebhookUrl] = useState("");
  const [hasChanges, setHasChanges] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [testResult, setTestResult] = useState<{
    delivered: boolean;
    message: string;
  } | null>(null);
  const [testing, setTesting] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["webhook-config"],
    queryFn: getWebhookConfig,
    retry: (failureCount, err: Error) => {
      if (err.message?.includes("404")) return false;
      return failureCount < 2;
    },
  });

  useEffect(() => {
    if (data?.webhook_url) {
      setWebhookUrl(data.webhook_url);
    }
  }, [data]);

  const updateMutation = useMutation({
    mutationFn: (url: string) => updateWebhookConfig({ webhook_url: url }),
    onSuccess: () => {
      setSuccess(true);
      setHasChanges(false);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["webhook-config"] });
      setTimeout(() => setSuccess(false), 3000);
    },
    onError: (err: Error) => {
      if (err instanceof ApiClientError) {
        setError(err.error.message);
      } else {
        setError("Failed to update webhook configuration");
      }
    },
  });

  const handleSave = useCallback(() => {
    if (!webhookUrl.trim()) return;
    setError(null);
    setSuccess(false);
    updateMutation.mutate(webhookUrl.trim());
  }, [webhookUrl, updateMutation]);

  const handleTest = useCallback(async () => {
    if (!webhookUrl) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testWebhook(webhookUrl);
      setTestResult({
        delivered: res.delivered,
        message: res.delivered
          ? "Delivered successfully"
          : `Failed: ${res.error ?? "unknown error"}`,
      });
    } catch {
      setTestResult({ delivered: false, message: "Test request failed" });
    } finally {
      setTesting(false);
    }
  }, [webhookUrl]);

  const handleUrlChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setWebhookUrl(e.target.value);
      setHasChanges(true);
      setTestResult(null);
      setSuccess(false);
    },
    [],
  );

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <h1 className={styles.title}>Webhooks</h1>
        </div>
        <div className={styles.loading}>Loading webhook configuration...</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Webhooks</h1>
      </div>

      <p className={styles.description}>
        Configure a default webhook URL for your account. FreightPipe will send
        POST requests to this URL for events like job completion, review needed,
        and failures. Per-job webhook URLs override this default when provided.
      </p>

      {error && (
        <div className={styles.error} role="alert">{error}</div>
      )}

      {success && (
        <div className={styles.success}>Webhook configuration saved.</div>
      )}

      <div className={styles.form}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="webhook-url">
            Webhook URL
          </label>
          <div className={styles.inputRow}>
            <div className={styles.field}>
              <input
                id="webhook-url"
                type="url"
                className={styles.input}
                placeholder="https://example.com/hooks/freightpipe"
                value={webhookUrl}
                onChange={handleUrlChange}
                disabled={updateMutation.isPending}
              />
            </div>
          </div>
        </div>

        {data?.webhook_secret && (
          <div className={styles.secretField}>
            <span className={styles.secretLabel}>Webhook Secret</span>
            <div className={styles.secretValue}>
              <span data-mono>{data.webhook_secret}</span>
            </div>
            <span className={styles.description}>
              Use this secret to verify webhook signatures. FreightPipe sends
              X-FreightPipe-Signature header with each delivery.
            </span>
          </div>
        )}

        {data?.updated_at && (
          <span className={styles.updatedAt}>
            Last updated:{" "}
            {new Date(data.updated_at).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        )}

        {testResult && (
          <div
            className={styles.testResult}
            data-success={testResult.delivered}
          >
            {testResult.message}
          </div>
        )}

        <div className={styles.actions}>
          <button
            type="button"
            className={styles.saveBtn}
            onClick={handleSave}
            disabled={!webhookUrl.trim() || !hasChanges || updateMutation.isPending}
          >
            {updateMutation.isPending ? (
              <>
                <span className={styles.spinner} /> Saving...
              </>
            ) : (
              "Save"
            )}
          </button>
          <button
            type="button"
            className={styles.testBtn}
            onClick={handleTest}
            disabled={!webhookUrl.trim() || testing}
          >
            {testing ? "Testing..." : "Test"}
          </button>
        </div>
      </div>
    </div>
  );
}
