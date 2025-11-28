import React, { useState } from "react";
import { useAuth } from "../auth/AuthProvider";

const PURPOSES = ["Education","Research","Analyzing","Legal","Medical","General","Others"];

export const Register: React.FC = () => {
  const { register } = useAuth();
  const [form, setForm] = useState({
    email: "", username: "", name: "", profession: "", purpose: PURPOSES[0], password: "", confirm: ""
  });
  const [msg, setMsg] = useState<{type:"ok"|"err", text:string} | null>(null);
  const [loading, setLoading] = useState(false);

  const onChange = (k: string, v: string) => setForm(f => ({...f, [k]: v}));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(null);
    if (!form.email || !form.username || !form.password) {
      setMsg({ type: "err", text: "Please fill email, username and password."});
      return;
    }
    if (form.password.length < 6) {
      setMsg({ type: "err", text: "Password should be at least 6 characters."});
      return;
    }
    if (form.password !== form.confirm) {
      setMsg({ type: "err", text: "Passwords do not match."});
      return;
    }
    setLoading(true);
    const res = await register({
      email: form.email,
      username: form.username,
      name: form.name,
      profession: form.profession,
      purpose: form.purpose,
      password: form.password
    });
    setLoading(false);
    if (!res.ok) return setMsg({ type: "err", text: res.msg || "Registration failed."});
    setMsg({ type: "ok", text: "🎉 Yay — you have registered! Please login to use the chatbot."});
    setForm({ email:"", username:"", name:"", profession:"", purpose:PURPOSES[0], password:"", confirm:"" });
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h3 className="text-2xl font-bold text-emerald-300">Create your account</h3>
      <p className="mt-2 text-slate-400">New here? Please register yourself.</p>

      <form className="mt-6 space-y-4" onSubmit={submit}>
        <div>
          <label className="text-sm text-slate-300 block mb-1">Enter your email to verify yourself</label>
          <input value={form.email} onChange={(e)=>onChange("email", e.target.value)} placeholder="you@example.com" className="w-full rounded-md bg-slate-900 border border-slate-800 px-3 py-2 text-slate-200"/>
        </div>

        <div>
          <label className="text-sm text-slate-300 block mb-1">Enter your username for the Cognitive Assistant to know it's you</label>
          <input value={form.username} onChange={(e)=>onChange("username", e.target.value)} placeholder="your-username" className="w-full rounded-md bg-slate-900 border border-slate-800 px-3 py-2 text-slate-200"/>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm text-slate-300 block mb-1">Name</label>
            <input value={form.name} onChange={(e)=>onChange("name", e.target.value)} placeholder="Your full name" className="w-full rounded-md bg-slate-900 border border-slate-800 px-3 py-2 text-slate-200"/>
          </div>
          <div>
            <label className="text-sm text-slate-300 block mb-1">Profession</label>
            <input value={form.profession} onChange={(e)=>onChange("profession", e.target.value)} placeholder="Choose your profession so the Assistant can assist you better" className="w-full rounded-md bg-slate-900 border border-slate-800 px-3 py-2 text-slate-200"/>
          </div>
        </div>

        <div>
          <label className="text-sm text-slate-300 block mb-1">Purpose of usage</label>
          <select value={form.purpose} onChange={(e)=>onChange("purpose", e.target.value)} className="w-full rounded-md bg-slate-900 border border-slate-800 px-3 py-2 text-slate-200">
            {PURPOSES.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm text-slate-300 block mb-1">Password</label>
            <input type="password" value={form.password} onChange={(e)=>onChange("password", e.target.value)} placeholder="Choose a good password" className="w-full rounded-md bg-slate-900 border border-slate-800 px-3 py-2 text-slate-200"/>
          </div>
          <div>
            <label className="text-sm text-slate-300 block mb-1">Confirm password</label>
            <input type="password" value={form.confirm} onChange={(e)=>onChange("confirm", e.target.value)} placeholder="Confirm password" className="w-full rounded-md bg-slate-900 border border-slate-800 px-3 py-2 text-slate-200"/>
          </div>
        </div>

        {msg && (
          <div className={`py-2 px-3 rounded ${msg.type==="ok" ? "bg-emerald-900/60 text-emerald-200" : "bg-red-900/60 text-red-200"}`}>
            {msg.text}
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="text-sm text-slate-400">You're just one click away from registering yourself — let's go.</div>
          <button type="submit" disabled={loading} className="px-4 py-2 rounded-md bg-emerald-500 text-slate-900 font-medium">{loading ? "Registering..." : "Register"}</button>
        </div>
      </form>
    </div>
  );
};
