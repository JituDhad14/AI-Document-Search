import React, { createContext, useContext, useState, useEffect } from "react";
import type { User } from "./types";

type AuthContextType = {
  user: User | null;
  register: (u: Omit<User, "createdAt">) => Promise<{ ok: boolean; msg?: string }>;
  login: (username: string, password: string) => Promise<{ ok: boolean; msg?: string }>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const STORAGE_USERS = "jj_users_v1";
const STORAGE_SESSION = "jj_session_v1";

function loadUsers(): User[] {
  try {
    const raw = localStorage.getItem(STORAGE_USERS);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveUsers(users: User[]) {
  localStorage.setItem(STORAGE_USERS, JSON.stringify(users));
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_SESSION);
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  });

  useEffect(() => {
    // nothing
  }, []);

  const register = async (u: Omit<User, "createdAt">) => {
    const users = loadUsers();
    if (users.find((x) => x.username === u.username || x.email === u.email)) {
      return { ok: false, msg: "Username or email already exists." };
    }
    const newUser: User = { ...u, createdAt: new Date().toISOString() };
    users.push(newUser);
    saveUsers(users);
    return { ok: true };
  };

  const login = async (username: string, password: string) => {
    const users = loadUsers();
    const found = users.find((x) => x.username === username && x.password === password);
    if (!found) return { ok: false, msg: "Invalid username or password." };
    localStorage.setItem(STORAGE_SESSION, JSON.stringify(found));
    setUser(found);
    return { ok: true };
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_SESSION);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, register, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
