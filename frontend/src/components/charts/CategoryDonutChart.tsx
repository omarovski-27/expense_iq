import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  type TooltipProps,
} from "recharts";
import type { CategoryBreakdown } from "../../types";
import { formatCurrency } from "../../utils/formatCurrency";
import { useCurrency } from "../../context/CurrencyContext";

interface Props {
  data: CategoryBreakdown[];
}

function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  const { currencySymbol } = useCurrency();
  if (!active || !payload?.length) return null;
  const entry = payload[0].payload as CategoryBreakdown & { name: string };
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-white text-sm shadow-xl">
      <p className="font-medium mb-1">
        {entry.category.icon} {entry.category.name}
      </p>
      <p className="text-amber-400">{formatCurrency(entry.amount, currencySymbol)}</p>
      <p className="text-gray-400 text-xs">{entry.percentage.toFixed(1)}% of total</p>
    </div>
  );
}

// Center label rendered as a custom label component inside PieChart
function CenterLabel({ total, cx, cy }: { total: number; cx?: number; cy?: number }) {
  const { currencySymbol } = useCurrency();
  return (
    <g>
      <text
        x={cx}
        y={(cy ?? 0) - 6}
        textAnchor="middle"
        dominantBaseline="central"
        className="fill-white"
        style={{ fill: "#ffffff", fontSize: 14, fontWeight: 700 }}
      >
        {formatCurrency(total, currencySymbol)}
      </text>
      <text
        x={cx}
        y={(cy ?? 0) + 12}
        textAnchor="middle"
        dominantBaseline="central"
        style={{ fill: "#9CA3AF", fontSize: 10 }}
      >
        total
      </text>
    </g>
  );
}

export default function CategoryDonutChart({ data }: Props) {
  const { currencySymbol } = useCurrency();
  const total = data.reduce((sum, d) => sum + d.amount, 0);

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 text-sm">
        <p className="font-semibold text-white text-sm mb-1">Category Breakdown</p>
        <p className="mt-6">No data this month.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <p className="font-semibold text-white text-sm mb-2">Category Breakdown</p>
      <ResponsiveContainer width="100%" height={190}>
        <PieChart>
          <Pie
            data={data}
            dataKey="amount"
            nameKey="category.name"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={2}
            labelLine={false}
            label={<CenterLabel total={total} />}
          >
            {data.map((entry, index) => (
              <Cell key={index} fill={entry.category.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="mt-2 space-y-1 overflow-y-auto max-h-[110px] pr-1">
        {data
          .slice()
          .sort((a, b) => b.amount - a.amount)
          .map((entry, i) => (
            <div key={i} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5 min-w-0">
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: entry.category.color }}
                />
                <span className="text-gray-300 truncate">
                  {entry.category.icon} {entry.category.name}
                </span>
              </div>
              <span className="text-gray-400 font-medium ml-2 whitespace-nowrap">
                {formatCurrency(entry.amount, currencySymbol)}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}
