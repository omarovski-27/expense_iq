export interface Category {
  id: number;
  name: string;
  color: string;
  icon: string;
  created_at: string;
}

export interface Expense {
  id: number;
  amount: number;
  description: string;
  category_id: number;
  category?: Category;
  merchant?: string;
  date: string;
  is_recurring: boolean;
  recurring_id?: number;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface Budget {
  id: number;
  category_id: number;
  monthly_limit: number;
  month: number;
  year: number;
}

export interface BudgetStatus {
  category: Category;
  monthly_limit: number;
  spent: number;
  percentage: number;
  remaining: number;
  projected_month_end: number;
  status: "on_track" | "warning" | "over_budget";
}

export interface RecurringRule {
  id: number;
  name: string;
  amount: number;
  category_id: number;
  category?: Category;
  frequency: "daily" | "weekly" | "monthly" | "yearly";
  next_due_date: string;
  last_run_date?: string;
  is_active: boolean;
}

export interface AIInsight {
  id: number;
  type: "outlier" | "spike" | "summary" | "recommendation";
  title: string;
  content: string;
  severity: "info" | "warning" | "critical";
  month?: number;
  year?: number;
  is_dismissed: boolean;
  created_at: string;
}

export interface AnalyticsSummary {
  total_this_month: number;
  mom_change_percent: number;
  budget_used_percent: number;
  daily_average: number;
  top_category: { name: string; icon: string; amount: number } | null;
}

export interface SpendingTrend {
  month: number;
  year: number;
  total: number;
  label: string;
}

export interface CategoryBreakdown {
  category: Category;
  amount: number;
  percentage: number;
}

export interface SpikeResult {
  category: string;
  current_spend: number;
  rolling_avg: number;
  percentage_above: number;
  severity: "warning" | "critical";
  explanation: string;
}

export interface MerchantBreakdown {
  merchant: string;
  amount: number;
  count: number;
}
