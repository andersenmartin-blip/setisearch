"""Local persistent CAS store used only for radio reservation engineering checks.

It stands in for a durable revisioned publication service. It is deliberately
marked local-fixture and cannot authorize start_source_session for a telescope.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import uuid
from seti_repeater import acquisition_radio as acquisition


class LocalFixtureStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.location = {"kind": "local-fixture", "store": self.directory.name}

    @classmethod
    def create(cls, directory, document):
        store = cls(directory)
        store.directory.mkdir(parents=True, exist_ok=False)
        (store.directory/"lock").touch(exist_ok=False)
        store._write(document, "0"*40)
        return store

    def _write(self, document, parent):
        data = acquisition.encode(document)
        revision = hashlib.sha1(parent.encode()+data).hexdigest()
        with (self.directory/(revision+".json")).open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        pointer = self.directory/(str(uuid.uuid4())+".tmp")
        with pointer.open("xb") as stream:
            stream.write(acquisition.encode({"revision": revision, "ledger_sha256": acquisition.digest(document)}))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pointer, self.directory/"current.json")
        acquisition._sync_directory(self.directory)

    def read(self):
        pointer = json.loads((self.directory/"current.json").read_text())
        document = json.loads((self.directory/(pointer["revision"]+".json")).read_text())
        acquisition.validate_ledger(document, pointer["ledger_sha256"])
        return acquisition.Checkpoint(document, pointer["revision"], self.location)

    def publish(self, expected_revision, expected_sha256, document):
        with (self.directory/"lock").open("rb") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            before = self.read()
            if before.revision != expected_revision or before.sha256 != expected_sha256:
                raise ValueError("compare-and-swap conflict")
            acquisition.validate_ledger(document, acquisition.digest(document))
            if (document["reservations"][:-1] != before.document["reservations"]
                    or len(document["reservations"]) != len(before.document["reservations"])+1
                    or {k: v for k, v in document.items() if k != "reservations"}
                    != {k: v for k, v in before.document.items() if k != "reservations"}):
                raise ValueError("publication is not one append-only reservation")
            self._write(document, before.revision)
