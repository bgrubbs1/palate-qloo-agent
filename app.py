#!/usr/bin/env python3
"""PALATE web app — a dependency-free Python HTTP server.

Serves the single-page UI plus one JSON API:

    GET  /                 the app
    GET  /api/healthz      {"ok": true, "mode": "live"|"mock", ...}
    POST /api/plan         {"city","mood","loves":[...]} -> full agent run

Run locally:      python3 app.py                (http://127.0.0.1:8000)
Force mock:       PALATE_MODE=mock python3 app.py
Live (hosted):    QLOO_API_KEY=... PALATE_MODE=live python3 app.py
Container/host:   binds 0.0.0.0 when $PORT is set (Render/HF Spaces friendly).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from palate import APP_NAME, APP_TAGLINE, __version__
from palate.agent import Concierge, InvalidRequest
from palate.qloo import QlooConfigError, QlooError, create_client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
MAX_BODY_BYTES = 32 * 1024
RATE_LIMIT_REQUESTS = 40
RATE_LIMIT_WINDOW = 60.0

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}

SERVICE = {"client": None, "info": None, "started": time.time()}
RATE_LOCK = threading.Lock()
RATE_BUCKETS = {}


def configure(mode=None, env=None):
    client, info = create_client(mode, env=env)
    SERVICE["client"] = client
    SERVICE["info"] = info
    return client, info


def run_agent(payload):
    """Run one agent pass, with a clearly-labelled simulated fallback in live mode."""
    client = SERVICE["client"]
    info = SERVICE["info"]
    allow_fallback = (os.environ.get("PALATE_MOCK_FALLBACK", "1") or "1").strip().lower() not in ("0", "false", "no")
    try:
        result = Concierge(client).run(payload)
    except QlooError as exc:
        if client.mode != "live" or not allow_fallback:
            raise
        result = None
        failure = str(exc)
    else:
        failure = result.get("meta", {}).get("qloo_error_sample")
    if result is not None:
        if client.mode != "live" or not allow_fallback:
            return result, False, None
        if result["summary"]["slots_filled"]:
            return result, False, None  # partial Qloo success is still a real result
        if not failure:
            return result, False, None
        from palate.qloo import MockQlooClient

        fallback = MockQlooClient()
        result = Concierge(fallback).run(payload)
        reason = failure
        result["mode"] = "mock-fallback"
        result["fallback_reason"] = reason
        result["meta"]["data_source"] = "simulated taste graph (live Qloo request failed)"
        result["trace"].append(
            {
                "step": len(result["trace"]) + 1,
                "phase": "system",
                "title": "Live Qloo call failed — showing a simulated run",
                "detail": "The app stayed up and used the bundled synthetic graph. Reason: %s" % reason,
                "data": {"fallback": True, "requested_mode": info["resolved"] if info else "live"},
            }
        )
        return result, True, reason


class PalateHandler(BaseHTTPRequestHandler):
    server_version = "Palate/%s" % __version__
    protocol_version = "HTTP/1.1"

    # -- routing -----------------------------------------------------------
    def do_GET(self):  # noqa: N802 - stdlib naming
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            return self._send_file(os.path.join(STATIC_DIR, "index.html"))
        if path == "/api/healthz":
            info = SERVICE["info"] or {}
            return self._send_json(
                {
                    "ok": True,
                    "app": APP_NAME,
                    "version": __version__,
                    "mode": (SERVICE["client"].mode if SERVICE["client"] else "unconfigured"),
                    "resolved_from": info,
                    "uptime_s": int(time.time() - SERVICE["started"]),
                    "live_configured": bool((os.environ.get("QLOO_API_KEY") or "").strip()),
                },
                status=HTTPStatus.OK,
            )
        if path == "/api/sample":
            return self._send_json(_sample_profiles(), status=HTTPStatus.OK)
        if path == "/favicon.ico":
            return self._send_bytes(b"", status=HTTPStatus.NO_CONTENT)
        if path.startswith("/static/"):
            relative = path[len("/static/") :]
            return self._send_static(relative)
        if path.startswith("/api/"):
            return self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
        return self._send_file(os.path.join(STATIC_DIR, "index.html"))

    def do_POST(self):  # noqa: N802 - stdlib naming
        path = urlparse(self.path).path
        if path != "/api/plan":
            return self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
        if not self._allow_request():
            return self._send_json(
                {"error": "Too many requests — give the agent a moment, then retry."},
                status=HTTPStatus.TOO_MANY_REQUESTS,
            )
        try:
            payload = self._read_json()
            result, fell_back, reason = run_agent(payload)
        except InvalidRequest as exc:
            return self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except QlooConfigError as exc:
            return self._send_json({"error": str(exc)}, status=HTTPStatus.SERVICE_UNAVAILABLE)
        except QlooError as exc:
            return self._send_json(
                {"error": "Qloo API error: %s" % exc},
                status=HTTPStatus.BAD_GATEWAY,
            )
        except ValueError as exc:
            return self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        headers = {"X-PALATE-Fallback": "1"} if fell_back else {}
        return self._send_json(result, status=HTTPStatus.OK, extra_headers=headers)

    def do_OPTIONS(self):  # noqa: N802 - stdlib naming
        self.send_response(HTTPStatus.NO_CONTENT)
        self._common_headers()
        self.send_header("Allow", "GET, POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    # -- helpers -----------------------------------------------------------
    def _read_json(self):
        length_header = self.headers.get("Content-Length") or "0"
        try:
            length = int(length_header)
        except ValueError:
            raise ValueError("Invalid Content-Length.")
        if length <= 0:
            raise ValueError("Empty request body — send JSON.")
        if length > MAX_BODY_BYTES:
            raise ValueError("Request body too large.")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            raise ValueError("Request body must be valid JSON.")
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _allow_request(self):
        ip = self.client_address[0] if self.client_address else "unknown"
        now = time.monotonic()
        with RATE_LOCK:
            bucket = RATE_BUCKETS.setdefault(ip, deque())
            while bucket and now - bucket[0] > RATE_LIMIT_WINDOW:
                bucket.popleft()
            if len(bucket) >= RATE_LIMIT_REQUESTS:
                return False
            bucket.append(now)
        return True

    def _send_static(self, relative):
        safe = os.path.normpath(relative).replace("\\", "/")
        if safe.startswith("..") or safe.startswith("/"):
            return self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
        target = os.path.join(STATIC_DIR, safe)
        if not os.path.isfile(target):
            return self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
        return self._send_file(target)

    def _send_file(self, path):
        if not os.path.isfile(path):
            return self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
        with open(path, "rb") as handle:
            body = handle.read()
        content_type = CONTENT_TYPES.get(os.path.splitext(path)[1].lower(), "application/octet-stream")
        self._send_bytes(body, content_type=content_type)

    def _send_json(self, payload, status=HTTPStatus.OK, extra_headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        }
        headers.update(extra_headers or {})
        self._send_bytes(body, status=status, content_type="application/json; charset=utf-8", extra_headers=headers)

    def _send_bytes(self, body, status=HTTPStatus.OK, content_type="application/octet-stream", extra_headers=None):
        self.send_response(status)
        self._common_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _common_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")

    def log_message(self, fmt, *args):  # concise, no query strings
        sys.stderr.write("[palate] %s - %s\n" % (self.address_string(), fmt % args))


def _sample_profiles():
    return {
        "profiles": [
            {
                "label": "Cozy but a little weird",
                "city": "New York",
                "mood": "cozy but a little weird — warm room, strange edges",
                "loves": ["Kamasi Washington", "Everything Everywhere All at Once", "Ramen Tsubaki"],
            },
            {
                "label": "High-energy date night",
                "city": "Los Angeles",
                "mood": "high-energy date night, cocktails and loud music",
                "loves": ["Little Simz", "Burna Boy", "The Echo Annex"],
            },
            {
                "label": "Low-key brainy Sunday",
                "city": "New York",
                "mood": "low-key and brainy, bookshops and quiet ambient",
                "loves": ["Nils Frahm", "Severance", "Piranesi"],
            },
        ],
        "cities": ["New York", "Los Angeles", "London"],
    }


def build_server(host, port):
    server = ThreadingHTTPServer((host, port), PalateHandler)
    server.daemon_threads = True
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="%s — %s" % (APP_NAME, APP_TAGLINE))
    parser.add_argument("--host", default=None, help="bind host (default: 127.0.0.1, or 0.0.0.0 when $PORT is set)")
    parser.add_argument("--port", type=int, default=None, help="port (default: $PORT or 8000)")
    parser.add_argument("--mode", choices=("auto", "mock", "live"), default=None, help="data source override")
    parser.add_argument("--version", action="version", version="%s %s" % (APP_NAME, __version__))
    args = parser.parse_args(argv)

    try:
        client, info = configure(args.mode)
    except QlooConfigError as exc:
        print("PALATE cannot start: %s" % exc, file=sys.stderr)
        return 2

    port = args.port if args.port is not None else int(os.environ.get("PORT") or 8000)
    host = args.host or os.environ.get("HOST") or ("0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    server = build_server(host, port)
    print("%s %s — %s" % (APP_NAME, __version__, APP_TAGLINE))
    print("  data source : %s (%s)" % (client.mode, info["reason"]))
    print("  base url    : %s" % client.base_url)
    print("  listening   : http://%s:%d" % (host, port))
    if client.mode == "mock":
        print("  NOTE: no QLOO_API_KEY found — using the bundled synthetic taste graph.")
        print("        Export QLOO_API_KEY to run against the real Qloo API.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
