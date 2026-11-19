import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError, type AxiosAdapter, type InternalAxiosRequestConfig } from "axios";

vi.mock("../api/ingest", () => ({
  getDeviceKey: vi.fn(() => "k1"),
  setDeviceKey: vi.fn(),
}));

import { getDeviceKey, setDeviceKey } from "../api/ingest";
import client, { AUTH_REQUIRED_EVENT } from "../api/client";
import { downloadExport, filenameFrom } from "../api/exports";
import KeyGate from "../components/auth/KeyGate";

// Fake transport: records the request and answers with the given status.
function fakeAdapter(status: number, data: unknown = {}, headers: Record<string, string> = {}) {
  const seen: InternalAxiosRequestConfig[] = [];
  const adapter: AxiosAdapter = async (config) => {
    seen.push(config);
    const response = { data, status, statusText: "", headers, config };
    if (status >= 400) {
      throw new AxiosError("fail", "ERR_BAD_REQUEST", config, null, response);
    }
    return response;
  };
  return { adapter, seen };
}

beforeEach(() => {
  vi.mocked(getDeviceKey).mockReturnValue("k1");
  vi.mocked(setDeviceKey).mockClear();
});

describe("API client", () => {
  it("sends the saved device key on every request", async () => {
    const { adapter, seen } = fakeAdapter(200);
    await client.get("/expenses/", { adapter });
    expect(seen[0].headers.get("X-API-Key")).toBe("k1");
  });

  it("sends no key header when none is saved", async () => {
    vi.mocked(getDeviceKey).mockReturnValue("");
    const { adapter, seen } = fakeAdapter(200);
    await client.get("/expenses/", { adapter });
    expect(seen[0].headers.get("X-API-Key")).toBeUndefined();
  });

  it("announces a rejected key so the key screen can open", async () => {
    const heard = vi.fn();
    window.addEventListener(AUTH_REQUIRED_EVENT, heard);
    const { adapter } = fakeAdapter(401, { detail: "Invalid or missing API key" });
    await expect(client.get("/expenses/", { adapter })).rejects.toBeTruthy();
    window.removeEventListener(AUTH_REQUIRED_EVENT, heard);
    expect(heard).toHaveBeenCalledTimes(1);
  });
});

describe("KeyGate", () => {
  it("asks for the key when none is saved, then shows the app", async () => {
    vi.mocked(getDeviceKey).mockReturnValue("");
    const user = userEvent.setup();
    render(<KeyGate><p>the app</p></KeyGate>);

    expect(screen.queryByText("the app")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/device key/i), "new-key");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(setDeviceKey).toHaveBeenCalledWith("new-key");
    expect(screen.getByText("the app")).toBeInTheDocument();
  });

  it("switches to the key screen when the server rejects the key", async () => {
    render(<KeyGate><p>the app</p></KeyGate>);
    expect(screen.getByText("the app")).toBeInTheDocument();

    act(() => {
      window.dispatchEvent(new Event(AUTH_REQUIRED_EVENT));
    });

    expect(screen.queryByText("the app")).not.toBeInTheDocument();
    expect(screen.getByText(/not accepted/i)).toBeInTheDocument();
  });
});

describe("downloadExport", () => {
  const created: string[] = [];
  let clicked: HTMLAnchorElement | null = null;

  beforeEach(() => {
    clicked = null;
    URL.createObjectURL = vi.fn(() => {
      created.push("blob:x");
      return "blob:x";
    });
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clicked = this;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches with the key and saves the file under the server's name", async () => {
    const { adapter, seen } = fakeAdapter(200, new Blob(["a,b"]), {
      "content-disposition": 'attachment; filename="expenseiq_report_2026_05.xlsx"',
    });
    const original = client.defaults.adapter;
    client.defaults.adapter = adapter;
    try {
      await downloadExport("excel", { month: 5, year: 2026 });
    } finally {
      client.defaults.adapter = original;
    }

    expect(seen[0].url).toBe("/exports/excel");
    expect(seen[0].params).toEqual({ month: 5, year: 2026 });
    expect(seen[0].headers.get("X-API-Key")).toBe("k1");
    expect(clicked?.download).toBe("expenseiq_report_2026_05.xlsx");
    expect(clicked?.href).toBe("blob:x");
  });

  it("reads the file name from the header", () => {
    expect(filenameFrom('attachment; filename="expenses.csv"')).toBe("expenses.csv");
    expect(filenameFrom(undefined)).toBeUndefined();
  });
});
