// Quick-capture API: the same free-text endpoint the iOS Shortcut uses.
// Uses fetch rather than the shared axios client so this page can show the
// server's own message inline instead of the global error toasts.

const env = (import.meta as ImportMeta & { env?: { VITE_API_URL?: string } }).env;
export const API_BASE = env?.VITE_API_URL ?? "http://localhost:8000/api";

const LS_DEVICE_KEY = "expenseiq_device_key";

// Browser storage can be unavailable (private mode, some embedded views), so
// every access is guarded.
export function getDeviceKey(): string {
  try {
    return localStorage.getItem(LS_DEVICE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setDeviceKey(key: string): void {
  try {
    if (key) localStorage.setItem(LS_DEVICE_KEY, key);
    else localStorage.removeItem(LS_DEVICE_KEY);
  } catch {
    /* storage unavailable: key lives only for this page view */
  }
}

export interface IngestResult {
  ok: boolean;
  message: string;
  status: number;
}

export async function authedPost(
  path: string,
  key: string,
  body: unknown,
  timeoutMs = 60000
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": key },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

export async function ingest(
  key: string,
  text: string,
  date?: "today" | "yesterday"
): Promise<IngestResult> {
  let res: Response;
  try {
    res = await authedPost("/ingest", key, date && date !== "today" ? { text, date } : { text });
  } catch {
    return { ok: false, status: 0, message: "Couldn't reach the server. Try again." };
  }
  if (res.status === 401) {
    return { ok: false, status: 401, message: "Device key rejected. Check it in setup." };
  }
  let data: { ok?: boolean; message?: string; detail?: unknown } = {};
  try {
    data = await res.json();
  } catch {
    /* non-JSON error page */
  }
  const message =
    data.message ??
    (typeof data.detail === "string" ? data.detail : res.ok ? "Saved." : "Something went wrong.");
  return { ok: res.ok && data.ok !== false, status: res.status, message };
}
