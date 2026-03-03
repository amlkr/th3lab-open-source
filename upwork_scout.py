#!/usr/bin/env python3
"""
upwork_scout.py — Fetch real Upwork job listings and send to WhatsApp

Requires a valid token in ~/.upwork_token.json (run upwork_auth.py first).

Usage: python3 upwork_scout.py
"""

import json
import subprocess
from pathlib import Path

import upwork
from upwork.routers import graphql

# ── Credentials ──────────────────────────────────────────────────────────────
CLIENT_ID     = "ddd09e0d"
CLIENT_SECRET = "PASTE_YOUR_CLIENT_SECRET_HERE"
REDIRECT_URI  = "http://localhost:8080/callback"
TOKEN_FILE    = Path.home() / ".upwork_token.json"
WHATSAPP_TO   = "+61432483747"
# ─────────────────────────────────────────────────────────────────────────────

# Searches: (label, keyword list for andTerms_all)
SEARCHES = [
    ("AI Video Analysis",  ["AI", "video", "analysis"]),
    ("Documentary + AI",   ["documentary", "AI", "filmmaker"]),
    ("Generative Art",     ["generative", "art", "AI"]),
    ("Visual AI Tools",    ["visual", "AI", "creative"]),
    ("Cinematographic AI", ["cinematographic", "film", "AI"]),
]

QUERY = """
query SearchJobs($terms: [String!]!) {
  marketplaceJobPostings(filter: {
    searchTerm_eq: { andTerms_all: $terms }
    sortAttributes: { field: CREATE_TIME, sortOrder: DESC }
  }) {
    totalCount
    edges {
      node {
        id
        title
        createdDateTime
        duration
        skills { name }
      }
    }
  }
}
"""


def get_client():
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"Token no encontrado en {TOKEN_FILE}. Corré upwork_auth.py primero."
        )
    token = json.loads(TOKEN_FILE.read_text())
    config = upwork.Config({
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri":  REDIRECT_URI,
        "token":         token,
    })
    client = upwork.Client(config)
    # Persist refreshed token if it changed
    if client.token != token:
        TOKEN_FILE.write_text(json.dumps(client.token, indent=2))
    return client


def search_jobs(client, terms):
    result = graphql.Api(client).execute({
        "query":     QUERY,
        "variables": {"terms": terms},
    })
    data = result.get("data") or {}
    edges = data.get("marketplaceJobPostings", {}).get("edges", [])
    return [e["node"] for e in edges]


def format_job(job):
    title = job.get("title", "Sin título")
    job_id = job.get("id", "")
    url = f"https://www.upwork.com/jobs/{job_id}" if job_id else "(sin link)"
    skills = ", ".join(s["name"] for s in job.get("skills", [])[:3])
    duration = job.get("duration", "")
    line = f"• {title}"
    if duration:
        line += f"  [{duration}]"
    line += f"\n  {url}"
    if skills:
        line += f"\n  Skills: {skills}"
    return line


def send_whatsapp(message):
    result = subprocess.run(
        ["openclaw", "message", "send",
         "--channel", "whatsapp",
         "--target",  WHATSAPP_TO,
         "--message", message],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        print("Enviado a WhatsApp OK")
    else:
        print(f"Error al enviar: {result.stderr}")
        print("--- Mensaje ---")
        print(message)


def main():
    if CLIENT_SECRET == "PASTE_YOUR_CLIENT_SECRET_HERE":
        print("ERROR: Paste your Client Secret into CLIENT_SECRET in upwork_scout.py")
        print("  Get it from: https://www.upwork.com/developer/keys")
        return

    client = get_client()

    lines = ["*Upwork Scout — Jobs reales*\n"]
    total_found = 0

    for label, terms in SEARCHES:
        try:
            jobs = search_jobs(client, terms)
        except Exception as e:
            print(f"Error buscando '{label}': {e}")
            continue

        if not jobs:
            continue

        total_found += len(jobs)
        lines.append(f"*{label}* ({len(jobs)} encontrados)")
        for job in jobs[:3]:
            lines.append(format_job(job))
        lines.append("")

    if total_found == 0:
        lines.append("_No se encontraron jobs en este momento._")

    lines.append("_Via upwork\\_scout.py · API Upwork GraphQL · amlkr dashboard_")

    message = "\n".join(lines)
    print(message)
    print()
    send_whatsapp(message)


if __name__ == "__main__":
    main()
