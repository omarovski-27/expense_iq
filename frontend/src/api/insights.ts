import client from "./client";
import type { AIInsight, SpikeResult } from "../types";

interface GetInsightsParams {
  month?: number;
  year?: number;
  type?: string;
  limit?: number;
}

export async function getInsights(
  params: GetInsightsParams = {}
): Promise<AIInsight[]> {
  const { data } = await client.get<AIInsight[]>("/insights", { params });
  return data;
}

export async function generateInsights(
  month: number,
  year: number
): Promise<AIInsight[]> {
  const { data } = await client.post<AIInsight[]>("/insights/generate", {
    month,
    year,
  });
  return data;
}

export async function chatWithAI(question: string): Promise<string> {
  const { data } = await client.post<{ response: string }>("/insights/chat", {
    question,
  });
  return data.response;
}

export async function getSpikes(
  month?: number,
  year?: number
): Promise<SpikeResult[]> {
  const { data } = await client.get<SpikeResult[]>("/insights/spikes", {
    params: { month, year },
  });
  return data;
}

export async function dismissInsight(id: number): Promise<void> {
  await client.delete(`/insights/${id}/dismiss`);
}
