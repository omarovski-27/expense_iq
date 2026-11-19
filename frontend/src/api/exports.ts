import client from "./client";

export type ExportType = "csv" | "excel";

// Exports need the device key, so they are fetched with it and saved as a
// file, instead of opening the export address in a new tab (which can't
// send the key).
export async function downloadExport(
  type: ExportType,
  params: { month?: number; year?: number } = {}
): Promise<void> {
  const res = await client.get<Blob>(`/exports/${type}`, { params, responseType: "blob" });
  const fallback = type === "csv" ? "expenses.csv" : "expenseiq_report.xlsx";
  const filename = filenameFrom(res.headers["content-disposition"]) ?? fallback;

  const url = URL.createObjectURL(res.data);
  try {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    // Give the browser a moment to start the download before freeing it.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}

export function filenameFrom(header: unknown): string | undefined {
  if (typeof header !== "string") return undefined;
  const match = /filename="?([^";]+)"?/i.exec(header);
  return match?.[1];
}
