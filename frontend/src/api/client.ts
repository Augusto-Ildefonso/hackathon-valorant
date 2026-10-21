// API client. Owner: Stream E. All screens go through `api()`; mocks are switched by VITE_USE_MOCKS=1.
import { mockResponse } from "./mock";

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "1";

export type Query = Record<string, string | number | undefined | null>;

export function withQuery(path: string, query?: Query): string {
  if (!query) return path;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  const s = qs.toString();
  return s ? `${path}?${s}` : path;
}

export async function api<T>(path: string, opts?: { query?: Query; body?: unknown }): Promise<T> {
  const url = withQuery(path, opts?.query);
  if (USE_MOCKS) return mockResponse(url) as T;
  const res = await fetch(url, {
    method: opts?.body ? "POST" : "GET",
    headers: opts?.body ? { "Content-Type": "application/json" } : undefined,
    body: opts?.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  return (await res.json()) as T;
}

/** Image URL for catalog assets (already prefixed with /assets by the backend). */
export const assetUrl = (url: string | null | undefined) => url ?? undefined;
