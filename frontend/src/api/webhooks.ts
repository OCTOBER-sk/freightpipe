// Webhooks API — BACKEND.md §4.1
import { apiPost } from "./client";
import type { WebhookTestResponse } from "@/types/backend";

/**
 * POST /v1/webhooks/test — send test payload to verify connectivity
 * §4.1: returns {delivered: true/false, status_code?, error?}
 */
export function testWebhook(webhookUrl: string): Promise<WebhookTestResponse> {
  return apiPost<WebhookTestResponse>("/webhooks/test", { webhook_url: webhookUrl });
}
