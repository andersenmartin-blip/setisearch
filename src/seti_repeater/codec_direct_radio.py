"""Local codec receipts -> direct-native inputs, with no telescope constructor.

The independently retained manifest binds the complete six-scan fixture, exact
source receipts, normalization origins, clock, runtime and direct factor bank.
Only local fixtures at .invalid URLs may cross this boundary. The resulting
SyntheticSource retains its codec receipt ancestry; it is never telescope
provenance or a calibration-transfer certificate.
"""
from dataclasses import dataclass
import json
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

from . import factors_radio as direct
from . import search_v0p6 as core
from . import source_m43h as rows
from . import source_radio as codec
from . import transfer_m43g as native

SCHEMA = "radio-local-codec-direct-binding-v1"
CLOCK_TOLERANCE_SECONDS = 1e-6


def header_clock(scopes):
    """Fixture clock only: relative UTC seconds from retained MJD headers."""
    headers = [scope["definition"]["expected_header"] for scope in scopes]
    origin = headers[0]["tstart_mjd"]
    anchor = headers[0]["tsamp_s"] / 2
    result = []
    for header in headers:
        start = (header["tstart_mjd"] - origin) * 86400 - anchor
        dt = header["tsamp_s"]
        result.extend([[start + i*dt, start + (i+.5)*dt, start + (i+1)*dt]
                       for i in range(16)])
    return np.asarray(result, dtype="<f8")


@dataclass(frozen=True)
class FixtureBinding:
    manifest_json: str
    identity: str

    @property
    def record(self):
        return json.loads(self.manifest_json)

    def validate(self, bank):
        direct.validate(bank)
        value = self.record
        if (native.digest(value) != self.identity or set(value) != {
                "schema", "domain", "window", "direct_factor_bank_sha256",
                "source_contract_sha256", "runtime", "scans"}
                or value["schema"] != SCHEMA or value["domain"] != "local-fixture"
                or value["direct_factor_bank_sha256"] != bank.identity
                or not isinstance(value["window"], str) or not value["window"]):
            raise ValueError("local codec/direct binding changed")
        core._frozen_sha256(value["source_contract_sha256"], "fixture source contract")
        if value["runtime"] != codec.runtime():
            raise ValueError("local codec/direct runtime changed")
        entries = value["scans"]
        if (len(entries) != 6
                or [entry["label"] for entry in entries] != list(direct.LABELS)):
            raise ValueError("exact ordered six-scan fixture inventory required")
        scopes = []
        for index, entry in enumerate(entries):
            if set(entry) != {"label", "scope", "receipt_sha256"}:
                raise ValueError("invalid local codec receipt entry")
            core._frozen_sha256(entry["receipt_sha256"], "trusted codec receipt")
            scope = entry["scope"]
            definition = scope["definition"]
            parsed = urlparse(definition["url"])
            if (scope["kind"] != "local-fixture"
                    or parsed.scheme != "https" or not parsed.hostname
                    or not parsed.hostname.endswith(".invalid")
                    or parsed.username or parsed.password or parsed.query or parsed.fragment
                    or definition["label"] != entry["label"]
                    or definition["role"] != ("on" if index % 2 == 0 else "off")
                    or definition["expected_header"]["dataset_shape"][0] != 16
                    or scope["window"] != value["window"]
                    or scope["contract_sha256"] != value["source_contract_sha256"]):
                raise ValueError("only exact local fixture scope is allowed")
            rebuilt = rows.make_scope(definition, scope["window"],
                scope["archive_interval"], scope["contract_sha256"], "local-fixture")
            if scope != rebuilt:
                raise ValueError("noncanonical fixture normalization/geometry scope")
            if native.memory_bound(16, scope["geometry"]["channel_count"]) > native.CONTRACT["memory_cap_bytes"]:
                raise core.V0P6CapacityError("codec/direct input memory cap exceeded")
            scopes.append(scope)
        if len({entry["scope"]["definition"]["url"] for entry in entries}) != 6:
            raise ValueError("fixture sources must be distinct")
        if len({entry["receipt_sha256"] for entry in entries}) != 6:
            raise ValueError("fixture receipts must be distinct")
        if any(scope["geometry"] != scopes[0]["geometry"]
               or scope["archive_interval"] != scopes[0]["archive_interval"]
               for scope in scopes[1:]):
            raise ValueError("fixture cadence geometry or interval differs")
        inputs = json.loads(bank.inputs_json)
        if inputs["provenance"]["source_contract_sha256"] != value["source_contract_sha256"]:
            raise ValueError("direct bank belongs to a different source contract")
        clock = header_clock(scopes)
        if not np.allclose(clock, inputs["clock_seconds"], rtol=0,
                           atol=CLOCK_TOLERANCE_SECONDS):
            raise ValueError("direct bank clock differs from codec scan headers")


