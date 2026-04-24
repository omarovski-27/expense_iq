import { useState, useEffect } from "react";
import { format, parseISO, getDaysInMonth, getDate, getYear, getMonth } from "date-fns";
import {
  Plus, Pencil, Trash2, X, RefreshCw,
} from "lucide-react";
import toast from "react-hot-toast";

import { getBudgetStatus, createBudget, updateBudget } from "../api/budgets";
import { getCategories } from "../api/categories";
import {
  getRecurringRules,
  createRecurringRule,
  updateRecurringRule,
  toggleRecurringRule,
  deleteRecurringRule,
} from "../api/recurring";

import type { BudgetStatus, Category, RecurringRule } from "../types";
import { formatCurrency } from "../utils/formatCurrency";
import { useCurrency } from "../context/CurrencyContext";

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Helpers
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const FREQ_LABELS: Record<string, string> = {
  daily: "Daily", weekly: "Weekly", monthly: "Monthly", yearly: "Yearly",
};

const STATUS_STYLES: Record<BudgetStatus["status"], { badge: string; ring: string }> = {
  on_track: { badge: "bg-green-500/15 text-green-400 border-green-500/30", ring: "#22c55e" },
  warning: { badge: "bg-amber-500/15 text-amber-400 border-amber-500/30", ring: "#f59e0b" },
  over_budget: { badge: "bg-red-500/15 text-red-400 border-red-500/30", ring: "#ef4444" },
};

