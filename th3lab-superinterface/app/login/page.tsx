"use client";

import { FormEvent, useState } from "react";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "No autorizado");
      }

      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error de login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="shell" style={{ maxWidth: 420, height: "auto" }}>
        <header className="shell-header">
          <div className="shell-title">TH3LAB PRIVATE ACCESS</div>
          <div className="status">secure</div>
        </header>
        <div className="input-wrap" style={{ borderTop: "none" }}>
          <form className="form" style={{ gridTemplateColumns: "1fr" }} onSubmit={onSubmit}>
            <input
              className="input"
              placeholder="Usuario"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
            />
            <input
              className="input"
              placeholder="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button className="btn" type="submit" disabled={loading || !username || !password}>
              {loading ? "Entrando..." : "Entrar"}
            </button>
          </form>
          {error ? <p className="hint">{error}</p> : null}
        </div>
      </section>
    </main>
  );
}
