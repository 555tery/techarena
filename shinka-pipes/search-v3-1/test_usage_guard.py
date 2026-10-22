import json

import tempfile
import unittest
from pathlib import Path

from usage_guard import (UsageGuardError, UsageStopped, gate, read_usage,
                         USAGE_METHOD)


def response(used, *, secondary=None):
    return {"rateLimitsByLimitId": {
        "codex": {
            "limitId": "codex",
            "limitName": None,
            "primary": {"usedPercent": used, "windowDurationMins": 300,
                        "resetsAt": 1800},
            "secondary": secondary,
        },
    }, "rateLimitResetCredits": {"availableCount": 12}}


class FakeRPC:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.methods = []

    def __call__(self, method):
        self.methods.append(method)
        if self.error:
            raise self.error
        return self.result


class UsageGuardTests(unittest.TestCase):
    def test_threshold_uses_remaining_and_allows_exactly_65(self):
        for used, remaining, allowed in ((9, 91, True), (35, 65, True), (36, 64, False)):
            with self.subTest(used=used), tempfile.TemporaryDirectory() as temporary:
                run = Path(temporary)
                rpc = FakeRPC(response(used))
                check = lambda: gate(run, rpc=rpc, now=lambda: 1000)
                if allowed:
                    snapshot = check()
                    self.assertEqual(snapshot["min_remaining_percent"], remaining)
                    self.assertFalse((run / "night-stop-request.json").exists())
                else:
                    with self.assertRaisesRegex(UsageStopped, "below 65%"):
                        check()
                    stopped = json.loads((run / "night-stop-request.json").read_text())
                    self.assertEqual(stopped["reason"], "quota_below_threshold")
                    self.assertEqual(stopped["quota"]["min_remaining_percent"], remaining)
                self.assertEqual(rpc.methods, [USAGE_METHOD])

    def test_all_null_windows_are_unavailable_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            rpc = FakeRPC({"rateLimitsByLimitId": {"codex": {
                "limitId": "codex", "primary": None, "secondary": None,
            }}})
            with self.assertRaisesRegex(UsageStopped, "could not be verified"):
                gate(run, rpc=rpc, now=lambda: 1000)
            self.assertEqual(json.loads((run / "night-stop-request.json").read_text())["reason"],
                             "quota_read_failed")
            self.assertFalse((run / "quota-usage.json").exists())

    def test_invalid_structures_raise_without_interpreting_unknown_as_remaining(self):
        invalid = [
            None,
            {"rateLimitsByLimitId": []},
            {"rateLimitsByLimitId": {"codex": "wrong"}},
            {"rateLimitsByLimitId": {"codex": {"primary": "wrong"}}},
            {"rateLimitsByLimitId": {"codex": {"primary": {"usedPercent": True}}}},
            {"rateLimitsByLimitId": {"codex": {"primary": {"usedPercent": 101}}}},
            {"rateLimitsByLimitId": {"codex": {"primary": None, "secondary": None}}},
            {"rateLimits": None},
        ]
        for bad_response in invalid:
            with self.subTest(response=bad_response):
                with self.assertRaises(UsageGuardError):
                    read_usage(rpc=FakeRPC(bad_response), now=lambda: 1000)

    def test_secondary_window_also_constrains_minimum_remaining(self):
        rpc = FakeRPC(response(9, secondary={"usedPercent": 36,
                                            "windowDurationMins": 10080,
                                            "resetsAt": 2400}))
        snapshot = read_usage(rpc=rpc, now=lambda: 1000)
        self.assertEqual(snapshot["min_remaining_percent"], 64)
        self.assertEqual([window["name"] for window in snapshot["buckets"][0]["windows"]],
                         ["primary", "secondary"])

    def test_legacy_single_bucket_view_is_supported(self):
        rpc = FakeRPC({"rateLimits": {"limitId": "codex", "primary": {
            "usedPercent": 35, "windowDurationMins": 300, "resetsAt": 2000,
        }, "secondary": None}})
        snapshot = read_usage(rpc=rpc, now=lambda: 1000)
        self.assertEqual(snapshot["min_remaining_percent"], 65)
        self.assertEqual(snapshot["buckets"][0]["limit_id"], "codex")

    def test_shared_snapshot_reused_until_expired_then_refreshed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            current_time = [1000.0]
            answers = [response(10), response(36)]
            rpc = FakeRPC()

            def changing_rpc(method):
                rpc.methods.append(method)
                return answers[len(rpc.methods) - 1]

            first = gate(run, rpc=changing_rpc, now=lambda: current_time[0])
            current_time[0] += 60
            at_expiry = gate(run, rpc=changing_rpc, now=lambda: current_time[0])
            self.assertEqual(at_expiry["captured_at"], first["captured_at"])
            self.assertEqual(len(rpc.methods), 1)

            current_time[0] += 1
            with self.assertRaisesRegex(UsageStopped, "below 65%"):
                gate(run, rpc=changing_rpc, now=lambda: current_time[0])
            self.assertEqual(len(rpc.methods), 2)
            persisted = json.loads((run / "quota-usage.json").read_text())
            self.assertEqual(persisted["captured_at"], current_time[0])

    def test_existing_stop_file_blocks_without_reading_quota(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "night-stop-request.json").write_text(json.dumps({"reason": "manual_stop"}))
            rpc = FakeRPC(response(9))
            with self.assertRaisesRegex(UsageStopped, "manual_stop"):
                gate(run, rpc=rpc, now=lambda: 1000)
            self.assertEqual(rpc.methods, [])

    def test_read_failure_persists_stop_and_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            rpc = FakeRPC(error=TimeoutError("network detail must not be persisted"))
            with self.assertRaisesRegex(UsageStopped, "could not be verified"):
                gate(run, rpc=rpc, now=lambda: 1000)
            stop = json.loads((run / "night-stop-request.json").read_text())
            self.assertEqual(stop["reason"], "quota_read_failed")
            self.assertEqual(stop["error_type"], "UsageGuardError")
            self.assertNotIn("network detail", json.dumps(stop))

    def test_corrupt_cached_snapshot_stops_instead_of_trusting_or_falling_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "quota-usage.json").write_text('{"protocol":"wrong"}')
            rpc = FakeRPC(response(9))
            with self.assertRaisesRegex(UsageStopped, "cached Codex quota data is invalid"):
                gate(run, rpc=rpc, now=lambda: 1000)
            self.assertEqual(rpc.methods, [])
            self.assertEqual(json.loads((run / "night-stop-request.json").read_text())["reason"],
                             "invalid_cached_quota")

