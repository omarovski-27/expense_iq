// Service worker registration and Web Push subscription for this device.
import { API_BASE, authedPost } from "../api/ingest";

export type PushState = "unsupported" | "needs-install" | "denied" | "off" | "on";

export function registerServiceWorker(): void {
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* app still works without it; it just can't be installed or receive push */
    });
  });
}

function isIos(): boolean {
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

export function isStandalone(): boolean {
  const nav = navigator as Navigator & { standalone?: boolean };
  return window.matchMedia?.("(display-mode: standalone)").matches || nav.standalone === true;
}

function urlBase64ToUint8Array(base64: string) {
  const padded = (base64 + "=".repeat((4 - (base64.length % 4)) % 4))
    .replace(/-/g, "+")
    .replace(/_/g, "/");
  const raw = atob(padded);
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

export async function getPushState(): Promise<PushState> {
  // iOS only exposes push to web apps added to the home screen.
  if (isIos() && !isStandalone()) return "needs-install";
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
    return "unsupported";
  }
  if (Notification.permission === "denied") return "denied";
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  return sub ? "on" : "off";
}

export async function enablePush(deviceKey: string): Promise<PushState> {
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return permission === "denied" ? "denied" : "off";

  const keyRes = await fetch(`${API_BASE}/notify/vapid-public-key`);
  if (!keyRes.ok) throw new Error("Push isn't configured on the server yet.");
  const { key } = (await keyRes.json()) as { key: string };

  const reg = await navigator.serviceWorker.ready;
  const sub =
    (await reg.pushManager.getSubscription()) ??
    (await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(key),
    }));

  const res = await authedPost("/notify/subscribe", deviceKey, sub.toJSON());
  if (!res.ok) {
    await sub.unsubscribe();
    throw new Error(res.status === 401 ? "Device key rejected." : "Couldn't save the subscription.");
  }
  return "on";
}

export async function disablePush(deviceKey: string): Promise<PushState> {
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  if (sub) {
    await authedPost("/notify/unsubscribe", deviceKey, { endpoint: sub.endpoint }).catch(() => {});
    await sub.unsubscribe();
  }
  return "off";
}

export async function sendTestPush(deviceKey: string): Promise<string> {
  const res = await authedPost("/notify/test", deviceKey, {});
  if (!res.ok) return "Test failed.";
  const { sent } = (await res.json()) as { sent: number };
  return sent > 0 ? "Test sent. It should arrive in a few seconds." : "No devices received it.";
}
