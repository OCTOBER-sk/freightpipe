import { apiGet, apiPost, apiDelete } from "./client";
import type {
  ApiKey,
  ApiKeyCreateRequest,
  ApiKeyCreateResponse,
} from "@/types/backend";

export function listApiKeys(): Promise<ApiKey[]> {
  return apiGet<ApiKey[]>("/settings/api-keys");
}

export function createApiKey(data: ApiKeyCreateRequest): Promise<ApiKeyCreateResponse> {
  return apiPost<ApiKeyCreateResponse>("/settings/api-keys", data);
}

export function revokeApiKey(keyId: string): Promise<void> {
  return apiDelete<void>(`/settings/api-keys/${keyId}`);
}
