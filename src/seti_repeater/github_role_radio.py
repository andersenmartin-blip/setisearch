"""GitHub v2 publication algorithm over an injected, isolated REST service.

No HTTP implementation, credentials, namespace initializer, or source budget
exists here. Only declared service fixtures are accepted in this qualification.
GitHub force=false is fast-forward protection, not an expected-head CAS API.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import threading
import uuid
from urllib.parse import quote

from . import acquisition_radio as acquisition
from . import execution_envelope_radio as envelope
from .publication_role_radio import validate_transition

FIXTURE_KIND = "isolated-github-v2-service-fixture"
LIMITS = {"max_calls": 128, "max_response_bytes": 8*1024**2,
          "max_ledger_bytes": 65536, "max_ancestry_commits": 16}


class PublicationStopped(RuntimeError):
    """Do not retry/refund. A reference update may already have committed."""


def git_sha(value):
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{40}", value):
        raise ValueError("invalid Git object SHA")
    return value


def blob_sha(payload):
    return hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()


def strict_json(payload):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def constant(value):
        raise ValueError("non-finite JSON number: " + value)
    return json.loads(payload, object_pairs_hook=pairs, parse_constant=constant)


class GitHubRoleStore:
    """Guarded remote algorithm, fixture-qualified only; no activation path.

    service.request(method, relative_api_path, body) returns (status, JSON).
    The injected service/immutable Git object addressing is trusted. Faults
    close this instance permanently; creating another instance never authorizes
    retry of an uncertain session. A caller must retain its independent head
    and ledger digest. Ref rollback by privileged outsiders is out of scope.
    """
    def __init__(self, service, spec_bytes, expected_spec_sha256, resource):
        if hashlib.sha256(spec_bytes).hexdigest() != expected_spec_sha256:
            raise ValueError("publication specification differs from independent pin")
        spec = strict_json(spec_bytes)
        resource.validate()
        if (spec.get("schema") != "radio-v2-github-publication-store-spec-v1"
                or spec.get("status") != "FROZEN_NOT_ACTIVATED"
                or spec.get("telescope_namespace_activated") is not False
                or spec.get("network_budget_issued") is not False
                or spec.get("resource_contract_sha256") != resource.identity
                or spec.get("source_inventory_sha256") != resource.source_inventory_sha256
                or spec.get("genesis_sha256") != envelope.ledger_digest(resource.genesis())):
            raise ValueError("publication specification/resource binding changed")
        location = spec["location"]
        if (set(location) != {"kind", "repository", "branch", "path"}
                or location["kind"] != "github"
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", location["repository"])
                or not location["branch"] or location["branch"].startswith("/")
                or any(x in ("", ".", "..") for x in location["path"].split("/"))):
            raise ValueError("invalid pinned GitHub location")
        if getattr(service, "kind", None) != FIXTURE_KIND:
            raise ValueError("isolated service fixture required; live namespace unactivated")
        self.service = service
        self._location_json = envelope.canonical(location)
        self._spec_sha = expected_spec_sha256
        self._genesis = envelope.ledger_digest(resource.genesis())
        self._resource, self._inventory = resource.identity, resource.source_inventory_sha256
        self._base = "/repos/" + location["repository"] + "/git/"
        self._ref = "heads/" + quote(location["branch"], safe="")
        self._parts = location["path"].split("/")
        self._lock = threading.Lock()
        self.stopped = False
        self.events = []
        self.receipts = []
        self._candidate = None

    @property
    def location(self):
        return json.loads(self._location_json)

    def _start(self, action):
        if self.stopped:
            raise PublicationStopped("store already stopped; no automatic retry")
        self._calls, self._bytes = 0, 0
        self._candidate = None
        self.events.append({"event": "begin", "action": action})

    def _stop(self, error):
        self.stopped = True
        self.events.append({"event": "stopped", "error_type": type(error).__name__,
            "reason": str(error), "candidate_commit": self._candidate,
            "quota_may_be_spent": True, "automatic_retry": False})
        return PublicationStopped("publication stopped; inspect evidence; quota may be spent: " + str(error))

    def _request(self, method, suffix, body=None):
        if self._calls >= LIMITS["max_calls"]:
            raise ValueError("service call budget exhausted")
        self._calls += 1
        event = {"event": "request", "index_in_operation": self._calls,
                 "method": method, "path": self._base+suffix, "body": body}
        self.events.append(event)
        # No retry loop, fallback service, credentials or HTTP client.
        status, response = self.service.request(method, self._base+suffix, body)
        payload = envelope.canonical(response).encode()
        self._bytes += len(payload)
        event.update(status=status, response_sha256=hashlib.sha256(payload).hexdigest(),
                     response_json_bytes=len(payload))
        if self._bytes > LIMITS["max_response_bytes"]:
            raise ValueError("service response budget exhausted")
        expected_status = 201 if method == "POST" else 200
        if type(status) is not int or status != expected_status:
            raise ValueError("service response not successful: " + str(status))
        if not isinstance(response, dict):
            raise ValueError("service response must be a JSON object")
        return response

    def _ref_head(self):
        value = self._request("GET", "ref/" + self._ref)
        if (value.get("ref") != "refs/heads/" + self.location["branch"]
                or value.get("object", {}).get("type") != "commit"):
            raise ValueError("branch reference identity/type changed")
        return git_sha(value["object"]["sha"])

    def _commit(self, sha):
        git_sha(sha)
        value = self._request("GET", "commits/" + sha)
        if value.get("sha") != sha:
            raise ValueError("commit response identity changed")
        tree = git_sha(value["tree"]["sha"])
        parents = [git_sha(p["sha"]) for p in value["parents"]]
        return {"sha": sha, "tree": tree, "parents": parents}

    def _tree(self, sha):
        value = self._request("GET", "trees/" + git_sha(sha))
        if value.get("sha") != sha or value.get("truncated") is not False:
            raise ValueError("tree identity changed or inventory truncated")
        entries = {}
        allowed = {("040000", "tree"), ("100644", "blob"), ("100755", "blob"),
                   ("120000", "blob"), ("160000", "commit")}
        for raw in value["tree"]:
            name = raw["path"]
            if (not isinstance(name, str) or name in ("", ".", "..") or "/" in name
                    or name in entries or (raw["mode"], raw["type"]) not in allowed):
                raise ValueError("invalid or duplicate tree entry")
            entries[name] = {"mode": raw["mode"], "type": raw["type"], "sha": git_sha(raw["sha"])}
        return entries

    def _path_inventory(self, tree):
        inventories = []
        for index, part in enumerate(self._parts):
            entries = self._tree(tree)
            inventories.append(entries)
            if part not in entries:
                raise ValueError("missing pinned ledger; initialization is forbidden")
            entry = entries[part]
            expected = ("100644", "blob") if index == len(self._parts)-1 else ("040000", "tree")
            if (entry["mode"], entry["type"]) != expected:
                raise ValueError("ledger path is not an ordinary file/directory")
            tree = entry["sha"]
        return inventories, tree

    def _blob(self, sha):
        value = self._request("GET", "blobs/" + git_sha(sha))
        if (value.get("sha") != sha or value.get("encoding") != "base64"
                or type(value.get("size")) is not int
                or not 0 <= value["size"] <= LIMITS["max_ledger_bytes"]):
            raise ValueError("invalid ledger blob identity/encoding/size")
        # GitHub base64 responses can contain line breaks; reject other garbage.
        text = value["content"].replace("\n", "").replace("\r", "")
        if len(text) > 4*((LIMITS["max_ledger_bytes"]+2)//3):
            raise ValueError("oversized encoded ledger")
        payload = base64.b64decode(text, validate=True)
        if len(payload) != value["size"] or blob_sha(payload) != sha:
            raise ValueError("ledger Git blob content hash mismatch")
        return payload

    def _validate_document(self, document):
        envelope.validate_resource_ledger(document, envelope.ledger_digest(document))
        if (document["resource_contract_sha256"] != self._resource
                or document["source_inventory_sha256"] != self._inventory
                or envelope.ledger_digest({**document, "reservations": []}) != self._genesis):
            raise ValueError("ledger namespace/genesis changed")
        if any(type(r["ordinal"]) is not int for r in document["reservations"]):
            raise ValueError("reservation ordinal must be an integer, not a boolean")

    def _checkpoint(self, revision):
        commit = self._commit(revision)
        inventories, blob = self._path_inventory(commit["tree"])
        payload = self._blob(blob)
        document = strict_json(payload)
        self._validate_document(document)
        return acquisition.Checkpoint(document, revision, self.location), commit, inventories, blob

    def read(self):
        with self._lock:
            self._start("read")
            try:
                checkpoint, _, _, _ = self._checkpoint(self._ref_head())
                return checkpoint
            except Exception as error:
                raise self._stop(error) from error

    def _verify_only_ledger_changed(self, before, tree, expected_blob):
        after, actual_blob = self._path_inventory(tree)
        if actual_blob != expected_blob:
            raise ValueError("candidate tree contains wrong ledger blob")
        for part, old, new in zip(self._parts, before, after):
            if ({k: v for k, v in old.items() if k != part}
                    != {k: v for k, v in new.items() if k != part}):
                raise ValueError("candidate tree changed an unrelated file")

    def _confirm_ancestry(self, candidate, expected_blob, expected_digest):
        # Conservative: a later reservation, merge, reset or uncertain ancestry
        # refuses confirmation. Unrelated first-parent commits are allowed only
        # when the ledger blob stays byte-identical at every intervening commit.
        current = self._ref_head()
        start = current
        visited = []
        for _ in range(LIMITS["max_ancestry_commits"]):
            if current in visited:
                raise ValueError("cyclic commit ancestry")
            visited.append(current)
            checkpoint, commit, _, blob = self._checkpoint(current)
            if blob != expected_blob or checkpoint.sha256 != expected_digest:
                raise ValueError("confirmation ledger changed; reservation may be spent")
            if current == candidate:
                return {"confirmed_head": start, "verified_commit_path": visited}
            if len(commit["parents"]) != 1:
                raise ValueError("confirmation ancestry is not a single-parent chain")
            current = commit["parents"][0]
        raise ValueError("confirmation ancestry bound exceeded")

    def publish(self, expected_revision, expected_sha256, document):
        with self._lock:
            self._start("publish")
            try:
                git_sha(expected_revision)
                envelope.sha(expected_sha256, "caller-held ledger digest")
                after = strict_json(envelope.canonical(document))
                self._validate_document(after)
                before, commit, inventories, _ = self._checkpoint(self._ref_head())
                if before.revision != expected_revision or before.sha256 != expected_sha256:
                    raise ValueError("caller-held branch/ledger checkpoint is stale")
                validate_transition(before.document, after, expected_sha256)
                payload = (envelope.canonical(after) + "\n").encode()
                if len(payload) > LIMITS["max_ledger_bytes"]:
                    raise ValueError("candidate ledger too large")
                expected_blob = blob_sha(payload)
                attempt_id = str(uuid.uuid4())
                self.events.append({"event": "prepared", "attempt_id": attempt_id,
                    "expected_head": expected_revision, "before_sha256": expected_sha256,
                    "after_sha256": envelope.ledger_digest(after), "blob_sha": expected_blob})
                tree = self._request("POST", "trees", {"base_tree": commit["tree"], "tree": [
                    {"path": self.location["path"], "mode": "100644", "type": "blob", "content": payload.decode()}]})
                tree_sha = git_sha(tree["sha"])
                self._verify_only_ledger_changed(inventories, tree_sha, expected_blob)
                made = self._request("POST", "commits", {"tree": tree_sha, "parents": [expected_revision],
                    "message": "Reserve radio v2 role; unique publication attempt " + attempt_id})
                self._candidate = git_sha(made["sha"])
                candidate = self._commit(self._candidate)
                if candidate["tree"] != tree_sha or candidate["parents"] != [expected_revision]:
                    raise ValueError("candidate commit tree/sole parent changed")
                if self._ref_head() != expected_revision:
                    raise ValueError("branch advanced before reference update")
                # Single attempt, explicit force=false. Distinct attempt IDs
                # keep identical competing payloads on divergent commit objects.
                updated = self._request("PATCH", "refs/" + self._ref,
                    {"sha": self._candidate, "force": False})
                if (updated.get("ref") != "refs/heads/" + self.location["branch"]
                        or updated.get("object", {}).get("type") != "commit"
                        or updated["object"].get("sha") != self._candidate):
                    raise ValueError("reference-update confirmation changed")
                # Read the immutable committed payload, not a mutable-branch file.
                landed, _, _, landed_blob = self._checkpoint(self._candidate)
                if landed_blob != expected_blob or landed.sha256 != envelope.ledger_digest(after):
                    raise ValueError("committed ledger read-back differs")
                ancestry = self._confirm_ancestry(self._candidate, expected_blob, landed.sha256)
                receipt = {"schema": "radio-github-v2-fixture-publication-receipt-v1",
                    "attempt_id": attempt_id, "location": self.location,
                    "specification_file_sha256": self._spec_sha,
                    "parent_commit": expected_revision, "commit": self._candidate,
                    "ledger_sha256": landed.sha256, "blob_sha": expected_blob,
                    "tree_sha": tree_sha, **ancestry,
                    "service_calls": self._calls, "response_json_bytes": self._bytes,
                    "qualification": "ISOLATED_SERVICE_FIXTURE_ONLY",
                    "network_budget_issued": False, "spectral_access_authorized": False}
                self.receipts.append(receipt)
                self.events.append({"event": "confirmed", "receipt": receipt})
                return receipt
            except Exception as error:
                raise self._stop(error) from error
