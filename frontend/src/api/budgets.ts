import client from "./client";
import type { Budget, BudgetStatus } from "../types";

export async function getBudgets(
  month?: number,
  year?: number
): Promise<Budget[]> {
  const { data } = await client.get<Budget[]>("/budgets", {
    params: { month, year },
  });
  return data;
}

export async function getBudgetStatus(
  month: number,
  year: number
): Promise<BudgetStatus[]> {
  const { data } = await client.get<BudgetStatus[]>("/budgets/status", {
    params: { month, year },
  });
  return data;
}

export async function createBudget(
  data: Omit<Budget, "id">
): Promise<Budget> {
  const { data: budget } = await client.post<Budget>("/budgets", data);
  return budget;
}

export async function updateBudget(
  id: number,
  monthly_limit: number
): Promise<Budget> {
  const { data: budget } = await client.put<Budget>(`/budgets/${id}`, {
    monthly_limit,
  });
  return budget;
}
