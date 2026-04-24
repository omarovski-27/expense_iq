import { useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transactions";
import Insights from "./pages/Insights";
import Budgets from "./pages/Budgets";
import Settings from "./pages/Settings";

function KeyboardShortcuts() {
  useEffect(() => {
    function isInputFocused() {
      const tag = document.activeElement?.tagName.toLowerCase();
      return tag === "input" || tag === "textarea" || tag === "select";
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "n" && !isInputFocused() && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        document.dispatchEvent(new CustomEvent("expenseiq:add-expense"));
      }
      if (e.key === "Escape") {
        document.dispatchEvent(new CustomEvent("expenseiq:close-modal"));
      }
      if (e.key === "/" && !isInputFocused()) {
        e.preventDefault();
        const el = document.querySelector<HTMLInputElement>("[data-search]");
        el?.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  return null;
}

export default function App() {
  return (
    <BrowserRouter>
      <KeyboardShortcuts />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/budgets" element={<Budgets />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
