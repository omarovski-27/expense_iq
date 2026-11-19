import { useState } from "react";
import { KeyRound } from "lucide-react";

// The device key input shared by Quick Add's setup panel and the app's key screen.
export default function DeviceKeyForm({
  initial = "",
  onSave,
  autoFocus = false,
}: {
  initial?: string;
  onSave: (key: string) => void;
  autoFocus?: boolean;
}) {
  const [draft, setDraft] = useState(initial);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSave(draft.trim());
      }}
    >
      <label className="mb-1 flex items-center gap-2 text-sm text-gray-400" htmlFor="device-key">
        <KeyRound size={14} /> Device key
      </label>
      <div className="flex gap-2">
        <input
          id="device-key"
          type="password"
          autoComplete="off"
          autoFocus={autoFocus}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="h-11 flex-1 rounded-lg border border-gray-700 bg-gray-900 px-3 text-base text-white focus:border-amber-500 focus:outline-none"
          placeholder="Your INGEST_API_KEY"
        />
        <button
          type="submit"
          className="h-11 rounded-lg bg-amber-500 px-4 font-medium text-gray-950 touch-manipulation"
        >
          Save
        </button>
      </div>
      <p className="mt-1 text-xs text-gray-500">Stored on this device only.</p>
    </form>
  );
}
