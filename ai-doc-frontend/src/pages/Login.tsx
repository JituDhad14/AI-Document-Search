import React, { useState } from "react";
import { useAuth } from "../auth/AuthProvider";
import { Link, useNavigate } from "react-router-dom";

export const Login: React.FC = () => {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(null);
    setLoading(true);
    const res = await login(username, password);
    setLoading(false);
    if (!res.ok) {
      setMsg(res.msg || "Login failed.");
      return;
    }
    nav("/"); // redirect to home or dashboard
  };

  return (
    <div className="max-w-lg mx-auto p-6">
      <h3 className="text-2xl font-bold text-emerald-300">Welcome back</h3>
      <p className="mt-2 text-slate-400">Already registered? Login below.</p>

      <form className="mt-6 space-y-4" onSubmit={submit}>
        <div>
          <label className="text-sm text-slate-300 block mb-1">Enter your username to know it's you</label>
          <input value={username} onChange={(e)=>setUsername(e.target.value)} placeholder="username" className="w-full rounded-md bg-slate-900 border border-slate-800 px-3 py-2 text-slate-200"/>
        </div>

        <div>
          <label className="text-sm text-slate-300 block mb-1">Enter password to verify</label>
          <input type="password" value={password} onChange={(e)=>setPassword(e.target.value)} placeholder="password" className="w-full rounded-md bg-slate-900 border border-slate-800 px-3 py-2 text-slate-200"/>
        </div>

        {msg && <div className="text-sm text-red-400">{msg}</div>}

        <div className="flex items-center justify-between">
          <div className="text-sm text-slate-400">You're just one click away from logging in — let's go.</div>
          <button type="submit" className="px-4 py-2 rounded-md bg-emerald-500 text-slate-900 font-medium">{loading ? "Signing in..." : "Login"}</button>
        </div>
      </form>

      <div className="mt-6 text-sm text-slate-400">
        New here? <Link to="/register" className="text-emerald-300 underline">Please register yourself</Link>.
      </div>
    </div>
  );
};
