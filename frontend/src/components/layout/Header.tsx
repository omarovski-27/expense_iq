import { Link, useLocation } from "react-router-dom";
import { Zap } from "lucide-react";
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
  const desktopDate = format(new Date(), "EEEE, MMMM d, yyyy");
  const mobileDate = format(new Date(), "MMM d, yyyy");

  return (
    <header className="flex items-center justify-between gap-4 bg-gray-950 border-b border-gray-800 h-16 px-4 md:px-6 flex-shrink-0">
      <h1 className="text-lg font-semibold text-white">{title}</h1>
      <div className="flex items-center gap-3">
        <span className="text-xs md:text-sm text-gray-400 text-right">
          <span className="md:hidden">{mobileDate}</span>
          <span className="hidden md:inline">{desktopDate}</span>
        </span>
        <Link
          to="/quick"
          className="md:hidden flex items-center gap-1 rounded-full bg-amber-500 px-3 py-1.5 text-sm font-medium text-gray-950 touch-manipulation"
        >
          <Zap size={14} /> Add
        </Link>
      </div>
    </header>
  );
}
