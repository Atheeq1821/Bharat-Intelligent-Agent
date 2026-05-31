"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export interface Message {
  role: "user" | "assistant";
  content: string;
  chart?: string;
  sql?: string;
  sources?: string[];
}

interface Props {
  messages: Message[];
  loading: boolean;
  onSend: (text: string) => void;
}

const SUGGESTIONS = [
  "Show latest codex events",
  "Count codex events by type for the last 7 days",
  "List recent claude events",
  "Show top 5 GitHub repositories by updated time",
];

function getExtFromSource(src: string): string {
  const dataMatch = src.match(/^data:image\/([a-zA-Z0-9+.-]+);base64,/);
  if (dataMatch?.[1]) return dataMatch[1].replace("jpeg", "jpg");
  const urlExt = src.split("?")[0].split(".").pop();
  if (urlExt && /^[a-zA-Z0-9]+$/.test(urlExt)) return urlExt.toLowerCase();
  return "png";
}

function normalizeMarkdown(content: string): string {
  const trimmed = content.trim();
  const fenced = trimmed.match(/^```(?:markdown|md)?\s*([\s\S]*?)\s*```$/i);
  return fenced ? fenced[1].trim() : content;
}

async function downloadImage(src: string, baseName = "bharat-intelligence-image"): Promise<void> {
  const ext = getExtFromSource(src);
  const filename = `${baseName}-${Date.now()}.${ext}`;

  if (src.startsWith("data:image/")) {
    const link = document.createElement("a");
    link.href = src;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    return;
  }

  const response = await fetch(src);
  if (!response.ok) throw new Error(`Failed to download image: ${response.status}`);
  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(blobUrl);
}

function downloadMarkdown(content: string, baseName = "bharat-intelligence-reply"): void {
  const text = normalizeMarkdown(content);
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = `${baseName}-${Date.now()}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(blobUrl);
}

function AssistantMarkdown({ content }: { content: string }) {
  const normalized = normalizeMarkdown(content);
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => <h1 className="text-base font-semibold mt-1 mb-2">{children}</h1>,
        h2: ({ children }) => <h2 className="text-sm font-semibold mt-3 mb-1.5">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-1">{children}</h3>,
        p: ({ children }) => <p className="whitespace-pre-wrap mb-2 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>,
        li: ({ children }) => <li>{children}</li>,
        table: ({ children }) => (
          <div className="overflow-x-auto mb-2">
            <table className="min-w-full text-xs border border-slate-700/60 rounded">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-slate-900/80">{children}</thead>,
        tbody: ({ children }) => <tbody>{children}</tbody>,
        tr: ({ children }) => <tr className="border-b border-slate-700/40">{children}</tr>,
        th: ({ children }) => <th className="text-left px-2 py-1.5 text-slate-200 font-semibold">{children}</th>,
        td: ({ children }) => <td className="px-2 py-1.5 text-slate-300 align-top">{children}</td>,
        code: ({ children }) => (
          <code className="bg-slate-900/80 text-slate-200 px-1 py-0.5 rounded text-xs">
            {children}
          </code>
        ),
        pre: ({ children }) => (
          <pre className="bg-slate-900/90 text-slate-200 p-2 rounded overflow-x-auto text-xs mb-2">
            {children}
          </pre>
        ),
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="text-indigo-300 underline hover:text-indigo-200"
          >
            {children}
          </a>
        ),
        img: ({ src, alt }) => {
          if (!src) return null;
          return (
            <div className="mt-3">
              <img src={src} alt={alt ?? "image"} className="rounded-lg w-full max-w-md border border-slate-700/50" />
              <button
                onClick={async () => {
                  try {
                    await downloadImage(src, "bharat-intelligence-md-image");
                  } catch (err) {
                    alert(err instanceof Error ? err.message : "Image download failed.");
                  }
                }}
                className="mt-2 text-xs bg-slate-700 hover:bg-slate-600 text-slate-100 rounded px-2 py-1"
              >
                Download Image
              </button>
            </div>
          );
        },
      }}
    >
      {normalized}
    </ReactMarkdown>
  );
}

export default function ChatWindow({ messages, loading, onSend }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    onSend(text);
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-160px)] bg-slate-900 rounded-xl border border-slate-700/50">
      <div className="px-4 py-3 border-b border-slate-700/50 flex items-center gap-3">
        <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse" />
        <span className="font-semibold text-slate-100 text-sm">Bharat Intelligence</span>
        <span className="ml-auto text-xs text-slate-500">Coral SQL - Live Connected Sources</span>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-6">
            <p className="text-slate-400 text-sm text-center max-w-xs">
              Ask anything across your connected Coral sources in plain English.
            </p>
            <div className="grid grid-cols-1 gap-2 w-full max-w-sm">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => onSend(s)}
                  className="text-left text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700/50 rounded-lg px-3 py-2 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`msg-enter flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-sm"
                  : "bg-slate-800 text-slate-100 rounded-bl-sm"
              }`}
            >
              {msg.role === "assistant" ? (
                <>
                  <AssistantMarkdown content={msg.content} />
                  <div className="mt-2 flex gap-2">
                    <button
                      onClick={() => downloadMarkdown(msg.content)}
                      className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-100 rounded px-2 py-1"
                    >
                      Download Reply (.md)
                    </button>
                  </div>
                </>
              ) : (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              )}

              {msg.chart && (
                <div className="mt-3">
                  <img src={msg.chart} alt="Chart" className="rounded-lg w-full max-w-md border border-slate-700/50" />
                  <button
                    onClick={async () => {
                      try {
                        await downloadImage(msg.chart as string, "bharat-intelligence-chart");
                      } catch (err) {
                        alert(err instanceof Error ? err.message : "Chart download failed.");
                      }
                    }}
                    className="mt-2 text-xs bg-indigo-700 hover:bg-indigo-600 text-white rounded px-2 py-1"
                  >
                    Download Chart
                  </button>
                </div>
              )}

              {msg.sql && (
                <details className="mt-2">
                  <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-300 select-none">
                    View SQL
                  </summary>
                  <pre className="mt-1.5 text-xs bg-slate-900/80 text-slate-300 p-2 rounded overflow-x-auto">
                    {msg.sql}
                  </pre>
                </details>
              )}

              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {msg.sources.map((s) => (
                    <span
                      key={s}
                      className="text-[10px] bg-indigo-900/50 text-indigo-300 border border-indigo-700/40 rounded px-1.5 py-0.5"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="msg-enter flex justify-start">
            <div className="bg-slate-800 rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-1.5">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="px-4 py-3 border-t border-slate-700/50">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask a business question..."
            rows={1}
            className="flex-1 resize-none bg-slate-800 border border-slate-600/50 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 max-h-32 overflow-y-auto"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="shrink-0 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
            aria-label="Send"
          >
            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
