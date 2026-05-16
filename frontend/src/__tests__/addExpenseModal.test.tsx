import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

// ── Hoist mock functions so vi.mock factories can reference them ──────────────
const { mockCreateExpense, mockGetCategories, mockToastError, mockToastSuccess } = vi.hoisted(() => ({
  mockCreateExpense: vi.fn(),
  mockGetCategories: vi.fn(),
  mockToastError: vi.fn(),
  mockToastSuccess: vi.fn(),
}));

vi.mock("../api/expenses", () => ({ createExpense: mockCreateExpense }));
vi.mock("../api/categories", () => ({ getCategories: mockGetCategories }));
vi.mock("react-hot-toast", () => ({
  default: { error: mockToastError, success: mockToastSuccess },
}));

import AddExpenseModal from "../components/expenses/AddExpenseModal";

const MOCK_CATEGORIES = [
  { id: 1, name: "Food", color: "#f00", icon: "🍔", created_at: "2026-01-01T00:00:00Z" },
  { id: 2, name: "Bills", color: "#00f", icon: "📋", created_at: "2026-01-01T00:00:00Z" },
];

function renderModal(overrides: Partial<{ onClose: () => void; onSaved: () => void }> = {}) {
  const props = {
    onClose: vi.fn(),
    onSaved: vi.fn(),
    ...overrides,
  };
  return { ...render(<AddExpenseModal {...props} />), ...props };
}

describe("AddExpenseModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetCategories.mockResolvedValue(MOCK_CATEGORIES);
    mockCreateExpense.mockResolvedValue({
      id: 1, amount: 5.0, description: "X", date: "2026-05-16",
    });
  });

  it("renders the modal title", async () => {
    renderModal();
    expect(screen.getByText("Add Expense")).toBeInTheDocument();
  });

  it("loads and displays categories", async () => {
    renderModal();
    await waitFor(() => {
      expect(screen.getByText(/🍔 Food/)).toBeInTheDocument();
    });
  });

  it("does not call createExpense when required fields are empty", async () => {
    renderModal();
    await waitFor(() => screen.getByText(/🍔 Food/));
    fireEvent.submit(screen.getByRole("button", { name: /save/i }).closest("form")!);
    expect(mockCreateExpense).not.toHaveBeenCalled();
  });

  it("shows toast error when required fields are missing", async () => {
    renderModal();
    await waitFor(() => screen.getByText(/🍔 Food/));
    fireEvent.submit(screen.getByRole("button", { name: /save/i }).closest("form")!);
    expect(mockToastError).toHaveBeenCalledWith(expect.stringContaining("required"));
  });

  it("calls createExpense with correct data when form is valid", async () => {
    renderModal();
    await waitFor(() => screen.getByText(/🍔 Food/));

    fireEvent.change(screen.getByPlaceholderText("0.00"), { target: { value: "12.5" } });
    fireEvent.change(screen.getByPlaceholderText("What was this for?"), { target: { value: "Lunch" } });
    // Select category — the select has multiple categories; pick id=1 (Food)
    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[0], { target: { value: "1" } });

    fireEvent.submit(screen.getByRole("button", { name: /save/i }).closest("form")!);

    await waitFor(() => {
      expect(mockCreateExpense).toHaveBeenCalledWith(
        expect.objectContaining({ amount: 12.5, description: "Lunch", category_id: 1 })
      );
    });
  });

  it("calls onSaved after successful submission", async () => {
    const onSaved = vi.fn();
    render(<AddExpenseModal onClose={vi.fn()} onSaved={onSaved} />);
    await waitFor(() => screen.getByText(/🍔 Food/));

    fireEvent.change(screen.getByPlaceholderText("0.00"), { target: { value: "5" } });
    fireEvent.change(screen.getByPlaceholderText("What was this for?"), { target: { value: "Coffee" } });
    fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: "1" } });
    fireEvent.submit(screen.getByRole("button", { name: /save/i }).closest("form")!);

    await waitFor(() => expect(onSaved).toHaveBeenCalled());
  });

  it("calls onClose when Cancel is clicked", async () => {
    const { onClose } = renderModal();
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it("does not call createExpense when description is missing", async () => {
    renderModal();
    await waitFor(() => screen.getByText(/🍔 Food/));
    fireEvent.change(screen.getByPlaceholderText("0.00"), { target: { value: "5" } });
    // skip description
    fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: "1" } });
    fireEvent.submit(screen.getByRole("button", { name: /save/i }).closest("form")!);
    expect(mockCreateExpense).not.toHaveBeenCalled();
    expect(mockToastError).toHaveBeenCalled();
  });

  it("does not call createExpense when category is missing", async () => {
    renderModal();
    await waitFor(() => screen.getByText(/🍔 Food/));
    fireEvent.change(screen.getByPlaceholderText("0.00"), { target: { value: "5" } });
    fireEvent.change(screen.getByPlaceholderText("What was this for?"), { target: { value: "Coffee" } });
    // skip category
    fireEvent.submit(screen.getByRole("button", { name: /save/i }).closest("form")!);
    expect(mockCreateExpense).not.toHaveBeenCalled();
  });
});
