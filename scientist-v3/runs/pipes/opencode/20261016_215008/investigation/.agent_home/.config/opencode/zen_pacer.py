#!/usr/bin/env python3
"""Per-request rate pacer for the OpenCode Zen relay.

Listens on 127.0.0.1:PACER_PORT and forwards every request to PACER_UPSTREAM
enforcing at least PACER_MIN_INTERVAL seconds between consecutive upstream
requests (global order). Responses with 429/5xx are retried (still paced)
until PACER_DEADLINE_SECONDS elapses; other responses pass through as-is.
Streaming responses are pumped through chunk by chunk.

Idempotent: if the port is already in use (a pacer is already running in this
container), the new instance exits quietly.

Stdlib only; no third-party dependencies.
"""

from __future__ import annotations

import http.client
import http.server
import os
import socket
import socketserver
import threading
import time
import urllib.parse
import urllib.request
import urllib.error

HOST = "127.0.0.1"
PORT = int(os.environ.get("PACER_PORT", "8787"))
UPSTREAM = os.environ.get("PACER_UPSTREAM", "https://opencode.ai/inference/openai/v1")
MIN_INTERVAL = float(os.environ.get("PACER_MIN_INTERVAL", "60"))
DEADLINE = float(os.environ.get("PACER_DEADLINE_SECONDS", "240"))

_slot_lock = threading.Condition()
_last_dispatched = [float("-inf")]


def _acquire_slot(deadline: float) -> None:
    """Block until a dispatch slot is free; marks the slot consumed."""
    with _slot_lock:
        while True:
            wait = _last_dispatched[0] + MIN_INTERVAL - time.monotonic()
            if wait <= 0:
                _last_dispatched[0] = time.monotonic()
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                # Out of budget: dispatch anyway rather than fail the request;
                # the upstream may still succeed between windows.
                _last_dispatched[0] = time.monotonic()
                return
            _slot_lock.wait(min(wait, remaining))


def _log(message: str) -> None:
    try:
        stamp = time.strftime("%H:%M:%S")
        with open(os.environ.get("PACER_LOG") or os.path.expanduser("~/zen_pacer.log"),
              "a", encoding="utf-8") as handle:
            handle.write(f"[{stamp}] {message}\n")
    except OSError:
        pass


_RETRYABLE = {429, 500, 502, 503, 504}


class _PacedProxy(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "zen-pacer/1"

    def log_message(self, fmt, *args):  # silence stderr
        self._log_line(fmt % args)

    def _log_line(self, message: str) -> None:
        _log(message)

    def _upstream_url(self) -> str:
        parsed = urllib.parse.urlparse(UPSTREAM)
        path = self.path.rstrip("/")
        base_path = parsed.path.rstrip("/")
        if path.startswith(base_path + "/"):
            merged = path
        elif base_path.endswith("/v1") and path.startswith("/v1/"):
            # Client pre-applied the /v1 suffix; don't duplicate it.
            merged = base_path + path[len("/v1"):]
        elif base_path and path.startswith("/"):
            merged = base_path + path
        else:
            merged = path or "/"
        return f"{parsed.scheme}://{parsed.netloc}{merged}"

    def _forward(self, method: str) -> None:
        url = self._upstream_url()
        hop = {"url": url}
        deadline = time.monotonic() + DEADLINE
        body = None
        if method not in ("GET", "HEAD"):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None

        while True:
            if time.monotonic() > deadline:
                self.send_error(504, "pacer deadline exceeded")
                return
            _acquire_slot(deadline if body is not None else time.monotonic() + DEADLINE)
            request_headers = {
                k: v
                for k, v in self.headers.items()
                if k.lower() not in ("host", "content-length", "connection",
                                     "transfer-encoding", "keep-alive",
                                     "accept-encoding")
            }
            request_headers.setdefault("Accept-Encoding", "identity")
            opencode_key = os.environ.get("OPENCODE_API_KEY")
            if opencode_key and "authorization" not in {
                k.lower() for k in request_headers
            }:
                request_headers["Authorization"] = f"Bearer {opencode_key}"
            try:
                req = urllib.request.Request(url, data=body, headers=request_headers,
                                             method=method)
                response = urllib.request.urlopen(req, timeout=560)
                status = getattr(response, "status", None) or 200
                hop["status"] = status
                if status in _RETRYABLE and time.monotonic() < deadline - 5:
                    _log(f"retryable status {status} for {url}; waiting for next slot")
                    response.close()
                    time.sleep(1.0)
                    continue
                break
            except urllib.error.HTTPError as error:
                # Body included; forward verbatim unless retryable.
                if error.code in _RETRYABLE and time.monotonic() < deadline - 5:
                    _log(f"retryable HTTPError {error.code} for {url}")
                    error.close()
                    time.sleep(1.0)
                    continue
                response = error
                status = error.code
                hop["status"] = status
                break
            except (urllib.error.URLError, socket.timeout, OSError) as error:
                hop["error"] = repr(error)
                if time.monotonic() < deadline - 5:
                    _log(f"transport error for {url}: {error!r}")
                    time.sleep(1.0)
                    continue
                self.send_error(502, f"upstream unreachable: {error}")
                return
            except Exception as error:  # noqa: BLE001 — never die silently
                hop["error"] = repr(error)
                _log(f"UNCAUGHT error for {url}: {error!r}")
                if time.monotonic() < deadline - 5:
                    time.sleep(1.0)
                    continue
                self.send_error(502, f"pacer failure: {error}")
                return

        try:
            self.send_response(status)
            for key, value in response.headers.items():
                if key.lower() in ("connection", "transfer-encoding",
                                   "keep-alive", "date", "server"):
                    continue
                if key.lower() == "content-length":
                    continue  # we stream; keep client chunked
                self.send_header(key, value)
            self.send_header("Connection", "close")
            self.end_headers()
            body_stream = getattr(response, "read", None)
            while True:
                chunk = body_stream(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
            if getattr(response, "close", None):
                response.close()
            self.close_connection = True
            _log(f"forwarded {method} {url} -> {status}")
        except (BrokenPipeError, ConnectionResetError) as error:
            self.close_connection = True
            _log(f"client disconnected while sending {method} {url} -> {status} ({error!r})")

    def do_GET(self):  # noqa: N802
        try:
            self._forward("GET")
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True

    def do_POST(self):  # noqa: N802
        try:
            self._forward("POST")
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True

    def do_DELETE(self):  # noqa: N802
        try:
            self._forward("DELETE")
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True


class _ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def main() -> int:
    try:
        server = _ThreadedServer((HOST, PORT), _PacedProxy)
    except OSError as error:
        # A pacer is already running in this container/namespace.
        _log(f"pacer not started (port busy): {error}")
        return 0
    _log(f"pacer up on {HOST}:{PORT} -> {UPSTREAM} (min interval {MIN_INTERVAL}s)")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    thread.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
