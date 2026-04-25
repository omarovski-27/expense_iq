import type { AIInsight } from "../../types";

interface Props {
  insight: AIInsight;
}

const severityStyles: Record<string, string> = {
  info: "border-l-blue-500",
  warning: "border-l-amber-500",
  critical: "border-l-red-500",
};

// Full implementation created in Prompt 4C
export default function InsightCard({ insight }: Props) {
  const severityClass = insight.severity ? severityStyles[insight.severity] : undefined;

  return (
    <div
      className={`bg-gray-800 rounded-xl p-4 border border-gray-700 border-l-4 ${
        severityClass ?? "border-l-gray-600"
      }`}
    >
      <p className="text-xs font-semibold text-gray-300 mb-1">{insight.title}</p>
      <p className="text-xs text-gray-400 line-clamp-3">{insight.content}</p>
    </div>
  );
}
