import { NavLink, Outlet } from "react-router-dom";
import {
  Brain,
  LayoutDashboard,
  Receipt,
  Settings2,
  Target,
} from "lucide-react";
import Sidebar from "./Sidebar";
import Header from "./Header";

const mobileNavItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/transactions", label: "Transactions", icon: Receipt },
  { to: "/insights", label: "Insights", icon: Brain },
  { to: "/budgets", label: "Budgets", icon: Target },
  { to: "/settings", label: "Settings", icon: Settings2 },
];

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-900 text-white overflow-hidden">
      <aside className="hidden md:flex md:w-60 flex-shrink-0 bg-gray-950 md:flex-col transition-all duration-200">
        <Sidebar />
      </aside>

      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 pb-24 md:pb-6">
          <Outlet />
        </main>
      </div>

      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 h-16 bg-gray-950 border-t border-gray-800 flex items-center justify-around px-2">
        {mobileNavItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              [
                "flex flex-col items-center gap-0.5 px-2 py-2 text-xs transition-colors",
                isActive ? "text-amber-400" : "text-gray-500",
              ].join(" ")
            }
          >
            <Icon size={22} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
