import client from "./client";
import type { Category } from "../types";

export async function getCategories(): Promise<Category[]> {
  const { data } = await client.get<Category[]>("/categories");
  return data;
}

export async function createCategory(
  data: Omit<Category, "id" | "created_at">
): Promise<Category> {
  const { data: category } = await client.post<Category>("/categories", data);
  return category;
}

export async function updateCategory(
  id: number,
  data: Partial<Omit<Category, "id" | "created_at">>
): Promise<Category> {
  const { data: category } = await client.put<Category>(
    `/categories/${id}`,
    data
  );
  return category;
}

export async function deleteCategory(
  id: number,
  reassign_to_id?: number
): Promise<void> {
  await client.delete(`/categories/${id}`, {
    params: reassign_to_id !== undefined ? { reassign_to_id } : undefined,
  });
}
