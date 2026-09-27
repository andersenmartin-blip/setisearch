"""An isolated REST-shaped service backed by real local Git objects.

No remote is configured. Git itself constructs trees/commits and checks ancestry,
so the fixture does not implement the client's tree or ledger validation logic.
"""
from __future__ import annotations

import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from urllib.parse import unquote

from seti_repeater import execution_envelope_radio as envelope
from seti_repeater.github_role_radio import FIXTURE_KIND

ROOT = Path(__file__).resolve().parents[1]
SPEC = "results_radio_codec_publication_2026-09-27/publication_store_spec.json"


def resource():
    return envelope.build_resource_contract(json.loads(
        (ROOT / "config/radio_execution_envelope_20260927.json").read_text()))


class GitServiceFixture:
    kind = FIXTURE_KIND

    def __init__(self, directory, document=None, include_ledger=True):
        self.directory = Path(directory)
        self.location = json.loads((ROOT / SPEC).read_text())["location"]
        self.ref = "refs/heads/" + self.location["branch"]
        self.base = "/repos/" + self.location["repository"] + "/git/"
        self.lock = threading.RLock()
        self.before = self.after = None
        self.calls = []
        self.env = dict(os.environ, GIT_AUTHOR_NAME="SETI isolated fixture",
            GIT_AUTHOR_EMAIL="fixture@example.invalid", GIT_COMMITTER_NAME="SETI isolated fixture",
            GIT_COMMITTER_EMAIL="fixture@example.invalid", GIT_AUTHOR_DATE="2026-09-27T12:00:00Z",
            GIT_COMMITTER_DATE="2026-09-27T12:00:00Z")
        subprocess.run(["git", "init", "--bare", "--quiet", str(self.directory)], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)
        empty = self.git("mktree", payload=b"").decode().strip()
        self.empty_tree = empty
        entries = [{"path": "README.md", "mode": "100644", "content": "Isolated service fixture.\n"},
                   {"path": "notes/keep.txt", "mode": "100644", "content": "Preserve this unrelated file.\n"}]
        if include_ledger:
            entries.append({"path": self.location["path"], "mode": "100644",
                "content": envelope.canonical(resource().genesis() if document is None else document)+"\n"})
        self.initial = self.commit(self.make_tree(empty, entries), [], "fixture genesis")
        self.git("update-ref", self.ref, self.initial)

    def git(self, *args, payload=None, env=None, check=True):
        result = subprocess.run(["git", "--git-dir="+str(self.directory), *args],
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=self.env if env is None else env, check=False)
        if check and result.returncode:
            raise RuntimeError(result.stderr.decode())
        return result.stdout if check else result

    @property
    def head(self):
        return self.git("rev-parse", self.ref).decode().strip()

    def make_tree(self, base, entries):
        with tempfile.TemporaryDirectory(dir=self.directory) as td:
            env = dict(self.env, GIT_INDEX_FILE=str(Path(td)/"index"))
            self.git("read-tree", base, env=env)
            for entry in entries:
                if "content" in entry:
                    sha = self.git("hash-object", "-w", "--stdin", payload=entry["content"].encode()).decode().strip()
                else:
                    sha = entry["sha"]
                self.git("update-index", "--add", "--cacheinfo", entry["mode"], sha, entry["path"], env=env)
            return self.git("write-tree", env=env).decode().strip()

    def commit(self, tree, parents, message):
        args = ["commit-tree", tree]
        for parent in parents:
            args += ["-p", parent]
        return self.git(*args, payload=(message+"\n").encode()).decode().strip()

    def commit_json(self, sha):
        raw = self.git("cat-file", "-p", sha).decode()
        header, message = raw.split("\n\n", 1)
        lines = header.splitlines()
        return {"sha": sha, "tree": {"sha": next(x[5:] for x in lines if x.startswith("tree "))},
            "parents": [{"sha": x[7:]} for x in lines if x.startswith("parent ")], "message": message.rstrip()}

    def external_commit(self, *, entries=None, parents=None, message="unrelated external change", update=True):
        with self.lock:
            parents = [self.head] if parents is None else parents
            tree = self.commit_json(parents[0])["tree"]["sha"] if parents else self.empty_tree
            if entries:
                tree = self.make_tree(tree, entries)
            sha = self.commit(tree, parents, message)
            if update:
                self.git("update-ref", self.ref, sha)
            return sha

    def ledger(self, revision=None):
        return json.loads(self.git("show", (revision or self.head)+":"+self.location["path"]))

    def request(self, method, path, body=None):
        with self.lock:
            entry = {"sequence": len(self.calls)+1, "method": method, "path": path,
                     "body": copy.deepcopy(body)}
            self.calls.append(entry)
        try:
            if self.before:
                override = self.before(method, path, body)
            else:
                override = None
            with self.lock:
                status, response = override if override is not None else self._dispatch(method, path, body)
            if self.after:
                replacement = self.after(method, path, body, status, response)
                if replacement is not None:
                    status, response = replacement
            entry.update(status=status, response=copy.deepcopy(response))
            return status, response
        except Exception as error:
            entry.update(raised=type(error).__name__, reason=str(error), head_after_error=self.head)
            raise

    def _dispatch(self, method, path, body):
        if not path.startswith(self.base):
            return 404, {"message": "wrong repository"}
        suffix = path[len(self.base):]
        if method == "GET" and suffix.startswith("ref/"):
            ref = "refs/"+unquote(suffix[4:])
            if ref != self.ref:
                return 404, {"message": "wrong ref"}
            return 200, {"ref": ref, "object": {"type": "commit", "sha": self.head}}
        if method == "GET" and suffix.startswith("commits/"):
            return 200, self.commit_json(suffix[8:])
        if method == "GET" and suffix.startswith("trees/"):
            sha = suffix[6:]
            entries = []
            for item in self.git("ls-tree", "-z", sha).split(b"\0"):
                if not item: continue
                meta, name = item.split(b"\t", 1)
                mode, kind, oid = meta.decode().split()
                entries.append({"path": name.decode(), "mode": mode, "type": kind, "sha": oid})
            return 200, {"sha": sha, "truncated": False, "tree": entries}
        if method == "GET" and suffix.startswith("blobs/"):
            sha = suffix[6:]
            data = self.git("cat-file", "blob", sha)
            return 200, {"sha": sha, "encoding": "base64", "size": len(data),
                         "content": base64.encodebytes(data).decode()}
        if method == "POST" and suffix == "trees":
            return 201, {"sha": self.make_tree(body["base_tree"], body["tree"])}
        if method == "POST" and suffix == "commits":
            return 201, {"sha": self.commit(body["tree"], body["parents"], body["message"])}
        if method == "PATCH" and suffix.startswith("refs/"):
            if "refs/"+unquote(suffix[5:]) != self.ref or body.get("force") is not False:
                return 422, {"message": "wrong ref or force flag"}
            current, target = self.head, body["sha"]
            # Git, not the client algorithm, decides the fast-forward condition.
            result = self.git("merge-base", "--is-ancestor", current, target, check=False)
            if result.returncode != 0:
                return 422, {"message": "not a fast-forward"}
            self.git("update-ref", self.ref, target, current)
            return 200, {"ref": self.ref, "object": {"type": "commit", "sha": target}}
        return 404, {"message": "unsupported fixture endpoint"}

    def evidence(self):
        objects = []
        inventory = self.git("cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)")
        for row in inventory.decode().splitlines():
            sha, kind = row.split()
            data = self.git("cat-file", kind, sha)
            objects.append({"sha": sha, "type": kind, "content_base64": base64.b64encode(data).decode()})
        return {"kind": self.kind, "initial_head": self.initial, "final_head": self.head,
                "calls": self.calls, "git_objects": objects,
                "git_remotes": self.git("remote").decode().splitlines(), "real_network_requests": 0}
