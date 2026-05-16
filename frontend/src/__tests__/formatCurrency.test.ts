import { describe, it, expect } from "vitest";
import { formatCurrency } from "../utils/formatCurrency";

describe("formatCurrency", () => {
  it("formats whole numbers with two decimal places", () => {
    expect(formatCurrency(10, "$")).toBe("$10.00");
  });

  it("formats decimal amounts correctly", () => {
    expect(formatCurrency(14.99, "$")).toBe("$14.99");
  });

  it("formats large numbers with commas", () => {
    expect(formatCurrency(1234.5, "$")).toBe("$1,234.50");
  });

  it("uses provided currency symbol", () => {
    expect(formatCurrency(5.0, "JD")).toBe("JD5.00");
    expect(formatCurrency(5.0, "€")).toBe("€5.00");
  });

  it("formats zero", () => {
    expect(formatCurrency(0, "$")).toBe("$0.00");
  });

  it("rounds to two decimal places", () => {
    expect(formatCurrency(1.005, "$")).toBe("$1.01");
  });

  it("handles negative amounts", () => {
    const result = formatCurrency(-10.5, "$");
    expect(result).toContain("10.50");
  });
});
