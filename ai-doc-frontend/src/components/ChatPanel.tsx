// src/components/ChatPanel.tsx
import React, { useState,useEffect } from "react";
import { chatWithDocs } from "../api/client";
import type { ChatResponse } from "../api/client";

interface ChatPanelProps {
  selectedDocIds: string[];
}

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: string[];
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ selectedDocIds }) => {
  const [messages, setMessages] = useState<Message[]>(() => {
  const saved = sessionStorage.getItem("chat_messages");
  return saved ? JSON.parse(saved) : [];
});
 

  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
   useEffect(() => {
  sessionStorage.setItem("chat_messages", JSON.stringify(messages));
}, [messages]);


  const handleSend = async () => {
    const query = input.trim();
    if (!query) return;
    if (selectedDocIds.length === 0) {
      alert("Upload at least one document before querying.");
      return;
    }

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: query,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsSending(true);

    try {
      const thinkingId = crypto.randomUUID();

      setMessages((prev) => [
        ...prev,
        { id: thinkingId, role: "system", content: "AI Document Search is thinking..." },
      ]);

      const selectedDoc = selectedDocIds.length === 1 ? selectedDocIds[0] : null;

      const res: ChatResponse = await chatWithDocs({
        query,
        k: 5,
        document: selectedDoc,
      });

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

      setMessages((prev) => prev.filter((m) => m.role !== "system"));

      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Backend error. Check server logs.",
      };

      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isSending) handleSend();
    }
  };

  return (
    <div className="flex flex-col flex-1 h-full">

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 text-sm text-center px-8">
            Ask a question about your uploaded PDFs.
          </div>
        ) : (
          messages.map((m) => {
            if (m.role === "system") {
              return (
                <div key={m.id} className="max-w-2xl ml-auto text-right">
                  <div className="inline-flex items-center gap-3 rounded-2xl px-4 py-2 text-sm bg-slate-800 border border-slate-700">
                    {m.content}
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
                  className={`inline-block rounded-2xl px-4 py-3 text-sm break-words ${
                    isUser
                      ? "bg-emerald-500 text-slate-950"
                      : "bg-slate-900 border border-slate-700"
                  }`}
                >
                  {m.content}
                </div>

                {m.role === "assistant" && m.sources && (
                  <div className="mt-2 text-xs text-slate-400">
                    Sources: {m.sources.join(", ")}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Input */}
<div className="border-t border-slate-800 p-4">
  <textarea
    rows={2}
    value={input}
    onChange={(e) => setInput(e.target.value)}
    onKeyDown={handleKeyDown}
    placeholder="Ask anything about the indexed documents..."
    className="w-full resize-none rounded-xl border border-emerald-500/50 bg-slate-950 px-4 py-3 text-sm"
  />

  <div className="mt-2 flex items-center justify-between">
    <button
  onClick={() => {
    setMessages([]);
    sessionStorage.removeItem("chat_messages");
  }}
  className="px-3 py-1 rounded-md bg-red-600 hover:bg-red-700 text-white text-xs font-medium"
>
  Clear chat
</button>


    <button
      disabled={isSending || !input.trim()}
      onClick={handleSend}
      className="px-4 py-2 rounded-full bg-emerald-500 text-slate-950 font-medium disabled:opacity-50"
    >
      {isSending ? "Thinking…" : "Send"}
    </button>
  </div>
</div>
</div>
);
};

