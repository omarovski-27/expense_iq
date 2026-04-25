import { useState, useEffect } from "react";
import { X } from "lucide-react";
import toast from "react-hot-toast";
import { updateExpense } from "../../api/expenses";
import { getCategories } from "../../api/categories";
import type { Category, Expense } from "../../types";

interface Props {
  expense: Expense;
  onClose: () => void;
  onSaved: () => void;
}

export default function EditExpenseModal({ expense, onClose, onSaved }: Props) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState({
    amount: String(expense.amount),
    description: expense.description,
    category_id: String(expense.category_id),
    merchant: expense.merchant ?? "",
    date: expense.date,
    is_recurring: expense.is_recurring,
    frequency: "monthly",        // frequency is not stored on Expense itself
    notes: expense.notes ?? "",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getCategories().then(setCategories);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.amount || !form.description || !form.category_id) {
      toast.error("Amount, description, and category are required.");
      return;
    }
    setSaving(true);
    try {
      await updateExpense(expense.id, {
        amount: parseFloat(form.amount),
        description: form.description,
        category_id: parseInt(form.category_id),
        merchant: form.merchant || undefined,
        date: form.date,
        is_recurring: form.is_recurring,
        notes: form.notes || undefined,
      });
      toast.success("Expense updated!");
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-end md:items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-800 rounded-t-2xl md:rounded-xl border border-gray-700 w-full md:max-w-md p-6 shadow-xl max-h-[90vh] overflow-y-auto">
        <div className="w-10 h-1 bg-gray-600 rounded-full mx-auto mt-0 mb-4 md:hidden" />
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-white font-semibold text-lg">Edit Expense</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white h-11 w-11 flex items-center justify-center touch-manipulation">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Amount *</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                required
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 h-11 text-white text-base focus:outline-none focus:border-amber-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Date *</label>
              <input
                type="date"
                required
                value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 h-11 text-white text-base focus:outline-none focus:border-amber-500"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Description *</label>
            <input
              type="text"
              required
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 h-11 text-white text-base focus:outline-none focus:border-amber-500"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Category *</label>
              <select
                required
                value={form.category_id}
                onChange={(e) => setForm({ ...form, category_id: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 h-11 text-white text-base focus:outline-none focus:border-amber-500"
              >
                <option value="">Selectâ€¦</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.icon} {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Merchant</label>
              <input
                type="text"
                value={form.merchant}
                onChange={(e) => setForm({ ...form, merchant: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 h-11 text-white text-base focus:outline-none focus:border-amber-500"
                placeholder="Optional"
              />
            </div>
          </div>

          {/* Recurring toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-300">Recurring expense</p>
              <p className="text-xs text-gray-500">Repeats on a schedule</p>
            </div>
            <button
              type="button"
              onClick={() => setForm({ ...form, is_recurring: !form.is_recurring })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors touch-manipulation ${
                form.is_recurring ? "bg-amber-500" : "bg-gray-600"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  form.is_recurring ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>

          {/* Frequency â€” shown only when recurring */}
          {form.is_recurring && (
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Frequency</label>
              <select
                value={form.frequency}
                onChange={(e) => setForm({ ...form, frequency: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 h-11 text-white text-base focus:outline-none focus:border-amber-500"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="yearly">Yearly</option>
              </select>
            </div>
          )}

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Notes</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={2}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-base focus:outline-none focus:border-amber-500 resize-none"
              placeholder="Optional notes"
            />
          </div>

          <div className="sticky bottom-0 flex gap-3 pt-3 pb-2 bg-gray-800">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 h-11 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700 text-sm transition-colors touch-manipulation"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 px-4 h-11 rounded-lg bg-amber-500 hover:bg-amber-400 text-white font-medium text-sm transition-colors disabled:opacity-50 touch-manipulation"
            >
              {saving ? "Savingâ€¦" : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
