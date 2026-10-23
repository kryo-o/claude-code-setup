"""Claude OS dashboard: a read-only local web page over your Claude Code install.

Run it yourself, outside Claude:  python3 -I dashboard/serve.py [--project PATH]
It binds 127.0.0.1 only, answers GET only, and has no route that writes or serves files.
"""
import argparse
import hmac
import json
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_os import propose, scan  # noqa: E402
from claude_os.redact import scrub  # noqa: E402

WEB = Path(__file__).resolve().parent / "web"
STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/lib.js": ("lib.js", "text/javascript; charset=utf-8"),
          "/app.css": ("app.css", "text/css; charset=utf-8")}
HEADERS = {
    "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                               "img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",  # the token is in the URL
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
}
MANAGED = {"darwin": "/Library/Application Support/ClaudeCode/managed-settings.json",
           "linux": "/etc/claude-code/managed-settings.json"}


def respond(method, path, host, port, token, inventory):
    """(status, headers, body) for one request. Every rule of the server lives here."""
    def out(status, body=b"", ctype="text/plain; charset=utf-8"):
        return status, {**HEADERS, "Content-Type": ctype}, body

    # A DNS-rebinding page reaches 127.0.0.1 under its own host name; only ours is served.
    if host not in (f"127.0.0.1:{port}", f"localhost:{port}"):
        return out(403, b"forbidden host")
    if method != "GET":
        return out(405, b"read-only")
    url = urlsplit(path)
    if url.path in STATIC:
        name, ctype = STATIC[url.path]
        return out(200, (WEB / name).read_bytes(), ctype)
    if url.path == "/api/inventory":
        given = (parse_qs(url.query).get("t") or [""])[0]
        if not hmac.compare_digest(given.encode(), token.encode()):
            return out(403, b"bad token")
        return out(200, json.dumps(scrub(inventory())).encode(), "application/json")
    return out(404, b"not found")


def make_server(inventory, token, port=0):
    class Handler(BaseHTTPRequestHandler):
        def handle_one(self):
            status, headers, body = respond(self.command, self.path, self.headers.get("Host", ""),
                                            self.server.server_address[1], token, inventory)
            self.send_response(status)
            for k, v in headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_HEAD = do_OPTIONS = handle_one

        def log_message(self, *a):  # request lines would print the token
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", help="also show this project's settings, skills and MCP servers")
    ap.add_argument("--port", type=int, default=0, help="default: a free port")
    a = ap.parse_args()
    home = Path.home()
    project = Path(a.project).resolve() if a.project else None
    managed = MANAGED.get(sys.platform)
    token = secrets.token_urlsafe(24)
    srv = make_server(lambda: propose.attach(scan.scan(home, project, managed)), token, a.port)
    print(f"Claude OS: http://127.0.0.1:{srv.server_address[1]}/?t={token}\nCtrl+C to stop.", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
