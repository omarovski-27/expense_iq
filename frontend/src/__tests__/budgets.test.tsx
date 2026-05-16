import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// ── Hoist mock functions ──────────────────────────────────────────────────────
const {
  mockGetBudgetStatus,
  mockGetCategories,
  mockGetRecurringRules,
} = vi.hoisted(() => ({
  mockGetBudgetStatus: vi.fn(),
  mockGetCategories: vi.fn(),
  mockGetRecurringRules: vi.fn(),
}));

vi.mock("../api/budgets", () => ({
  getBudgetStatus: mockGetBudgetStatus,
  createBudget: vi.fn().mockResolvedValue({ id: 1 }),
  updateBudget: vi.fn().mockResolvedValue({ id: 1 }),
}));
vi.mock("../api/categories", () => ({ getCategories: mockGetCategories }));
vi.mock("../api/recurring", () => ({
  getRecurringRules: mockGetRecurringRules,
  createRecurringRule: vi.fn(),
  updateRecurringRule: vi.fn(),
  toggleRecurringRule: vi.fn(),
  deleteRecurringRule: vi.fn(),
}));
vi.mock("react-hot-toast", () => ({
  default: { error: vi.fn(), success: vi.fn() },
}));
vi.mock("../context/CurrencyContext", () => ({
  useCurrency: () => ({ currencySymbol: "JD" }),
}));

import Budgets from "../pages/Budgets";

const MOCK_CATEGORIES = [
  { id: 1, name: "Food", color: "#f00", icon: "🍔", created_at: "2026-01-01T00:00:00Z" },
];

const MOCK_BUDGET_STATUS = [
  {
    budget_id: 1,
    category: { id: 1, name: "Food", color: "#f00", icon: "🍔", created_at: "2026-01-01T00:00:00Z" },
    monthly_limit: 200,
    spent: 50,
    percentage: 25,
    remaining: 150,
    projected_month_end: 100,
    status: "on_track" as const,
  },
];

describe("Budgets page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetBudgetStatus.mockResolvedValue([]);
    mockGetCategories.mockResolvedValue(MOCK_CATEGORIES);
    mockGetRecurringRules.mockResolvedValue([]);
  });

  it("renders without crashing and calls getBudgetStatus on mount", async () => {
    render(<Budgets />);
    await waitFor(() => {
      expect(mockGetBudgetStatus).toHaveBeenCalledTimes(1);
    });
  });

  it("calls getBudgetStatus with a valid month and year", async () => {
    render(<Budgets />);
    await waitFor(() => {
      const [month, year] = mockGetBudgetStatus.mock.calls[0];
      expect(month).toBeGreaterThanOrEqual(1);
      expect(month).toBeLessThanOrEqual(12);
      expect(year).toBeGreaterThanOrEqual(2020);
    });
  });

  it("shows 'No budgets set' when no budgets are returned", async () => {
    mockGetBudgetStatus.mockResolvedValue([]);
    render(<Budgets />);
    await waitFor(() => {
      expect(screen.getByText(/no budgets set/i)).toBeInTheDocument();
    });
  });

  it("renders budget cards when budget data is returned", async () => {
    mockGetBudgetStatus.mockResolvedValue(MOCK_BUDGET_STATUS);
    render(<Budgets />);
    await waitFor(() => {
      expect(screen.getByText("Food")).toBeInTheDocument();
    });
  });

  it("shows budget status label (On Track)", async () => {
    mockGetBudgetStatus.mockResolvedValue(MOCK_BUDGET_STATUS);
    render(<Budgets />);
    await waitFor(() => {
      expect(screen.getByText(/on track/i)).toBeInTheDocument();
    });
  });

  it("re-fetches with new month when month selector changes", async () => {
    const user = userEvent.setup();
    render(<Budgets />);
    await waitFor(() => expect(mockGetBudgetStatus).toHaveBeenCalledTimes(1));

    const selects = screen.getAllByRole("combobox");
    const monthSelect = selects[0]; // first select is month
    await user.selectOptions(monthSelect, "1"); // January

    await waitFor(() => {
      expect(mockGetBudgetStatus).toHaveBeenCalledTimes(2);
      expect(mockGetBudgetStatus.mock.calls[1][0]).toBe(1);
    });
  });

  it("re-fetches with new year when year selector changes", async () => {
    const user = userEvent.setup();
    render(<Budgets />);
    await waitFor(() => expect(mockGetBudgetStatus).toHaveBeenCalledTimes(1));

    const selects = screen.getAllByRole("combobox");
    const yearSelect = selects[1]; // second select is year
    const options = yearSelect.querySelectorAll("option");
    const secondYearValue = options[1]?.getAttribute("value");

    if (secondYearValue) {
      await user.selectOptions(yearSelect, secondYearValue);
      await waitFor(() => {
        expect(mockGetBudgetStatus).toHaveBeenCalledTimes(2);
        expect(String(mockGetBudgetStatus.mock.calls[1][1])).toBe(secondYearValue);
      });
    }
  });
});
