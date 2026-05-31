"use client";

interface HistoryEntry {
  id: number;
  session_id: string;
  user_message: string;
  sql_generated: string | null;
  result_summary: string | null;
  sources_used: string[];
  created_at: string;
}

interface Props {
  history: HistoryEntry[];
  onRefresh?: () => void;
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

const SOURCE_COLORS: Record<string, string> = {
  codex: "bg-cyan-900/50 text-cyan-300 border-cyan-700/40",
  claude: "bg-amber-900/50 text-amber-300 border-amber-700/40",
  github: "bg-zinc-900/50 text-zinc-300 border-zinc-700/40",
  intercom: "bg-orange-900/50 text-orange-300 border-orange-700/40",
  zoho_books: "bg-emerald-900/50 text-emerald-300 border-emerald-700/40",
  postgresql: "bg-blue-900/50 text-blue-300 border-blue-700/40",
  postgres: "bg-blue-900/50 text-blue-300 border-blue-700/40",
  slack: "bg-purple-900/50 text-purple-300 border-purple-700/40",
};

export default function QueryHistory({ history, onRefresh }: Props) {
  return (
    <div className="flex flex-col h-[calc(100vh-160px)] bg-slate-900 rounded-xl border border-slate-700/50">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between">
        <span className="font-semibold text-slate-100 text-sm">Query History</span>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            Refresh
          </button>
        )}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-800">
        {history.length === 0 && (
          <p className="text-slate-500 text-xs text-center py-10">
            No queries yet. Ask something!
          </p>
        )}

        {history.map((entry) => (
          <div key={entry.id} className="px-4 py-3 hover:bg-slate-800/50 transition-colors group">
            {/* Question */}
            <p className="text-slate-100 text-xs font-medium leading-snug line-clamp-2">
              {entry.user_message}
            </p>

            {/* Summary */}
            {entry.result_summary && (
              <p className="mt-1 text-slate-400 text-xs line-clamp-2 leading-relaxed">
                {entry.result_summary}
              </p>
            )}

            {/* SQL (expandable) */}
            {entry.sql_generated && (
              <details className="mt-1.5">
                <summary className="text-[10px] text-slate-500 cursor-pointer hover:text-slate-400 select-none">
                  SQL
                </summary>
                <pre className="mt-1 text-[10px] bg-slate-950 text-slate-400 p-2 rounded overflow-x-auto leading-relaxed">
                  {entry.sql_generated}
                </pre>
              </details>
            )}

            {/* Footer */}
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              {(entry.sources_used ?? []).map((s) => (
                <span
                  key={s}
                  className={`text-[10px] border rounded px-1.5 py-0.5 ${SOURCE_COLORS[s] ?? "bg-slate-800 text-slate-400 border-slate-700"}`}
                >
                  {s}
                </span>
              ))}
              <span className="ml-auto text-[10px] text-slate-600">
                {relativeTime(entry.created_at)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
