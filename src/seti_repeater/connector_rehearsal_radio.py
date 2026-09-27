"""Typed connector-envelope/model integration. All dispatch remains OFFLINE.

No HTTP status is synthesized. Reuse the frozen Git-object validation methods,
but explicitly bind the distinct rehearsal model and override transport and
publication acknowledgement semantics. A live provider is never accepted.
"""
from dataclasses import dataclass
import hashlib
import json
import threading
from urllib.parse import quote

from . import acquisition_radio as acquisition
from . import execution_envelope_radio as envelope
from . import github_role_radio as gitcore
from . import rehearsal_contract_radio as rehearsal
from .publication_role_radio import validate_transition


@dataclass(frozen=True)
class ConnectorReply:
    kind: str
    value: dict
    http_status: None = None
    api_version: None = None
    internal_attempts: None = None


class ConnectorUncertain(RuntimeError):
    """No resend: a provider failure need not imply an absent side effect."""


def decode_reply(operation, raw):
    value = rehearsal.strict_json(raw)
    if not isinstance(value, dict) or value.get("isError") is not False:
        raise ConnectorUncertain("missing success envelope or provider error; HTTP outcome unknown")
    structured = value.get("structuredContent")
    if not isinstance(structured, dict):
        raise ConnectorUncertain("missing typed structured content; no text fallback")
    if operation == "read":
        content = structured.get("content")
        if type(content) is not str:
            raise ConnectorUncertain("GET content is not an exact JSON string")
        nested = structured.get("structuredContent")
        if nested is not None and (not isinstance(nested, dict) or nested.get("content") != content):
            raise ConnectorUncertain("inconsistent duplicated GET content")
        payload = rehearsal.strict_json(content)
        if not isinstance(payload, dict):
            raise ConnectorUncertain("GET result is not an object")
        return ConnectorReply("git_object", payload)
    if operation in ("create_tree", "create_commit"):
        return ConnectorReply("object_identity", {"sha": gitcore.git_sha(structured.get("sha"))})
    if operation == "update_ref":
        if structured.get("success") is not True:
            raise ConnectorUncertain("reference tool did not explicitly acknowledge success")
        # This is an ACK, NOT a made-up refs/object/sha response. Read back Git.
        return ConnectorReply("acknowledgement", {"success": True})
    raise ValueError("unsupported typed connector operation")


class JournaledConnectorFixture:
    """Use the old local journal with a separately identified connector fixture."""
    kind = "local-rehearsal-call-fixture"

    def __init__(self, connector, authority, owner):
        if getattr(connector, "kind", None) != "isolated-connector-envelope-fixture":
            raise ValueError("offline connector-envelope fixture required")
        if getattr(authority, "kind", None) != "independent-admission-authority-fixture":
            raise ValueError("explicit independent admission fixture required")
        self.connector, self.authority, self.owner = connector, authority, owner

    def dispatch(self, operation, request):
        # The journal has fsynced intent first. The independent FIXTURE authority
        # commits one call debit before any simulated connector side effect.
        self.authority.admit(self.owner, operation, request)
        result = self.connector.invoke(request["tool"], request["arguments"])
        return rehearsal.encode(result).decode()


