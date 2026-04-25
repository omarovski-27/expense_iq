import {
  useState,
  useEffect,
  useRef,
  useCallback,
} from "react";
import {
  Plus,
  Upload,
  Download,
  FileSpreadsheet,
  RefreshCw,
  Pencil,
  Trash2,
  ChevronLeft,
  ChevronRight,
  X,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { format, parseISO, getYear } from "date-fns";
import toast from "react-hot-toast";

import { getExpenses, deleteExpense, bulkImport } from "../api/expenses";
import { getCategories } from "../api/categories";
import AddExpenseModal from "../components/expenses/AddExpenseModal";
import EditExpenseModal from "../components/expenses/EditExpenseModal";
import { formatCurrency } from "../utils/formatCurrency";
import client from "../api/client";
import { useCurrency } from "../context/CurrencyContext";

import type { Expense, Category } from "../types";

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Helpers
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];
const PAGE_SIZE = 25;

type SortKey = "date" | "amount" | "merchant" | "description";
type SortDir = "asc" | "desc";

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Component
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function Transactions() {
  const now = new Date();

  // â”€â”€ Filters â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const [filterMonth, setFilterMonth] = useState(now.getMonth() + 1);
  const [filterYear, setFilterYear] = useState(getYear(now));
  const [filterCategory, setFilterCategory] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");        // debounced
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // â”€â”€ Data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const { currencySymbol } = useCurrency();

  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  // â”€â”€ Sorting & pagination â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);

  // â”€â”€ Modals â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const [showAdd, setShowAdd] = useState(false);
  const [editExpense, setEditExpense] = useState<Expense | null>(null);
  const [pendingDelete, setPendingDelete] = useState<number | null>(null);

  // â”€â”€ Hidden file input for CSV import â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const fileInputRef = useRef<HTMLInputElement>(null);

  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // Fetch
  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  async function fetchExpenses() {
    setLoading(true);
    try {
      const data = await getExpenses({
        month: filterMonth || undefined,
        year: filterYear || undefined,
        category_id: filterCategory ? Number(filterCategory) : undefined,
        search: search || undefined,
        limit: 1000,
      });
      setExpenses(data);
      setPage(1);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    getCategories().then(setCategories);
  }, []);

  useEffect(() => {
    fetchExpenses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterMonth, filterYear, filterCategory, search]);

  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // Debounce search
  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  const handleSearchChange = useCallback((value: string) => {
    setSearchInput(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setSearch(value), 300);
  }, []);

  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // Sort + paginate (client-side)
  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  const sorted = [...expenses].sort((a, b) => {
    let cmp = 0;
    if (sortKey === "date") cmp = a.date.localeCompare(b.date);
    else if (sortKey === "amount") cmp = a.amount - b.amount;
    else if (sortKey === "merchant")
      cmp = (a.merchant ?? "").localeCompare(b.merchant ?? "");
    else if (sortKey === "description")
      cmp = a.description.localeCompare(b.description);
    return sortDir === "asc" ? cmp : -cmp;
  });

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const paginated = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("desc"); }
  }

  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // Handlers
  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  function clearFilters() {
    setFilterMonth(now.getMonth() + 1);
    setFilterYear(getYear(now));
    setFilterCategory("");
    setSearchInput("");
    setSearch("");
  }

  async function handleDelete(id: number) {
    await deleteExpense(id);
    toast.success("Expense deleted");
    setPendingDelete(null);
    fetchExpenses();
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await bulkImport(file);
      toast.success(`Imported ${result.imported} expenses (${result.skipped} skipped)`);
      fetchExpenses();
    } catch {
      // error toast handled by axios interceptor
    } finally {
      e.target.value = "";
    }
  }

  function exportUrl(type: "csv" | "excel") {
    const base = `${client.defaults.baseURL}/exports`;
    const params = new URLSearchParams();
    if (filterMonth) params.set("month", String(filterMonth));
    if (filterYear) params.set("year", String(filterYear));
    return `${base}/${type === "csv" ? "csv" : "excel"}?${params}`;
  }

  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // Sort header helper
  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  function SortIcon({ col }: { col: SortKey }) {
    if (sortKey !== col) return <ChevronUp size={12} className="text-gray-600" />;
    return sortDir === "asc"
      ? <ChevronUp size={12} className="text-amber-400" />
      : <ChevronDown size={12} className="text-amber-400" />;
  }

  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // Render
  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  const currentYear = getYear(now);
  const years = Array.from({ length: 5 }, (_, i) => currentYear - i);

  return (
    <div className="space-y-4 pb-8">

      {/* â”€â”€ Filter Bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 flex flex-col sm:flex-row sm:flex-wrap items-stretch sm:items-center gap-3">
        {/* Month */}
        <select
          value={filterMonth}
          onChange={(e) => setFilterMonth(Number(e.target.value))}
          className="w-full sm:w-auto bg-gray-700 border border-gray-600 text-white text-base rounded-lg px-3 h-11 focus:outline-none focus:border-amber-500"
        >
          <option value={0}>All months</option>
          {MONTHS.map((m, i) => (
            <option key={i} value={i + 1}>{m}</option>
          ))}
        </select>

        {/* Year */}
        <select
          value={filterYear}
          onChange={(e) => setFilterYear(Number(e.target.value))}
          className="w-full sm:w-auto bg-gray-700 border border-gray-600 text-white text-base rounded-lg px-3 h-11 focus:outline-none focus:border-amber-500"
        >
          {years.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>

        {/* Category */}
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="w-full sm:w-auto bg-gray-700 border border-gray-600 text-white text-base rounded-lg px-3 h-11 focus:outline-none focus:border-amber-500"
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
          ))}
        </select>

        {/* Search */}
        <input
          type="text"
          data-search
          ref={searchInputRef}
          placeholder="Search description or merchant…"
          value={searchInput}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="w-full sm:flex-1 sm:min-w-[200px] bg-gray-700 border border-gray-600 text-white text-base rounded-lg px-3 h-11 focus:outline-none focus:border-amber-500 placeholder-gray-500"
        />

        {/* Clear */}
        <button
          onClick={clearFilters}
          className="flex items-center justify-center gap-1.5 w-full sm:w-auto px-3 h-11 rounded-lg border border-gray-600 text-gray-400 hover:text-white hover:bg-gray-700 text-sm transition-colors touch-manipulation"
        >
          <X size={14} /> Clear
        </button>

        {/* Count */}
        <span className="text-xs text-gray-500 sm:ml-auto w-full sm:w-auto text-left sm:text-right">
          Showing {expenses.length} expense{expenses.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* â”€â”€ Action Bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="grid grid-cols-1 sm:flex sm:flex-wrap items-stretch sm:items-center gap-2">
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center justify-center gap-2 px-4 h-11 rounded-lg bg-amber-500 hover:bg-amber-400 text-white text-sm font-medium transition-colors touch-manipulation"
        >
          <Plus size={16} /> Add Expense
        </button>

        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center justify-center gap-2 px-4 h-11 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700 text-sm transition-colors touch-manipulation"
        >
          <Upload size={16} /> Import CSV
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={handleImport}
        />

        <button
          onClick={() => window.open(exportUrl("csv"), "_blank")}
          className="flex items-center justify-center gap-2 px-4 h-11 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700 text-sm transition-colors touch-manipulation"
        >
          <Download size={16} /> Export CSV
        </button>

        <button
          onClick={() => window.open(exportUrl("excel"), "_blank")}
          className="flex items-center justify-center gap-2 px-4 h-11 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700 text-sm transition-colors touch-manipulation"
        >
          <FileSpreadsheet size={16} /> Export Excel
        </button>
      </div>

      <div className="md:hidden space-y-3">
        {loading ? (
          Array.from({ length: 6 }).map((_, index) => (
            <div
              key={index}
              className="bg-gray-800 rounded-xl border border-gray-700 p-4 space-y-3"
            >
              <div className="h-5 w-1/2 bg-gray-700 rounded animate-pulse" />
              <div className="h-4 w-1/3 bg-gray-700 rounded animate-pulse" />
              <div className="h-4 w-1/4 bg-gray-700 rounded animate-pulse" />
            </div>
          ))
        ) : paginated.length === 0 ? (
          <div className="bg-gray-800 rounded-xl border border-gray-700 px-4 py-16 text-center">
            <p className="text-4xl mb-3">ðŸ“­</p>
            <p className="text-white font-semibold mb-1">No expenses found</p>
            <p className="text-gray-500 text-sm">Try adjusting your filters or add a new expense</p>
          </div>
        ) : (
          paginated.map((exp) => (
            <div key={exp.id} className="space-y-2">
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 flex justify-between items-start gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-white font-medium truncate">{exp.merchant || exp.description}</p>
                  {exp.merchant && (
                    <p className="text-sm text-gray-400 mt-1 truncate">{exp.description}</p>
                  )}
                  <div className="flex flex-wrap items-center gap-2 mt-3 text-sm text-gray-400">
                    {exp.category ? (
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                        style={{
                          backgroundColor: exp.category.color + "22",
                          color: exp.category.color,
                        }}
                      >
                        {exp.category.icon} {exp.category.name}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-500">No category</span>
                    )}
                    <span>{format(parseISO(exp.date), "MMM d, yyyy")}</span>
                    {exp.is_recurring && (
                      <span className="inline-flex items-center gap-1 text-amber-400 text-xs">
                        <RefreshCw size={12} /> Recurring
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-3 flex-shrink-0">
                  <p className="text-amber-400 font-bold text-base whitespace-nowrap">
                    {formatCurrency(exp.amount, currencySymbol)}
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setEditExpense(exp)}
                      className="h-10 w-10 rounded-lg border border-gray-700 text-gray-400 hover:text-amber-400 hover:bg-gray-700/60 transition-colors touch-manipulation flex items-center justify-center"
                      title="Edit"
                      aria-label={`Edit ${exp.description}`}
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      onClick={() =>
                        setPendingDelete(pendingDelete === exp.id ? null : exp.id)
                      }
                      className="h-10 w-10 rounded-lg border border-gray-700 text-gray-400 hover:text-red-400 hover:bg-gray-700/60 transition-colors touch-manipulation flex items-center justify-center"
                      title="Delete"
                      aria-label={`Delete ${exp.description}`}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>

              {pendingDelete === exp.id && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 flex items-start justify-between gap-3">
                  <span className="text-red-300 text-sm">
                    Delete <strong>{exp.description}</strong>?
                  </span>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => setPendingDelete(null)}
                      className="px-3 h-9 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700 text-xs touch-manipulation"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleDelete(exp.id)}
                      className="px-3 h-9 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-medium touch-manipulation"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* â”€â”€ Table â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="hidden md:block bg-gray-800 rounded-xl border border-gray-700 overflow-x-auto">
        <table className="w-full min-w-[900px] text-sm">
          <thead>
            <tr className="border-b border-gray-700 text-gray-400 text-xs uppercase tracking-wide">
              <th
                className="px-4 py-3 text-left cursor-pointer hover:text-white select-none"
                onClick={() => toggleSort("date")}
              >
                <span className="flex items-center gap-1">Date <SortIcon col="date" /></span>
              </th>
              <th
                className="px-4 py-3 text-left cursor-pointer hover:text-white select-none"
                onClick={() => toggleSort("merchant")}
              >
                <span className="flex items-center gap-1">Merchant <SortIcon col="merchant" /></span>
              </th>
              <th
                className="px-4 py-3 text-left cursor-pointer hover:text-white select-none"
                onClick={() => toggleSort("description")}
              >
                <span className="flex items-center gap-1">Description <SortIcon col="description" /></span>
              </th>
              <th className="px-4 py-3 text-left">Category</th>
              <th
                className="px-4 py-3 text-right cursor-pointer hover:text-white select-none"
                onClick={() => toggleSort("amount")}
              >
                <span className="flex items-center justify-end gap-1">Amount <SortIcon col="amount" /></span>
              </th>
              <th className="px-4 py-3 text-center w-8"></th>
              <th className="px-4 py-3 text-center w-20">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700/60">
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 7 }).map((__, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-gray-700 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : paginated.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-16 text-center">
                  <p className="text-4xl mb-3">ðŸ“­</p>
                  <p className="text-white font-semibold mb-1">No expenses found</p>
                  <p className="text-gray-500 text-xs">Try adjusting your filters or add a new expense</p>
                </td>
              </tr>
            ) : (
              paginated.map((exp) => (
                <>
                  <tr
                    key={exp.id}
                    className="text-gray-300 hover:bg-gray-700/40 transition-colors"
                  >
                    <td className="px-4 py-3 text-gray-400 whitespace-nowrap">
                      {format(parseISO(exp.date), "MMM d, yyyy")}
                    </td>
                    <td className="px-4 py-3 text-gray-300 max-w-[120px] truncate">
                      {exp.merchant || <span className="text-gray-600">â€”</span>}
                    </td>
                    <td className="px-4 py-3 max-w-[200px] truncate">{exp.description}</td>
                    <td className="px-4 py-3">
                      {exp.category ? (
                        <span
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                          style={{
                            backgroundColor: exp.category.color + "22",
                            color: exp.category.color,
                          }}
                        >
                          {exp.category.icon} {exp.category.name}
                        </span>
                      ) : (
                        <span className="text-gray-600 text-xs">â€”</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-white whitespace-nowrap">
                      {formatCurrency(exp.amount, currencySymbol)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {exp.is_recurring && (
                        <RefreshCw size={13} className="text-amber-400 inline" />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => setEditExpense(exp)}
                          className="text-gray-500 hover:text-amber-400 transition-colors"
                          title="Edit"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() =>
                            setPendingDelete(pendingDelete === exp.id ? null : exp.id)
                          }
                          className="text-gray-500 hover:text-red-400 transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* Inline delete confirmation */}
                  {pendingDelete === exp.id && (
                    <tr key={`del-${exp.id}`} className="bg-red-500/10">
                      <td colSpan={7} className="px-4 py-3">
                        <div className="flex items-center justify-between">
                          <span className="text-red-400 text-sm">
                            Delete <strong>{exp.description}</strong>? This cannot be undone.
                          </span>
                          <div className="flex gap-2">
                            <button
                              onClick={() => setPendingDelete(null)}
                              className="px-3 py-1 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700 text-xs"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => handleDelete(exp.id)}
                              className="px-3 py-1 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-medium"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* â”€â”€ Pagination â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {!loading && expenses.length > PAGE_SIZE && (
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed text-sm transition-colors"
          >
            <ChevronLeft size={14} /> Previous
          </button>
          <span className="text-gray-400 text-sm">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed text-sm transition-colors"
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      )}

      {/* â”€â”€ Modals â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {showAdd && (
        <AddExpenseModal
          onClose={() => setShowAdd(false)}
          onSaved={() => { setShowAdd(false); fetchExpenses(); }}
        />
      )}

      {editExpense && (
        <EditExpenseModal
          expense={editExpense}
          onClose={() => setEditExpense(null)}
          onSaved={() => { setEditExpense(null); fetchExpenses(); }}
        />
      )}
    </div>
  );
}

