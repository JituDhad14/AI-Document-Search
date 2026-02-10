// src/pages/Home.tsx
import React from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";

// Local sample PDF path (from your machine)
const SAMPLE_PDF_URL = "file:///C:/Desktop/ai-pdf-chatbot/app/data/raw/Base-Paper-TS.pdf";

export const Home: React.FC = () => {
  const nav = useNavigate();
  const { user } = useAuth();

  const handleLetsGo = () => {
    if (user) {
      nav("/chat");
    } else {
      nav("/login");
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center py-12 px-6">
      <div className="max-w-3xl text-center">
        <h2 className="text-4xl font-extrabold text-emerald-300 mb-3">AI Document Search</h2>
        <p className="text-sm text-slate-400 mb-8">Search smarter · Work faster</p>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-left text-slate-200 leading-relaxed">
          <p className="text-lg">
            This AI Document Search helps you analyze and interpret documents faster — turning static files into an interactive knowledge source. It’s designed to speed up workflows across domains such as education, finance, legal research and healthcare.
          </p>
        </div>

        <div className="mt-6">
          <div className="inline-flex items-center gap-3 text-sm text-amber-400">
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none"><path d="M12 9v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/><path d="M12 17h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
            <div className="ticker font-medium">⚠️ AI Document Search can make mistakes — always verify before making decisions.</div>
          </div>
        </div>

        <div className="mt-8 flex flex-col items-center gap-4">
          <a className="text-sm text-emerald-300 underline" href={SAMPLE_PDF_URL} target="_blank" rel="noreferrer">
          </a>

          {/* LET'S GO BUTTON */}
          <button
            onClick={handleLetsGo}
            className="mt-2 inline-flex items-center gap-2 px-6 py-3 rounded-full bg-emerald-500 text-slate-900 font-semibold shadow-lg hover:brightness-105"
          >
            Let's go
            <span aria-hidden>🚀</span>
          </button>
        </div>
      </div>
    </div>
  );
};
