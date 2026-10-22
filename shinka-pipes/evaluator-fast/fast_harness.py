#!/usr/bin/env python3
"""The pinned Pipes harness with event-driven stdout; no checks replaced."""

from __future__ import annotations

import io
import queue
import threading
from types import SimpleNamespace

from reference import check_reference, load_frozen
from selector_transport import ReadHub

BUFFER_SIZE = 65536


def start_line_reader(stream, out_queue, label):
    def run():
        reader = None
        try:
            # readline returns as soon as a flushed LF arrives; it does not
            # wait for BUFFER_SIZE bytes. The bound is the original 4097 bytes.
            reader = io.BufferedReader(stream, buffer_size=BUFFER_SIZE)
            while True:
                line = reader.readline(4096 + 1)
                if not line:
                    break
                out_queue.put(line)
                if len(line) > 4096 and not line.endswith(b"\n"):
                    continue  # Same rejection/draining behavior as the reference.
        except Exception as exc:
            out_queue.put(("reader_error", label + ": " + repr(exc)))
        finally:
            if reader is not None:
                # Popen/raw stdout retains ownership. Never close its file
                # descriptor from a BufferedReader destructor in this thread.
                try:
                    reader.detach()
                except (OSError, ValueError):
                    pass
            out_queue.put(None)

    thread = threading.Thread(target=run, name="pipes-reader-" + label, daemon=True)
    thread.start()
    return thread


def build_harness(*, transport: str = "selector"):
    harness = load_frozen("task/tools/pipes_harness.py")
    if harness.MAX_RESPONSE_LINE != 4096:
        raise ValueError("unexpected reference line limit")
    if transport == "buffered":
        # This is a private module object in this process. No source or other
        # process is patched. All run_case/main/limits/aggregation code is reused.
        harness.start_line_reader = start_line_reader
    elif transport == "selector":
        reference_run_case = harness.run_case
        harness.reference_run_case = reference_run_case

        def run_case(*args, **kwargs):
            hub = ReadHub()
            previous_queue, previous_reader = harness.queue, harness.start_line_reader
            harness.queue = SimpleNamespace(Queue=hub.new_queue, Empty=queue.Empty)
            harness.start_line_reader = hub.attach
            try:
                return reference_run_case(*args, **kwargs)
            finally:
                harness.queue, harness.start_line_reader = previous_queue, previous_reader
                hub.close()

        harness.run_case = run_case
    elif transport != "reference":
        raise ValueError("unknown transport")
    return harness


def main() -> int:
    check_reference()
    return build_harness().main()


if __name__ == "__main__":
    raise SystemExit(main())
