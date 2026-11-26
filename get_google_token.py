#!/usr/bin/env python3
"""Get a Google Photos refresh token for GOOGLE_REFRESH_TOKEN.

Run this yourself (on a computer, or in a GitHub Codespace from your phone's
browser). Never in CI.

It uses Google's loopback sign-in flow for Desktop app clients: Google sends
your browser to http://127.0.0.1:<port>/ with a one-time code.

- On a computer, the script listens on that address and catches the code.
- With --paste (on automatically inside a Codespace), the redirect page fails
  to load, which is expected. Copy the full address from the browser's
  address bar and paste it into the script.

The client ID and secret come from --client-id/--client-secret, or the
GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET environment variables. If the secret is
missing, the script asks for it without echoing it to the screen.

Usage:
    pip install -r requirements-dev.txt
    python get_google_token.py                # computer
    python get_google_token.py --paste        # phone / Codespace
"""

import argparse
import base64
import getpass
import hashlib
import http.server
import os
import secrets
import sys
import urllib.parse
import webbrowser

import requests

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/photoslibrary.appendonly"
DEFAULT_PORT = 8765


def make_pkce_pair():
    """Return (code_verifier, code_challenge) for PKCE with S256."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_auth_url(client_id, redirect_uri, state, code_challenge):
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def parse_redirect(url, expected_state):
    """Pull the authorization code out of the URL Google redirected to.

    Raises ValueError if Google returned an error, the state does not match,
    or there is no code.
    """
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url.strip()).query)
    if "error" in query:
        raise ValueError(f"Google returned an error: {query['error'][0]}")
    if query.get("state", [None])[0] != expected_state:
        raise ValueError(
            "The state in that URL doesn't match this run. Paste the URL from "
            "this run's sign-in, not an older one."
        )
    code = query.get("code", [None])[0]
    if not code:
        raise ValueError("No code found in that URL.")
    return code


def wait_for_redirect(port):
    """Serve one request on 127.0.0.1:port and return the full redirect URL."""
    captured = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            captured["url"] = f"http://127.0.0.1:{port}{self.path}"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Done. You can close this tab and go back to the terminal.")

        def log_message(self, *args):
            pass

    with http.server.HTTPServer(("127.0.0.1", port), Handler) as server:
        while "url" not in captured:
            server.handle_request()
    return captured["url"]


def exchange_code(client_id, client_secret, code, redirect_uri, code_verifier):
    r = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    if not r.ok:
        sys.exit(f"Token exchange failed ({r.status_code}): {r.text}")
    tokens = r.json()
    if "refresh_token" not in tokens:
        sys.exit("Google didn't return a refresh token. Run the script again.")
    return tokens["refresh_token"]


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--client-id", default=os.environ.get("GOOGLE_CLIENT_ID"))
    parser.add_argument("--client-secret", default=os.environ.get("GOOGLE_CLIENT_SECRET"))
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--paste",
        action="store_true",
        default=os.environ.get("CODESPACES") == "true",
        help="Paste the redirect URL instead of catching it (default inside a Codespace).",
    )
    args = parser.parse_args()

    client_id = args.client_id or input("Google client ID: ").strip()
    client_secret = args.client_secret or getpass.getpass("Google client secret (hidden): ").strip()

    redirect_uri = f"http://127.0.0.1:{args.port}/"
    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = make_pkce_pair()
    auth_url = build_auth_url(client_id, redirect_uri, state, code_challenge)

    print("\n1. Open this link and approve access with your Google account:\n")
    print(auth_url, "\n")

    if args.paste:
        print(
            "2. Google then sends you to a 127.0.0.1 page that won't load. That's\n"
            "   expected. Copy the full address from the address bar.\n"
        )
        redirect_url = input("3. Paste that address here: ")
    else:
        webbrowser.open(auth_url)
        print(f"2. Waiting for Google to redirect to {redirect_uri} ...")
        redirect_url = wait_for_redirect(args.port)

    try:
        code = parse_redirect(redirect_url, state)
    except ValueError as e:
        sys.exit(str(e))

    refresh_token = exchange_code(client_id, client_secret, code, redirect_uri, code_verifier)
    print("\nSuccess. Set this as the GOOGLE_REFRESH_TOKEN GitHub secret:\n")
    print(refresh_token)


if __name__ == "__main__":
    main()
