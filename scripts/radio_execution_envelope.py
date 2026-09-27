"""Build the blocked HD 1461 execution envelope without spectral access."""
import hashlib
import json
import platform
from pathlib import Path
import sys

from seti_repeater import acquisition_radio as acquisition
from seti_repeater import execution_envelope_radio as envelope

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/radio_execution_envelope_20260927.json"
OUT = ROOT / "results_radio_execution_envelope_2026-09-27"
PINNED_CODE = [
    "src/seti_repeater/source_radio.py",
    "src/seti_repeater/source_m43h.py",
    "src/seti_repeater/acquisition_radio.py",
    "src/seti_repeater/direct_contract_radio.py",
    "src/seti_repeater/pipeline_direct_radio.py",
    "src/seti_repeater/calibration_transfer_radio.py",
    "src/seti_repeater/control_freeze_radio.py",
    "src/seti_repeater/execution_envelope_radio.py",
    "src/seti_repeater/search_v0p6.py",
]


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True,
                                       allow_nan=False) + "\n")


def build():
    cfg = json.loads(CONFIG.read_text())
    cfg["config_sha256"] = file_sha(CONFIG)
    observed = {name: file_sha(ROOT / path)
                for name, path in cfg["input_evidence"].items()}
    if observed != cfg["expected_input_sha256"]:
        raise ValueError("published execution-envelope input evidence changed")
    inputs = {name: json.loads((ROOT / path).read_text())
              for name, path in cfg["input_evidence"].items()}
    source_runtime = inputs["source_qualification"]["runtime"]
    factor_runtime = inputs["direct_factor_result"]["runtime"]
    if source_runtime["numpy"] != factor_runtime["numpy"]:
        raise ValueError("published codec and factor runtimes differ")
    runtime = {
        "schema": "radio-execution-runtime-manifest-v1",
        "python": factor_runtime["python"],
        "current_python_matches_pinned": platform.python_version() == factor_runtime["python"],
        "python_implementation": platform.python_implementation(),
        "system": platform.system().lower(),
        "machine": platform.machine(),
        "byteorder": sys.byteorder,
        "numpy": source_runtime["numpy"],
        "h5py": source_runtime["h5py"],
        "hdf5": source_runtime["hdf5"],
        "hdf5plugin": source_runtime["hdf5plugin"],
        "astropy": factor_runtime["astropy"],
        "astropy-iers-data": factor_runtime["astropy-iers-data"],
        "pyerfa": factor_runtime["pyerfa"],
        "version_source": "published codec and direct-factor qualification receipts",
        "current_executor_dependency_import_required": False,
        "implementation_sha256": {p: file_sha(ROOT / p) for p in PINNED_CODE},
        "spectral_values_read": False,
    }
    source = inputs["source_qualification"]
    codec = {
        "schema": "radio-codec-evidence-binding-v1",
        "source_qualification_file_sha256": observed["source_qualification"],
        "fixture_codecs": source["fixture_codecs"],
        "fixture_tests_passed": source["tests_run"],
        "fixture_runtime": source["runtime"],
        "implementation_sha256": source["implementation_sha256"],
        "local_codec_receipt_path_passed": source["status"] == "LOCAL_SOFTWARE_CHECKS_PASS",
        "telescope_codec_receipt_handoff_passed": False,
        "telescope_requests": 0,
        "telescope_values_opened": False,
    }
    factors = inputs["direct_factor_result"]
    catalogue = next(x for x in factors["coordinate_scenarios"]
                     if x["scenario"] == "catalogue_fixed")
    motion = {
        "schema": "radio-motion-evidence-binding-v1",
        "direct_factor_result_file_sha256": observed["direct_factor_result"],
        "catalogue_fixed_factor_bank_sha256": catalogue["factor_bank_sha256"],
        "factor_values_compared": sum(x["factor_values"]
                                      for x in factors["coordinate_scenarios"]),
        "native_score_cells_bit_exact": factors["score_cells_bit_exact"],
        "arithmetic_qualified": True,
        "physical_model_qualified": False,
        "source_pointing_resolved": False,
        "working_model": factors["working_model"],
    }
    resource = envelope.build_resource_contract(cfg)
    genesis = resource.genesis()
    built = envelope.build_envelope(
        cfg, runtime_manifest=runtime, codec_evidence=codec,
        motion_evidence=motion, resource_contract=resource,
        resource_genesis=genesis)
    return cfg, runtime, codec, motion, resource, genesis, built


def main():
    OUT.mkdir(exist_ok=True)
    cfg, runtime, codec, motion, resource, genesis, built = build()
    write("runtime_manifest.json", runtime)
    write("codec_evidence.json", codec)
    write("motion_evidence.json", motion)
    write("resource_contract.json", {**resource.record(),
                                      "resource_contract_sha256": resource.identity})
    write("resource_ledger_genesis.json", genesis)
    write("execution_envelope.json", {**built.record(),
                                      "execution_envelope_sha256": built.identity})
    result = {
        "schema": "radio-execution-envelope-result-v1",
        "status": built.record()["status"],
        "execution_envelope_sha256": built.identity,
        "runtime_manifest_sha256": built.runtime_manifest_sha256,
        "codec_evidence_sha256": built.codec_evidence_sha256,
        "motion_evidence_sha256": built.motion_evidence_sha256,
        "resource_contract_sha256": resource.identity,
        "resource_ledger_genesis_sha256": envelope.ledger_digest(genesis),
        "passed_gate_count": sum(x["passed"] for x in cfg["gates"].values()),
        "blockers": built.record()["blockers"],
        "prior_closed_ledger_reset": False,
        "prospective_reservations": 0,
        "local_v2_durable_controller_qualified": True,
        "network_budget_issued": False,
        "scientific_evaluation_executed": False,
        "spectral_access_authorized": False,
        "telescope_values_opened": False,
        "telescope_requests": 0,
    }
    write("result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
