// src/pages/Contact.tsx
import React, { useState } from "react";

export const Contact: React.FC = () => {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("General");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const FAQ = [
    {
      q: "How does the AI Document Search work?",
      a: "It uses Retrieval-Augmented Generation (RAG): document chunks are embedded, stored in FAISS, retrieved based on similarity, and passed into an LLM to generate responses."
    },
    {
      q: "Is my data stored or shared?",
      a: "Uploaded PDFs remain on your device during this prototype. In production, secure encrypted storage should be used."
    },
    {
      q: "Can I upload multiple PDFs?",
      a: "Yes — the system supports many PDFs and treats them all as a combined knowledge base."
    },
    {
      q: "Can the assistant make mistakes?",
      a: "Yes. Always verify important information before making decisions."
    }
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setNotice(null);

    // Validation
    if (!name || !email || !message) {
      setNotice({ type: "err", text: "Please fill name, email and message." });
      return;
    }

    if (!/\S+@\S+\.\S+/.test(email)) {
      setNotice({ type: "err", text: "Please enter a valid email." });
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, subject, message }),
      });

      if (!res.ok) throw new Error("Failed to submit feedback");

      setNotice({
        type: "ok",
        text: "Your message has been submitted. Thank you!",
      });

      // Reset form
      setName("");
      setEmail("");
      setSubject("General");
      setMessage("");

    } catch (err) {
      console.error(err);
      setNotice({
        type: "err",
        text: "Something went wrong. Please try again later.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 p-8">
      <div className="max-w-4xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8">

        {/* LEFT — CONTACT FORM */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <h2 className="text-2xl font-bold text-emerald-300 mb-2">
            Facing issues or need help?
          </h2>
          <p className="text-slate-300 mb-4">
            Feel free to contact us — we value your feedback.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">

            <div>
              <label className="text-sm text-slate-400 block mb-1">Your name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Full name"
                className="w-full rounded-md bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100"
              />
            </div>

            <div>
              <label className="text-sm text-slate-400 block mb-1">Your email</label>
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full rounded-md bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100"
              />
            </div>

            <div>
              <label className="text-sm text-slate-400 block mb-1">Subject</label>
              <select
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full rounded-md bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100"
              >
                <option>General</option>
                <option>Bug Report</option>
                <option>Feature Request</option>
                <option>Other</option>
              </select>
            </div>

            <div>
              <label className="text-sm text-slate-400 block mb-1">Message</label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={6}
                placeholder="Write your message here..."
                className="w-full rounded-md bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100 resize-y"
              />
            </div>

            {notice && (
              <div
                className={`py-2 px-3 rounded ${
                  notice.type === "ok"
                    ? "bg-emerald-900/50 text-emerald-200"
                    : "bg-red-900/50 text-red-200"
                }`}
              >
                {notice.text}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-md bg-emerald-500 text-slate-900 font-medium disabled:opacity-50"
            >
              {loading ? "Sending..." : "Send Message"}
            </button>
          </form>
        </div>

        {/* RIGHT — FAQ */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <h3 className="text-xl font-semibold text-emerald-300 mb-3">
            Frequently Asked Questions
          </h3>

          <div className="space-y-2">
            {FAQ.map((f, i) => (
              <details key={i} className="group border border-slate-800 rounded-md">
                <summary className="cursor-pointer px-4 py-3 bg-slate-900 flex justify-between">
                  <span className="text-slate-200">{f.q}</span>
                  <span className="text-slate-400 group-open:rotate-180 transition-transform">
                    ▾
                  </span>
                </summary>
                <div className="px-4 py-3 text-slate-400 bg-slate-800">
                  {f.a}
                </div>
              </details>
            ))}
          </div>

          <div className="mt-6 text-xs text-slate-500">
            Your feedback helps us improve AI Document Search.
          </div>
        </div>

      </div>
    </div>
  );
};

export default Contact;
