// src/components/UploadPanel.tsx
import React, { useState } from "react";

type PostOpt = { key: string; label: string };

export function UploadPanel({
  onUploadSuccess,
}: {
  onUploadSuccess?: (payload: { filename: string; postprocessOptions: PostOpt[] }) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  // explicit API URL (Vite exposes env vars that start with VITE_)
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    setMsg(null);
    const f = e.target.files?.[0] ?? null;
    setFile(f);
  };

  const upload = async () => {
    if (!file) {
      setMsg("Choose a PDF file first.");
      return;
    }
    setLoading(true);
    setMsg(null);

    try {
      const fd = new FormData();
      fd.append("file", file, file.name);

      const res = await fetch(`${API_URL}/api/upload`, {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
        // robust error parsing (handles JSON or plain text)
        let errText = `${res.status}`;
        try {
          const errJson = await res.json();
          errText = errJson?.detail || JSON.stringify(errJson);
        } catch {
          errText = await res.text().catch(() => errText);
        }
        throw new Error(`Upload failed (${errText})`);
      }

      const data = await res.json();
      // data expected: { filename, postprocess_options: [{key,label}], file_url, chunks_added }
      setMsg(`Uploaded ${data.filename} • ${data.chunks_added} chunks.`);
      const options = data.postprocess_options?.map((o: any) => ({ key: o.key, label: o.label })) ?? [];

      onUploadSuccess?.({ filename: data.filename, postprocessOptions: options });
    } catch (e: any) {
      console.error(e);
      setMsg(`Upload error: ${e.message || e}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="rounded-md p-3 border border-slate-800 bg-slate-900">
        <div className="text-sm font-semibold mb-2">Upload PDFs</div>
        <input type="file" accept="application/pdf" onChange={handleFile} />
        <div className="mt-3 flex gap-2">
          <button
            onClick={upload}
            disabled={loading}
            className="px-3 py-1 rounded bg-emerald-500 text-slate-900 text-sm"
          >
            {loading ? "Uploading…" : "Upload & Index"}
          </button>
          <button
            onClick={() => { setFile(null); setMsg(null); }}
            className="px-3 py-1 rounded bg-slate-700 text-slate-200 text-sm"
          >
            Clear
          </button>
        </div>
        {msg && <div className="mt-2 text-xs text-slate-400">{msg}</div>}
        <div className="mt-2 text-[11px] text-slate-500">Files are sent to FastAPI, chunked, embedded, and stored in FAISS.</div>
      </div>
    </div>
  );
}
