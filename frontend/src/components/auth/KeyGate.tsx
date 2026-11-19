import { Fragment, useEffect, useState, type ReactNode } from "react";
import { AUTH_REQUIRED_EVENT } from "../../api/client";
import { getDeviceKey, setDeviceKey } from "../../api/ingest";
import DeviceKeyForm from "./DeviceKeyForm";

// Shows one "enter your device key" screen when no key is saved, or when the
// server rejects the saved one. After a new key is saved, the pages below are
// remounted so they load their data again with it.
export default function KeyGate({ children }: { children: ReactNode }) {
  const [key, setKey] = useState(getDeviceKey);
  const [rejected, setRejected] = useState(false);
  const [generation, setGeneration] = useState(0);

  useEffect(() => {
    const onRejected = () => setRejected(true);
    window.addEventListener(AUTH_REQUIRED_EVENT, onRejected);
    return () => window.removeEventListener(AUTH_REQUIRED_EVENT, onRejected);
  }, []);

  function save(next: string) {
    if (!next) return;
    setDeviceKey(next);
    setKey(next);
    setRejected(false);
    setGeneration((g) => g + 1);
  }

  if (!key || rejected) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-900 px-4 text-white">
        <div className="w-full max-w-sm space-y-4 rounded-xl border border-gray-800 bg-gray-950 p-5">
          <h1 className="text-lg font-bold">
            <span className="text-amber-400">$</span> ExpenseIQ
          </h1>
          <p className="text-sm text-gray-400">
            {rejected
              ? "That device key was not accepted. Enter the current one."
              : "Enter your device key to open your expenses."}
          </p>
          <DeviceKeyForm key={generation} initial={key} onSave={save} autoFocus />
        </div>
      </div>
    );
  }

  return <Fragment key={generation}>{children}</Fragment>;
}
