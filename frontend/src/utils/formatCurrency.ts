/**
 * Format a number as a currency string.
 * Reads the currency symbol from localStorage (key: expenseiq_currency) if
 * no symbol is explicitly passed. Defaults to "$".
 *
 * Examples:
 *   formatCurrency(1234.5)       → "$1,234.50"
 *   formatCurrency(1234.5, "€")  → "€1,234.50"
 */
export function formatCurrency(amount: number, symbol?: string): string {
  const sym = symbol ?? localStorage.getItem("expenseiq_currency") ?? "$";
  return `${sym}${new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)}`;
}
