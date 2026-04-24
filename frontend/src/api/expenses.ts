import client from "./client";
import type { Expense } from "../types";

interface GetExpensesParams {
  month?: number;
  year?: number;
  category_id?: number;
  search?: string;
  limit?: number;
  offset?: number;
}

export async function getExpenses(params: GetExpensesParams = {}): Promise<Expense[]> {
  const { data } = await client.get<Expense[]>("/expenses", { params });
  return data;
}

export async function createExpense(
  data: Omit<Expense, "id" | "created_at" | "updated_at" | "category">
): Promise<Expense> {
  const { data: expense } = await client.post<Expense>("/expenses", data);
  return expense;
}

export async function updateExpense(
  id: number,
  data: Partial<Omit<Expense, "id" | "created_at" | "updated_at" | "category">>
): Promise<Expense> {
  const { data: expense } = await client.put<Expense>(`/expenses/${id}`, data);
  return expense;
}

export async function deleteExpense(id: number): Promise<void> {
  await client.delete(`/expenses/${id}`);
}

export async function bulkImport(
  file: File
): Promise<{ imported: number; skipped: number }> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await client.post<{ imported: number; skipped: number }>(
    "/expenses/bulk-import",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}
