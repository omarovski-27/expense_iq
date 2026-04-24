import client from "./client";
import type { RecurringRule } from "../types";

export interface RecurringRuleCreate {
  name: string;
  amount: number;
  category_id: number;
  frequency: "daily" | "weekly" | "monthly" | "yearly";
  next_due_date: string;
  is_active?: boolean;
}

export async function getRecurringRules(): Promise<RecurringRule[]> {
  const { data } = await client.get<RecurringRule[]>("/recurring");
  return data;
}

export async function createRecurringRule(
  data: RecurringRuleCreate
): Promise<RecurringRule> {
  const { data: rule } = await client.post<RecurringRule>("/recurring", data);
  return rule;
}

export async function updateRecurringRule(
  id: number,
  data: Partial<RecurringRuleCreate>
): Promise<RecurringRule> {
  const { data: rule } = await client.put<RecurringRule>(`/recurring/${id}`, data);
  return rule;
}

export async function toggleRecurringRule(id: number): Promise<RecurringRule> {
  const { data } = await client.patch<RecurringRule>(`/recurring/${id}/toggle`);
  return data;
}

export async function deleteRecurringRule(id: number): Promise<void> {
  await client.delete(`/recurring/${id}`);
}

export async function runRecurring(): Promise<{ message: string; created: number }> {
  const { data } = await client.post<{ message: string; created: number }>("/recurring/run");
  return data;
}
