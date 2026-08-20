import type { ApiError } from "@/types/backend";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export class ApiClientError extends Error {
  status: number;
  body: ApiError;

  constructor(status: number, body: ApiError) {
    super(body.detail);
    this.name = "ApiClientError";
    this.status = status;
    this.body = body;
  }
}

function getApiKey(): string | null {
  return localStorage.getItem("freightpipe_api_key");
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
    let body: ApiError;
    try {
      body = await res.json();
    } catch {
      body = { detail: res.statusText, status_code: res.status };
    }
    throw new ApiClientError(res.status, body);
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

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    body: body instanceof FormData ? body : JSON.stringify(body),
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
