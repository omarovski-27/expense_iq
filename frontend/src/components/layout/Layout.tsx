import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-900 text-white overflow-hidden">
      {/* Fixed left sidebar â€” collapses to icon-only on mobile */}
      <aside className="w-14 md:w-60 flex-shrink-0 bg-gray-950 flex flex-col transition-all duration-200">
        <Sidebar />
      </aside>

      {/* Main content area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
