// src/components/UploadPanel.tsx
import React, { useState } from "react";

type PostOpt = { key: string; label: string };

export function UploadPanel({
  onUploadSuccess,
}: {
  onUploadSuccess?: (payload: { documents: string[]; postprocessOptions: PostOpt[] }) => void;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const handleFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    setMsg(null);

    const selected = Array.from(e.target.files ?? []);

    if (selected.length > 2) {
      setMsg("Maximum 2 files allowed.");
      return;
    }

    setFiles(selected);
  };

  const upload = async () => {
    if (files.length === 0) {
      setMsg("Choose up to 2 PDF files first.");
      return;
    }

    setLoading(true);
    setMsg(null);

    try {
      const fd = new FormData();

      for (const f of files) {
        fd.append("files", f, f.name);
      }

      const res = await fetch(`${API_URL}/api/upload`, {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
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

      setMsg(`Uploaded: ${data.documents.join(", ")}`);

      const options =
        data.postprocess_options?.map((o: any) => ({
          key: o.key,
          label: o.label,
        })) ?? [];

      onUploadSuccess?.({
        documents: data.documents,
        postprocessOptions: options,
      });

      setFiles([]); // reset UI after upload
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
        <div className="text-sm font-semibold mb-2">Upload PDFs (max 2)</div>

        <input
          type="file"
          accept="application/pdf"
          multiple
          onChange={handleFiles}
        />

        {files.length > 0 && (
          <div className="mt-2 text-xs text-slate-400">
            Selected: {files.map((f) => f.name).join(", ")}
          </div>
        )}

        <div className="mt-3 flex gap-2">
          <button
            onClick={upload}
            disabled={loading}
            className="px-3 py-1 rounded bg-emerald-500 text-slate-900 text-sm"
          >
            {loading ? "Uploading…" : "Upload & Index"}
          </button>

          <button
            onClick={() => {
              setFiles([]);
              setMsg(null);
            }}
            className="px-3 py-1 rounded bg-slate-700 text-slate-200 text-sm"
          >
            Clear
          </button>
        </div>

        {msg && <div className="mt-2 text-xs text-slate-400">{msg}</div>}

        <div className="mt-2 text-[11px] text-slate-500">
          Files are sent to FastAPI, chunked, embedded, and stored in FAISS.
        </div>
      </div>
    </div>
  );
}
