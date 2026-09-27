"""Independent local admission MODEL and connector envelopes over bare Git.

The SQLite authority is a supplied trust primitive, NOT an implementation via
GitHub. Its setup/grants are explicitly fixture assumptions. The bootstrap
counterexample demonstrates why this dependency cannot be hidden in a live run.
"""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
import threading
import uuid

from radio_github_v2_fixture import GitServiceFixture
from seti_repeater import rehearsal_contract_radio as r


@dataclass(eq=False)
class OwnerHandle:
    grant: dict
    token: object


class IndependentAdmissionFixture:
    kind = "independent-admission-authority-fixture"

    def __init__(self, path, cfg):
        self.path, self.cfg = Path(path), r.validate_config(cfg)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock, self.active = threading.RLock(), {}
        with self.connect() as con:
            con.execute("CREATE TABLE IF NOT EXISTS identity (contract TEXT PRIMARY KEY)")
            con.execute("CREATE TABLE IF NOT EXISTS phases (phase TEXT PRIMARY KEY, grant_json TEXT, state TEXT, calls INTEGER, reserved_bytes INTEGER)")
            row = con.execute("SELECT contract FROM identity").fetchall()
            if not row:
                con.execute("INSERT INTO identity VALUES (?)", (r.digest(cfg),))
            elif row != [(r.digest(cfg),)]:
                raise ValueError("independent fixture authority namespace changed")

    def connect(self):
        con = sqlite3.connect(self.path, timeout=5)
        con.execute("PRAGMA synchronous=FULL")
        return con

    def claim(self, phase, expected_head, expected_model_sha256):
        grant = r.fixture_grant(self.cfg, phase, expected_head, expected_model_sha256)
        with self.lock, self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute("SELECT phase,state FROM phases").fetchall()
            seen = dict(rows)
            if phase in seen:
                raise ValueError("phase already charged; no new owner or refund")
            prior = r.PHASES[:r.PHASES.index(phase)]
            if set(seen) != set(prior) or any(state == "running" for state in seen.values()):
                raise ValueError("phase ownership out of order or prior owner still active")
            if any(seen.get(p) != "closed" for p in prior if p not in ("lost_reply_append", "readonly_recovery")):
                raise ValueError("earlier prerequisite did not complete")
            con.execute("INSERT INTO phases VALUES (?,?,?,?,?)",
                        (phase, r.encode(grant).decode(), "running", 0, 0))
        owner = OwnerHandle(deepcopy(grant), object())
        self.active[owner.token] = owner
        return owner

    def _owner(self, owner):
        if type(owner) is not OwnerHandle or self.active.get(owner.token) is not owner:
            raise ValueError("no active non-restorable owner channel")

    def admit(self, owner, operation, request):
        with self.lock, self.connect() as con:
            self._owner(owner)
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT grant_json,state,calls,reserved_bytes FROM phases WHERE phase=?",
                              (owner.grant["phase"],)).fetchone()
            if row is None or row[0] != r.encode(owner.grant).decode() or row[1] != "running":
                raise ValueError("owner does not match irrevocable phase grant")
            caps = owner.grant["reserved_limits"]
            if (row[2]+1 > caps["max_tool_calls"] or row[3]+65536 > caps["max_response_utf8_bytes"]
                    or (owner.grant["phase"] == "readonly_recovery" and operation != "read")):
                raise ValueError("independent admission refused")
            con.execute("UPDATE phases SET calls=calls+1,reserved_bytes=reserved_bytes+65536 WHERE phase=?",
                        (owner.grant["phase"],))
        # The SQLite transaction has committed before the fixture connector runs.

    def finish(self, owner, state="closed"):
        if state not in ("closed", "uncertain"):
            raise ValueError("invalid irreversible finish state")
        with self.lock, self.connect() as con:
            self._owner(owner)
            con.execute("UPDATE phases SET state=? WHERE phase=?", (state, owner.grant["phase"]))
        self.active.pop(owner.token)

    def abandon_after_client_loss(self, phase):
        """SERVER-SIDE fixture action, not a free GitHub admin operation."""
        with self.lock, self.connect() as con:
            changed = con.execute("UPDATE phases SET state='uncertain' WHERE phase=? AND state='running'", (phase,)).rowcount
            if changed != 1:
                raise ValueError("no running owner to abandon")
        self.active = {key: value for key, value in self.active.items() if value.grant["phase"] != phase}

    def snapshot(self):
        with self.connect() as con:
            values = con.execute("SELECT phase,grant_json,state,calls,reserved_bytes FROM phases").fetchall()
        rows = [{"phase": phase, "grant": json.loads(grant), "state": state,
                 "calls_debited": calls, "reserved_reply_bytes_debited": size}
                for phase, grant, state, calls, size in values]
        rows.sort(key=lambda row: r.PHASES.index(row["phase"]))
        charged = {key: sum(row["grant"]["reserved_limits"][key] for row in rows) for key in r.LIMIT_KEYS}
        return {"kind": self.kind, "supplied_before_any_connector_call": True, "phases": rows,
            "charged_whole_phase_limits": charged,
            "remaining_whole_phase_limits": {key: self.cfg["total_limits"][key]-charged[key] for key in r.LIMIT_KEYS},
            "live_remote_authority_implemented": False, "telescope_access_authorized": False}


