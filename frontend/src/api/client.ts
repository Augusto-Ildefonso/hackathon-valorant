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

/** Downloads the printable plan (a text-first PDF). Resolves with how the body was written: "llm" or "rules". */
export async function downloadPlanPdf(body: unknown): Promise<{ source: string; note: string }> {
  if (USE_MOCKS) throw new Error("o PDF precisa do backend (modo de mock ativo)");
  const res = await fetch("/api/plan/report", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  const name = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? "plano-de-acao.pdf";
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
  return { source: res.headers.get("X-Report-Source") ?? "rules", note: decodeURIComponent(res.headers.get("X-Report-Note") ?? "") };
}

/** Image URL for catalog assets (already prefixed with /assets by the backend). */
export const assetUrl = (url: string | null | undefined) => url ?? undefined;
