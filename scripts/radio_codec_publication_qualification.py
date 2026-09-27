"""Run only new codec/publication tests and retain their complete evidence."""
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from radio_codec_publication_fixture import configuration
from seti_repeater import execution_envelope_radio as envelope
from seti_repeater import source_radio
from test_radio_codec_publication import CodecDirectTests, PublicationTests

OUT = ROOT / "results_radio_codec_publication_2026-09-27"
OWN_PATHS = [
    "src/seti_repeater/codec_direct_radio.py",
    "src/seti_repeater/publication_role_radio.py",
    "scripts/radio_codec_publication_fixture.py",
    "scripts/radio_codec_publication_qualification.py",
    "tests/test_radio_codec_publication.py",
    "config/radio_codec_publication_engineering_20260927.json",
    "RADIO_CODEC_PUBLICATION_2026-09-27_PROTOCOL.md",
    "RADIO_CODEC_PUBLICATION_2026-09-27_RESULT.md",
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def publication_spec():
    cfg = json.loads((ROOT / "config/radio_execution_envelope_20260927.json").read_text())
    resource = envelope.build_resource_contract(cfg)
    return {
        "schema": "radio-v2-github-publication-store-spec-v1",
        "status": "FROZEN_NOT_ACTIVATED",
        "location": {"kind": "github", "repository": "andersenmartin-blip/setisearch",
            "branch": "m43-support-qualification",
            "path": "results_radio_hd1461_live_v2/resource_ledger.json"},
        "resource_contract_sha256": resource.identity,
        "source_inventory_sha256": resource.source_inventory_sha256,
        "genesis_sha256": envelope.ledger_digest(resource.genesis()),
        "ledger_encoding": "SHA256 of sorted compact UTF-8 JSON, allow_nan=false, no newline",
        "transition": "exactly one ordered full-role append; same root and exact old prefix",
        "read": "read branch head and tree; read ledger at that exact commit; missing ledger is fatal",
        "publish": [
            "require caller-held expected branch head and ledger SHA256",
            "verify pinned repository/branch/path, resource contract, inventory and genesis",
            "validate full v2 ledger and exact single-append transition",
            "create tree changing only the pinned ledger path from expected head tree",
            "create commit with exactly expected branch head as sole parent",
            "update that branch with force=false; any divergent head refuses publication",
            "read back committed ledger and current branch ancestry, checking exact content",
        ],
        "uncertainty": "stop on any ambiguous outcome; no automatic retry, refund or activation",
        "initialization": "requires a separately published gate-qualified activation; never implicit",
        "backend_boundary": "specification only; remote v2 backend not implemented or qualified here",
        "local_backend": "BoundRoleStore over fsynced LocalRoleStore; independently pinned location",
        "network_budget_issued": False, "telescope_namespace_activated": False,
        "closed_demo_reused_or_reset": False,
    }


def main():
    cfg = configuration()
    OUT.mkdir(exist_ok=True)
    log = io.StringIO()
    suite = unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(CodecDirectTests),
        unittest.defaultTestLoader.loadTestsFromTestCase(PublicationTests)])
    run = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (OUT / "qualification.log").write_text(log.getvalue())
    if not run.wasSuccessful():
        print(log.getvalue())
        raise RuntimeError("codec/publication changed-risk qualification failed")
    # All old artifacts remain byte-identical after the new local tests.
    configuration()
    for name, evidence in CodecDirectTests.evidence.items():
        write(name + "_codec_direct.json", evidence)
    write("publication_local_evidence.json", PublicationTests.evidence)
    spec = publication_spec(); write("publication_store_spec.json", spec)
    old = json.loads((ROOT / "results_radio_execution_envelope_2026-09-27/execution_envelope.json").read_text())
    runtime = {"schema": "radio-codec-publication-runtime-supplement-v1",
        "parent_execution_envelope_sha256": old["execution_envelope_sha256"],
        "python": platform.python_version(), "byteorder": sys.byteorder,
        "system": platform.system(), "machine": platform.machine(),
        **source_radio.runtime(),
        "astropy": importlib.metadata.version("astropy"),
        "pyerfa": importlib.metadata.version("pyerfa"),
        "implementation_sha256": {p: sha(ROOT / p) for p in OWN_PATHS if p.endswith(".py")},
        "scope": "local fixtures; parent runtime/envelope remain immutable"}
    write("runtime_supplement.json", runtime)
    evidence = CodecDirectTests.evidence
    primary_calls = sum(len(t["simulated_calls"]) for e in evidence.values() for t in e["transports"].values())
    primary_bytes = sum(t["input_hdf5_bytes"] for e in evidence.values() for t in e["transports"].values())
    result = {
        "schema": "radio-codec-publication-qualification-v1",
        "status": "LOCAL_CODEC_DIRECT_AND_PUBLICATION_BOUNDARY_PASS",
        "execution_status": "BLOCKED", "new_tests_passed": run.testsRun,
        "source_commit": cfg["source_commit"],
        "parent_execution_envelope_sha256": old["execution_envelope_sha256"],
        "parent_blockers_unchanged": old["blockers"],
        "primary": "neighbor9", "codec_fixture_count": len(evidence),
        "codec_scan_receipts": sum(len(e["codec_receipts"]) for e in evidence.values()),
        "normalized_cells_bit_exact": sum(e["normalized_cells_bit_exact"] for e in evidence.values()),
        "score_cells_bit_exact": sum(e["score_cells_bit_exact"] for e in evidence.values()),
        "independent_synthetic_background_realizations": 1,
        "background_scope": "same six-scan synthetic cadence encoded twice; no recovery/control evaluation",
        "primary_codec_fixture_simulated_calls": primary_calls,
        "replay_fixture_simulated_calls": CodecDirectTests.replay_simulated_calls,
        "total_qualification_simulated_calls": primary_calls + CodecDirectTests.replay_simulated_calls,
        "total_qualification_generated_hdf5_bytes": primary_bytes + CodecDirectTests.replay_encoded_bytes,
        "preserved_input_sha256": cfg["input_sha256"],
        "publication_spec_sha256": envelope.ledger_digest(spec),
        "new_boundary_risk": "unguarded LocalRoleStore accepts a coherent ledger reset; guarded protocol rejects it",
        "old_ledger_reset": False, "prospective_telescope_reservations": 0,
        "remote_v2_backend_qualified": False, "network_budget_issued": False,
        "scientific_evaluation_executed": False, "telescope_requests": 0,
        "telescope_values_opened": False, "fresh_24_case_panel_executed": False,
        "original_m43af_holdouts_opened": False,
        "runtime_supplement_sha256": sha(OUT / "runtime_supplement.json"),
    }
    write("result.json", result)
    paths = [ROOT / p for p in OWN_PATHS] + sorted(p for p in OUT.iterdir() if p.is_file())
    manifest = "\n".join(f"{sha(p)}  {p.relative_to(ROOT)}" for p in paths) + "\n"
    (ROOT / "RESULTS_MANIFEST_RADIO_CODEC_PUBLICATION_2026-09-27.sha256").write_text(manifest)
    print(json.dumps({k: result[k] for k in ("status", "new_tests_passed", "codec_scan_receipts",
        "normalized_cells_bit_exact", "score_cells_bit_exact", "telescope_requests")}, indent=2))


if __name__ == "__main__":
    main()
