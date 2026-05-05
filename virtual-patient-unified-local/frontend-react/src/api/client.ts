// Backend origin — reads from env for deployed split-host setup, falls back to same-origin
export const BACKEND_URL = import.meta.env.VITE_API_URL || "";

// API base URL
const BASE = BACKEND_URL + "/api";

interface RequestOptions {
  method?: string;
  body?: unknown;
  token?: string;
}

export async function apiFetch<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, token } = opts;

  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body) headers["Content-Type"] = "application/json";

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json();
}

/** Resolve a backend-relative path (e.g. /uploads/avatars/foo.png) to a full URL */
export function backendAsset(path: string): string {
  return `${BACKEND_URL}${path}`;
}
