import { format } from "date-fns";

import type { AIInsight } from "../../types";

interface Props {
  insight: AIInsight;
}

const severityStyles: Record<string, string> = {
  info: "border-l-blue-500",
  warning: "border-l-amber-500",
  critical: "border-l-red-500",
};

export default function InsightCard({ insight }: Props) {
  const severityClass = insight.severity ? severityStyles[insight.severity] : undefined;
  // Label the period this insight was generated for, so a card can never
  // silently sit under the wrong month's header on the dashboard.
  const periodLabel =
    insight.month && insight.year
      ? format(new Date(insight.year, insight.month - 1, 1), "MMM yyyy")
      : null;

  return (
    <div
      className={`bg-gray-800 rounded-xl p-4 border border-gray-700 border-l-4 ${
        severityClass ?? "border-l-gray-600"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <p className="text-xs font-semibold text-gray-300">{insight.title}</p>
        {periodLabel && (
          <span className="shrink-0 text-[10px] font-medium text-gray-500 bg-gray-700/50 px-1.5 py-0.5 rounded">
            {periodLabel}
          </span>
        )}
      </div>
      <p className="text-xs text-gray-400 line-clamp-3">{insight.content}</p>
    </div>
  );
}
