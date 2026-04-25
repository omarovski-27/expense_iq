import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import {
  Check,
  Database,
  Download,
  Edit2,
  ExternalLink,
  Palette,
  Plus,
  Tag,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import client from "../api/client";
import { useCurrency } from "../context/CurrencyContext";

import {
  createCategory,
  deleteCategory,
  getCategories,
  updateCategory,
} from "../api/categories";
import { bulkImport } from "../api/expenses";
import type { Category } from "../types";

// â”€â”€â”€ helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const LS_CURRENCY = "expenseiq_currency";
const LS_DATE_FORMAT = "expenseiq_date_format";
const LS_LAST_BACKUP = "expenseiq_last_backup";

function getCurrency() {
  return localStorage.getItem(LS_CURRENCY) ?? "$";
}
function getDateFormat() {
  return (localStorage.getItem(LS_DATE_FORMAT) as "MM/DD/YYYY" | "DD/MM/YYYY") ?? "MM/DD/YYYY";
}
function getLastBackup() {
  return localStorage.getItem(LS_LAST_BACKUP) ?? null;
}

// â”€â”€â”€ sub-components â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface EditRowProps {
  category: Category;
  onSave: (id: number, data: { name: string; color: string; icon: string }) => Promise<void>;
  onCancel: () => void;
}

function EditRow({ category, onSave, onCancel }: EditRowProps) {
  const [name, setName] = useState(category.name);
  const [color, setColor] = useState(category.color);
  const [icon, setIcon] = useState(category.icon);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave(category.id, { name: name.trim(), color, icon });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 py-3 px-3 bg-gray-700 rounded-lg">
      <input
        type="color"
        value={color}
        onChange={(e) => setColor(e.target.value)}
        className="w-10 h-10 rounded cursor-pointer border-0 bg-transparent"
        title="Category color"
      />
      <input
        value={icon}
        onChange={(e) => setIcon(e.target.value)}
        className="w-full sm:w-14 text-center bg-gray-600 border border-gray-500 rounded px-1 h-11 text-white text-lg"
        maxLength={2}
        placeholder="ðŸ·"
      />
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSave()}
        className="flex-1 bg-gray-600 border border-gray-500 rounded px-3 h-11 text-white text-base focus:outline-none focus:border-amber-500"
        placeholder="Category name"
      />
      <div className="flex items-center gap-2 sm:ml-auto">
        <button
          onClick={handleSave}
          disabled={saving}
          className="h-10 px-3 text-green-400 hover:text-green-300 hover:bg-green-400/10 rounded touch-manipulation"
          title="Save"
        >
          <Check size={16} />
        </button>
        <button
          onClick={onCancel}
          className="h-10 px-3 text-gray-400 hover:text-white hover:bg-gray-600 rounded touch-manipulation"
          title="Cancel"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
}