class ConnectorGitFixture(GitServiceFixture):
    kind = "isolated-connector-envelope-fixture"

    def __init__(self, directory, prepared):
        super().__init__(directory, include_ledger=False)
        self.location = deepcopy(prepared["config"]["location"])
        # The bare-Git model starts with its reference ledger already present.
        # This is fixture setup, explicitly NOT qualification of live bootstrap.
        self.initial = self.external_commit(entries=[{"path": self.location["path"], "mode": "100644",
            "content": r.encode(prepared["model_genesis"]).decode()+"\n"}], message="offline model genesis")
        self.tool_calls = []
        self.tool_after = None

    def invoke(self, tool, args):
        entry = {"tool": tool, "arguments": deepcopy(args)}
        self.tool_calls.append(entry)
        try:
            if tool == "github_fetch":
                method, path, body = "GET", args["url"].removeprefix("https://api.github.com"), None
            else:
                if args["repository_full_name"] != self.location["repository"]:
                    raise ValueError("wrong fixture repository")
                if tool == "github_create_tree":
                    method, path = "POST", self.base+"trees"
                    body = {"base_tree": args["base_tree_sha"], "tree": args["tree_elements"]}
                elif tool == "github_create_commit":
                    method, path = "POST", self.base+"commits"
                    body = {"parents": [args["parent_sha"]], "tree": args["tree_sha"], "message": args["message"]}
                elif tool == "github_update_ref":
                    if args["branch_name"] != self.location["branch"]:
                        raise ValueError("wrong fixture branch")
                    method, path, body = "PATCH", self.base+"refs/heads/"+args["branch_name"], {"sha": args["sha"], "force": args["force"]}
                else:
                    raise ValueError("unsupported connector fixture tool")
            status, payload = self.request(method, path, body)
            if status not in (200, 201):
                result = {"isError": True, "structuredContent": {"error": "fixture provider failure"},
                          "content": [{"type": "text", "text": "Fixture operation failed"}]}
            elif method == "GET":
                result = {"isError": False, "structuredContent": {"content": r.encode(payload).decode()},
                          "content": [{"type": "text", "text": "Fixture object returned"}]}
            else:
                result = {"isError": False, "structuredContent": {"success": True} if method == "PATCH" else {"sha": payload["sha"]},
                          "content": [{"type": "text", "text": "Fixture operation completed"}]}
            if self.tool_after:
                result = self.tool_after(tool, args, result)
            entry["result"] = deepcopy(result)
            return result
        except BaseException as error:
            entry.update(error_class=type(error).__name__, reason=str(error), head_after_error=self.head)
            raise

    def evidence(self):
        return {**super().evidence(), "tool_calls": self.tool_calls,
                "bootstrap_assumption": "independent fixture authority and model genesis pre-exist"}


def bootstrap_counterexample(service, call_limit):
    """Finite trace: crash after the first GET, before any durable Git write.

    Every restart has the identical client/visible branch state. Permitting the same
    bootstrap step again spends one more call with no ledger evidence. This is
    an actual trace through the bare-Git connector FIXTURE, not live traffic or
    a claim about every possible external admission runtime.
    """
    r.positive_int(call_limit)
    initial = service.head
    events = []
    for i in range(call_limit+1):
        # Deliberately unsafe baseline, bypassing both protective admission and
        # journal: the missing primitive is precisely what is being exposed.
        response = service.invoke("github_fetch", {"url": "https://api.github.com"+service.base+"ref/heads/"+service.location["branch"]})
        if service.head != initial:
            raise ValueError("negative baseline unexpectedly changed branch state")
        events.append({"worker": i, "client_state": "fresh", "remote_grants": 0,
            "tool_call": "GET current branch", "durable_remote_change": False,
            "crash_before_grant_write": True, "cumulative_calls": i+1,
            "response_sha256": r.digest(response)})
    return {"policy": "allow first GET with empty grant and no independent admission",
        "call_limit": call_limit, "events": events,
        "counterexample_calls": call_limit+1, "remote_grants_after_trace": 0,
        "bound_exceeded": True, "real_connector_calls": 0}
