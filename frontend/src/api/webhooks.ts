import { apiGet, apiPost, apiDelete } from "./client";
import type {
  Webhook,
  WebhookCreateRequest,
} from "@/types/backend";

export function listWebhooks(): Promise<Webhook[]> {
  return apiGet<Webhook[]>("/webhooks");
}

export function getWebhook(webhookId: string): Promise<Webhook> {
  return apiGet<Webhook>(`/webhooks/${webhookId}`);
}

export function createWebhook(data: WebhookCreateRequest): Promise<Webhook> {
  return apiPost<Webhook>("/webhooks", data);
}

export function deleteWebhook(webhookId: string): Promise<void> {
  return apiDelete<void>(`/webhooks/${webhookId}`);
}

export function testWebhook(webhookId: string): Promise<{ success: boolean }> {
  return apiPost<{ success: boolean }>(`/webhooks/${webhookId}/test`);
}
