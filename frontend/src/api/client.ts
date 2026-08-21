import type { ErrorEnvelope } from "@/types/backend";

// API base URL: env var > localStorage > empty (relative)
function getApiBase(): string {
  const envBase = import.meta.env.VITE_API_BASE;
  if (envBase) return envBase;
  try {
    return localStorage.getItem("freightpipe_api_base") ?? "https://freightpipe.onrender.com/v1";
  } catch {
    return "";
  }
}

export function setApiBase(url: string) {
  try {
    localStorage.setItem("freightpipe_api_base", url.replace(/\/+$/, ""));
  } catch {
    // ignore
  }
}

export function getApiBaseUrl(): string {
  return getApiBase();
}

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

function getToken(): string | null {
  return localStorage.getItem("freightpipe_token");
}

function getApiKey(): string | null {
  return localStorage.getItem("freightpipe_api_key");
}

export function setToken(token: string): void {
  localStorage.setItem("freightpipe_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("freightpipe_token");
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

  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const apiKey = getApiKey();
  if (apiKey) {
    headers.set("X-Api-Key", apiKey);
  }

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${getApiBase()}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    if (res.status === 401) {
      clearToken();
      if (
        !window.location.pathname.startsWith("/login") &&
        !window.location.pathname.startsWith("/register") &&
        window.location.pathname !== "/" &&
        !window.location.pathname.startsWith("/docs")
      ) {
        window.location.href = "/login";
      }
    }

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
