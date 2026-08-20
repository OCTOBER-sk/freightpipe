// API client — fetch wrapper with X-Api-Key injection, error handling, base URL
// BACKEND.md §4: Auth via header X-Api-Key on every request

import type { ErrorEnvelope } from "@/types/backend";

const API_BASE = import.meta.env.VITE_API_BASE ?? "https://api.freightpipe.dev/v1";

export class ApiClientError extends Error {
  status: number;
  error: ErrorEnvelope;

  constructor(status: number, error: ErrorEnvelope) {
    super(error.message);
    this.name = "ApiClientError";
    this.status = status;
    this.error = error;
  }
}

function getApiKey(): string | null {
  return localStorage.getItem("freightpipe_api_key");
}

export function setApiKey(key: string): void {
  localStorage.setItem("freightpipe_api_key", key);
}

export function clearApiKey(): void {
  localStorage.removeItem("freightpipe_api_key");
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  const apiKey = getApiKey();
  if (apiKey) {
    headers.set("X-Api-Key", apiKey);
  }

  // Don't set Content-Type for FormData (browser sets boundary automatically)
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let error: ErrorEnvelope;
    try {
      const body = await res.json();
      error = body.error ?? body;
    } catch {
      error = {
        code: "internal_error",
        message: res.statusText,
        request_id: "",
      };
    }
    throw new ApiClientError(res.status, error);
  }

  // Handle 204 No Content
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export function apiGet<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "GET" });
}

export function apiPost<T>(path: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    body: body instanceof FormData ? body : JSON.stringify(body),
    headers,
  });
}

export function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function apiDelete<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "DELETE" });
}
