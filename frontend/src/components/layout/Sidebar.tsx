import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Receipt,
  Brain,
  Target,
  Settings2,
} from "lucide-react";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/transactions", label: "Transactions", icon: Receipt },
  { to: "/insights", label: "Insights", icon: Brain },
  { to: "/budgets", label: "Budgets", icon: Target },
  { to: "/settings", label: "Settings", icon: Settings2 },
];

export default function Sidebar() {
  return (
    <div className="flex flex-col h-full">
      {/* Branding */}
      <div className="px-3 md:px-5 py-5 border-b border-gray-800 flex items-center justify-center md:justify-start overflow-hidden">
        <span className="text-lg font-bold text-white whitespace-nowrap">
          <span className="text-amber-400">ðŸ’°</span>
          <span className="hidden md:inline"> ExpenseIQ</span>
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              [
                "relative group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-amber-500/10 text-amber-400 border-r-2 border-amber-400"
                  : "text-gray-400 hover:text-white hover:bg-gray-800",
              ].join(" ")
            }
          >
            <Icon size={18} className="flex-shrink-0" />
            <span className="hidden md:inline">{label}</span>
            {/* Tooltip shown on mobile (icon-only) on hover */}
            <span className="md:hidden absolute left-full ml-2 top-1/2 -translate-y-1/2 bg-gray-900 border border-gray-700 text-white text-xs px-2 py-1 rounded shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none z-50 whitespace-nowrap transition-opacity">
              {label}
            </span>
          </NavLink>
        ))}
      </nav>

      {/* Footer credit */}
      <div className="px-3 md:px-5 py-4 border-t border-gray-800">
        <p className="hidden md:block text-xs text-gray-600">Powered by Claude AI</p>
        <p className="md:hidden text-xs text-gray-700 text-center">AI</p>
      </div>
    </div>
  );
}