// â”€â”€â”€ main page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function Settings() {
  // â”€â”€ categories state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const [categories, setCategories] = useState<Category[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [reassignTo, setReassignTo] = useState<number | "">("");

  // add form
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState("#6366f1");
  const [newIcon, setNewIcon] = useState("");
  const [addingCat, setAddingCat] = useState(false);

  // â”€â”€ data management state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const importRef = useRef<HTMLInputElement>(null);
  const [lastBackup, setLastBackup] = useState<string | null>(getLastBackup);

  // â”€â”€ preferences state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const { setCurrencySymbol } = useCurrency();
  const [currency, setCurrency] = useState(getCurrency);
  const [dateFormat, setDateFormat] = useState<"MM/DD/YYYY" | "DD/MM/YYYY">(getDateFormat);

  // â”€â”€ load â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  useEffect(() => {
    getCategories().then(setCategories).catch(() => {});
  }, []);

  // â”€â”€ category handlers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  async function handleSaveEdit(
    id: number,
    data: { name: string; color: string; icon: string }
  ) {
    try {
      const updated = await updateCategory(id, data);
      setCategories((prev) => prev.map((c) => (c.id === id ? updated : c)));
      setEditingId(null);
      toast.success("Category updated");
    } catch {
      // error toast handled by axios interceptor
    }
  }

  function startDelete(id: number) {
    setDeletingId(id);
    setReassignTo("");
  }

  async function confirmDelete() {
    if (deletingId === null) return;
    try {
      await deleteCategory(
        deletingId,
        reassignTo !== "" ? (reassignTo as number) : undefined
      );
      setCategories((prev) => prev.filter((c) => c.id !== deletingId));
      setDeletingId(null);
      toast.success("Category deleted");
    } catch {
      // error toast handled by interceptor
    }
  }

  async function handleAddCategory() {
    if (!newName.trim()) {
      toast.error("Name is required");
      return;
    }
    setAddingCat(true);
    try {
      const cat = await createCategory({
        name: newName.trim(),
        color: newColor,
        icon: newIcon || "ðŸ“¦",
      });
      setCategories((prev) => [...prev, cat]);
      setNewName("");
      setNewColor("#6366f1");
      setNewIcon("");
      toast.success("Category added");
    } finally {
      setAddingCat(false);
    }
  }

  // â”€â”€ data management handlers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  function handleExportCSV() {
    const ts = new Date().toISOString();
    localStorage.setItem(LS_LAST_BACKUP, ts);
    setLastBackup(ts);
    window.open(`${client.defaults.baseURL}/exports/csv`, "_blank");
  }

  function handleExportExcel() {
    const now = new Date();
    const ts = now.toISOString();
    localStorage.setItem(LS_LAST_BACKUP, ts);
    setLastBackup(ts);
    const month = now.getMonth() + 1;
    const year = now.getFullYear();
    window.open(
      `${client.defaults.baseURL}/exports/excel?month=${month}&year=${year}`,
      "_blank"
    );
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await bulkImport(file);
      toast.success(`Imported ${result.imported} expenses (${result.skipped} skipped)`);
    } catch {
      // handled by interceptor
    } finally {
      if (importRef.current) importRef.current.value = "";
    }
  }

  // â”€â”€ preference handlers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  function saveCurrency(val: string) {
    setCurrency(val);
    setCurrencySymbol(val);
  }

  function saveDateFormat(val: "MM/DD/YYYY" | "DD/MM/YYYY") {
    setDateFormat(val);
    localStorage.setItem(LS_DATE_FORMAT, val);
  }

  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // Render
  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const sectionClass = "bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6";
  const sectionTitleClass = "flex items-center gap-2 text-lg font-semibold text-white mb-5";
  const labelClass = "text-sm text-gray-400 mb-1";
  const inputClass =
    "bg-gray-700 border border-gray-600 rounded-lg px-3 h-11 text-white text-base focus:outline-none focus:border-amber-500 w-full";

  return (
    <div className="p-4 md:p-6 max-w-3xl mx-auto pb-24 md:pb-6">
      <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>

      {/* â”€â”€ SECTION 1: Category Manager â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className={sectionClass}>
        <h2 className={sectionTitleClass}>
          <Tag size={18} className="text-amber-400" />
          Category Manager
        </h2>

        <div className="space-y-2 mb-6">
          {categories.map((cat) => (
            <div key={cat.id}>
              {editingId === cat.id ? (
                <EditRow
                  category={cat}
                  onSave={handleSaveEdit}
                  onCancel={() => setEditingId(null)}
                />
              ) : deletingId === cat.id ? (
                /* delete confirmation row */
                <div className="flex flex-col sm:flex-row sm:items-center gap-3 py-3 px-3 bg-red-900/20 border border-red-700/50 rounded-lg">
                  <span className="text-sm text-red-300 flex-1">
                    Delete <strong>{cat.name}</strong>?
                  </span>
                  <select
                    value={reassignTo}
                    onChange={(e) =>
                      setReassignTo(e.target.value === "" ? "" : Number(e.target.value))
                    }
                    className="w-full sm:w-auto bg-gray-700 border border-gray-600 rounded px-3 h-11 text-base text-white focus:outline-none focus:border-amber-500"
                    title="Reassign expenses to"
                  >
                    <option value="">Reassign expenses toâ€¦</option>
                    {categories
                      .filter((c) => c.id !== cat.id)
                      .map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.icon} {c.name}
                        </option>
                      ))}
                  </select>
                  <button
                    onClick={confirmDelete}
                    className="px-3 h-11 bg-red-600 hover:bg-red-500 text-white text-sm rounded font-medium touch-manipulation"
                  >
                    Delete
                  </button>
                  <button
                    onClick={() => setDeletingId(null)}
                    className="h-11 w-11 text-gray-400 hover:text-white hover:bg-gray-700 rounded touch-manipulation"
                  >
                    <X size={14} />
                  </button>
                </div>
              ) : (
                /* normal row */
                <div className="flex items-center gap-3 py-2 px-3 hover:bg-gray-700/50 rounded-lg group">
                  <span
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: cat.color }}
                  />
                  <span className="text-lg leading-none">{cat.icon}</span>
                  <span className="flex-1 text-sm text-white">{cat.name}</span>
                  <button
                    onClick={() => setEditingId(cat.id)}
                    className="p-2 text-gray-500 hover:text-amber-400 hover:bg-amber-400/10 rounded opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity touch-manipulation"
                    title="Edit"
                  >
                    <Edit2 size={14} />
                  </button>
                  <button
                    onClick={() => startDelete(cat.id)}
                    className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-400/10 rounded opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity touch-manipulation"
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Add Category form */}
        <div className="border-t border-gray-700 pt-5">
          <p className="text-sm font-medium text-gray-300 mb-3">Add Category</p>
          <div className="flex flex-col sm:flex-row sm:items-end gap-3">
            <div>
              <p className={labelClass}>Color</p>
              <input
                type="color"
                value={newColor}
                onChange={(e) => setNewColor(e.target.value)}
                className="w-full sm:w-10 h-11 rounded cursor-pointer border border-gray-600 bg-transparent"
                title="Pick a color"
              />
            </div>
            <div className="w-full sm:w-20">
              <p className={labelClass}>Emoji</p>
              <input
                value={newIcon}
                onChange={(e) => setNewIcon(e.target.value)}
                placeholder="ðŸ“¦"
                maxLength={2}
                className={inputClass + " text-center text-lg"}
              />
            </div>
            <div className="flex-1">
              <p className={labelClass}>Name *</p>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAddCategory()}
                placeholder="Category name"
                className={inputClass}
              />
            </div>
            <button
              onClick={handleAddCategory}
              disabled={addingCat}
              className="flex items-center justify-center gap-1.5 px-4 h-11 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black text-sm font-semibold rounded-lg transition-colors touch-manipulation"
            >
              <Plus size={16} />
              Add
            </button>
          </div>
        </div>
      </div>

      {/* â”€â”€ SECTION 2: Data Management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className={sectionClass}>
        <h2 className={sectionTitleClass}>
          <Database size={18} className="text-amber-400" />
          Data Management
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
          <button
            onClick={handleExportCSV}
            className="flex items-center justify-center gap-2 px-4 h-11 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg border border-gray-600 transition-colors touch-manipulation"
          >
            <Download size={16} className="text-green-400" />
            Export All Data (CSV)
          </button>

          <button
            onClick={handleExportExcel}
            className="flex items-center justify-center gap-2 px-4 h-11 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg border border-gray-600 transition-colors touch-manipulation"
          >
            <Download size={16} className="text-blue-400" />
            Export Excel Report
          </button>

          <button
            onClick={() => importRef.current?.click()}
            className="flex items-center justify-center gap-2 px-4 h-11 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg border border-gray-600 transition-colors touch-manipulation"
          >
            <Upload size={16} className="text-amber-400" />
            Import CSV
          </button>
        </div>

        <input
          ref={importRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={handleImport}
        />

        {lastBackup && (
          <p className="text-xs text-gray-500">
            Last export:{" "}
            <span className="text-gray-400">
              {new Date(lastBackup).toLocaleString()}
            </span>
          </p>
        )}
      </div>

      {/* â”€â”€ SECTION 3: Preferences â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className={sectionClass}>
        <h2 className={sectionTitleClass}>
          <Palette size={18} className="text-amber-400" />
          Preferences
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {/* Currency symbol */}
          <div>
            <p className={labelClass}>Currency Symbol</p>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                value={currency}
                onChange={(e) => saveCurrency(e.target.value)}
                maxLength={3}
                className="w-full sm:w-20 bg-gray-700 border border-gray-600 rounded-lg px-3 h-11 text-white text-base text-center focus:outline-none focus:border-amber-500"
                placeholder="$"
              />
              <span className="text-xs text-gray-500 self-center">
                Used for display only
              </span>
            </div>
          </div>

          {/* Date format toggle */}
          <div>
            <p className={labelClass}>Date Format</p>
            <div className="flex flex-col sm:flex-row gap-2">
              {(["MM/DD/YYYY", "DD/MM/YYYY"] as const).map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => saveDateFormat(fmt)}
                  className={`px-4 h-11 rounded-lg text-sm font-medium border transition-colors touch-manipulation ${
                    dateFormat === fmt
                      ? "bg-amber-500 border-amber-500 text-black"
                      : "bg-gray-700 border-gray-600 text-gray-300 hover:bg-gray-600"
                  }`}
                >
                  {fmt}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* â”€â”€ SECTION 4: About â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className={sectionClass}>
        <h2 className={sectionTitleClass}>
          <ExternalLink size={18} className="text-amber-400" />
          About
        </h2>

        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-2xl">ðŸ’°</span>
            <div>
              <p className="text-white font-semibold text-base">ExpenseIQ v1.0.0</p>
              <p className="text-gray-400 text-sm">AI-powered personal expense tracker</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 pt-1">
            {["React 18", "FastAPI", "SQLite", "Claude AI"].map((tech) => (
              <span
                key={tech}
                className="px-3 py-1 bg-gray-700 border border-gray-600 rounded-full text-xs text-gray-300"
              >
                {tech}
              </span>
            ))}
          </div>

          <div className="pt-2">
            <a
              href="https://github.com/omarovski-27/expense_iq"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-amber-400 hover:text-amber-300 transition-colors"
            >
              <ExternalLink size={14} />
              View on GitHub
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

