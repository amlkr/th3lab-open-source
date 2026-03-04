"use client";

import { FormEvent, useMemo, useState } from "react";
import type { ChatMessage } from "@/lib/types";

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

  const status = useMemo(() => (loading ? "thinking..." : "connected"), [loading]);

  async function onLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
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
        body: JSON.stringify({ messages: nextMessages })
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
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${message}` }
      ]);
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
                placeholder="Escribe para chat_con_agente_principal..."
                disabled={loading}
                autoFocus
              />
              <button className="btn" type="submit" disabled={loading || !input.trim()}>
                Send
              </button>
            </form>
            <p className="hint">Bridge: /api/th3lab -&gt; localhost:3000 (MCP)</p>
          </div>
        </div>
      </section>
    </main>
  );
}