const STATUS_LABELS: Record<BudgetStatus["status"], string> = {
  on_track: "On Track", warning: "Warning", over_budget: "Over Budget",
};

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Circular Progress Ring (CSS-only via conic-gradient)
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function CircularProgress({ pct, color }: { pct: number; color: string }) {
  const clamped = Math.min(pct, 100);
  return (
    <div
      className="w-16 h-16 rounded-full flex items-center justify-center relative"
      style={{
        background: `conic-gradient(${color} ${clamped}%, #374151 ${clamped}%)`,
      }}
    >
      {/* Inner circle cutout */}
      <div className="w-11 h-11 rounded-full bg-gray-800 flex items-center justify-center">
        <span className="text-xs font-bold text-white">{Math.round(clamped)}%</span>
      </div>
    </div>
  );
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Add/Edit Recurring Modal
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface RecurringModalProps {
  rule?: RecurringRule | null;
  categories: Category[];
  onClose: () => void;
  onSaved: () => void;
}

function RecurringModal({ rule, categories, onClose, onSaved }: RecurringModalProps) {
  const [form, setForm] = useState({
    name: rule?.name ?? "",
    amount: rule ? String(rule.amount) : "",
    category_id: rule ? String(rule.category_id) : "",
    frequency: rule?.frequency ?? "monthly",
    next_due_date: rule?.next_due_date ?? format(new Date(), "yyyy-MM-dd"),
    is_active: rule?.is_active ?? true,
  });
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name || !form.amount || !form.category_id) {
      toast.error("Name, amount, and category are required.");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        name: form.name,
        amount: parseFloat(form.amount),
        category_id: parseInt(form.category_id),
        frequency: form.frequency as RecurringRule["frequency"],
        next_due_date: form.next_due_date,
        is_active: form.is_active,
      };
      if (rule) {
        await updateRecurringRule(rule.id, payload);
        toast.success("Recurring rule updated!");
      } else {
        await createRecurringRule(payload);
        toast.success("Recurring rule created!");
      }
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-800 rounded-xl border border-gray-700 w-full max-w-md p-6 shadow-xl">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-white font-semibold text-lg">
            {rule ? "Edit" : "Add"} Recurring Expense
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Name *</label>
            <input
              type="text" required value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-amber-500"
              placeholder="e.g. Netflix Subscription"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Amount *</label>
              <input
                type="number" step="0.01" min="0.01" required value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-amber-500"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Frequency *</label>
              <select
                value={form.frequency}
                onChange={(e) => setForm({ ...form, frequency: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-amber-500"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="yearly">Yearly</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Category *</label>
              <select
                required value={form.category_id}
                onChange={(e) => setForm({ ...form, category_id: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-amber-500"
              >
                <option value="">Select…</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Start Date *</label>
              <input
                type="date" required value={form.next_due_date}
                onChange={(e) => setForm({ ...form, next_due_date: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-amber-500"
              />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700 text-sm transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className="flex-1 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-white font-medium text-sm transition-colors disabled:opacity-50">
              {saving ? "Saving…" : rule ? "Save Changes" : "Add Rule"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Inline budget limit editor
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface InlineLimitProps {
  budgetId: number | undefined;
  categoryId: number;
  currentLimit: number;
  month: number;
  year: number;
  onSaved: () => void;
}

function InlineLimitEditor({ budgetId, categoryId, currentLimit, month, year, onSaved }: InlineLimitProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(String(currentLimit));
  const [saving, setSaving] = useState(false);

  async function save() {
    const limit = parseFloat(value);
    if (!limit || limit <= 0) { toast.error("Enter a valid limit"); return; }
    setSaving(true);
    try {
      if (budgetId) {
        await updateBudget(budgetId, limit);
      } else {
        await createBudget({ category_id: categoryId, monthly_limit: limit, month, year });
      }
      toast.success("Budget updated!");
      setEditing(false);
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <button
        onClick={() => setEditing(true)}
        className="text-white font-bold text-xl hover:text-amber-400 transition-colors"
        title="Click to edit"
      >
        {formatCurrency(currentLimit, currencySymbol)}
      </button>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <input
        type="number" step="0.01" min="1" value={value} autoFocus
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditing(false); }}
        className="w-24 bg-gray-700 border border-amber-500 rounded px-2 py-1 text-white text-sm focus:outline-none"
      />
      <button onClick={save} disabled={saving}
        className="text-xs px-2 py-1 bg-amber-500 hover:bg-amber-400 text-white rounded transition-colors disabled:opacity-50">
        {saving ? "â€¦" : "âœ“"}
      </button>
      <button onClick={() => setEditing(false)} className="text-xs text-gray-500 hover:text-white">âœ•</button>
    </div>
  );
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Main page
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function Budgets() {
  const now = new Date();
  const { currencySymbol } = useCurrency();
  const [month, setMonth] = useState(getMonth(now) + 1);
  const [year, setYear] = useState(getYear(now));

  const [budgetStatus, setBudgetStatus] = useState<BudgetStatus[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [recurringRules, setRecurringRules] = useState<RecurringRule[]>([]);
  const [loading, setLoading] = useState(true);

  const [showRecurringModal, setShowRecurringModal] = useState(false);
  const [editingRule, setEditingRule] = useState<RecurringRule | null>(null);
  const [pendingDeleteRule, setPendingDeleteRule] = useState<number | null>(null);

  // Add Budget form state
  const [newBudgetCategoryId, setNewBudgetCategoryId] = useState("");
  const [newBudgetLimit, setNewBudgetLimit] = useState("");
  const [savingBudget, setSavingBudget] = useState(false);

  const currentYear = getYear(now);
  const years = Array.from({ length: 5 }, (_, i) => currentYear - i);
  const daysInMonth = getDaysInMonth(new Date(year, month - 1));
  const today = getDate(now);
  const daysRemaining = month === getMonth(now) + 1 && year === currentYear
    ? daysInMonth - today
    : 0;

  async function fetchAll() {
    setLoading(true);
    try {
      const [bs, cats, rules] = await Promise.all([
        getBudgetStatus(month, year),
        getCategories(),
        getRecurringRules(),
      ]);
      setBudgetStatus(bs);
      setCategories(cats);
      setRecurringRules(rules);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchAll(); }, [month, year]);

  async function handleDeleteRule(id: number) {
    await deleteRecurringRule(id);
    toast.success("Recurring rule deleted");
    setPendingDeleteRule(null);
    fetchAll();
  }

  async function handleToggleRule(id: number) {
    await toggleRecurringRule(id);
    fetchAll();
  }

  async function handleAddBudget(e: React.FormEvent) {
    e.preventDefault();
    if (!newBudgetCategoryId || !newBudgetLimit) {
      toast.error("Category and limit are required");
      return;
    }
    const limit = parseFloat(newBudgetLimit);
    if (!limit || limit <= 0) { toast.error("Enter a valid limit"); return; }
    setSavingBudget(true);
    try {
      await createBudget({
        category_id: parseInt(newBudgetCategoryId),
        monthly_limit: limit,
        month,
        year,
      });
      toast.success("Budget added!");
      setNewBudgetCategoryId("");
      setNewBudgetLimit("");
      fetchAll();
    } finally {
      setSavingBudget(false);
    }
  }

  // â”€â”€ Summary calculations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const totalBudgeted = budgetStatus.reduce((s, b) => s + b.monthly_limit, 0);
  const totalSpent = budgetStatus.reduce((s, b) => s + b.spent, 0);
  const totalRemaining = totalBudgeted - totalSpent;
  const overBudget = totalSpent > totalBudgeted;

  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // Render
  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  return (
    <div className="space-y-6 pb-8">

      {/* â”€â”€ Month/Year selector â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="flex items-center gap-3">
        <select
          value={month}
          onChange={(e) => setMonth(Number(e.target.value))}
          className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-amber-500"
        >
          {MONTHS.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
        </select>
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-amber-500"
        >
          {years.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
        <span className="text-gray-500 text-sm">{daysRemaining > 0 ? `${daysRemaining} days remaining` : ""}</span>
      </div>

      {/* â”€â”€ Budget Status Grid â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {loading ? (
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-44 bg-gray-800 rounded-xl animate-pulse border border-gray-700" />
          ))}
        </div>
      ) : budgetStatus.length === 0 ? (
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-10 text-center">
          <p className="text-4xl mb-3">🎯</p>
          <p className="text-white font-semibold mb-1">No budgets set</p>
          <p className="text-gray-500 text-sm">Add a budget below to start tracking your spending.</p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {budgetStatus.map((b) => {
            const style = STATUS_STYLES[b.status];
            return (
              <div
                key={b.category.id}
                className="bg-gray-800 rounded-xl border border-gray-700 p-5 border-l-4"
                style={{ borderLeftColor: b.category.color }}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="text-lg">{b.category.icon}</p>
                    <p className="text-white font-semibold text-sm mt-0.5">{b.category.name}</p>
                  </div>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border font-medium ${style.badge}`}
                  >
                    {STATUS_LABELS[b.status]}
                  </span>
                </div>

                {/* Ring + amounts */}
                <div className="flex items-center gap-4">
                  <CircularProgress pct={b.percentage} color={style.ring} />
                  <div className="flex-1 space-y-1">
                    <div>
                      <p className="text-xs text-gray-500">Limit</p>
                      <InlineLimitEditor
                        budgetId={undefined}
                        categoryId={b.category.id}
                        currentLimit={b.monthly_limit}
                        month={month}
                        year={year}
                        onSaved={fetchAll}
                      />
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Spent</p>
                      <p className="text-sm font-medium text-white">{formatCurrency(b.spent, currencySymbol)}</p>
                    </div>
                  </div>
                </div>

                {/* Footer */}
                <div className="mt-4 pt-3 border-t border-gray-700 flex justify-between text-xs text-gray-500">
                  <span>Projected: <span className="text-gray-300">{formatCurrency(b.projected_month_end, currencySymbol)}</span></span>
                  <span>
                    {b.remaining >= 0
                      ? <span className="text-green-400">{formatCurrency(b.remaining, currencySymbol)} left</span>
                      : <span className="text-red-400">{formatCurrency(Math.abs(b.remaining), currencySymbol)} over</span>}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* -- Add Budget Form ------------------------------------------------ */}
      {!loading && (
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Plus size={16} className="text-amber-400" />
            Add / Update Budget
          </h2>
          <form onSubmit={handleAddBudget} className="flex flex-wrap items-end gap-3">
            <div>
              <p className="text-xs text-gray-400 mb-1">Category *</p>
              <select
                required
                value={newBudgetCategoryId}
                onChange={(e) => setNewBudgetCategoryId(e.target.value)}
                className="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-amber-500 min-w-[160px]"
              >
                <option value="">Select category...</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Monthly Limit *</p>
              <input
                type="number"
                step="0.01"
                min="0.01"
                required
                value={newBudgetLimit}
                onChange={(e) => setNewBudgetLimit(e.target.value)}
                placeholder="0.00"
                className="bg-gray-700 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 w-32 focus:outline-none focus:border-amber-500"
              />
            </div>
            <button
              type="submit"
              disabled={savingBudget}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              {savingBudget ? "Saving..." : "Set Budget"}
            </button>
          </form>
        </div>
      )}

      {/* -- Recurring Expense Manager --------------------------------------- */}
      <div className="bg-gray-800 rounded-xl border border-gray-700">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <div>
            <h2 className="text-white font-semibold">Recurring Expenses</h2>
            <p className="text-xs text-gray-500 mt-0.5">Automatic expense rules</p>
          </div>
          <button
            onClick={() => { setEditingRule(null); setShowRecurringModal(true); }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-white text-sm font-medium transition-colors"
          >
            <Plus size={14} /> Add Recurring
          </button>
        </div>

        {recurringRules.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">
            No recurring rules. Click "Add Recurring" to create one.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase tracking-wide border-b border-gray-700">
                <th className="px-5 py-3 text-left">Name</th>
                <th className="px-5 py-3 text-left">Amount</th>
                <th className="px-5 py-3 text-left">Category</th>
                <th className="px-5 py-3 text-left">Frequency</th>
                <th className="px-5 py-3 text-left">Next Due</th>
                <th className="px-5 py-3 text-center">Active</th>
                <th className="px-5 py-3 text-center w-20">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/60">
              {recurringRules.map((rule) => (
                <>
                  <tr key={rule.id} className="text-gray-300 hover:bg-gray-700/30 transition-colors">
                    <td className="px-5 py-3 font-medium text-white">{rule.name}</td>
                    <td className="px-5 py-3">{formatCurrency(rule.amount, currencySymbol)}</td>
                    <td className="px-5 py-3">
                      {rule.category ? (
                        <span
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                          style={{
                            backgroundColor: rule.category.color + "22",
                            color: rule.category.color,
                          }}
                        >
                          {rule.category.icon} {rule.category.name}
                        </span>
                      ) : "â€”"}
                    </td>
                    <td className="px-5 py-3">{FREQ_LABELS[rule.frequency]}</td>
                    <td className="px-5 py-3 text-gray-400">
                      {format(parseISO(rule.next_due_date), "MMM d, yyyy")}
                    </td>
                    <td className="px-5 py-3 text-center">
                      <button
                        onClick={() => handleToggleRule(rule.id)}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                          rule.is_active ? "bg-amber-500" : "bg-gray-600"
                        }`}
                      >
                        <span
                          className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                            rule.is_active ? "translate-x-5" : "translate-x-0.5"
                          }`}
                        />
                      </button>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => { setEditingRule(rule); setShowRecurringModal(true); }}
                          className="text-gray-500 hover:text-amber-400 transition-colors"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => setPendingDeleteRule(pendingDeleteRule === rule.id ? null : rule.id)}
                          className="text-gray-500 hover:text-red-400 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>

                  {pendingDeleteRule === rule.id && (
                    <tr key={`del-${rule.id}`} className="bg-red-500/10">
                      <td colSpan={7} className="px-5 py-3">
                        <div className="flex items-center justify-between">
                          <span className="text-red-400 text-sm">
                            Delete <strong>{rule.name}</strong>? This cannot be undone.
                          </span>
                          <div className="flex gap-2">
                            <button onClick={() => setPendingDeleteRule(null)}
                              className="px-3 py-1 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700 text-xs">
                              Cancel
                            </button>
                            <button onClick={() => handleDeleteRule(rule.id)}
                              className="px-3 py-1 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-medium">
                              Delete
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* -- Recurring Total Summary --------------------------------------- */}
      {recurringRules.length > 0 && (() => {
        const activeCount = recurringRules.filter((r) => r.is_active).length;
        const activeTotal = recurringRules
          .filter((r) => r.is_active)
          .reduce((s, r) => s + r.amount, 0);
        return (
          <div className="bg-gray-700 border border-gray-600 rounded-lg p-4 flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Monthly Recurring Total</p>
              <p className="text-gray-500 text-xs mt-0.5">
                {activeCount} of {recurringRules.length} subscriptions active
              </p>
            </div>
            <p className="text-amber-400 font-bold text-lg">
              {formatCurrency(activeTotal, currencySymbol)}
            </p>
          </div>
        );
      })()}

      {/* â”€â”€ Summary Bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {budgetStatus.length > 0 && (
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Total Budgeted</p>
              <p className="text-xl font-bold text-white">{formatCurrency(totalBudgeted, currencySymbol)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Total Spent</p>
              <p className="text-xl font-bold text-white">{formatCurrency(totalSpent, currencySymbol)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Remaining</p>
              <p className={`text-xl font-bold ${totalRemaining >= 0 ? "text-green-400" : "text-red-400"}`}>
                {formatCurrency(Math.abs(totalRemaining), currencySymbol)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Status</p>
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold border ${
                overBudget
                  ? "bg-red-500/15 text-red-400 border-red-500/30"
                  : "bg-green-500/15 text-green-400 border-green-500/30"
              }`}>
                {overBudget ? "Over Budget" : "Under Budget"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* â”€â”€ Modals â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {showRecurringModal && (
        <RecurringModal
          rule={editingRule}
          categories={categories}
          onClose={() => { setShowRecurringModal(false); setEditingRule(null); }}
          onSaved={() => { setShowRecurringModal(false); setEditingRule(null); fetchAll(); }}
        />
      )}
    </div>
  );
}

