// Settings API — BACKEND.md §4.1
// API key CRUD + account-level webhook configuration
import { apiGet, apiPost, apiDelete, apiPut } from "./client";
import type {
  ApiKeyListResponse,
  ApiKeyCreateResponse,
  ApiKeyRevokeResponse,
  WebhookConfig,
  WebhookConfigUpdate,
} from "@/types/backend";

// ── API Keys ────────────────────────────────────────────────────────────────

/**
 * GET /v1/api-keys — list API keys (masked)
 * §4.1: returns {items: [{id, label, key_prefix, created_at, revoked_at}]}
 */
export function listApiKeys(): Promise<ApiKeyListResponse> {
  return apiGet<ApiKeyListResponse>("/api-keys");
}

/**
 * POST /v1/api-keys — create a new API key
 * §4.1: raw key returned ONLY in this response, stored as key_hash
 */
export function createApiKey(label: string): Promise<ApiKeyCreateResponse> {
  return apiPost<ApiKeyCreateResponse>("/api-keys", { label });
}

/**
 * DELETE /v1/api-keys/{key_id} — revoke an API key
 * §4.1: returns {id, revoked_at}
 */
export function revokeApiKey(keyId: string): Promise<ApiKeyRevokeResponse> {
  return apiDelete<ApiKeyRevokeResponse>(`/api-keys/${keyId}`);
}

// ── Webhook Settings ────────────────────────────────────────────────────────

/**
 * GET /v1/settings/webhook — get account-level default webhook config
 * §4.1: returns {webhook_url, webhook_secret, updated_at}
 * 404 if no account-level webhook configured
 */
export function getWebhookConfig(): Promise<WebhookConfig> {
  return apiGet<WebhookConfig>("/settings/webhook");
}

/**
 * PUT /v1/settings/webhook — set/update account-level default webhook
 * §4.1: per-job webhook_url in POST /v1/documents overrides this default
 */
export function updateWebhookConfig(data: WebhookConfigUpdate): Promise<WebhookConfig> {
  return apiPut<WebhookConfig>("/settings/webhook", data);
}
