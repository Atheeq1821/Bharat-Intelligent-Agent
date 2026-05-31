"use client";

import { useCallback, useEffect, useState } from "react";
import ChatWindow, { type Message } from "@/components/ChatWindow";
import QueryHistory from "@/components/QueryHistory";

interface HistoryEntry {
  id: number;
  session_id: string;
  user_message: string;
  sql_generated: string | null;
  result_summary: string | null;
  sources_used: string[];
  created_at: string;
}

interface SourceHealth {
  status: "ok" | "warning" | "error" | string;
  checked_at: string;
  error: string | null;
  source_count: number;
  table_count: number;
  sources: Array<{
    source: string;
    table_count: number;
    status: string;
  }>;
}

function prettySourceName(source: string): string {
  return source
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [sourceHealth, setSourceHealth] = useState<SourceHealth | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch("/api/history");
      const data = await res.json();
      setHistory(data.history ?? []);
    } catch {
      // history is non-critical; ignore fetch errors
    }
  }, []);

  const fetchSourceHealth = useCallback(async () => {
    try {
      const res = await fetch("/api/source-health");
      const data = (await res.json()) as SourceHealth;
      setSourceHealth(data);
    } catch {
      // source health is non-critical; ignore fetch errors
    }
  }, []);

  useEffect(() => {
    fetchHistory();
    fetchSourceHealth();
    // Poll every 10 seconds so other sessions (WhatsApp) show up too
    const id = setInterval(fetchHistory, 10_000);
    const sourceId = setInterval(fetchSourceHealth, 30_000);
    return () => {
      clearInterval(id);
      clearInterval(sourceId);
    };
  }, [fetchHistory, fetchSourceHealth]);

  const sendMessage = async (text: string) => {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: "web" }),
      });

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response ?? "No response received.",
          chart: data.chart ?? undefined,
          sql: data.sql ?? undefined,
          sources: data.sources_used ?? [],
        },
      ]);
      await fetchHistory();
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Is the backend running?" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950">
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="mb-6 flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-lg">
            BI
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-100 leading-none">
              Bharat Intelligence Agent
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Ask business questions across connected Coral sources
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-slate-500 hidden sm:inline">Live Sources</span>
            {(sourceHealth?.sources ?? []).map((s) => (
              <span
                key={s.source}
                className="text-[10px] bg-slate-800 border border-slate-700/50 text-slate-300 rounded px-2 py-0.5"
                title={`${s.table_count} tables`}
              >
                {prettySourceName(s.source)}
              </span>
            ))}
            {!sourceHealth?.sources?.length && (
              <span className="text-[10px] bg-slate-800 border border-slate-700/50 text-slate-500 rounded px-2 py-0.5">
                No Sources
              </span>
            )}
          </div>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <ChatWindow messages={messages} loading={loading} onSend={sendMessage} />
          </div>
          <div>
            <QueryHistory history={history} onRefresh={fetchHistory} />
          </div>
        </div>
      </div>
    </main>
  );
}
