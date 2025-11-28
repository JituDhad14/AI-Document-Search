// src/App.tsx
import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./auth/AuthProvider";
import { NavBar } from "./components/NavBar";
import { Footer } from "./components/Footer";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Contact } from "./pages/Contact";
import { Profile } from "./pages/Profile"; // make sure this file exists
import { UploadPanel } from "./components/UploadPanel";
import { ChatPanel } from "./components/ChatPanel";
import type { DocumentMeta } from "./api/client";
import { listDocuments } from "./api/client";

/* Inline ChatLayout uses your existing UploadPanel + ChatPanel */
const ChatLayout: React.FC = () => {
  const [docs, setDocs] = React.useState<DocumentMeta[]>([]);
  const [selectedDocIds, setSelectedDocIds] = React.useState<string[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = React.useState(false);

    const refreshDocs = async () => {
    try {
      setIsLoadingDocs(true);

      // listDocuments may return either an array OR an object { documents: [...] }
      const data = await listDocuments();

      // Defensive handling: handle both shapes
      let docsArray: DocumentMeta[] = [];
      if (Array.isArray(data)) {
        docsArray = data;
      } else if (data && Array.isArray((data as any).documents)) {
        docsArray = (data as any).documents;
      } else {
        // If server returned a wrapped object like { documents: [...] } under some other key,
        // try to find the first array-like field:
        const maybeArray = Object.values(data || {}).find((v) => Array.isArray(v));
        if (maybeArray) docsArray = maybeArray as DocumentMeta[];
      }

      setDocs(docsArray);

      // choose a sensible default selection if none selected
      if (docsArray.length > 0 && selectedDocIds.length === 0) setSelectedDocIds([docsArray[0].id]);
    } catch (err) {
      // Log the error so we can see what's failing
      console.error("refreshDocs failed:", err);
      // Optionally show non-blocking UI message: you can integrate a toast here
      // For now we keep existing UI but you can uncomment an alert for debugging:
      // alert('Failed to refresh documents. See console for details.');
    } finally {
      setIsLoadingDocs(false);
    }
  };


  const toggleDocSelection = (id: string) => {
    setSelectedDocIds((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]));
  };

  // ----- NEW: delete handler passed to ChatPanel -----
  const handleDeleteDocument = async (docId: string) => {
    const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

    // Optional client-side confirmation (ChatPanel already confirms too)
    if (!window.confirm(`Delete document "${docId}"? This cannot be undone.`)) return;

    try {
      const res = await fetch(`${API}/api/documents/${encodeURIComponent(docId)}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        let errText = `${res.status}`;
        try {
          const j = await res.json();
          errText = j.detail || JSON.stringify(j);
        } catch {
          errText = await res.text().catch(() => errText);
        }
        throw new Error(errText);
      }

      // Remove locally and update selection
      setDocs((prev) => prev.filter((d) => d.id !== docId));
      setSelectedDocIds((prev) => prev.filter((id) => id !== docId));

      // Optionally re-fetch to be fully synced:
      // await refreshDocs();
    } catch (e: any) {
      console.error("Delete failed", e);
      alert(`Delete failed: ${e?.message || e}`);
    }
  };
  // --------------------------------------------------

  return (
    <div className="h-screen flex flex-col">
      <header className="border-b border-slate-800 px-4 py-2 flex items-center justify-between bg-slate-950/80 backdrop-blur">
        <div>
          <h1 className="text-lg font-semibold">AI Document Search & Chat</h1>
          <p className="text-xs text-slate-400">RAG over your PDFs • FastAPI + FAISS + Gemini</p>
        </div>
        <span className="text-xs text-slate-500">API: {import.meta.env.VITE_API_URL || "http://localhost:8000/api"}</span>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-80 border-r border-slate-800 bg-slate-950/60 p-4 flex flex-col gap-4">
          {/* UploadPanel uses onUploadSuccess to call refreshDocs */}
          <UploadPanel onUploadSuccess={refreshDocs} />

          <div className="flex-1 overflow-y-auto">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold">Documents</h2>
              {isLoadingDocs && <span className="text-[10px] text-slate-500">Refreshing…</span>}
            </div>

            {docs.length === 0 ? (
              <p className="text-xs text-slate-500">No documents yet. Upload PDFs to start chatting.</p>
            ) : (
              <ul className="space-y-1 text-xs">
                {docs.map((d) => {
                  const selected = selectedDocIds.includes(d.id);
                  return (
                    <li
                      key={d.id}
                      onClick={() => toggleDocSelection(d.id)}
                      className={`flex items-center justify-between rounded-md border px-2 py-1 cursor-pointer ${
                        selected ? "border-emerald-500 bg-emerald-500/10" : "border-slate-800 hover:border-slate-600"
                      }`}
                    >
                      <div className="flex flex-col">
                        <span className="truncate max-w-[180px]">{d.name}</span>
                        {typeof d.chunks === "number" && <span className="text-[10px] text-slate-500">{d.chunks} chunks</span>}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </aside>

        <main className="flex-1 bg-slate-950 flex">
          {/* Pass documents + onDeleteDocument to ChatPanel (keeps existing props) */}
          <ChatPanel
            selectedDocIds={selectedDocIds}
            documents={docs.map((d) => ({ id: d.id, name: d.name, file_url: d.file_url }))}
            onDeleteDocument={handleDeleteDocument}
          />
        </main>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen flex flex-col bg-slate-950 text-slate-50">
          <NavBar />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/chat" element={<ChatLayout />} />
              <Route path="/contact" element={<Contact />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/profile" element={<Profile />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;