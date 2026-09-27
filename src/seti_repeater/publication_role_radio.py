"""Pinned, append-only v2 publication protocol; no remote activation or budget.

LocalRoleStore is the atomic CAS primitive. This boundary additionally binds
its identity and prohibits resetting/rebinding a self-consistent document.
Future remote backends must enforce the same transition atomically and meet
the separately frozen GitHub-store obligations before being usable.
"""
from dataclasses import dataclass
import json

from . import execution_envelope_radio as envelope

SCHEMA = "radio-role-publication-protocol-v2"


def validate_transition(before, after, expected_parent_sha256):
    envelope.validate_resource_ledger(before, expected_parent_sha256)
    envelope.validate_resource_ledger(after, envelope.ledger_digest(after))
    if ({**before, "reservations": []} != {**after, "reservations": []}
            or len(after["reservations"]) != len(before["reservations"]) + 1
            or after["reservations"][:-1] != before["reservations"]
            or after["reservations"][-1]["prior_ledger_sha256"] != expected_parent_sha256):
        raise ValueError("publication must append exactly one reservation without rebinding")


@dataclass(frozen=True)
class StoreProtocol:
    record_json: str
    identity: str

    @property
    def record(self):
        return json.loads(self.record_json)

    def validate(self):
        value = self.record
        if (envelope.ledger_digest(value) != self.identity or set(value) != {
                "schema", "location", "resource_contract_sha256",
                "source_inventory_sha256", "genesis_sha256", "mode"}
                or value["schema"] != SCHEMA or value["mode"] != "LOCAL_QUALIFICATION_ONLY"
                or set(value["location"]) != {"kind", "path"}
                or value["location"]["kind"] != "local-v2-qualification-only"
                or not value["location"]["path"].startswith("/")):
            raise ValueError("publication store protocol changed")
        for key in ("resource_contract_sha256", "source_inventory_sha256", "genesis_sha256"):
            envelope.sha(value[key], key)

    def validate_checkpoint(self, checkpoint):
        self.validate()
        value = self.record
        if (checkpoint.location != value["location"]
                or not isinstance(checkpoint.revision, str) or not checkpoint.revision.isdigit()):
            raise ValueError("publication store location/revision changed")
        document = checkpoint.document
        envelope.validate_resource_ledger(document, envelope.ledger_digest(document))
        if (document["resource_contract_sha256"] != value["resource_contract_sha256"]
                or document["source_inventory_sha256"] != value["source_inventory_sha256"]
                or envelope.ledger_digest({**document, "reservations": []}) != value["genesis_sha256"]
                or int(checkpoint.revision) != len(document["reservations"])):
            raise ValueError("publication namespace or local revision ancestry changed")


def bind_local_protocol(location, resource, genesis):
    resource.validate()
    if genesis != resource.genesis():
        raise ValueError("store genesis differs from frozen resource contract")
    record = {"schema": SCHEMA, "location": location,
        "resource_contract_sha256": resource.identity,
        "source_inventory_sha256": resource.source_inventory_sha256,
        "genesis_sha256": envelope.ledger_digest(genesis),
        "mode": "LOCAL_QUALIFICATION_ONLY"}
    protocol = StoreProtocol(envelope.canonical(record), envelope.ledger_digest(record))
    protocol.validate()
    return protocol


class BoundRoleStore:
    """Only this guarded store is allowed at the v2 reservation boundary.

    The backend is a trusted CAS primitive, not an adversarial filesystem.
    Rollback by an external privileged writer is outside this local proof;
    an independent caller-held revision/digest remains required on every call.
    """
    def __init__(self, backend, protocol):
        if type(protocol) is not StoreProtocol:
            raise ValueError("typed publication store protocol required")
        protocol.validate()
        self.backend, self.protocol = backend, protocol

    def read(self):
        checkpoint = self.backend.read()
        self.protocol.validate_checkpoint(checkpoint)
        return checkpoint

    def publish(self, expected_revision, expected_sha256, document):
        before = self.read()
        if (before.revision != expected_revision
                or envelope.ledger_digest(before.document) != expected_sha256):
            raise ValueError("publication checkpoint changed before CAS")
        validate_transition(before.document, document, expected_sha256)
        # The backend's locked compare-and-swap is the linearization point.
        # Exceptions and uncertain replies are propagated; never retry/refund.
        self.backend.publish(expected_revision, expected_sha256, document)
        after = self.read()
        if (after.revision != str(int(expected_revision) + 1)
                or envelope.ledger_digest(after.document) != envelope.ledger_digest(document)):
            raise ValueError("publication confirmation ambiguous; quota may be spent")
