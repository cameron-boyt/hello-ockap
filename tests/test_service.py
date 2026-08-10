import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from hello_ockap.__main__ import H
from hello_ockap import __main__ as main


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


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    # Patch the MODULE GLOBAL, not the environment. DB_PATH is read once at import time,
    # so monkeypatch.setenv() inside a test happens far too late to have any effect —
    # and the test would then write to /var/lib/hello-ockap, pass on your machine, and
    # fail in CI where that path does not exist.
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "test.db"))


def test_visit_increments_the_count(server):
    conn = HTTPConnection(*server)
    conn.request("POST", "/visit")
    assert conn.getresponse().status == 201

    conn = HTTPConnection(*server)
    conn.request("GET", "/visits")
    assert json.loads(conn.getresponse().read()) == {"count": 1}