class ConnectorModelStore(gitcore.GitHubRoleStore):
    """Explicit model binding; no production ResourceContract or fixture spoofing.

    Inherit only the frozen pure Git read/validation/ancestry algorithm. The
    constructor, _request and publish paths below use typed connector semantics
    and the phase-wide write-ahead journal, without resetting that phase budget.
    """
    def __init__(self, journal, prepared_bytes, expected_prepared_sha256, reply_allowance=65536):
        if hashlib.sha256(prepared_bytes).hexdigest() != expected_prepared_sha256:
            raise ValueError("prepared contract differs from independent pin")
        prepared = rehearsal.strict_json(prepared_bytes)
        cfg = rehearsal.validate_config(prepared["config"])
        if (prepared["contract_sha256"] != rehearsal.digest(cfg)
                or prepared["live_execution_authorized"] is not False
                or prepared["telescope_access_authorized"] is not False
                or prepared["activation_gates"] != dict.fromkeys(rehearsal.GATES, False)):
            raise ValueError("inactive preparation binding changed")
        if (type(journal) is not rehearsal.FixtureAttemptJournal
                or type(journal.provider) is not JournaledConnectorFixture
                or journal.grant["contract_sha256"] != prepared["contract_sha256"]):
            raise ValueError("journal/model binding changed")
        model = prepared["model_genesis"]
        envelope.validate_resource_ledger(model, prepared["model_genesis_sha256"])
        if model["reservations"]:
            raise ValueError("planned model genesis is not empty")
        if type(reply_allowance) is not int or reply_allowance != 65536:
            raise ValueError("fixed 64 KiB per fixture response reservation required")
        self.journal, self.reply_allowance = journal, reply_allowance
        self._location_json = envelope.canonical(cfg["location"])
        self._spec_sha = expected_prepared_sha256
        self._genesis = prepared["model_genesis_sha256"]
        self._resource, self._inventory = model["resource_contract_sha256"], model["source_inventory_sha256"]
        self._base = "/repos/"+self.location["repository"]+"/git/"
        self._ref = "heads/"+quote(self.location["branch"], safe="")
        self._parts = self.location["path"].split("/")
        self._lock = threading.Lock()
        self.stopped = False
        self.events, self.receipts, self.typed_replies = [], [], []
        self._candidate = None

    def _request(self, method, suffix, body=None):
        repo = self.location["repository"]
        if method == "GET" and (suffix == "ref/"+self._ref or any(
                suffix.startswith(prefix) and len(suffix[len(prefix):]) == 40
                for prefix in ("commits/", "trees/", "blobs/"))):
            op, tool = "read", "github_fetch"
            args = {"url": "https://api.github.com"+self._base+suffix}
        elif method == "POST" and suffix == "trees":
            op, tool = "create_tree", "github_create_tree"
            args = {"repository_full_name": repo, "base_tree_sha": body["base_tree"],
                    "tree_elements": body["tree"]}
        elif method == "POST" and suffix == "commits":
            if len(body["parents"]) != 1:
                raise ValueError("one explicit commit parent required")
            op, tool = "create_commit", "github_create_commit"
            args = {"repository_full_name": repo, "parent_sha": body["parents"][0],
                    "tree_sha": body["tree"], "message": body["message"]}
        elif method == "PATCH" and suffix == "refs/"+self._ref and body.get("force") is False:
            op, tool = "update_ref", "github_update_ref"
            args = {"repository_full_name": repo, "branch_name": self.location["branch"],
                    "sha": body["sha"], "force": False}
        else:
            raise ValueError("request outside pinned connector operation map")
        request = {"tool": tool, "arguments": args}
        if op == "update_ref":
            request["force"] = False  # the frozen journal requires this guard too
        raw = self.journal.call(op, request,
                                reserve_reply_bytes=self.reply_allowance)
        self._calls += 1
        self._bytes += len(raw.encode())
        try:
            reply = decode_reply(op, raw)
        except Exception as error:
            self.events.append({"event": "typed_reply_veto", "operation": op,
                                "reason": str(error), "http_status": None})
            raise
        self.typed_replies.append({"operation": op, "kind": reply.kind,
            "http_status": None, "api_version": None, "internal_attempts": None})
        return reply.value

    def _commit(self, sha):
        gitcore.git_sha(sha)
        value = self._request("GET", "commits/"+sha)
        if value.get("sha") != sha or type(value.get("message")) is not str:
            raise ValueError("commit identity/message changed")
        return {"sha": sha, "tree": gitcore.git_sha(value["tree"]["sha"]),
            "parents": [gitcore.git_sha(p["sha"]) for p in value["parents"]],
            "message": value["message"]}

    def publish(self, expected_revision, expected_sha256, document):
        with self._lock:
            self._start("typed_model_publish")
            try:
                if self.journal.grant["phase"] not in ("normal_append", "lost_reply_append"):
                    raise ValueError("this model publisher only implements the two append phases")
                if (expected_revision != self.journal.grant["expected_head"]
                        or expected_sha256 != self.journal.grant["expected_model_sha256"]):
                    raise ValueError("publication differs from pre-bound owner checkpoint")
                gitcore.git_sha(expected_revision)
                envelope.sha(expected_sha256, "caller-held model digest")
                after = rehearsal.strict_json(envelope.canonical(document))
                self._validate_document(after)
                before, commit, inventories, _ = self._checkpoint(self._ref_head())
                if before.revision != expected_revision or before.sha256 != expected_sha256:
                    raise ValueError("caller-held model checkpoint is stale")
                validate_transition(before.document, after, expected_sha256)
                payload = (envelope.canonical(after)+"\n").encode()
                if len(payload) > gitcore.LIMITS["max_ledger_bytes"]:
                    raise ValueError("candidate model too large")
                expected_blob = gitcore.blob_sha(payload)
                attempt_id = self.journal.grant["attempt_id"]
                message = "Offline radio rehearsal model; phase " + self.journal.grant["phase"] + "; attempt " + attempt_id
                tree = self._request("POST", "trees", {"base_tree": commit["tree"], "tree": [
                    {"path": self.location["path"], "mode": "100644", "type": "blob", "content": payload.decode()}]})
                tree_sha = gitcore.git_sha(tree["sha"])
                self._verify_only_ledger_changed(inventories, tree_sha, expected_blob)
                made = self._request("POST", "commits", {"tree": tree_sha,
                    "parents": [expected_revision], "message": message})
                self._candidate = gitcore.git_sha(made["sha"])
                candidate = self._commit(self._candidate)
                if (candidate["tree"] != tree_sha or candidate["parents"] != [expected_revision]
                        or candidate["message"] != message):
                    raise ValueError("candidate tree/parent/unique-attempt message changed")
                if self._ref_head() != expected_revision:
                    raise ValueError("branch advanced before update")
                ack = self._request("PATCH", "refs/"+self._ref,
                                    {"sha": self._candidate, "force": False})
                if ack != {"success": True}:
                    raise ValueError("typed acknowledgement changed")
                landed, _, _, landed_blob = self._checkpoint(self._candidate)
                if landed_blob != expected_blob or landed.sha256 != envelope.ledger_digest(after):
                    raise ValueError("immutable committed model differs")
                ancestry = self._confirm_ancestry(self._candidate, expected_blob, landed.sha256)
                receipt = {"schema": "radio-typed-connector-model-receipt-v1", "attempt_id": attempt_id,
                    "location": self.location, "prepared_contract_file_sha256": self._spec_sha,
                    "parent_commit": expected_revision, "commit": self._candidate,
                    "ledger_sha256": landed.sha256, "blob_sha": expected_blob, "tree_sha": tree_sha,
                    **ancestry, "tool_calls_in_publish": self._calls,
                    "tool_result_json_utf8_bytes_in_publish": self._bytes,
                    "http_status": None, "api_version": None, "internal_attempts": None,
                    "qualification": "OFFLINE_CONNECTOR_AND_INDEPENDENT_ADMISSION_FIXTURES_ONLY",
                    "network_budget_issued": False, "spectral_access_authorized": False}
                self.receipts.append(receipt)
                self.events.append({"event": "confirmed", "receipt": receipt})
                return receipt
            except Exception as error:
                raise self._stop(error) from error
