// src/components/NavBar.tsx
import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";

export const NavBar: React.FC = () => {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  const handleLogout = () => {
    logout();
    nav("/");
  };

  return (
    <nav className="w-full border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 py-4 flex items-center justify-between">
      <div>
        <Link to="/" className="text-xl font-extrabold tracking-tight text-emerald-300">
          AI Document Search
        </Link>
        <div className="text-xs text-slate-400">Search smarter, work faster</div>
      </div>

      <div className="flex items-center gap-4">
        <Link to="/" className="text-sm text-slate-300 hover:text-emerald-300">Home</Link>
        <Link to="/chat" className="text-sm text-slate-300 hover:text-emerald-300">Chat</Link>
        <Link to="/contact" className="text-sm text-slate-300 hover:text-emerald-300">Contact</Link>

        {user ? (
          <>
            <Link to="/profile" className="text-sm text-slate-300 hover:text-emerald-300">Profile</Link>
            <span className="text-sm text-slate-300">Hi, {user.name ? (user.name.split(" ")[0]) : user.username}</span>
            <button onClick={handleLogout} className="text-sm px-3 py-1 rounded-md bg-slate-700 text-slate-200">Logout</button>
          </>
        ) : (
          <Link to="/login" className="text-sm px-3 py-1 rounded-md bg-emerald-500 text-slate-900 font-medium">Login / Register</Link>
        )}
      </div>
    </nav>
  );
};
