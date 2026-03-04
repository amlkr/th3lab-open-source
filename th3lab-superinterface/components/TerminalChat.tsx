"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import type { ChatMessage } from "@/lib/types";

type SessionAttachment = {
  name: string;
  kind: "document" | "media";
  type: string;
  note?: string;
};

type WorldDoc = {
  source: string;
  chunks: number;
};

const START_MESSAGES: ChatMessage[] = [
  {
    role: "assistant",
    content: "TH3LAB online. Escribe tu mensaje para el agente principal."
  }
];

export default function TerminalChat() {
  const [messages, setMessages] = useState<ChatMessage[]>(START_MESSAGES);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [attachments, setAttachments] = useState<SessionAttachment[]>([]);
  const [worldDocs, setWorldDocs] = useState<WorldDoc[]>([]);

  const status = useMemo(() => {
    if (uploading) return "uploading...";
    if (loading) return "thinking...";
    return "connected";
  }, [loading, uploading]);

  async function onLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  async function loadWorldDocuments() {
    try {
      const response = await fetch("/api/th3lab/documents", { cache: "no-store" });
      if (!response.ok) return;
      const data = (await response.json()) as { documents?: WorldDoc[] };
      setWorldDocs(Array.isArray(data.documents) ? data.documents : []);
    } catch {
      // ignore transient fetch issues
    }
  }

  useEffect(() => {
    loadWorldDocuments();
  }, []);

  async function onUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || uploading) return;

    setUploading(true);
    try {
      const form = new FormData();
      form.set("file", file);
      const response = await fetch("/api/th3lab/upload", {
        method: "POST",
        body: form
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "Upload failed");
      }

      const kind: "document" | "media" = data.kind === "media" ? "media" : "document";
      setAttachments((prev) => [
        {
          name: file.name,
          kind,
          type: file.type || "application/octet-stream",
          note: kind === "media" ? "referencia en sesion" : "ingestado en mundo"
        },
        ...prev
      ]);

      if (kind === "document") {
        await loadWorldDocuments();
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Upload error";
      setMessages((prev) => [...prev, { role: "assistant", content: `Error upload: ${msg}` }]);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = input.trim();
    if (!content || loading) return;

    const userMessage: ChatMessage = { role: "user", content };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("/api/th3lab", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: nextMessages,
          attachments: attachments.slice(0, 20)
        })
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "Bridge error");
      }

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: data.reply ?? "Sin respuesta del MCP"
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Error inesperado";
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${message}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="shell" aria-label="TH3LAB chat shell">
        <header className="shell-header">
          <div className="shell-title">TH3LAB / MCP / MAIN AGENT</div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div className="status">{status}</div>
            <button className="btn" type="button" onClick={onLogout}>
              Logout
            </button>
          </div>
        </header>

        <div className="chat-layout">
          <div className="chat">
            <div className="messages">
              {messages.map((msg, index) => (
                <article
                  key={`${msg.role}-${index}`}
                  className={`msg ${msg.role === "user" ? "msg-user" : "msg-assistant"}`}
                >
                  {msg.content}
                </article>
              ))}
            </div>

            <div className="input-wrap">
              <form className="form" onSubmit={onSubmit}>
                <input
                  className="input"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="Habla con el agente principal..."
                  disabled={loading}
                  autoFocus
                />
                <button className="btn" type="submit" disabled={loading || !input.trim()}>
                  Send
                </button>
              </form>
              <p className="hint">Dialogo con contexto de adjuntos de la sesion.</p>
            </div>
          </div>

          <aside className="asset-panel" aria-label="Panel de materiales">
            <div className="asset-title">MATERIAL DEL BRIEF</div>

            <label className="upload-box">
              <input
                type="file"
                onChange={onUpload}
                disabled={uploading}
                accept=".pdf,.txt,.md,.epub,.docx,.jpg,.jpeg,.png,.webp,.gif,.mp4,.mov,.mp3,.wav,.m4a"
              />
              {uploading ? "Subiendo..." : "+ Cargar doc / foto / video / audio"}
            </label>

            <div className="asset-section">
              <div className="asset-subtitle">Adjuntos de sesion</div>
              <div className="asset-list">
                {attachments.length === 0 ? (
                  <p className="hint">Sin adjuntos todavía.</p>
                ) : (
                  attachments.map((a, i) => (
                    <div key={`${a.name}-${i}`} className="asset-item">
                      <div>{a.name}</div>
                      <div className="asset-meta">{a.kind}</div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="asset-section">
              <div className="asset-subtitle">Docs ingestados en mundo</div>
              <div className="asset-list">
                {worldDocs.length === 0 ? (
                  <p className="hint">Sin documentos ingestados aún.</p>
                ) : (
                  worldDocs.map((d, i) => (
                    <div key={`${d.source}-${i}`} className="asset-item">
                      <div>{d.source}</div>
                      <div className="asset-meta">{d.chunks} chunks</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
