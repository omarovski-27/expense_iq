import { useEffect, useState } from "react";
import { Plus, TrendingDown, TrendingUp } from "lucide-react";
import { format, parseISO } from "date-fns";

import { formatCurrency } from "../utils/formatCurrency";
import { useCurrency } from "../context/CurrencyContext";
import { getSummary, getTrends, getCategoryBreakdown } from "../api/analytics";
import { getExpenses } from "../api/expenses";
import { getBudgetStatus } from "../api/budgets";
import { getInsights } from "../api/insights";

import SpendingTrendChart from "../components/charts/SpendingTrendChart";
import CategoryDonutChart from "../components/charts/CategoryDonutChart";
import BudgetProgressBar from "../components/charts/BudgetProgressBar";
import InsightCard from "../components/ai/InsightCard";
import AddExpenseModal from "../components/expenses/AddExpenseModal";

import type {
  AnalyticsSummary,
  SpendingTrend,
  CategoryBreakdown,
  BudgetStatus,
  Expense,
  AIInsight,
} from "../types";

// ---------------------------------------------------------------------------
// Skeleton primitives
// ---------------------------------------------------------------------------

function SkeletonCard() {
  return (
    <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 h-28 animate-pulse" />
  );
}

function SkeletonBlock({ className = "" }: { className?: string }) {
  return (
    <div className={`bg-gray-800 rounded-xl border border-gray-700 animate-pulse ${className}`} />
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export default function Dashboard() {
  const now = new Date();
  const month = now.getMonth() + 1;
  const year = now.getFullYear();
  const { currencySymbol } = useCurrency();

  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [trends, setTrends] = useState<SpendingTrend[]>([]);
  const [breakdown, setBreakdown] = useState<CategoryBreakdown[]>([]);
  const [budgetStatus, setBudgetStatus] = useState<BudgetStatus[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [insights, setInsights] = useState<AIInsight[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);

  async function fetchAll() {
    try {
      const [s, t, cb, bs, e, i] = await Promise.all([
        getSummary(month, year),
        getTrends(),
        getCategoryBreakdown(month, year),
        getBudgetStatus(month, year),
        getExpenses({ month, year, limit: 10 }),
        getInsights({ limit: 3 }),
      ]);
      setSummary(s);
      setTrends(t);
      setBreakdown(cb);
      setBudgetStatus(bs);
      setExpenses(e);
      setInsights(i);
    } finally {
      setLoading(false);
    }
  }

  // Global keyboard shortcut: 'n' dispatches expenseiq:add-expense
  useEffect(() => {
    function handleAddExpense() {
      setShowAddModal(true);
    }
    document.addEventListener("expenseiq:add-expense", handleAddExpense);
    return () => document.removeEventListener("expenseiq:add-expense", handleAddExpense);
  }, []);

  useEffect(() => {
    fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [month, year]);

  // ---- KPI helpers --------------------------------------------------------

  const momPct = summary?.mom_change_percent ?? 0;
  const budgetPct = summary?.budget_used_percent ?? 0;

  const budgetColor =
    budgetPct < 70
      ? "text-green-400"
      : budgetPct < 90
      ? "text-amber-400"
      : "text-red-400";

  // -------------------------------------------------------------------------
  // RENDER
  // -------------------------------------------------------------------------

  return (
    <div className="space-y-6">

      {/* ------------------------------------------------------------------ */}
      {/* SECTION 1 — KPI Row                                                 */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            {/* Card 1 — Total This Month */}
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">
                Total This Month
              </p>
              <p className="text-2xl font-bold text-white">
                {formatCurrency(summary?.total_this_month ?? 0, currencySymbol)}
              </p>
              <div className="flex items-center gap-1 mt-2">
                {momPct <= 0 ? (
                  <TrendingDown size={14} className="text-green-400" />
                ) : (
                  <TrendingUp size={14} className="text-red-400" />
                )}
                <span
                  className={`text-xs font-medium ${
                    momPct <= 0 ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {Math.abs(momPct).toFixed(1)}% vs last month
                </span>
              </div>
            </div>

            {/* Card 2 — Budget Used */}
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">
                Budget Used
              </p>
              <p className={`text-2xl font-bold ${budgetColor}`}>
                {budgetPct.toFixed(0)}%
              </p>
              <p className="text-xs text-gray-500 mt-2">of monthly budget</p>
            </div>

            {/* Card 3 — Daily Average */}
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">
                Daily Average
              </p>
              <p className="text-2xl font-bold text-white">
                {formatCurrency(summary?.daily_average ?? 0, currencySymbol)}
              </p>
              <p className="text-xs text-gray-500 mt-2">per day this month</p>
            </div>

            {/* Card 4 — Top Category */}
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">
                Top Category
              </p>
              {summary?.top_category ? (
                <>
                  <p className="text-2xl font-bold text-white">
                    {summary.top_category.icon}{" "}
                    <span className="text-lg">{summary.top_category.name}</span>
                  </p>
                  <p className="text-xs text-gray-400 mt-2">
                    {formatCurrency(summary.top_category.amount, currencySymbol)}
                  </p>
                </>
              ) : (
                <p className="text-gray-500 text-sm mt-2">No data</p>
              )}
            </div>
          </>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* SECTION 2 — Charts (60/40)                                          */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex flex-col md:flex-row gap-4">
        {loading ? (
          <>
            <SkeletonBlock className="flex-[3] h-72" />
            <SkeletonBlock className="flex-[2] h-72" />
          </>
        ) : (
          <>
            <div className="md:flex-[3] bg-gray-800 rounded-xl p-5 border border-gray-700 min-w-0">
              <SpendingTrendChart data={trends} />
            </div>
            <div className="md:flex-[2] bg-gray-800 rounded-xl p-5 border border-gray-700 min-w-0">
              <CategoryDonutChart data={breakdown} />
            </div>
          </>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* SECTION 3 — Budget Progress (full width)                            */}
      {/* ------------------------------------------------------------------ */}
      {loading ? (
        <SkeletonBlock className="h-40" />
      ) : budgetStatus.length > 0 ? (
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">
            Budget Progress
          </h2>
          <BudgetProgressBar data={budgetStatus} />
        </div>
      ) : null}

      {/* ------------------------------------------------------------------ */}
      {/* SECTION 4 — Recent Transactions (60%) + Insights (40%)             */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex flex-col md:flex-row gap-4">
        {/* Recent Transactions */}
        <div className="md:flex-[3] bg-gray-800 rounded-xl p-5 border border-gray-700 min-w-0">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">
            Recent Transactions
          </h2>
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 10 }).map((_, i) => (
                <div
                  key={i}
                  className="h-8 bg-gray-700 rounded animate-pulse"
                />
              ))}
            </div>
          ) : expenses.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <span className="text-5xl mb-4">📭</span>
              <h3 className="text-white font-semibold text-base mb-1">No expenses yet</h3>
              <p className="text-gray-400 text-sm mb-4">Add your first expense to get started</p>
              <button
                onClick={() => setShowAddModal(true)}
                className="flex items-center gap-2 px-4 h-11 bg-amber-500 hover:bg-amber-400 text-black text-sm font-semibold rounded-lg transition-colors touch-manipulation"
              >
                <Plus size={16} /> Add Expense
              </button>
            </div>
          ) : (
            <>
              <div className="block md:hidden">
                {expenses.map((exp) => (
                  <div
                    key={exp.id}
                    className="border-b border-gray-700 py-3 flex items-start justify-between gap-3 last:border-b-0"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-white text-sm font-medium truncate">
                        {exp.merchant || exp.description}
                      </p>
                      {exp.category && (
                        <div className="mt-1">
                          <span
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                            style={{
                              backgroundColor: exp.category.color + "22",
                              color: exp.category.color,
                            }}
                          >
                            {exp.category.icon} {exp.category.name}
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-amber-400 font-medium text-sm">
                        {formatCurrency(exp.amount, currencySymbol)}
                      </p>
                      <p className="text-gray-500 text-xs mt-1">
                        {format(parseISO(exp.date), "MMM d")}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              <table className="hidden md:table w-full text-sm">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-700 text-left">
                    <th className="pb-2 font-medium">Date</th>
                    <th className="pb-2 font-medium">Description</th>
                    <th className="pb-2 font-medium">Category</th>
                    <th className="pb-2 font-medium text-right">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {expenses.map((exp) => (
                    <tr key={exp.id} className="text-gray-300">
                      <td className="py-2 text-gray-400 whitespace-nowrap">
                        {format(parseISO(exp.date), "MMM d")}
                      </td>
                      <td className="py-2 truncate max-w-[160px]">
                        {exp.merchant || exp.description}
                      </td>
                      <td className="py-2">
                        {exp.category && (
                          <span
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                            style={{
                              backgroundColor: exp.category.color + "22",
                              color: exp.category.color,
                            }}
                          >
                            {exp.category.icon} {exp.category.name}
                          </span>
                        )}
                      </td>
                      <td className="py-2 text-right font-medium text-white">
                        {formatCurrency(exp.amount, currencySymbol)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>

        {/* AI Insight Cards */}
        <div className="flex-[2] flex flex-col gap-3">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <SkeletonBlock key={i} className="h-24" />
            ))
          ) : insights.length === 0 ? (
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 text-gray-500 text-sm">
              No AI insights yet. Generate a report on the Insights page.
            </div>
          ) : (
            insights.map((insight) => (
              <InsightCard key={insight.id} insight={insight} />
            ))
          )}
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Floating "+" button                                                  */}
      {/* ------------------------------------------------------------------ */}
      <button
        onClick={() => setShowAddModal(true)}
        className="fixed bottom-24 right-4 md:bottom-8 md:right-8 w-14 h-14 bg-amber-500 hover:bg-amber-400 text-white rounded-full shadow-lg flex items-center justify-center transition-colors touch-manipulation z-40"
        aria-label="Add expense"
      >
        <Plus size={24} />
      </button>

      {/* Add Expense Modal */}
      {showAddModal && (
        <AddExpenseModal
          onClose={() => setShowAddModal(false)}
          onSaved={() => {
            setShowAddModal(false);
            fetchAll();
          }}
        />
      )}
    </div>
  );
}

