"""stdout transport for the unchanged harness; stderr still drains independently."""

from collections import deque
import os
import queue
import selectors
import time

CHUNK_SIZE = 65536
LINE_CHUNK_LIMIT = 4097  # Exact readline(MAX_RESPONSE_LINE + 1) behavior.


class LineQueue:
    def __init__(self, hub):
        self.hub = hub
        self.items = deque()
        self.pending = bytearray()
        self.fd = None
        self.label = "unbound"

    def get(self, block=True, timeout=None):
        if not block:
            if self.items:
                return self.items.popleft()
            raise queue.Empty
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative")
        deadline = None if timeout is None else time.monotonic() + timeout
        while not self.items:
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                raise queue.Empty
            self.hub.pump(remaining)
        return self.items.popleft()

    def feed(self, data):
        self.pending.extend(data)
        offset, length = 0, len(self.pending)
        while offset < length:
            end = min(length, offset + LINE_CHUNK_LIMIT)
            newline = self.pending.find(b"\n", offset, end)
            if newline >= 0:
                end = newline + 1
            elif end - offset < LINE_CHUNK_LIMIT:
                break
            self.items.append(bytes(self.pending[offset:end]))
            offset = end
        if offset:
            del self.pending[:offset]


class ReadHub:
    def __init__(self):
        self.selector = selectors.DefaultSelector()

    def new_queue(self):
        return LineQueue(self)

    def attach(self, stream, out_queue, label):
        out_queue.label = label
        try:
            out_queue.fd = stream.fileno()
            os.set_blocking(out_queue.fd, False)
            self.selector.register(out_queue.fd, selectors.EVENT_READ, out_queue)
        except Exception as exc:
            out_queue.items.append(("reader_error", label + ": " + repr(exc)))
            out_queue.items.append(None)
        # run_case only stores this return value; it never joins stdout readers.
        return None

    def finish(self, out_queue, error=None):
        try:
            self.selector.unregister(out_queue.fd)
        except (KeyError, OSError, ValueError):
            pass
        if error is None:
            if out_queue.pending:
                out_queue.items.append(bytes(out_queue.pending))
        else:
            out_queue.items.append(("reader_error", out_queue.label + ": " + repr(error)))
        out_queue.pending.clear()
        out_queue.items.append(None)

    def pump(self, timeout):
        try:
            ready = self.selector.select(timeout)
        except InterruptedError:
            return
        for key, _ in ready:
            out_queue = key.data
            try:
                data = os.read(key.fd, CHUNK_SIZE)
            except BlockingIOError:
                continue
            except OSError as exc:
                self.finish(out_queue, exc)
                continue
            if data:
                out_queue.feed(data)
            else:
                self.finish(out_queue)

    def close(self):
        # Only the readiness monitor is owned here; Popen still owns its pipes
        # and the reference run_case has already killed/reaped/closed children.
        self.selector.close()
