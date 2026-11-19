import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Bell, BellOff, LayoutDashboard, Loader2, Settings2, Undo2 } from "lucide-react";
import { getDeviceKey, ingest, setDeviceKey } from "../api/ingest";
import { getCategories } from "../api/categories";
import {
  disablePush,
  enablePush,
  getPushState,
  sendTestPush,
  type PushState,
} from "../utils/push";
import type { Category } from "../types";
import DeviceKeyForm from "../components/auth/DeviceKeyForm";

type Day = "today" | "yesterday";
interface Status {
  ok: boolean;
  text: string;
}

function DeviceSetup({
  deviceKey,
  onKeyChange,
}: {
  deviceKey: string;
  onKeyChange: (k: string) => void;
}) {
  const [push, setPush] = useState<PushState | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getPushState().then(setPush).catch(() => setPush("unsupported"));
  }, []);

  async function togglePush() {
    setBusy(true);
    setNote("");
    try {
      setPush(push === "on" ? await disablePush(deviceKey) : await enablePush(deviceKey));
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Couldn't change notifications.");
    } finally {
      setBusy(false);
    }
  }

  const pushHint: Record<PushState, string> = {
    unsupported: "This browser can't receive notifications.",
    "needs-install": "On iPhone, add this page to your Home Screen first (Share → Add to Home Screen), then open it from there.",
    denied: "Notifications are blocked. Allow them for this app in system settings.",
    off: "Get notified when a subscription is charged.",
    on: "Notifications are on for this device.",
  };

  return (
    <div className="space-y-4 rounded-xl border border-gray-800 bg-gray-950 p-4">
      <DeviceKeyForm initial={deviceKey} onSave={onKeyChange} />

      {deviceKey && push && (
        <div>
          <p className="mb-2 text-sm text-gray-400">{pushHint[push]}</p>
          {(push === "on" || push === "off") && (
            <div className="flex gap-2">
              <button
                onClick={togglePush}
                disabled={busy}
                className="flex h-10 items-center gap-2 rounded-lg border border-gray-700 px-3 text-sm touch-manipulation"
              >
                {push === "on" ? <BellOff size={16} /> : <Bell size={16} />}
                {push === "on" ? "Turn off notifications" : "Turn on notifications"}
              </button>
              {push === "on" && (
                <button
                  onClick={async () => setNote(await sendTestPush(deviceKey))}
                  className="h-10 rounded-lg border border-gray-700 px-3 text-sm touch-manipulation"
                >
                  Send test
                </button>
              )}
            </div>
          )}
          {note && <p className="mt-2 text-sm text-gray-400">{note}</p>}
        </div>
      )}
    </div>
  );
}

export default function QuickAdd() {
  const [deviceKey, setKey] = useState(getDeviceKey);
  const [showSetup, setShowSetup] = useState(!getDeviceKey());
  const [text, setText] = useState("");
  const [day, setDay] = useState<Day>("today");
  const [categories, setCategories] = useState<Category[]>([]);
  const [sending, setSending] = useState(false);
  const [slow, setSlow] = useState(false);
  const [status, setStatus] = useState<Status | null>(null);
  const [canUndo, setCanUndo] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getCategories().then(setCategories).catch(() => setCategories([]));
  }, []);

  function saveKey(k: string) {
    setDeviceKey(k);
    setKey(k);
    if (k) setShowSetup(false);
    inputRef.current?.focus();
  }

  async function send(payload: string, sendDay: Day) {
    if (!payload.trim() || sending) return;
    setSending(true);
    setStatus(null);
    const slowTimer = setTimeout(() => setSlow(true), 3000);
    const result = await ingest(deviceKey, payload.trim(), sendDay);
    clearTimeout(slowTimer);
    setSlow(false);
    setSending(false);
    setStatus({ ok: result.ok, text: result.message });
    if (result.status === 401) setShowSetup(true);
    return result;
  }

  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    const result = await send(text, day);
    if (result?.ok) {
      setText("");
      setDay("today");
      setCanUndo(true);
    }
    inputRef.current?.focus();
  }

  async function undo() {
    const result = await send("undo", "today");
    if (result?.ok || result?.status === 404 || result?.status === 409) setCanUndo(false);
  }

  function addCategory(name: string) {
    const words = text.trim().split(/\s+/).filter(Boolean);
    const known = new Set(categories.map((c) => c.name.toLowerCase()));
    const kept = words.filter((w) => !known.has(w.toLowerCase()));
    setText([...kept, name.toLowerCase()].join(" ") + " ");
    inputRef.current?.focus();
  }

  return (
    <div className="min-h-screen bg-gray-900 px-4 pb-10 pt-[max(1rem,env(safe-area-inset-top))] text-white">
      <div className="mx-auto max-w-md space-y-5">
        <header className="flex items-center justify-between">
          <span className="text-lg font-bold">
            <span className="text-amber-400">$</span> ExpenseIQ
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowSetup((s) => !s)}
              className="rounded-lg p-2 text-gray-400 hover:text-white touch-manipulation"
              aria-label="Device setup"
            >
              <Settings2 size={20} />
            </button>
            <Link
              to="/"
              className="flex items-center gap-1 rounded-lg p-2 text-sm text-gray-400 hover:text-white"
            >
              <LayoutDashboard size={18} /> Dashboard
            </Link>
          </div>
        </header>

        {showSetup && <DeviceSetup deviceKey={deviceKey} onKeyChange={saveKey} />}

        <form onSubmit={submit} className="space-y-3">
          <input
            ref={inputRef}
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={!deviceKey}
            enterKeyHint="send"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            inputMode="text"
            placeholder={deviceKey ? "coffee 2.5 food" : "Add your device key first"}
            aria-label="Expense"
            className="h-14 w-full rounded-xl border border-gray-700 bg-gray-950 px-4 text-xl text-white placeholder-gray-600 focus:border-amber-500 focus:outline-none disabled:opacity-50"
          />

          <div className="flex items-center gap-2">
            {(["today", "yesterday"] as Day[]).map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setDay(d)}
                className={[
                  "h-9 rounded-full px-4 text-sm capitalize touch-manipulation",
                  day === d ? "bg-amber-500 text-gray-950" : "border border-gray-700 text-gray-400",
                ].join(" ")}
              >
                {d}
              </button>
            ))}
            <button
              type="submit"
              disabled={!deviceKey || !text.trim() || sending}
              className="ml-auto flex h-11 min-w-24 items-center justify-center rounded-xl bg-amber-500 px-5 font-semibold text-gray-950 disabled:opacity-40 touch-manipulation"
            >
              {sending ? <Loader2 size={18} className="animate-spin" /> : "Add"}
            </button>
          </div>

          {categories.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {categories.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => addCategory(c.name)}
                  className="h-9 rounded-full border border-gray-800 bg-gray-950 px-3 text-sm text-gray-300 touch-manipulation"
                >
                  {c.icon} {c.name}
                </button>
              ))}
            </div>
          )}
        </form>

        <div aria-live="polite" className="min-h-[3rem]">
          {slow && <p className="text-sm text-gray-500">Waking the server up, this can take ~30s…</p>}
          {status && (
            <div className="flex items-start justify-between gap-3">
              <p className={status.ok ? "text-green-400" : "text-red-400"}>{status.text}</p>
              {canUndo && status.ok && (
                <button
                  onClick={undo}
                  disabled={sending}
                  className="flex shrink-0 items-center gap-1 rounded-lg border border-gray-700 px-3 py-1.5 text-sm text-gray-300 touch-manipulation"
                >
                  <Undo2 size={14} /> Undo
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
