import http.client
import json
import threading
import unittest
from pathlib import Path

import serve
from tests.helpers import SECRETS

TOKEN = "t0ken-for-tests"


class Resp:
    def __init__(self, status, headers):
        self.status, self._h = status, {k.lower(): v for k, v in headers.items()}

    def getheader(self, name):
        return self._h.get(name.lower())
FAKE = {"skills": [{"name": "x", "description": "<img src=x onerror=alert(1)>"}], "env": SECRETS[0]}


class ServeTest(unittest.TestCase):
    """Runs over a real socket where binding is allowed, else against serve.respond directly."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.srv = serve.make_server(lambda: FAKE, TOKEN, port=0)
        except PermissionError:
            cls.srv, cls.port = None, 8765  # the Claude Code sandbox turns local binding off
            return
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        if cls.srv:
            cls.srv.shutdown()
            cls.srv.server_close()

    def req(self, method, path, host=None):
        host = host or f"127.0.0.1:{self.port}"
        if not self.srv:
            status, headers, body = serve.respond(method, path, host, self.port, TOKEN, lambda: FAKE)
            return Resp(status, headers), body
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.putrequest(method, path, skip_host=True)
        c.putheader("Host", host)
        c.endheaders()
        r = c.getresponse()
        body = r.read()
        c.close()
        return r, body

    def test_binds_loopback_only(self):
        if not self.srv:
            self.skipTest("local binding is off in this sandbox; run the tests in your own terminal")
        self.assertEqual(self.srv.server_address[0], "127.0.0.1")

    def test_inventory_with_token(self):
        r, body = self.req("GET", f"/api/inventory?t={TOKEN}")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.getheader("Content-Type"), "application/json")
        self.assertEqual(json.loads(body)["skills"][0]["name"], "x")

    def test_inventory_output_is_scrubbed_again(self):
        _, body = self.req("GET", f"/api/inventory?t={TOKEN}")
        self.assertNotIn(SECRETS[0].encode(), body)

    def test_missing_or_bad_token(self):
        for path in ("/api/inventory", "/api/inventory?t=wrong", "/api/inventory?t="):
            self.assertEqual(self.req("GET", path)[0].status, 403, path)

    def test_foreign_host_refused(self):
        # A DNS-rebinding page reaches 127.0.0.1 under its own host name.
        for host in ("evil.example", f"evil.example:{self.port}", "127.0.0.1.evil.example"):
            self.assertEqual(self.req("GET", "/", host=host)[0].status, 403, host)
        self.assertEqual(self.req("GET", "/", host=f"localhost:{self.port}")[0].status, 200)

    def test_write_methods_refused(self):
        for m in ("POST", "PUT", "DELETE", "PATCH"):
            self.assertEqual(self.req(m, f"/api/inventory?t={TOKEN}")[0].status, 405, m)

    def test_no_file_serving(self):
        for path in ("/../serve.py", "/..%2fserve.py", "/serve.py", "/etc/passwd", "/web/index.html"):
            self.assertEqual(self.req("GET", path)[0].status, 404, path)

    def test_static_pages(self):
        for path, kind in (("/", "text/html"), ("/app.js", "text/javascript"), ("/lib.js", "text/javascript"),
                           ("/app.css", "text/css")):
            r, _ = self.req("GET", path)
            self.assertEqual(r.status, 200, path)
            self.assertTrue(r.getheader("Content-Type").startswith(kind), path)

    def test_printed_link_opens_the_page(self):
        r, body = self.req("GET", f"/?t={TOKEN}")
        self.assertEqual(r.status, 200)
        self.assertIn(b"<title>Claude OS</title>", body)

    def test_security_headers(self):
        r, _ = self.req("GET", "/")
        csp = r.getheader("Content-Security-Policy")
        self.assertIn("default-src 'none'", csp)
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertEqual(r.getheader("Referrer-Policy"), "no-referrer")
        self.assertEqual(r.getheader("X-Content-Type-Options"), "nosniff")
        self.assertIsNone(r.getheader("Access-Control-Allow-Origin"))


class PageTest(unittest.TestCase):
    def test_page_never_renders_html_from_data(self):
        # Skill descriptions come from third-party plugins, so they are text, never markup.
        web = Path(serve.__file__).parent / "web"
        js = (web / "app.js").read_text() + (web / "lib.js").read_text()
        for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(bad, js)

    def test_nested_children_are_flattened_fully(self):
        # Views return lists of lists; a one-level flat() printed "[object HTMLDivElement]".
        js = (Path(serve.__file__).parent / "web/app.js").read_text()
        self.assertNotRegex(js, r"\.flat\(\)")
        self.assertIn(".flat(Infinity)", js)



if __name__ == "__main__":
    unittest.main()
