"""Fault/race tests of the new remote boundary with real isolated Git graphs."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch

from seti_repeater import execution_envelope_radio as envelope
from seti_repeater import github_role_radio as remote
from radio_github_v2_fixture import GitServiceFixture, ROOT, SPEC, resource


def next_document(before, session=1):
    result = copy.deepcopy(before)
    ordinal = len(before["reservations"])
    result["reservations"].append({"ordinal": ordinal,
        "role": envelope.EXPECTED_ROLES[ordinal], "session_id": str(uuid.UUID(int=session)),
        "prior_ledger_sha256": envelope.ledger_digest(before),
        "reserved_limits": dict(envelope.SESSION_LIMITS), "created_utc": "2026-09-27T12:00:00Z"})
    return result


class RemoteTests(unittest.TestCase):
    evidence = {}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.fixtures, self.stores = [], []
        self.resource = resource()
        self.spec = (ROOT/SPEC).read_bytes()
        self.spec_sha = json.loads((ROOT/"config/radio_github_v2_engineering_20260927.json").read_text())["input_sha256"][SPEC]
        self.service = self.fixture()
        self.store = self.make_store(self.service)
        self.genesis = self.resource.genesis()
        self.after = next_document(self.genesis)

    def fixture(self, **kwargs):
        service = GitServiceFixture(Path(self.temp.name)/str(len(self.fixtures)), **kwargs)
        self.fixtures.append(service)
        return service

    def make_store(self, service):
        result = remote.GitHubRoleStore(service, self.spec, self.spec_sha, self.resource)
        self.stores.append(result)
        return result

    def tearDown(self):
        self.evidence[self._testMethodName] = {
            "services": [s.evidence() for s in self.fixtures],
            "clients": [{"events": s.events, "receipts": s.receipts, "stopped": s.stopped} for s in self.stores]}
        self.temp.cleanup()

    def publish(self, store=None, document=None, revision=None, digest=None):
        store = store or self.store
        return store.publish(revision or self.service.initial,
            digest or envelope.ledger_digest(self.genesis), self.after if document is None else document)

    def assert_no_update(self):
        self.assertEqual(self.service.head, self.service.initial)
        self.assertFalse(any(c["method"] == "PATCH" for c in self.service.calls))

    def assert_stopped_without_retry(self, store=None):
        store = store or self.store
        count = len(store.service.calls)
        with self.assertRaises(remote.PublicationStopped): store.read()
        with self.assertRaises(remote.PublicationStopped): self.publish(store=store)
        self.assertEqual(len(store.service.calls), count)

    def test_controller_three_ordered_roles_and_fourth_refused(self):
        receipts = []
        for index, role in enumerate(envelope.EXPECTED_ROLES):
            checkpoint = self.store.read()
            result = envelope.reserve_role(self.store, expected_revision=checkpoint.revision,
                expected_ledger_sha256=checkpoint.sha256, role=role,
                session_id=str(uuid.UUID(int=index+1)), created_utc="2026-09-27T12:00:00Z")
            self.assertFalse(result["network_budget_issued"])
            self.assertFalse(result["spectral_access_authorized"])
            receipts.append(result)
        ledger = self.service.ledger()
        self.assertEqual(len(ledger["reservations"]), 3)
        self.assertEqual(envelope.validate_resource_ledger(ledger, envelope.ledger_digest(ledger))["remaining_limits"],
                         {"max_bytes": 0, "max_requests": 0, "max_seconds": 0})
        checkpoint = self.store.read()
        with self.assertRaisesRegex(ValueError, "out of order"):
            envelope.reserve_role(self.store, expected_revision=checkpoint.revision,
                expected_ledger_sha256=checkpoint.sha256, role="pilot",
                session_id=str(uuid.UUID(int=4)), created_utc="2026-09-27T12:00:00Z")
        self.assertEqual(self.service.ledger(), ledger)
        self.assertEqual(len(self.store.receipts), 3)

    def test_success_changes_exactly_the_ledger_in_git(self):
        receipt = self.publish()
        self.assertEqual(self.service.ledger(), self.after)
        changed = self.service.git("diff-tree", "--no-commit-id", "--name-only", "-r", receipt["commit"]).decode().splitlines()
        self.assertEqual(changed, [self.service.location["path"]])
        self.assertEqual(self.service.commit_json(receipt["commit"])["parents"], [{"sha": self.service.initial}])
        self.assertEqual(self.service.git("remote"), b"")
        updates = [c for c in self.service.calls if c["method"] == "PATCH"]
        self.assertEqual(len(updates), 1)
        self.assertIs(updates[0]["body"]["force"], False)

    def test_spec_pin_and_live_service_refused_before_calls(self):
        bad = self.spec.replace(b'"branch": "m43-support-qualification"', b'"branch": "main"')
        with self.assertRaisesRegex(ValueError, "independent pin"):
            remote.GitHubRoleStore(self.service, bad, self.spec_sha, self.resource)
        self.service.kind = "live-github"
        with self.assertRaisesRegex(ValueError, "isolated service"):
            self.make_store(self.service)
        self.assertEqual(self.service.calls, [])

    def test_missing_ledger_never_initialized(self):
        service = self.fixture(include_ledger=False)
        store = self.make_store(service)
        with self.assertRaisesRegex(remote.PublicationStopped, "missing pinned ledger"):
            store.read()
        self.assertTrue(all(c["method"] == "GET" for c in service.calls))
        self.assertEqual(service.head, service.initial)

    def test_same_commit_wrong_ledger_digest_refused_before_mutation(self):
        with self.assertRaisesRegex(remote.PublicationStopped, "stale"):
            self.publish(digest="a"*64)
        self.assert_no_update()
        self.assertTrue(all(c["method"] == "GET" for c in self.service.calls))

    def test_stale_branch_cannot_be_rebased_automatically(self):
        changed = self.service.external_commit()
        with self.assertRaisesRegex(remote.PublicationStopped, "stale"):
            self.publish()
        self.assertEqual(self.service.head, changed)
        self.assertTrue(all(c["method"] == "GET" for c in self.service.calls))

    def test_read_is_at_observed_commit_when_branch_advances(self):
        fired = []
        def after(method, path, body, status, response):
            if "/ref/" in path and not fired:
                fired.append(True)
                self.service.external_commit(entries=[{"path": self.service.location["path"],
                    "mode": "100644", "content": envelope.canonical(self.after)+"\n"}])
        self.service.after = after
        checkpoint = self.store.read()
        self.assertEqual(checkpoint.revision, self.service.initial)
        self.assertEqual(checkpoint.document, self.genesis)
        self.assertNotEqual(self.service.head, checkpoint.revision)

    def test_coherent_wrong_namespace_refused(self):
        changed = self.resource.genesis()
        changed["resource_contract_sha256"] = "a"*64
        service = self.fixture(document=changed)
        with self.assertRaisesRegex(remote.PublicationStopped, "namespace"):
            self.make_store(service).read()

    def test_reset_after_success_is_not_published(self):
        self.publish()
        checkpoint = self.store.read()
        with self.assertRaisesRegex(remote.PublicationStopped, "append exactly one"):
            self.store.publish(checkpoint.revision, checkpoint.sha256, self.genesis)
        self.assertEqual(self.service.ledger(), self.after)
        self.assertEqual(sum(c["method"] == "PATCH" for c in self.service.calls), 1)

    def test_skipped_append_and_boolean_ordinal_refused(self):
        for document in (next_document(self.after, 2),
                         self.after | {"reservations": [self.after["reservations"][0] | {"ordinal": False}]}):
            store = self.make_store(self.service)
            with self.assertRaises(remote.PublicationStopped):
                self.publish(store=store, document=document)
        self.assert_no_update()

    def test_tree_response_cannot_delete_or_change_unrelated_files(self):
        for fault in ("missing_base", "root_change", "nested_change", "wrong_ledger"):
            service = self.fixture()
            store = self.make_store(service)
            def before(method, path, body, fault=fault, service=service):
                if method == "POST" and path.endswith("/trees"):
                    entries = copy.deepcopy(body["tree"])
                    base = body["base_tree"]
                    if fault == "missing_base": base = service.empty_tree
                    if fault == "root_change": entries.append({"path": "README.md", "mode": "100644", "content": "corrupted"})
                    if fault == "nested_change": entries.append({"path": "notes/keep.txt", "mode": "100644", "content": "corrupted"})
                    if fault == "wrong_ledger": entries[0]["content"] = envelope.canonical(self.genesis)
                    return 201, {"sha": service.make_tree(base, entries)}
            service.before = before
            with self.subTest(fault=fault), self.assertRaises(remote.PublicationStopped):
                store.publish(service.initial, envelope.ledger_digest(self.genesis), self.after)
            self.assertEqual(service.head, service.initial)
            self.assertFalse(any(c["method"] == "PATCH" for c in service.calls))

    def test_wrong_commit_parent_and_tree_refused_before_update(self):
        for fault in ("parent", "tree"):
            service = self.fixture()
            store = self.make_store(service)
            def before(method, path, body, fault=fault, service=service):
                if method == "POST" and path.endswith("/commits"):
                    tree = service.empty_tree if fault == "tree" else body["tree"]
                    parents = [] if fault == "parent" else body["parents"]
                    return 201, {"sha": service.commit(tree, parents, body["message"])}
            service.before = before
            with self.assertRaisesRegex(remote.PublicationStopped, "sole parent"):
                store.publish(service.initial, envelope.ledger_digest(self.genesis), self.after)
            self.assertEqual(service.head, service.initial)

    def test_concurrent_identical_payloads_have_one_winner(self):
        self.race(identical=True)

    def test_fast_forward_alone_can_acknowledge_same_commit_twice(self):
        # Unsafe baseline: identical parent/tree/message can identify one commit.
        # This is service/Git semantics, not an authorized reservation path.
        tree = self.service.make_tree(self.service.commit_json(self.service.initial)["tree"]["sha"],
            [{"path": self.service.location["path"], "mode": "100644",
              "content": envelope.canonical(self.after)+"\n"}])
        first = self.service.commit(tree, [self.service.initial], "same deterministic request")
        second = self.service.commit(tree, [self.service.initial], "same deterministic request")
        self.assertEqual(first, second)
        for sha in (first, second):
            status, _ = self.service.request("PATCH", self.service.base+"refs/heads/"+self.service.location["branch"],
                {"sha": sha, "force": False})
            self.assertEqual(status, 200)
        self.assertEqual(len(self.service.ledger()["reservations"]), 1)

    def test_concurrent_distinct_payloads_have_one_winner(self):
        self.race(identical=False)

    def race(self, identical):
        barrier = threading.Barrier(2)
        def before(method, path, body):
            if method == "PATCH": barrier.wait(timeout=10)
        self.service.before = before
        stores = [self.store, self.make_store(self.service)]
        outcomes = []
        def writer(index):
            try:
                receipt = self.publish(store=stores[index], document=next_document(self.genesis, 1 if identical else index+1))
                outcomes.append(("confirmed", receipt["commit"]))
            except remote.PublicationStopped:
                outcomes.append(("stopped", None))
        workers = [threading.Thread(target=writer, args=(i,)) for i in range(2)]
        for worker in workers: worker.start()
        for worker in workers: worker.join(timeout=15)
        self.assertTrue(all(not w.is_alive() for w in workers))
        self.assertEqual(sorted(x[0] for x in outcomes), ["confirmed", "stopped"])
        self.assertEqual(len(self.service.ledger()["reservations"]), 1)
        updates = [c for c in self.service.calls if c["method"] == "PATCH"]
        self.assertEqual(len(set(c["body"]["sha"] for c in updates)), 2)
        self.assertEqual(sorted(c["status"] for c in updates), [200, 422])

    def test_lost_update_reply_preserves_spent_reservation_and_stops(self):
        def after(method, path, body, status, response):
            if method == "PATCH": raise TimeoutError("reply lost after durable update")
        self.service.after = after
        with self.assertRaisesRegex(remote.PublicationStopped, "reply lost"):
            self.publish()
        self.assertEqual(self.service.ledger(), self.after)
        self.assertEqual(self.store.receipts, [])
        self.assert_stopped_without_retry()

    def test_timeout_before_update_retains_orphan_without_retry(self):
        def before(method, path, body):
            if method == "PATCH": raise TimeoutError("update not delivered")
        self.service.before = before
        with self.assertRaisesRegex(remote.PublicationStopped, "not delivered"):
            self.publish()
        self.assertEqual(self.service.head, self.service.initial)
        self.assertIsNotNone(self.store._candidate)
        self.assertEqual(self.service.ledger(self.store._candidate), self.after)
        self.assert_stopped_without_retry()

    def test_fresh_client_after_lost_reply_refuses_old_checkpoint(self):
        def after(method, path, body, status, response):
            if method == "PATCH": raise TimeoutError("lost reservation reply")
        self.service.after = after
        with self.assertRaises(remote.PublicationStopped): self.publish()
        self.service.after = None
        restarted = self.make_store(self.service)
        self.assertEqual(restarted.read().document, self.after)
        with self.assertRaisesRegex(remote.PublicationStopped, "stale"):
            self.publish(store=restarted)
        self.assertEqual(sum(c["method"] == "PATCH" for c in self.service.calls), 1)
        self.assertEqual(len(self.service.ledger()["reservations"]), 1)

    def test_lost_tree_or_commit_reply_never_updates_ref(self):
        for target in ("trees", "commits"):
            service = self.fixture()
            store = self.make_store(service)
            def after(method, path, body, status, response, target=target):
                if method == "POST" and path.endswith("/"+target):
                    raise TimeoutError("object reply lost")
            service.after = after
            with self.assertRaises(remote.PublicationStopped):
                store.publish(service.initial, envelope.ledger_digest(self.genesis), self.after)
            self.assertEqual(service.head, service.initial)
            self.assertFalse(any(c["method"] == "PATCH" for c in service.calls))
            self.assert_stopped_without_retry(store)

    def test_wrong_update_ack_is_ambiguous_not_a_refund(self):
        def after(method, path, body, status, response):
            if method == "PATCH": response["object"]["sha"] = self.service.initial
        self.service.after = after
        with self.assertRaisesRegex(remote.PublicationStopped, "confirmation changed"):
            self.publish()
        self.assertEqual(self.service.ledger(), self.after)
        self.assertEqual(self.store.receipts, [])

    def test_branch_advance_between_preflight_and_patch_is_refused(self):
        def before(method, path, body):
            if method == "PATCH": self.service.external_commit(message="race after preflight")
        self.service.before = before
        with self.assertRaisesRegex(remote.PublicationStopped, "422"):
            self.publish()
        self.assertEqual(self.service.ledger(), self.genesis)

    def test_unrelated_descendant_with_same_ledger_is_confirmed(self):
        def after(method, path, body, status, response):
            if method == "PATCH": self.service.external_commit(entries=[{"path": "README.md", "mode": "100644", "content": "new unrelated text"}])
        self.service.after = after
        receipt = self.publish()
        self.assertEqual(len(receipt["verified_commit_path"]), 2)
        self.assertNotEqual(receipt["commit"], receipt["confirmed_head"])
        self.assertEqual(receipt["confirmed_head"], self.service.head)

    def test_same_ledger_on_unrelated_history_is_not_confirmation(self):
        def after(method, path, body, status, response):
            if method == "PATCH":
                tree = self.service.commit_json(body["sha"])["tree"]["sha"]
                shadow = self.service.commit(tree, [], "unrelated root with copied ledger")
                self.service.git("update-ref", self.service.ref, shadow)
        self.service.after = after
        with self.assertRaisesRegex(remote.PublicationStopped, "ancestry"):
            self.publish()
        self.assertEqual(self.service.ledger(), self.after)

    def test_reset_and_restore_in_confirmation_history_is_refused(self):
        def after(method, path, body, status, response):
            if method == "PATCH":
                for name, document in (("reset", self.genesis), ("restore", self.after)):
                    self.service.external_commit(message=name, entries=[{"path": self.service.location["path"],
                        "mode": "100644", "content": envelope.canonical(document)+"\n"}])
        self.service.after = after
        with self.assertRaisesRegex(remote.PublicationStopped, "confirmation ledger changed"):
            self.publish()
        self.assertEqual(self.service.ledger(), self.after)

    def test_later_role_during_confirmation_stops_without_erasing_it(self):
        later = next_document(self.after, 2)
        def after(method, path, body, status, response):
            if method == "PATCH": self.service.external_commit(entries=[{"path": self.service.location["path"],
                "mode": "100644", "content": envelope.canonical(later)+"\n"}])
        self.service.after = after
        with self.assertRaisesRegex(remote.PublicationStopped, "confirmation ledger changed"):
            self.publish()
        self.assertEqual(len(self.service.ledger()["reservations"]), 2)

    def test_merge_and_bounded_ancestry_fail_closed(self):
        for fault in ("merge", "too_long"):
            service = self.fixture()
            store = self.make_store(service)
            def after(method, path, body, status, response, fault=fault, service=service):
                if method == "PATCH":
                    if fault == "merge":
                        sibling = service.external_commit(parents=[service.initial], message="sibling", update=False)
                        service.external_commit(parents=[service.head, sibling], message="merge")
                    else:
                        for i in range(remote.LIMITS["max_ancestry_commits"]):
                            service.external_commit(message="intervening " + str(i))
            service.after = after
            with self.assertRaisesRegex(remote.PublicationStopped, "ancestry"):
                store.publish(service.initial, envelope.ledger_digest(self.genesis), self.after)
            self.assertEqual(service.ledger(), self.after)

    def test_truncated_duplicate_and_symlink_tree_entries_refused(self):
        for fault in ("truncated", "duplicate", "symlink"):
            service = self.fixture()
            store = self.make_store(service)
            def after(method, path, body, status, response, fault=fault, service=service):
                if method == "GET" and "/trees/" in path:
                    if fault == "truncated": response["truncated"] = True
                    if fault == "duplicate": response["tree"].append(copy.deepcopy(response["tree"][0]))
                    if fault == "symlink":
                        for row in response["tree"]:
                            if row["path"] == service.location["path"].split("/")[0]:
                                row.update(mode="120000", type="blob")
            service.after = after
            with self.assertRaises(remote.PublicationStopped): store.read()
            self.assertTrue(all(c["method"] == "GET" for c in service.calls))

    def test_corrupt_blob_hash_rejected_even_after_successful_update(self):
        landed = []
        def after(method, path, body, status, response):
            if method == "PATCH": landed.append(True)
            if landed and method == "GET" and "/blobs/" in path:
                raw = base64.b64decode(response["content"])
                response["content"] = base64.b64encode(raw[:-1]+b"X").decode()
        self.service.after = after
        with self.assertRaisesRegex(remote.PublicationStopped, "blob content hash"):
            self.publish()
        self.assertEqual(self.service.ledger(), self.after)

    def test_duplicate_and_nonfinite_json_rejected_from_real_git_blobs(self):
        for payload in ('{"roles":[],"roles":[]}', '{"bad":NaN}'):
            service = self.fixture()
            service.external_commit(entries=[{"path": service.location["path"], "mode": "100644", "content": payload}])
            with self.assertRaisesRegex(remote.PublicationStopped, "duplicate|non-finite"):
                self.make_store(service).read()

    def test_reference_and_commit_identity_substitution_refused(self):
        for fault in ("ref", "commit"):
            service = self.fixture()
            def after(method, path, body, status, response, fault=fault):
                if "/ref/" in path and fault == "ref": response["ref"] = "refs/heads/main"
                if "/commits/" in path and fault == "commit": response["sha"] = "a"*40
            service.after = after
            with self.assertRaises(remote.PublicationStopped): self.make_store(service).read()

    def test_service_failure_and_operation_caps_do_not_retry(self):
        for fault in ("rate_limit", "call_cap", "response_cap"):
            service = self.fixture()
            store = self.make_store(service)
            if fault == "rate_limit":
                service.before = lambda *args: (429, {"message": "rate limited"})
            limits = dict(remote.LIMITS)
            if fault == "call_cap": limits["max_calls"] = 1
            if fault == "response_cap": limits["max_response_bytes"] = 1
            with patch.dict(remote.LIMITS, limits), self.assertRaises(remote.PublicationStopped): store.read()
            self.assertEqual(len(service.calls), 1)
            self.assert_stopped_without_retry(store)


if __name__ == "__main__":
    unittest.main()
