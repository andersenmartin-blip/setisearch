"""New risks for grouped immutable readback; no closed live case is replayed."""
import base64
import copy
import unittest

from seti_repeater import whole_cadence_readbatch_radio as r


def blob(data):
    return r.git_object("blob", data)


class ReadDouble:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []
        self.transform = lambda result: result

    def invoke(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        items = []
        for request in params["requests"]:
            data = self.payloads[request["path"]]
            items.append({
                "ordinal": request["ordinal"],
                "ok": True,
                "result": {"sha": blob(data), "encoding": "base64",
                           "content": base64.b64encode(data).decode("ascii")},
            })
        return self.transform({"items": items, "underlying_request_count": len(items)})


class ReadbackBatchTests(unittest.TestCase):
    def setUp(self):
        self.payloads = {r.PREFIX + f"part{i}.txt": (f"part-{i}" * 13).encode() for i in range(3)}
        self.requests = [
            {"ordinal": i, "path": path, "ref": "a" * 40,
             "blob_sha": blob(data), "cap": len(data)}
            for i, (path, data) in enumerate(self.payloads.items())
        ]
        self.remote = ReadDouble(self.payloads)

    def client(self, **kwargs):
        return r.ImmutableReadbackBatch(self.remote.invoke, **kwargs)

    def test_success_charges_every_request_before_one_aggregate(self):
        client = self.client()
        self.assertEqual(client.read(self.requests), list(self.payloads.values()))
        self.assertEqual(client.underlying_calls, 3)
        self.assertEqual(len(self.remote.calls), 1)
        self.assertGreater(client.reserved_bytes, client.response_bytes)
        self.assertEqual(client.events[0]["status"], "verified")

    def test_reordered_replies_verify_by_ordinal(self):
        self.remote.transform = lambda result: {**result, "items": list(reversed(result["items"]))}
        client = self.client()
        self.assertEqual(client.read(self.requests), list(self.payloads.values()))
        self.assertEqual(client.events[0]["reply_order"], [2, 1, 0])

    def test_missing_reply_stops_without_retry(self):
        self.remote.transform = lambda result: {**result, "items": result["items"][:-1]}
        client = self.client()
        with self.assertRaisesRegex(r.ReadbackStopped, "Missing"):
            client.read(self.requests)
        with self.assertRaisesRegex(r.ReadbackStopped, "already stopped"):
            client.read(self.requests)
        self.assertEqual(len(self.remote.calls), 1)

    def test_duplicate_reply_stops(self):
        self.remote.transform = lambda result: {**result, "items": result["items"] + [result["items"][0]]}
        with self.assertRaisesRegex(r.ReadbackStopped, "Duplicate"):
            self.client().read(self.requests)

    def test_partial_failure_is_preserved_and_nonretryable(self):
        def fail(result):
            result["items"][1] = {"ordinal": 1, "ok": False, "error": "bounded failure",
                                  "automatic_retry": False}
            return result
        self.remote.transform = fail
        client = self.client()
        with self.assertRaisesRegex(r.ReadbackStopped, "Partial"):
            client.read(self.requests)
        self.assertEqual(client.events[0]["failures"], [{"ordinal": 1, "error": "bounded failure"}])
        self.assertEqual(client.underlying_calls, 3)

    def test_retry_authorization_in_failure_is_rejected(self):
        def fail(result):
            result["items"][0] = {"ordinal": 0, "ok": False, "error": "x",
                                  "automatic_retry": True}
            return result
        self.remote.transform = fail
        with self.assertRaisesRegex(r.ReadbackStopped, "cannot authorize retry"):
            self.client().read(self.requests)

    def test_corrupt_content_is_rejected(self):
        def corrupt(result):
            result["items"][0]["result"]["content"] = base64.b64encode(b"wrong").decode()
            return result
        self.remote.transform = corrupt
        with self.assertRaisesRegex(r.ReadbackStopped, "content hash"):
            self.client().read(self.requests)

    def test_wrong_sha_or_encoding_is_rejected(self):
        for field, value in (("sha", "b" * 40), ("encoding", "utf-8")):
            def alter(result, field=field, value=value):
                result["items"][0]["result"][field] = value
                return result
            self.remote.transform = alter
            with self.assertRaisesRegex(r.ReadbackStopped, "identity"):
                self.client().read(self.requests)

    def test_response_reservation_refuses_before_dispatch(self):
        client = self.client(response_limit=100)
        with self.assertRaisesRegex(r.ReadbackStopped, "reservation"):
            client.read(self.requests)
        self.assertEqual(self.remote.calls, [])
        self.assertEqual(client.underlying_calls, 0)

    def test_actual_response_above_reservation_stops(self):
        def inflate(result):
            result["padding"] = "x"
            return result
        self.remote.transform = inflate
        with self.assertRaisesRegex(r.ReadbackStopped, "frame"):
            self.client().read(self.requests)

    def test_call_limit_refuses_before_dispatch(self):
        client = self.client(call_limit=3, prior_calls=1)
        with self.assertRaisesRegex(r.ReadbackStopped, "request limit"):
            client.read(self.requests)
        self.assertEqual(self.remote.calls, [])

    def test_duplicate_path_and_bad_ordinals_refused(self):
        duplicate = copy.deepcopy(self.requests)
        duplicate[1]["path"] = duplicate[0]["path"]
        with self.assertRaisesRegex(r.ReadbackStopped, "Duplicate"):
            self.client().read(duplicate)
        bad = copy.deepcopy(self.requests)
        bad[1]["ordinal"] = 7
        with self.assertRaisesRegex(r.ReadbackStopped, "ordinals"):
            self.client().read(bad)

    def test_mutable_ref_and_namespace_escape_refused(self):
        for field, value in (("ref", "main"), ("path", "README.md")):
            bad = copy.deepcopy(self.requests)
            bad[0][field] = value
            with self.assertRaises(r.ReadbackStopped):
                self.client().read(bad)

    def test_distinct_live02_exact_path_is_admitted(self):
        data = b"fresh-live02-witness"
        path = "PROJECT_DIRECTION.md"
        remote = ReadDouble({path: data})
        request = [{"ordinal": 0, "path": path, "ref": "b" * 40,
                    "blob_sha": blob(data), "cap": len(data)}]
        client = r.ImmutableReadbackBatch(remote.invoke)
        self.assertEqual(client.read(request), [data])

    def test_declared_cap_is_enforced(self):
        bad = copy.deepcopy(self.requests)
        bad[0]["cap"] -= 1
        with self.assertRaisesRegex(r.ReadbackStopped, "exceeds cap"):
            self.client().read(bad)


if __name__ == "__main__":
    unittest.main()
