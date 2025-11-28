// src/components/ChatPanel.tsx
import React, { useState, useEffect } from "react";
import { chatWithDocs } from "../api/client";
import type { ChatResponse } from "../api/client";

interface ChatPanelProps {
  selectedDocIds: string[];
  // Parent can register a function so it can append assistant messages into the chat
  registerAppend?: (fn: (text: string, sources?: any[], label?: string) => void) => void;

  /**
   * NEW (optional):
   * documents: list of uploaded documents to display in the left mini-list
   * Each doc should have at least { id: string, name: string, file_url?: string }
   */
  documents?: { id: string; name: string; file_url?: string }[];

  /**
   * NEW (optional):
   * onDeleteDocument: parent-provided callback to actually delete the document.
   * Signature: (docId: string) => Promise<void> | void
   *
   * If not provided, ChatPanel will try a default DELETE to:
   *   `${API_URL}/api/documents/${docId}`
   * (You can change that default backend path later.)
   */
  onDeleteDocument?: (docId: string) => Promise<void> | void;
}

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: string[];
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  selectedDocIds,
  documents = [],
  onDeleteDocument,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [isSending, setIsSending] = useState(false);

  // NEW: UI state for document hover & deletion
  const [hoveredDocId, setHoveredDocId] = useState<string | null>(null);
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const handleSend = async () => {
    const query = input.trim();
    if (!query) return;
    if (selectedDocIds.length === 0) {
      alert("Upload at least one document before querying.");
      return;
    }

    // Push user message immediately
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: query,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsThinking(true);
    setIsSending(true);

    try {
      // show "thinking" system bubble (visual only)
      const thinkingId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        { id: thinkingId, role: "system", content: "Cognitive Assistant is thinking..." },
      ]);

      const res: ChatResponse = await chatWithDocs({ query, k: 5 });

      // remove the thinking system bubble
      setMessages((prev) => prev.filter((m) => m.id !== thinkingId));

      const botMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: res.answer,
        sources: res.sources,
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      console.error(err);
      // remove any thinking bubble
      setMessages((prev) => prev.filter((m) => m.role !== "system"));

      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "I couldn’t get a response from the backend. Check FastAPI logs or API URL.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsThinking(false);
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isSending) handleSend();
    }
  };

  // --- Document deletion flow ---
  const confirmAndDelete = async (docId: string) => {
    const doc = documents.find((d) => d.id === docId);
    const prettyName = doc?.name ?? docId;
    const ok = window.confirm(`Delete document "${prettyName}"? This action cannot be undone.`);
    if (!ok) return;

    try {
      setDeletingDocId(docId);
      if (onDeleteDocument) {
        // parent will handle deletion (preferred)
        await onDeleteDocument(docId);
      } else {
        // fallback: attempt a default DELETE route on the backend
        const res = await fetch(`${API_URL}/api/documents/${encodeURIComponent(docId)}`, {
          method: "DELETE",
        });
        if (!res.ok) {
          let errText = `${res.status}`;
          try {
            const body = await res.json();
            errText = body?.detail || JSON.stringify(body);
          } catch {
            errText = await res.text().catch(() => errText);
          }
          throw new Error(errText);
        }
      }

      // Inform user and let parent update docs/selection (parent should re-fetch docs)
      // We'll also push a small system message to the chat to notify deletion
      const sysMsg: Message = {
        id: crypto.randomUUID(),
        role: "system",
        content: `Document "${prettyName}" deleted.`,
      };
      setMessages((prev) => [...prev, sysMsg]);

      // cleanup hover / deleting states after success
      setHoveredDocId(null);
      setDeletingDocId(null);
    } catch (e: any) {
      console.error("Delete failed", e);
      alert(`Delete failed: ${e?.message || e}`);
      setDeletingDocId(null);
    }
  };

  return (
    <div className="flex flex-col flex-1 h-full">
      {/* Top horizontal area: small document list (left) + messages */}
      <div className="flex gap-4 p-4">
        {/* Documents column (small, unobtrusive) */}
        <div className="w-60 max-h-48 overflow-y-auto">
          <div className="text-xs text-slate-400 mb-2">Uploaded documents</div>
          <div className="space-y-2">
            {documents.length === 0 ? (
              <div className="text-[12px] text-slate-500">No documents uploaded yet</div>
            ) : (
              documents.map((doc) => {
                const isHovered = hoveredDocId === doc.id;
                const isDeleting = deletingDocId === doc.id;
                // show whether this doc is currently selected
                const isSelected = selectedDocIds.includes(doc.id);
                return (
                  <div
                    key={doc.id}
                    onMouseEnter={() => setHoveredDocId(doc.id)}
                    onMouseLeave={() => setHoveredDocId((id) => (id === doc.id ? null : id))}
                    className={`rounded-md p-2 border ${isSelected ? "border-emerald-500 bg-emerald-900/20" : "border-slate-800 bg-slate-900"}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="text-sm truncate" title={doc.name}>
                        {doc.name}
                      </div>
                      <div className="text-xs text-slate-400 ml-2">
                        {isSelected ? "Selected" : ""}
                      </div>
                    </div>

                    {/* Hover area: delete button & hint */}
                    {isHovered && (
                      <div className="mt-2 flex items-center justify-between text-[12px]">
                        <div className="text-slate-400">Actions</div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => confirmAndDelete(doc.id)}
                            disabled={isDeleting}
                            className="px-2 py-1 rounded text-xs bg-red-600 hover:bg-red-700 disabled:opacity-50"
                          >
                            {isDeleting ? "Deleting…" : "Delete document"}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Messages panel (rest remains unchanged) */}
        <div className="flex-1 h-[60vh] overflow-y-auto p-6 space-y-4 bg-transparent">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center text-slate-500 text-sm text-center px-8">
              Ask a question about your uploaded PDFs. Cognitive Assistant will run RAG and answer with citations.
            </div>
          ) : (
            messages.map((m) => {
              // system (thinking) bubble
              if (m.role === "system") {
                return (
                  <div key={m.id} className="max-w-2xl ml-auto text-right">
                    <div className="inline-flex items-center gap-3 rounded-2xl px-4 py-2 text-sm bg-slate-800 border border-slate-700">
                      <span className="text-slate-300">{m.content}</span>
                      {/* animated dots (if thinking) */}
                      {m.content.toLowerCase().includes("thinking") && (
                        <span className="ml-2 inline-flex items-center">
                          <span className="dot" />
                          <span className="dot delay-1" />
                          <span className="dot delay-2" />
                        </span>
                      )}
                    </div>
                  </div>
                );
              }

              const isUser = m.role === "user";
              return (
                <div
                  key={m.id}
                  className={`max-w-3xl ${isUser ? "ml-auto text-right" : "mr-auto text-left"}`}
                >
                  <div
                    className={`inline-block rounded-2xl px-4 py-3 text-sm leading-relaxed break-words ${
                      isUser ? "bg-emerald-500 text-slate-950" : "bg-slate-900 border border-slate-700"
                    }`}
                  >
                    {m.content}
                  </div>

                  {/* metadata pill: "You asked 👤" or "Cognitive Assistant replied 🤖" */}
                  <div
                    className={`mt-2 inline-flex items-center text-[12px] px-2 py-0.5 rounded-md ${
                      isUser ? "ml-auto bg-slate-800 text-slate-300" : "mr-auto bg-slate-800 text-slate-300"
                    }`}
                    style={{ gap: 8 }}
                  >
                    {isUser ? (
                      <>
                        <span className="font-medium">You asked</span>
                        <span aria-hidden>👤</span>
                      </>
                    ) : (
                      <>
                        <span aria-hidden>🤖</span>
                        <span className="font-medium">Cognitive Assistant replied</span>
                      </>
                    )}
                  </div>

                  {/* sources (if assistant) */}
                  {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                    <div className="mt-2 text-[12px] text-slate-400">
                      Sources:{" "}
                      {m.sources.map((s, i) => {
                        const fileUrl = `file:///C:/Desktop/ai-pdf-chatbot/app/data/raw/${s}`;
                        return (
                          <span key={s}>
                            <a
                              className="underline hover:text-emerald-400"
                              href={fileUrl}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {s}
                            </a>
                            {i < m.sources!.length - 1 ? ", " : ""}
                          </span>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Input area (unchanged) */}
      <div className="border-t border-slate-800 p-4">
        <div className="max-w-3xl mx-auto flex flex-col gap-2">
          <textarea
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about the indexed documents..."
            className="w-full resize-none rounded-xl border border-emerald-500/50 bg-slate-950 px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500">Enter to send • Shift+Enter for newline</span>
            <button
              disabled={isSending || !input.trim()}
              onClick={handleSend}
              className="px-4 py-2 rounded-full bg-emerald-500 text-slate-950 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSending ? "Thinking…" : "Send"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
