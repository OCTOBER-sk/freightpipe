import { useState, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { submitDocument } from "@/api/jobs";
import { testWebhook } from "@/api/webhooks";
import { ApiClientError } from "@/api/client";
import UploadZone from "@/components/UploadZone";
import styles from "./JobSubmit.module.css";

const ERROR_MESSAGES: Record<string, string> = {
  invalid_pdf:
    "This file couldn't be read as a PDF. Check that it's not corrupted and try again.",
  file_too_large:
    "This file is too large \u2014 FreightPipe accepts PDFs up to 25MB. Try splitting it into separate documents.",
  rate_limited: "Rate limit reached. You can submit again in",
  internal_error: "Something went wrong. Please try again.",
};

export default function JobSubmit() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);
  const [retryAfter, setRetryAfter] = useState<number | null>(null);

  const [testResult, setTestResult] = useState<{
    delivered: boolean;
    message: string;
  } | null>(null);
  const [testingWebhook, setTestingWebhook] = useState(false);

  const submitMutation = useMutation({
    mutationFn: () =>
      submitDocument({
        file: file!,
        webhookUrl: webhookUrl || undefined,
        idempotencyKey: idempotencyKey || undefined,
      }),
    onSuccess: (data) => {
      navigate(`/jobs/${data.job_id}`);
    },
    onError: (err: Error) => {
      if (err instanceof ApiClientError) {
        const code = err.error.code;
        let message = ERROR_MESSAGES[code] ?? err.error.message;

        if (code === "rate_limited") {
          const retryHeader = err.status === 429 ? 60 : null;
          if (retryHeader) {
            setRetryAfter(retryHeader);
            startCountdown(retryHeader);
          }
          message = ERROR_MESSAGES.rate_limited;
        }

        setError({ code, message });
      } else {
        setError({ code: "internal_error", message: ERROR_MESSAGES.internal_error });
      }
    },
  });

  const startCountdown = useCallback((seconds: number) => {
    let remaining = seconds;
    const interval = setInterval(() => {
      remaining -= 1;
      setRetryAfter(remaining);
      if (remaining <= 0) {
        clearInterval(interval);
        setRetryAfter(null);
      }
    }, 1000);
  }, []);

  const handleTestWebhook = useCallback(async () => {
    if (!webhookUrl) return;
    setTestingWebhook(true);
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
      setTestingWebhook(false);
    }
  }, [webhookUrl]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!file) return;
      setError(null);
      setRetryAfter(null);
      submitMutation.mutate();
    },
    [file, submitMutation],
  );

  const isSubmitting = submitMutation.isPending;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Link to="/jobs" className={styles.back}>
          {"< Jobs"}
        </Link>
        <h1 className={styles.title}>Submit Document</h1>
      </div>

      <form className={styles.form} onSubmit={handleSubmit}>
        <UploadZone
          onFileSelect={setFile}
          file={file}
          state={isSubmitting ? "uploading" : undefined}
          disabled={isSubmitting}
        />

        {error && (
          <div
            className={styles.error}
            data-code={error.code}
            role="alert"
          >
            {error.code === "rate_limited" && retryAfter != null ? (
              <>
                {error.message} {Math.floor(retryAfter / 60)}:
                {String(retryAfter % 60).padStart(2, "0")}.
              </>
            ) : (
              error.message
            )}
          </div>
        )}

        <div className={styles.field}>
          <label className={styles.label} htmlFor="webhook-url">
            Webhook URL (optional)
          </label>
          <div className={styles.fieldRow}>
            <div className={styles.field} style={{ flex: 1 }}>
              <input
                id="webhook-url"
                type="url"
                className={styles.input}
                placeholder="https://example.com/hooks/freightpipe"
                value={webhookUrl}
                onChange={(e) => {
                  setWebhookUrl(e.target.value);
                  setTestResult(null);
                }}
                disabled={isSubmitting}
              />
            </div>
            <button
              type="button"
              className={styles.testBtn}
              onClick={handleTestWebhook}
              disabled={!webhookUrl || testingWebhook || isSubmitting}
            >
              {testingWebhook ? "Testing..." : "Test"}
            </button>
          </div>
          {testResult && (
            <span
              className={styles.testResult}
              data-success={testResult.delivered}
            >
              {testResult.message}
            </span>
          )}
        </div>

        <div>
          <button
            type="button"
            className={styles.advancedToggle}
            onClick={() => setShowAdvanced((v) => !v)}
            aria-expanded={showAdvanced}
          >
            {showAdvanced ? "▾" : "▸"} Advanced options
          </button>
          {showAdvanced && (
            <div className={styles.advancedContent}>
              <div className={styles.field}>
                <label className={styles.label} htmlFor="idempotency-key">
                  Idempotency key (optional)
                </label>
                <input
                  id="idempotency-key"
                  type="text"
                  className={styles.input}
                  placeholder="Unique key to prevent duplicate submissions"
                  value={idempotencyKey}
                  onChange={(e) => setIdempotencyKey(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
            </div>
          )}
        </div>

        <div className={styles.actions}>
          <button
            type="submit"
            className={styles.submitBtn}
            disabled={!file || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className={styles.spinner} /> Submitting...
              </>
            ) : (
              "Submit Document"
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
