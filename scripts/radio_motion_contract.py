"""Reproduce the new motion-contract evidence offline; never acquires data."""
from __future__ import annotations

import gzip
import hashlib
import html
import io
import json
from pathlib import Path
import platform
import re
import sys
import time
import unittest

import numpy as np

from seti_repeater import motion_contract_radio as contract
from seti_repeater.motion_radio import C_M_S, kepler_velocity

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_radio_motion_contract_2026-09-27"
CONFIG = "config/radio_motion_contract_study_20260927.json"
OWN = [CONFIG, "src/seti_repeater/motion_contract_radio.py",
       "scripts/radio_motion_contract.py", "tests/test_radio_motion_contract.py",
       "RADIO_MOTION_CONTRACT_2026-09-27_PROTOCOL.md",
       "RADIO_MOTION_CONTRACT_2026-09-27_RESULT.md"]
FIELDS = {"period": "pl_orbper", "axis": "pl_orbsmax", "eccentricity": "pl_orbeccen",
          "periastron_epoch": "pl_orbtper", "omega": "pl_orblper"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n")


def verify_inputs(cfg):
    for path, expected in cfg["input_sha256"].items():
        if sha(ROOT / path) != expected:
            raise ValueError("pinned input differs: " + path)


def ref_id(link):
    match = re.search(r"refstr=([^\s>]+)", link or "")
    return html.unescape(match.group(1)) if match else None


def orbital_provenance():
    rows = read(OUT.relative_to(ROOT) / "orbital_solutions.json")
    composite = read(OUT.relative_to(ROOT) / "composite_limits.json")[0]
    previous = read("results_radio_restart_2026-09-26/astrometry/official_response.json")[0]
    parameters = {}
    for name, key in FIELDS.items():
        if previous[key] != composite[key]:
            raise ValueError("historical scalar changed; do not silently substitute")
        reference = ref_id(composite.get(key + "_reflink"))
        basis = "explicit composite reference link"
        matching = []
        if reference is None:
            # A value alone is insufficient; compare the complete retained tuple.
            matching = [ref_id(r["pl_refname"]) for r in rows
                        if tuple(r.get(key+s) for s in ("", "err1", "err2", "lim"))
                        == tuple(composite.get(key+s) for s in ("", "err1", "err2", "lim"))]
            reference = matching[0] if len(matching) == 1 else None
            basis = "inferred unique value/error/limit tuple among the four retained PS rows"
        parameters[name] = {"value": composite[key], "limit_flag": composite[key+"lim"],
            "err1": composite[key+"err1"], "err2": composite[key+"err2"],
            "reference": reference, "reference_basis": basis,
            "matching_reference_ids": matching, "consumed_by_historical_bank": name != "periastron_epoch"}
    unresolved = {"phase_policy": "all_phases", "time_scale": None,
                  "omega_body": None, "axis_definition": "relative", "mass_conversion_evidence": None}
    return {"schema": "radio-orbital-provenance-audit-v1", "parameters": parameters,
            "retained_solution_count": len(rows), "historical_scalar_values_unchanged": True,
            "central_orbit_audit_all_phases": contract.central_solution_audit(parameters, unresolved),
            "central_orbit_audit_epoch_anchored": contract.central_solution_audit(
                parameters, unresolved | {"phase_policy": "epoch_anchored"}),
            "eccentricity_semantics": "99% upper credible limit; not a measured central eccentricity",
            "historical_arithmetic_disposition": "preserved conditional engineering scenario",
            "absolute_epoch_used_by_historical_bank": False,
            "physical_model_qualified": False}


def coverage_witness(cfg):
    with gzip.open(ROOT / "results_radio_direct_factors_2026-09-26/factor_banks.json.gz") as stream:
        bank = json.load(stream)["catalogue_fixed"]
    inputs = bank["record"]["inputs"]
    factors = np.asarray(bank["factors"], dtype="<f8")
    if hashlib.sha256(factors.tobytes()).hexdigest() != bank["record"]["factors_sha256"]:
        raise ValueError("retained factor payload differs")
    clock = read("results_radio_motion_2026-09-26/clock.json")["rows"]
    t = np.asarray(inputs["clock_seconds"], dtype=float)[:, 1]
    if not np.array_equal(t, [r["mid_offset_seconds"] for r in clock]):
        raise ValueError("retained clock alignment differs")
    spec = cfg["coverage_witness"]
    velocity = kepler_velocity(t, [spec["phase_cycles"]], **inputs["orbit"])[0]
    observer = np.asarray(inputs["observer_multipliers"], dtype=float)[:, 1]
    truth = observer*(1-spec["projected_scale"]*velocity/C_M_S)
    truth /= truth[0]
    # Widen stored float64 factors before multiplication/cancellation.
    target = np.longdouble(spec["frequency_hz"])*truth.astype(np.longdouble)
    channels = read("results_radio_motion_2026-09-26/result.json")["native_channel_width_hz"]
    scope_scans = {"all_three_on_epochs": [0, 2, 4], "on_epochs_1_2": [0, 2],
                   "on_epochs_1_3": [0, 4], "on_epochs_2_3": [2, 4]}
    if set(spec["scopes"]) != set(scope_scans):
        raise ValueError("only the fixed witness and its declared restrictions are supported")
    scopes = {}
    for name in spec["scopes"]:
        indices = [i for i, row in enumerate(clock) if row["scan_index"] in scope_scans[name]]
        fits = []
        for template in inputs["templates"]:
            j = template["template_index"]
            fit = contract.carrier_minimax(target[indices], factors[j, indices, 1])
            fit["active_pair_clock_indices"] = [indices[i] for i in fit["active_pair_local_indices"]]
            fits.append(template | fit | {"error_channels": fit["error_hz"]/channels})
        best = min(fits, key=lambda f: f["error_hz"])
        best_residual = best["residual_hz"]
        for fit in fits:
            del fit["residual_hz"]
        scopes[name] = {"clock_indices": indices, "all_template_fits": fits,
            "best_template_index": best["template_index"], "minimum_max_error_hz": best["error_hz"],
            "minimum_max_error_channels": best["error_channels"], "best_residual_hz": best_residual,
            "half_channel_center_coverage": best["error_channels"] <= spec["reporting_tolerance_channels"]}
    return {"schema": "radio-single-motion-coverage-witness-v1", "witness": spec,
            "retained_bank_identity": bank["identity"], "historical_orbit": inputs["orbit"],
            "midpoint_truth_factors": truth.tolist(), "native_channel_width_hz": channels,
            "scopes": scopes, "independent_witness_count": 1, "templates_added": 0,
            "detector_recovery_evaluated": False, "physical_domain_adopted": False}


def main():
    started = time.perf_counter()
    cfg = read(CONFIG)
    verify_inputs(cfg)
    sys.path.insert(0, str(ROOT / "tests"))
    suite = unittest.defaultTestLoader.loadTestsFromName("test_radio_motion_contract")
    log = io.StringIO()
    tested = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (OUT / "qualification.log").write_text(log.getvalue())
    if not tested.wasSuccessful():
        print(log.getvalue())
        raise RuntimeError("new motion-contract checks failed")
    provenance, coverage = orbital_provenance(), coverage_witness(cfg)
    orbit = coverage["historical_orbit"]
    bounds = contract.kepler_domain_bounds(period_days=orbit["period_days"],
        semi_major_axis_au=orbit["semi_major_axis_au"], eccentricity_max=orbit["eccentricity"],
        integration_seconds=17.986224128, frequency_hz=cfg["coverage_witness"]["frequency_hz"])
    bounds["conditioning"] = "Central P/a and e <= .172 is an illustrative deterministic restriction, not a 99% joint credible domain"
    required = ["pointing_and_observer", "orbital_domain_and_conventions", "time_mapping",
                "relativistic_emitter_and_systemic_motion", "exposure_and_instrument_response",
                "continuous_template_coverage", "numerical_transfer"]
    # None means unknown. No conditional subcomponent is a bound on these full terms.
    terms = {name: {"bound_hz": None, "qualified": False} for name in required}
    terms["continuous_template_coverage"]["evidence"] = "one fixed center-track counterexample; not an upper bound or recovery result"
    total = contract.accuracy_contract(terms, required,
        coverage["native_channel_width_hz"]*cfg["coverage_witness"]["reporting_tolerance_channels"],
        "future adopted physical domain, complete cadence and instrument response")
    old = read("results_radio_execution_envelope_2026-09-27/execution_envelope.json")
    receipt = read(OUT.relative_to(ROOT) / "acquisition.json")
    for name, obj in (("orbital_provenance_audit.json", provenance), ("coverage_witness.json", coverage),
                      ("conditional_bounds.json", bounds), ("accuracy_contract.json", total)):
        write(name, obj)
    runtime = {"python": platform.python_version(), "numpy": np.__version__,
        "platform": platform.platform(), "longdouble_mantissa_bits": np.finfo(np.longdouble).nmant,
        "implementation_sha256": {p: sha(ROOT/p) for p in OWN if p.endswith(".py")}}
    write("runtime.json", runtime)
    verify_inputs(cfg)
    result = {"schema": "radio-motion-contract-result-v1", "source_commit": cfg["source_commit"],
        "status": "METADATA_CORRECTION_AND_CONDITIONAL_CENTER_COVERAGE_FAILURE",
        "new_tests_passed": tested.testsRun, "execution_status": "BLOCKED", "primary": "neighbor9",
        "physical_model_qualified": False, "parent_execution_envelope_sha256": old["execution_envelope_sha256"],
        "parent_blockers_unchanged": old["blockers"], "preserved_input_sha256": cfg["input_sha256"],
        "orbital_metadata_acquisition_requests": len(receipt["requests"]),
        "orbital_metadata_acquisition_response_bytes": receipt["response_bytes"],
        "acquisition_receipt_scope": "three direct artifact requests; discovery page/search tool bytes not instrumented",
        "offline_reproduction_network_requests": 0, "telescope_requests": 0, "spectral_values_opened": False,
        "fresh_24_case_panel_executed": False, "closed_2048_phase_audit_rerun": False,
        "independent_motion_witnesses": 1, "template_scope_fits": 132, "templates_added": 0,
        "scientific_trials_added": 0, "prospective_telescope_reservations": 0,
        "published_synthetic_ledger_reset": False, "original_m43af_holdouts_opened": False,
        "offline_wall_seconds": time.perf_counter()-started}
    write("result.json", result)
    paths = [ROOT/p for p in OWN] + sorted(p for p in OUT.iterdir() if p.is_file())
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError("complete protocol/report required before manifest: " + str(missing))
    (ROOT / "RESULTS_MANIFEST_RADIO_MOTION_CONTRACT_2026-09-27.sha256").write_text(
        "".join(f"{sha(p)}  {p.relative_to(ROOT)}\n" for p in paths))
    print(json.dumps({k: result[k] for k in ("status", "new_tests_passed", "execution_status", "telescope_requests")}, indent=2))


if __name__ == "__main__":
    main()
