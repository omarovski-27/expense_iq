import type { BudgetStatus } from "../../types";
import { formatCurrency } from "../../utils/formatCurrency";
import { useCurrency } from "../../context/CurrencyContext";

interface Props {
  data: BudgetStatus[];
}

function barColor(pct: number) {
  if (pct >= 90) return "bg-red-500";
  if (pct >= 70) return "bg-amber-500";
  return "bg-green-500";
}

const STATUS_STYLES: Record<BudgetStatus["status"], { label: string; cls: string }> = {
  on_track: { label: "On Track", cls: "bg-green-500/15 text-green-400 border-green-500/30" },
  warning: { label: "Warning", cls: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
  over_budget: { label: "Over Budget", cls: "bg-red-500/15 text-red-400 border-red-500/30" },
};

export default function BudgetProgressBar({ data }: Props) {
  const { currencySymbol } = useCurrency();
  if (data.length === 0) {
    return <p className="text-gray-500 text-sm">No budgets set for this month.</p>;
  }

  return (
    <div className="space-y-4">
      {data.map((b) => {
        const pct = Math.min(b.percentage, 100);
        const style = STATUS_STYLES[b.status];
        return (
          <div key={b.category.id}>
            {/* Row header */}
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="text-base">{b.category.icon}</span>
                <span className="text-sm font-medium text-gray-200">{b.category.name}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-400">
                  {formatCurrency(b.spent, currencySymbol)}
                  <span className="text-gray-600"> / </span>
                  {formatCurrency(b.monthly_limit, currencySymbol)}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                    style.cls
                  }`}
                >
                  {style.label}
                </span>
              </div>
            </div>

            {/* Progress bar */}
            <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${barColor(b.percentage)}`}
                style={{ width: `${pct}%` }}
              />
            </div>

            {/* Sub-row */}
            <div className="flex justify-between mt-1">
              <span className="text-xs text-gray-500">
                {b.percentage.toFixed(0)}% used
              </span>
              {b.remaining > 0 ? (
                <span className="text-xs text-gray-500">
                  {formatCurrency(b.remaining, currencySymbol)} remaining
                </span>
              ) : (
                <span className="text-xs text-red-400">
                  {formatCurrency(Math.abs(b.remaining), currencySymbol)} over limit
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
