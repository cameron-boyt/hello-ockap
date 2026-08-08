import json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

def log(**kw):
    print(json.dumps(kw), file=sys.stdout, flush=True)   # flush: journald reads the pipe

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        ok = self.path == "/healthz"
        body = json.dumps({"status": "ok"} if ok else {"error": "not found"}).encode()
        self.send_response(200 if ok else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *a):
        log(msg=fmt % a, path=self.path)

if __name__ == "__main__":
    # 0.0.0.0, NOT 127.0.0.1. Inside the container, 127.0.0.1 is the container's own
    # loopback. PublishPort forwards to the container's external address, so a service
    # bound to loopback publishes a port that refuses every connection. It still works
    # under `podman run --network host` on your laptop, which is exactly why this
    # mistake survives every local test and first appears at stage 3.
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), H).serve_forever()