def bind(manifest, trusted_manifest_sha256, bank):
    """Never infer the trusted hash from a receipt directory being opened."""
    core._frozen_sha256(trusted_manifest_sha256, "trusted fixture binding")
    result = FixtureBinding(core.canonical_json_bytes(manifest).decode(),
                            trusted_manifest_sha256)
    result.validate(bank)
    return result


def adapt_fixture(directory, binding, bank, label):
    """Rehydrate, verify and copy native rows into immutable direct inputs."""
    if type(binding) is not FixtureBinding:
        raise ValueError("typed local codec/direct binding required")
    binding.validate(bank)
    entry = next((s for s in binding.record["scans"] if s["label"] == label), None)
    if entry is None:
        raise ValueError("unknown local fixture scan")
    directory = Path(directory)
    # Refuse a wrong kind, identity, scan or window before reading any NPY row.
    receipt = rows.verify(json.loads((directory / "source.json").read_text()))
    if (receipt["receipt_sha256"] != entry["receipt_sha256"]
            or receipt["scope"] != entry["scope"]
            or receipt["complete"] is not True):
        raise ValueError("codec receipt differs from trusted fixture binding")
    transport = receipt["transport"]
    definition = entry["scope"]["definition"]
    expected_remote = {"url": definition["url"],
        "size": definition["expected_remote_size_bytes"],
        "etag": definition["expected_etag"]}
    if (transport.get("kind") != "local-HDF5-over-simulated-HTTP"
            or transport.get("hdf5_runtime") != binding.record["runtime"]
            or transport.get("identity") != expected_remote):
        raise ValueError("local codec transport ancestry changed")
    rows.verify_transport_checkpoint(transport["checkpoint"], expected_remote)
    receipt = rows.rehydrate(directory, entry["receipt_sha256"],
                              required_kind="local-fixture")

    def reader(row):
        # Hash the actual owned bytes used, closing the rehydrate/read race.
        value = np.load(directory / f"row{row:02d}.native.npy", allow_pickle=False)
        if rows.array_hash(value) != receipt["rows"][row]["native_sha256"]:
            raise ValueError("native row changed after receipt verification")
        return value

    geometry = core.NativeFrequencyGeometry(**entry["scope"]["geometry"])
    source = native.normalize_synthetic_rows(reader, geometry, 16,
        input_orientation="descending", scope={
            "kind": "synthetic", "input_domain": "local-codec-fixture",
            "scan": label, "window": binding.record["window"],
            "direct_factor_bank_sha256": bank.identity,
            "codec_direct_binding_sha256": binding.identity,
            "codec_receipt_sha256": entry["receipt_sha256"],
            "codec_scope_sha256": rows.digest(entry["scope"]),
            "telescope_provenance": False,
            "scientific_candidate_selection_authorized": False})
    for row, expected in enumerate(receipt["rows"]):
        if native.array_hash(source.values[row]) != expected["normalized_sha256"]:
            raise ValueError("codec/direct normalization differs")
    native.validate_source(source)
    return source


def fixture_run(context, binding, directories):
    """The cadence entry point binds all six inputs to one downstream window.

    Capacity, inventory and context/window checks precede any native row read.
    Individual adapt_fixture results are diagnostic objects; callers must not
    assemble mixed manifests into a claimed receipt-qualified cadence.
    """
    from . import pipeline_direct_radio as pipeline
    if type(context) is not pipeline.Context or type(binding) is not FixtureBinding:
        raise ValueError("typed direct context and fixture binding required")
    context.validate()
    bank = context.factor_contract.factors
    binding.validate(bank)
    if (context.window != binding.record["window"]
            or set(directories) != set(direct.LABELS)):
        raise ValueError("codec/direct cadence window or directory inventory differs")
    n = binding.record["scans"][0]["scope"]["geometry"]["channel_count"]
    if any(scan["expected_header"]["dataset_shape"] != [16, 1, n]
           for scan in context.scans):
        raise ValueError("codec/direct context geometry differs")
    if pipeline.legacy.modelled_array_bytes(context, 16, n) > context.memory_limit_bytes:
        raise core.V0P6CapacityError("codec/direct cadence memory cap exceeded before rows")
    sources = {label: adapt_fixture(directories[label], binding, bank, label)
               for label in direct.LABELS}
    return pipeline.NativeRun(context, sources)
