#!/usr/bin/env python3
"""One-time helper: get a Google Drive refresh token for the backup job.

Run this once on your Mac. It prints three values to put in backend/.env and
in Render's Environment tab. Nothing here touches the server.

    python3 scripts/google_auth.py

Before running, in the Google Cloud Console (console.cloud.google.com):

  1. Create or pick a project.
  2. APIs & Services -> Library -> enable "Google Drive API".
  3. APIs & Services -> OAuth consent screen:
       - User type: External
       - Add yourself under "Test users"
       - Publishing status: Publish. In "Testing", refresh tokens expire after
         7 days, which would silently break the backup mid-trip.
  4. APIs & Services -> Credentials -> Create credentials
       -> OAuth client ID -> Application type: **Desktop app**.
     Copy the client ID and client secret.

Why not a service account: on a personal Google account a service account has
its own Drive identity with zero storage quota, so uploads fail with "storage
quota exceeded" however you share the folder. A refresh token makes the server
act as you, so the files are yours and use your 15GB.
"""
from __future__ import annotations

import http.server
import json
import secrets
import socketserver
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PORT = 8765
REDIRECT = f"http://localhost:{PORT}"

# Only files this app creates. It can never see the rest of your Drive, which
# is why the backup job makes its own folder instead of writing into one you
# nominate.
SCOPE = "https://www.googleapis.com/auth/drive.file"

_result: dict = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        _result.update({k: v[0] for k, v in params.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        ok = "code" in _result
        self.wfile.write(
            ("<h2>%s</h2><p>You can close this tab and return to the terminal.</p>"
             % ("Authorized ✓" if ok else "Authorization failed"))
            .encode("utf-8")
        )

    def log_message(self, *args):
        pass  # keep the console clean


def main() -> int:
    client_id = input("OAuth client ID: ").strip()
    client_secret = input("OAuth client secret: ").strip()
    if not client_id or not client_secret:
        print("Both values are required.", file=sys.stderr)
        return 1

    state = secrets.token_urlsafe(16)
    url = f"{AUTH_URL}?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": SCOPE,
        # Google only returns a refresh token when both are set, and only on
        # the first consent — hence prompt=consent, so re-running this works.
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })

    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("localhost", PORT), Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()

    print("\nOpening your browser to authorize…")
    print(f"If it doesn't open, paste this in:\n\n{url}\n")
    webbrowser.open(url)

    for _ in range(600):  # ~5 minutes
        if _result:
            break
        threading.Event().wait(0.5)
    server.server_close()

    if _result.get("state") != state:
        print("State mismatch — start over.", file=sys.stderr)
        return 1
    if "code" not in _result:
        print(f"No code returned: {_result}", file=sys.stderr)
        return 1

    body = urllib.parse.urlencode({
        "code": _result["code"],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT,
        "grant_type": "authorization_code",
    }).encode()
    with urllib.request.urlopen(TOKEN_URL, data=body) as resp:
        payload = json.load(resp)

    refresh = payload.get("refresh_token")
    if not refresh:
        print("No refresh token returned. Revoke this app's access at "
              "https://myaccount.google.com/permissions and run again.",
              file=sys.stderr)
        return 1

    print("\n" + "=" * 62)
    print("Add these to backend/.env and to Render -> Environment:\n")
    print(f"GOOGLE_CLIENT_ID={client_id}")
    print(f"GOOGLE_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={refresh}")
    print("=" * 62)
    print("\nThen: scripts/job.sh backup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
