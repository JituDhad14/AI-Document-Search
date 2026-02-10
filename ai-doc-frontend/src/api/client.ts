// src/api/client.ts
import axios from "axios";

/**
 * API base:
 * Make sure VITE_API_URL is set to "http://localhost:8000" (no trailing /api)
 * or to your deployed backend root. The axios instance below will add "/api".
 */
const ROOT = import.meta.env.VITE_API_URL || "http://localhost:8000";
const BASE_URL = ROOT.replace(/\/$/, "") + "/api";

export const api = axios.create({
  baseURL: BASE_URL,
  // you can set timeout, headers etc. here if desired
});

// ---- TYPES ----
export type DocumentMeta = {
  id: string;
  name: string;
  chunks?: number;
  file_url?: string;
};

export interface ChatRequest {
  query: string;
  k?: number;
  document?: string | null;
}

export interface ChatResponse {
  query: string;
  answer: string;
  sources: string[];
}

// ---- FUNCTIONS ----

/**
 * Upload one or more files. Returns array of backend responses.
 */
export async function uploadDocuments(files: File[]): Promise<any[]> {
  const results: any[] = [];

  for (const file of files) {
    const form = new FormData();
    form.append("file", file);

    const res = await api.post("/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    results.push(res.data);
  }

  return results;
}
export async function submitFeedback(payload: {
  name: string;
  email: string;
  subject: string;
  message: string;
}) {
  const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const res = await fetch(`${API}/api/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Failed to submit feedback");
  }

  return res.json();
}

/**
 * Get the list of documents from the backend.
 * Backend responds with { documents: DocumentMeta[] }.
 */
export async function listDocuments(): Promise<DocumentMeta[]> {
  const res = await api.get<{ documents: DocumentMeta[] }>("/docs");
  // defensive: if backend returns { documents: [...] } use that, otherwise attempt to coerce
  if (res.data && Array.isArray((res.data as any).documents)) {
    return res.data.documents;
  }
  // fallback: if somehow the backend returned an array directly:
  if (Array.isArray((res.data as any))) {
    return res.data as any as DocumentMeta[];
  }
  // otherwise return empty array to avoid UI crash
  return [];
}

/**
 * Chat / RAG endpoint.
 */
export async function chatWithDocs(payload: ChatRequest): Promise<ChatResponse> {
  const res = await api.post<ChatResponse>("/chat", payload);
  return res.data;
}
