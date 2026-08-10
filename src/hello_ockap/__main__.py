import json
import os
import sqlite3
import sys
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = os.environ.get("DB_PATH", "/var/lib/hello-ockap/app.db")


def log(**kw):
    print(json.dumps(kw), file=sys.stdout, flush=True)  # flush: journald reads the pipe


def db():
    # A NEW connection per request, not one held open. ThreadingHTTPServer serves each
    # request on its own thread, and a sqlite3 connection may not cross threads by
    # default: sharing one raises ProgrammingError intermittently, under concurrency
    # only, which is a miserable thing to debug. Connections are cheap.
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS visits (ts TEXT NOT NULL)")
    return conn


class H(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            self._send(200, {"status": "ok"})
        elif self.path == "/visits":
            conn = db()
            try:
                (n,) = conn.execute("SELECT count(*) FROM visits").fetchone()
            finally:
                conn.close()
            self._send(200, {"count": n})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/visit":
            self._send(404, {"error": "not found"})
            return
        conn = db()
        try:
            # `with conn` commits the transaction. It does NOT close the connection —
            # that is the trap. Without the finally, one descriptor leaks per request
            # until the process hits its file limit and starts refusing connections,
            # by which time the cause is hours behind the symptom.
            with conn:
                conn.execute(
                    "INSERT INTO visits (ts) VALUES (?)",
                    (datetime.now(UTC).isoformat(),),
                )
        finally:
            conn.close()
        self._send(201, {"status": "recorded"})

    def log_message(self, fmt, *a):
        log(msg=fmt % a, path=self.path)


if __name__ == "__main__":
    # 0.0.0.0, NOT 127.0.0.1 — see A.1.1.
    ThreadingHTTPServer(
        ("0.0.0.0", int(os.environ.get("PORT", "8000"))), H
    ).serve_forever()
