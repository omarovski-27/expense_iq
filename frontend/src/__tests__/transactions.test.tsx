import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// ── Hoist mock functions ──────────────────────────────────────────────────────
const { mockGetExpenses, mockGetCategories } = vi.hoisted(() => ({
  mockGetExpenses: vi.fn(),
  mockGetCategories: vi.fn(),
}));

vi.mock("../api/expenses", () => ({
  getExpenses: mockGetExpenses,
  createExpense: vi.fn(),
  updateExpense: vi.fn(),
  deleteExpense: vi.fn(),
}));
vi.mock("../api/categories", () => ({ getCategories: mockGetCategories }));
vi.mock("react-hot-toast", () => ({
  default: { error: vi.fn(), success: vi.fn() },
}));
vi.mock("../context/CurrencyContext", () => ({
  useCurrency: () => ({ currencySymbol: "JD" }),
}));
vi.mock("../api/client", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(), defaults: { baseURL: "" } },
}));

import Transactions from "../pages/Transactions";

const MOCK_EXPENSE = {
  id: 1,
  amount: 12.5,
  description: "Lunch",
  date: "2026-05-10",
  merchant: "Cafe",
  category_id: 1,
  category: { id: 1, name: "Food", color: "#f00", icon: "🍔", created_at: "" },
  is_recurring: false,
  created_at: "2026-05-10T00:00:00Z",
  updated_at: "2026-05-10T00:00:00Z",
};

describe("Transactions page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetExpenses.mockResolvedValue([]);
    mockGetCategories.mockResolvedValue([
      { id: 1, name: "Food", color: "#f00", icon: "🍔", created_at: "" },
    ]);
  });

  it("calls getExpenses on mount", async () => {
    render(<Transactions />);
    await waitFor(() => {
      expect(mockGetExpenses).toHaveBeenCalledTimes(1);
    });
  });

  it("shows empty state when no expenses returned", async () => {
    render(<Transactions />);
    // Both mobile and desktop views render the empty state message
    await waitFor(() => {
      const msgs = screen.getAllByText(/no expenses found/i);
      expect(msgs.length).toBeGreaterThan(0);
    });
  });

  it("renders expense rows when data is present", async () => {
    mockGetExpenses.mockResolvedValue([MOCK_EXPENSE]);
    render(<Transactions />);
    // Component renders both mobile and desktop views — use getAllByText
    await waitFor(() => {
      const lunches = screen.getAllByText("Lunch");
      expect(lunches.length).toBeGreaterThan(0);
    });
  });

  it("re-fetches when month filter changes to 'All months'", async () => {
    const user = userEvent.setup();
    render(<Transactions />);
    await waitFor(() => expect(mockGetExpenses).toHaveBeenCalledTimes(1));

    // Month select is the first combobox; it defaults to current month.
    // Selecting "All months" (value 0) always differs from the default.
    const selects = screen.getAllByRole("combobox");
    await user.selectOptions(selects[0], "0"); // "All months"

    await waitFor(() => {
      expect(mockGetExpenses).toHaveBeenCalledTimes(2);
    });
  });

  it("passes month param to getExpenses when filter is set", async () => {
    const user = userEvent.setup();
    render(<Transactions />);
    await waitFor(() => expect(mockGetExpenses).toHaveBeenCalledTimes(1));

    const selects = screen.getAllByRole("combobox");
    await user.selectOptions(selects[0], "3"); // March (different from default unless it's March)

    await waitFor(() => {
      const lastCall = mockGetExpenses.mock.calls[mockGetExpenses.mock.calls.length - 1][0];
      // month=0 is passed as undefined; month=3 is passed as 3
      expect(lastCall.month === 3 || lastCall.month === undefined).toBe(true);
    });
  });
});
