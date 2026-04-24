import client from "./client";
import type {
  AnalyticsSummary,
  CategoryBreakdown,
  MerchantBreakdown,
  SpendingTrend,
} from "../types";

export async function getSummary(
  month: number,
  year: number
): Promise<AnalyticsSummary> {
  const { data } = await client.get<AnalyticsSummary>("/analytics/summary", {
    params: { month, year },
  });
  return data;
}

export async function getTrends(): Promise<SpendingTrend[]> {
  const { data } = await client.get<SpendingTrend[]>("/analytics/trends");
  return data;
}

export async function getCategoryBreakdown(
  month: number,
  year: number
): Promise<CategoryBreakdown[]> {
  const { data } = await client.get<CategoryBreakdown[]>(
    "/analytics/category-breakdown",
    { params: { month, year } }
  );
  return data;
}

export async function getMerchantBreakdown(
  month: number,
  year: number
): Promise<MerchantBreakdown[]> {
  const { data } = await client.get<MerchantBreakdown[]>(
    "/analytics/merchant-breakdown",
    { params: { month, year } }
  );
  return data;
}
