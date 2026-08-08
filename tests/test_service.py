import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from hello_ockap.__main__ import H


@pytest.fixture
def server():
    # Port 0 lets the OS pick a free one. A hard-coded port turns "something else is
    # listening" into a test failure, and in CI that is an unreproducible flake.
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address
    srv.shutdown()


def test_healthz_reports_ok(server):
    conn = HTTPConnection(*server)
    conn.request("GET", "/healthz")
    resp = conn.getresponse()
    assert resp.status == 200
    assert json.loads(resp.read()) == {"status": "ok"}


def test_unknown_path_is_404(server):
    conn = HTTPConnection(*server)
    conn.request("GET", "/nope")
    assert conn.getresponse().status == 404
