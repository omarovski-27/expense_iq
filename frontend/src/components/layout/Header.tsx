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
  const desktopDate = format(new Date(), "EEEE, MMMM d, yyyy");
  const mobileDate = format(new Date(), "MMM d, yyyy");

  return (
    <header className="flex items-center justify-between gap-4 bg-gray-950 border-b border-gray-800 h-16 px-4 md:px-6 flex-shrink-0">
      <h1 className="text-lg font-semibold text-white">{title}</h1>
      <span className="text-xs md:text-sm text-gray-400 text-right">
        <span className="md:hidden">{mobileDate}</span>
        <span className="hidden md:inline">{desktopDate}</span>
      </span>
    </header>
  );
}
