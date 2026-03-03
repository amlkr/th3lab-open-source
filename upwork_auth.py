#!/usr/bin/env python3
"""
upwork_auth.py — One-time Upwork OAuth 2.0 authorization

Run once to get an access token. It will:
  1. Open Upwork in your browser for authorization
  2. Capture the code via a local HTTP server on port 8080
  3. Save the token to ~/.upwork_token.json

Usage:
  python3 upwork_auth.py

Requires:
  pip install python-upwork-oauth2

Setup:
  - Set CLIENT_SECRET below (from https://www.upwork.com/developer/keys)
  - Ensure http://localhost:8080/callback is registered as a redirect URI
    in your Upwork app settings
"""

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import upwork

# ── Credentials ──────────────────────────────────────────────────────────────
CLIENT_ID     = "ddd09e0d"
CLIENT_SECRET = "PASTE_YOUR_CLIENT_SECRET_HERE"
REDIRECT_URI  = "http://localhost:8080/callback"
TOKEN_FILE    = Path.home() / ".upwork_token.json"
# ─────────────────────────────────────────────────────────────────────────────


def main():
    if CLIENT_SECRET == "PASTE_YOUR_CLIENT_SECRET_HERE":
        print("ERROR: Paste your Client Secret into CLIENT_SECRET in upwork_auth.py")
        print("  Get it from: https://www.upwork.com/developer/keys")
        return

    config = upwork.Config({
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri":  REDIRECT_URI,
    })
    client = upwork.Client(config)

    auth_url, state = client.get_authorization_url()

    # Capture the authorization code via a one-shot local server
    code_holder = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            q = parse_qs(urlparse(self.path).query)
            code_holder["code"] = q.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<h2 style='font-family:sans-serif'>Autorizado! Podes cerrar esta tab.</h2>"
            )

        def log_message(self, *args):
            pass  # silence server logs

    print(f"\nAbriendo Upwork en el browser para autorizar...")
    print(f"(Si no abre automáticamente, abrí esta URL manualmente:)\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8080), CallbackHandler)
    print("Esperando callback de Upwork en http://localhost:8080/callback ...")
    server.handle_request()  # blocks until one request arrives, then returns

    code = code_holder.get("code")
    if not code:
        print("ERROR: No se recibio el codigo de autorización.")
        return

    print(f"Codigo recibido. Intercambiando por token...")
    token = client.get_access_token(code)

    TOKEN_FILE.write_text(json.dumps(token, indent=2))
    print(f"\nToken guardado en: {TOKEN_FILE}")
    print("Ya podes correr upwork_scout.py para buscar jobs.")


if __name__ == "__main__":
    main()
