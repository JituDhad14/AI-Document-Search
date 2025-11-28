// src/components/PostProcessPanel.tsx
import React, { useState } from "react";

type PostOpt = { key: string; label: string };

export function PostProcessPanel({
  filename,
  options,
  onResult,
}: {
  filename: string;
  options: PostOpt[];
  onResult: (payload: { text: string; sources: Array<[string, number | null]>; label: string }) => void;
}) {
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const apiBase = import.meta.env.VITE_API_URL || "/api";

  const handleClick = async (opt: PostOpt) => {
    if (!filename) return;
    setLoadingKey(opt.key);
    try {
      const res = await fetch(`${apiBase}/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, option: opt.key, k: 5 }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `Process failed (${res.status})`);
      }
      const data = await res.json();
      // data.result is the LLM output; data.sources is returned as array
      onResult({ text: data.result || data?.result?.text || "", sources: data.sources || [], label: data.label || opt.label });
    } catch (e: any) {
      console.error(e);
      onResult({ text: `Processing error: ${e.message || e}`, sources: [], label: opt.label });
    } finally {
      setLoadingKey(null);
    }
  };

  if (!options || options.length === 0) return null;

  return (
    <div className="mt-3">
      <div className="text-xs text-slate-400 mb-2">Post-upload actions</div>
      <div className="flex flex-col gap-2">
        {options.map((o) => (
          <button
            key={o.key}
            onClick={() => handleClick(o)}
            disabled={!!loadingKey}
            className="text-left px-3 py-2 rounded border border-slate-800 bg-slate-900 hover:bg-slate-880"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-slate-200">{o.label}</div>
                <div className="text-[11px] text-slate-500">Click to generate {o.label.toLowerCase()}.</div>
              </div>
              <div className="ml-4 text-xs text-slate-400">
                {loadingKey === o.key ? "Working…" : "Run"}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
