import { useLocation } from "react-router-dom";
import { format } from "date-fns";

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/transactions": "Transactions",
  "/insights": "Insights",
  "/budgets": "Budgets",
  "/settings": "Settings",
};

export default function Header() {
  const { pathname } = useLocation();
  const title = PAGE_TITLES[pathname] ?? "ExpenseIQ";
  const today = format(new Date(), "EEEE, MMMM d, yyyy"); // e.g. "Friday, April 24, 2026"

  return (
    <header className="flex items-center justify-between bg-gray-950 border-b border-gray-800 h-16 px-6 flex-shrink-0">
      <h1 className="text-lg font-semibold text-white">{title}</h1>
      <span className="text-sm text-gray-400">{today}</span>
    </header>
  );
}
