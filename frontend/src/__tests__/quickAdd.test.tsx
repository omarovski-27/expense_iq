import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("../api/categories", () => ({
  getCategories: vi.fn().mockResolvedValue([
    { id: 1, name: "Food", color: "#fff", icon: "🍔", created_at: "" },
    { id: 2, name: "Transport", color: "#fff", icon: "🚗", created_at: "" },
  ]),
}));

vi.mock("../utils/push", () => ({
  getPushState: vi.fn().mockResolvedValue("unsupported"),
  enablePush: vi.fn(),
  disablePush: vi.fn(),
  sendTestPush: vi.fn(),
}));

import QuickAdd from "../pages/QuickAdd";

function jsonResponse(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

function renderPage() {
  return render(
    <MemoryRouter>
      <QuickAdd />
    </MemoryRouter>
  );
}

async function enterKey(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/device key/i), "k123");
  await user.click(screen.getByRole("button", { name: "Save" }));
}

describe("QuickAdd", () => {
  afterEach(() => {
    // Restore only the fetch spy; restoreAllMocks would also wipe the module mocks above.
    (globalThis.fetch as unknown as { mockRestore?: () => void }).mockRestore?.();
  });

  it("asks for a device key before allowing input", () => {
    renderPage();
    expect(screen.getByLabelText("Expense")).toBeDisabled();
    expect(screen.getByLabelText(/device key/i)).toBeInTheDocument();
  });

  it("sends the text with the key and shows the server's message", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() =>
        jsonResponse(200, { ok: true, message: "Added coffee: 2.50 JD (Food). Today: 2.50 JD" })
      );
    const user = userEvent.setup();
    renderPage();
    await enterKey(user);

    await user.type(screen.getByLabelText("Expense"), "coffee 2.5");
    await user.click(await screen.findByRole("button", { name: /Food/ }));
    await user.click(screen.getByRole("button", { name: "Add" }));

    expect(await screen.findByText(/Added coffee/)).toBeInTheDocument();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/ingest$/);
    expect((init.headers as Record<string, string>)["X-API-Key"]).toBe("k123");
    expect(JSON.parse(init.body as string)).toEqual({ text: "coffee 2.5 food" });
    expect(screen.getByLabelText("Expense")).toHaveValue("");
    expect(screen.getByRole("button", { name: /Undo/ })).toBeInTheDocument();
  });

  it("sends the date when Yesterday is selected", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => jsonResponse(200, { ok: true, message: "Added taxi" }));
    const user = userEvent.setup();
    renderPage();
    await enterKey(user);
    await user.click(screen.getByRole("button", { name: "yesterday" }));
    await user.type(screen.getByLabelText("Expense"), "taxi 4{Enter}");

    await screen.findByText("Added taxi");
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(init.body as string)).toEqual({ text: "taxi 4", date: "yesterday" });
  });

  it("keeps the text and shows the error when the server can't parse it", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      jsonResponse(422, { ok: false, message: "Couldn't read that. Try: coffee 2.5 food" })
    );
    const user = userEvent.setup();
    renderPage();
    await enterKey(user);
    await user.type(screen.getByLabelText("Expense"), "hello{Enter}");

    expect(await screen.findByText(/Couldn't read that/)).toBeInTheDocument();
    expect(screen.getByLabelText("Expense")).toHaveValue("hello");
    expect(screen.queryByRole("button", { name: /Undo/ })).not.toBeInTheDocument();
  });

  it("reopens setup when the key is rejected", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      jsonResponse(401, { detail: "Invalid API key" })
    );
    const user = userEvent.setup();
    renderPage();
    await enterKey(user);
    await waitFor(() => expect(screen.queryByLabelText(/device key/i)).not.toBeInTheDocument());
    await user.type(screen.getByLabelText("Expense"), "coffee 2{Enter}");

    expect(await screen.findByText(/Device key rejected/)).toBeInTheDocument();
    expect(screen.getByLabelText(/device key/i)).toBeInTheDocument();
  });
});
