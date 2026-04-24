import { useState, useEffect, useRef } from "react";
import { format, parseISO, getMonth, getYear } from "date-fns";
import {
  Sparkles, Brain, Lightbulb, X, Send, Loader2,
} from "lucide-react";
import toast from "react-hot-toast";

import { getInsights, generateInsights, chatWithAI, getSpikes, dismissInsight } from "../api/insights";
import { getMerchantBreakdown } from "../api/analytics";
import type { AIInsight, SpikeResult, MerchantBreakdown } from "../types";
import { formatCurrency } from "../utils/formatCurrency";
import { useCurrency } from "../context/CurrencyContext";

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Helpers
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const EXAMPLE_PROMPTS = [
  "How much did I spend on food last month?",
  "What's my biggest recurring expense?",
  "Am I on track with my budget?",
];

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Main page
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function Insights() {
  const now = new Date();
  const { currencySymbol } = useCurrency();
  const [currentMonth] = useState(getMonth(now) + 1);
  const [currentYear] = useState(getYear(now));

  const [report, setReport] = useState<AIInsight | null>(null);
  const [spikes, setSpikes] = useState<SpikeResult[]>([]);
  const [insights, setInsights] = useState<AIInsight[]>([]);
  const [merchants, setMerchants] = useState<MerchantBreakdown[]>([]);
  const [lastGenerated, setLastGenerated] = useState<string | null>(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [loading, setLoading] = useState(true);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // â”€â”€ Initial load â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  async function loadAll() {
    setLoading(true);
    try {
      const [allInsights, spikeData, merchantData] = await Promise.all([
        getInsights({ month: currentMonth, year: currentYear, limit: 50 }),
        getSpikes(currentMonth, currentYear),
        getMerchantBreakdown(currentMonth, currentYear),
      ]);

      setInsights(allInsights);
      setSpikes(spikeData);
      setMerchants(merchantData);

      const summaryInsight = allInsights.find((i) => i.type === "summary") ?? null;
      setReport(summaryInsight);

      if (summaryInsight) {
        setLastGenerated(summaryInsight.created_at);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, []);

  // Scroll chat to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // â”€â”€ Generate report â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  async function handleGenerate() {
    setIsGenerating(true);
    try {
      const saved = await generateInsights(currentMonth, currentYear);
      setInsights(saved);
      const summary = saved.find((i) => i.type === "summary") ?? null;
      setReport(summary);
      if (summary) setLastGenerated(summary.created_at);

      // Refresh spikes too (they're computed fresh)
      const spikeData = await getSpikes(currentMonth, currentYear);
      setSpikes(spikeData);

      toast.success("AI report generated!");
    } catch {
      toast.error("Failed to generate report");
    } finally {
      setIsGenerating(false);
    }
  }

  // â”€â”€ Dismiss spike â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  async function handleDismissSpike(insightId: number | undefined) {
    if (!insightId) return;
    await dismissInsight(insightId);
    setInsights((prev) => prev.filter((i) => i.id !== insightId));
    setSpikes((prev) => prev.filter((_, idx) => {
      // Remove the spike card whose matching insight was dismissed
      return idx !== prev.findIndex((s) => {
        const match = insights.find(
          (i) => i.type === "spike" && i.content === s.explanation
        );
        return match?.id === insightId;
      });
    }));
    toast.success("Insight dismissed");
  }

  // â”€â”€ Dismiss recommendation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  async function handleDismissInsight(id: number) {
    await dismissInsight(id);
    setInsights((prev) => prev.filter((i) => i.id !== id));
    toast.success("Insight dismissed");
  }

  // â”€â”€ Chat send â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  async function handleSend(question?: string) {
    const text = (question ?? chatInput).trim();
    if (!text) return;
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsChatLoading(true);
    try {
      const response = await chatWithAI(text);
      setChatMessages((prev) => [...prev, { role: "assistant", content: response }]);
    } catch {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I couldn't process that. Please try again." },
      ]);
    } finally {
      setIsChatLoading(false);
    }
  }

  // â”€â”€ Derived â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const recommendations = insights.filter((i) => i.type === "recommendation").slice(0, 3);


  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  // Render
  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  return (
    <div className="space-y-6 pb-10">

      {/* â”€â”€ SECTION 1: Top bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-white font-medium text-sm transition-colors disabled:opacity-60"
          >
            {isGenerating
              ? <Loader2 size={16} className="animate-spin" />
              : <Sparkles size={16} />}
            {isGenerating ? "Generatingâ€¦" : "Generate AI Report"}
          </button>
          {lastGenerated && (
            <span className="text-gray-500 text-sm">
              Last generated:{" "}
              <span className="text-gray-400">
                {format(parseISO(lastGenerated), "MMM d, yyyy 'at' h:mm a")}
              </span>
            </span>
          )}
        </div>
        <span className="text-gray-500 text-sm">
          {new Date(currentYear, currentMonth - 1).toLocaleString("default", { month: "long" })} {currentYear}
        </span>
      </div>

      {/* â”€â”€ SECTION 2: Monthly Narrative â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 border-l-4 border-l-indigo-500 p-6">
        <div className="flex items-center gap-2 mb-3">
          <Brain size={18} className="text-indigo-400" />
          <h2 className="text-white font-semibold">Monthly Summary</h2>
        </div>
        {loading ? (
          <div className="space-y-2">
            <div className="h-4 bg-gray-700 rounded animate-pulse w-full" />
            <div className="h-4 bg-gray-700 rounded animate-pulse w-5/6" />
            <div className="h-4 bg-gray-700 rounded animate-pulse w-4/6" />
          </div>
        ) : report ? (
          <p className="text-gray-300 leading-relaxed">{report.content}</p>
        ) : (
          <p className="text-gray-500 italic">
            Click "Generate AI Report" to analyze your finances for this month.
          </p>
        )}
      </div>

      {/* â”€â”€ SECTION 3: Spending Spikes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {spikes.length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">
            Spending Spikes
            <span className="ml-2 text-xs text-gray-500 font-normal">Categories above average</span>
          </h2>
          <div className="grid grid-cols-3 gap-4">
            {spikes.map((spike, idx) => (
              <div
                key={idx}
                className={`bg-gray-800 rounded-xl border border-gray-700 p-5 border-l-4 ${
                  spike.severity === "critical" ? "border-l-red-500" : "border-l-amber-500"
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <p className="text-white font-semibold text-sm">{spike.category}</p>
                    <span
                      className={`inline-block mt-1 text-xs px-2 py-0.5 rounded-full font-medium border ${
                        spike.severity === "critical"
                          ? "bg-red-500/15 text-red-400 border-red-500/30"
                          : "bg-amber-500/15 text-amber-400 border-amber-500/30"
                      }`}
                    >
                      â†‘ {spike.percentage_above.toFixed(0)}% above average
                    </span>
                  </div>
                  <button
                    onClick={() => handleDismissSpike(spike)}
                    className="text-gray-600 hover:text-gray-400 transition-colors ml-2 mt-0.5"
                    title="Dismiss"
                  >
                    <X size={14} />
                  </button>
                </div>
                <p className="text-gray-400 text-xs leading-relaxed mt-2">{spike.explanation}</p>
                <div className="mt-3 flex gap-3 text-xs text-gray-500">
                  <span>This month: <span className="text-white">{formatCurrency(spike.current_spend, currencySymbol)}</span></span>
                  <span>Avg: <span className="text-gray-400">{formatCurrency(spike.rolling_avg, currencySymbol)}</span></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* â”€â”€ SECTION 6: Top Merchants (placed after spikes, before recommendations) */}
      {merchants.length > 0 && (
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-700">
            <h2 className="text-white font-semibold">Top Merchants</h2>
            <p className="text-xs text-gray-500 mt-0.5">Where you spend the most this month</p>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase tracking-wide border-b border-gray-700">
                <th className="px-5 py-3 text-left w-12">Rank</th>
                <th className="px-5 py-3 text-left">Merchant</th>
                <th className="px-5 py-3 text-right">Total</th>
                <th className="px-5 py-3 text-right"># Transactions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/60">
              {merchants.slice(0, 10).map((m, idx) => (
                <tr key={m.merchant} className="text-gray-300 hover:bg-gray-700/30 transition-colors">
                  <td className="px-5 py-3 text-gray-500 font-mono">#{idx + 1}</td>
                  <td className="px-5 py-3 text-white font-medium">{m.merchant || "Unknown"}</td>
                  <td className="px-5 py-3 text-right text-amber-400 font-medium">{formatCurrency(m.amount, currencySymbol)}</td>
                  <td className="px-5 py-3 text-right text-gray-400">{m.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* â”€â”€ SECTION 4: Recommendations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      {recommendations.length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-3">Recommendations</h2>
          <div className="grid grid-cols-3 gap-4">
            {recommendations.map((ins) => {
              // Try to parse estimated_savings from content (e.g. "save $50")
              const savingsMatch = ins.content.match(/\$(\d[\d,.]*)/);
              const estimatedSavings = savingsMatch ? parseFloat(savingsMatch[1].replace(/,/g, "")) : null;

              return (
                <div
                  key={ins.id}
                  className="bg-gray-800 rounded-xl border border-gray-700 border-l-4 border-l-green-500 p-5"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Lightbulb size={16} className="text-green-400 shrink-0" />
                      <p className="text-white font-semibold text-sm">{ins.title}</p>
                    </div>
                    <button
                      onClick={() => handleDismissInsight(ins.id)}
                      className="text-gray-600 hover:text-gray-400 transition-colors ml-2"
                      title="Dismiss"
                    >
                      <X size={14} />
                    </button>
                  </div>
                  <p className="text-gray-400 text-xs leading-relaxed">{ins.content}</p>
                  {estimatedSavings !== null && !isNaN(estimatedSavings) && (
                    <div className="mt-3">
                      <span className="text-xs px-2 py-1 rounded-full bg-green-500/15 text-green-400 border border-green-500/30 font-medium">
                        ðŸ’° Save up to {formatCurrency(estimatedSavings, currencySymbol)}/month
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* â”€â”€ SECTION 5: AI Chat â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-700 flex items-center gap-2">
          <Sparkles size={16} className="text-amber-400" />
          <h2 className="text-white font-semibold">Ask AI About Your Finances</h2>
        </div>

        {/* Message area */}
        <div className="h-80 overflow-y-auto px-5 py-4 space-y-4">
          {chatMessages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center gap-4">
              <p className="text-gray-500 text-sm">Ask anything about your spending</p>
              <div className="flex flex-wrap gap-2 justify-center">
                {EXAMPLE_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleSend(prompt)}
                    className="text-xs px-3 py-1.5 rounded-full bg-gray-700 hover:bg-gray-600 text-gray-300 border border-gray-600 transition-colors"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {chatMessages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-amber-500 text-white rounded-br-sm"
                        : "bg-gray-700 text-gray-200 rounded-bl-sm"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              {isChatLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-700 px-4 py-2.5 rounded-2xl rounded-bl-sm">
                    <div className="flex gap-1 items-center h-4">
                      <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </>
          )}
        </div>

        {/* Input bar */}
        <div className="px-5 py-4 border-t border-gray-700 flex gap-3">
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="Ask about your spendingâ€¦"
            disabled={isChatLoading}
            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-amber-500 disabled:opacity-50"
          />
          <button
            onClick={() => handleSend()}
            disabled={isChatLoading || !chatInput.trim()}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-white text-sm font-medium transition-colors disabled:opacity-50"
          >
            {isChatLoading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

