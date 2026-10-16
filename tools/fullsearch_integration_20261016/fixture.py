"""Fixed engineering counter-hash input specification; no RNG or study bank.

Importing this file creates no numerical arrays.  The uint64 avalanche below is
a deterministic function of scan/local-row/local-channel indices, with explicit
wrapping arithmetic.  It makes no independent-noise or physical-noise claim.
"""
from __future__ import annotations

import hashlib

IDENTITY = "SETI_FULLSEARCH_PAYLOAD_ENGINEERING_20261016_V1"
MODE = "ENGINEERING_FIXTURES_ONLY"
SHAPE = (16, 12096)
OFFSET = 0x9E3779B97F4A7C15
MULTIPLIER1 = 0xBF58476D1CE4E5B9
MULTIPLIER2 = 0x94D049BB133111EB
MASK64 = (1 << 64) - 1
MASK20 = (1 << 20) - 1
WINDOW = (6, 7, 8, 9)
RAW_EXCESS = 2.0


def fixture_spec(contract):
    geometry = contract["geometry"]
    return {
        "schema": "SETI_DETERMINISTIC_COUNTERHASH_FULLSEARCH_FIXTURE_V1",
        "identity": IDENTITY, "mode": MODE, "six_scan_shape": [6, *SHAPE],
        "raw_dtype_exact": "<f4", "local_index": "row*12096+column;C-order",
        "counter_offset": "((scan_index+1)*0x9E3779B97F4A7C15)mod2^64",
        "hash_steps": [
            "z=(local_index+counter_offset)mod2^64",
            "z=((z XOR(z>>30))*0xBF58476D1CE4E5B9)mod2^64",
            "z=((z XOR(z>>27))*0x94D049BB133111EB)mod2^64",
            "z=z XOR(z>>31)", "q=z AND(2^20-1)"],
        "base_power_operation_order": "float64(0.75)+float64(q)*float64(2^-21);then cast <f4",
        "base_power_min_inclusive": 0.75,
        "base_power_max_inclusive": 1.25 - 2. ** -21,
        "quantum": 2. ** -21,
        "overflow_semantics": "unsigned64 wrap modulo2^64 after each addition/multiplication",
        "line_addition_operation_order": "after <f4 base cast, inplace add float32(2.0) to selected four cells",
        "probes": [
            {"name": "matched", "scan_indices": [0, 1], "source_rows": list(WINDOW),
             "source_channel_offset_from_corefirst": 1024, "raw_power_excess": RAW_EXCESS,
             "drift_hz_s": 0., "intrinsic_width_channels": 1},
            {"name": "primary", "scan_indices": [2], "source_rows": list(WINDOW),
             "source_channel_offset_from_corefirst": 3072, "raw_power_excess": RAW_EXCESS,
             "drift_hz_s": 0., "intrinsic_width_channels": 1}],
        "primary_truth_active_ON_scan_indices": [2],
        "loaded_source_channel_interval": list(geometry["loaded_source_channel_interval"]),
        "reference_source_channel_interval": list(geometry["reference_source_channel_interval"]),
        "scan_ids": [s["scan_id"] for s in geometry["scan_metadata"]],
        "RNG_APIs_or_RNG_state_used": False, "random_or_independent_noise_law_asserted": False,
        "calibration_panel_available": False,
        "rank_status": "NOT_APPLIED_NO_CALIBRATION",
        "scientific_admission": False, "qualified_SETI_detection": False,
        "original_A_B": "FAIL_CLOSED", "new_observation": False}


def build_inputs(np, contract):
    """Construct each prescribed raw byte array once; all operations are fixed."""
    geometry = contract["geometry"]
    loadedfirst, loadedstop = geometry["loaded_source_channel_interval"]
    corefirst, corestop = geometry["reference_source_channel_interval"]
    if (loadedstop - loadedfirst != SHAPE[1] or corestop - corefirst != 4096 or
            corefirst - loadedfirst != 4000 or len(geometry["scan_metadata"]) != 6):
        raise ValueError("Exact legacy12096/4096/4000 six-scan geometry required")
    if [s["role"] for s in geometry["scan_metadata"]] != ["ON", "OFF"] * 3:
        raise ValueError("Exact chronological ON/OFF cadence required")
    inputs = []
    for scan_index in range(6):
        # Array uint64 operations wrap; the scalar offset is reduced explicitly
        # in Python before conversion so overflow warnings cannot alter control.
        counter_offset = ((scan_index + 1) * OFFSET) & MASK64
        z = np.arange(SHAPE[0] * SHAPE[1], dtype=np.uint64)
        z += np.uint64(counter_offset)
        z = (z ^ (z >> 30)) * np.uint64(MULTIPLIER1)
        z = (z ^ (z >> 27)) * np.uint64(MULTIPLIER2)
        z ^= z >> 31
        q = z & np.uint64(MASK20)
        values = np.float64(.75) + q.astype(np.float64) * np.float64(2. ** -21)
        raw = np.ascontiguousarray(values.reshape(SHAPE), dtype=np.dtype("<f4"))
        if scan_index in (0, 1):
            raw[6:10, corefirst + 1024 - loadedfirst] += np.float32(RAW_EXCESS)
        elif scan_index == 2:
            raw[6:10, corefirst + 3072 - loadedfirst] += np.float32(RAW_EXCESS)
        inputs.append(raw)
    return inputs


def recipe():
    return {"case_id": IDENTITY, "family": "engineering_fixture",
            "seed_sha256": hashlib.sha256(IDENTITY.encode("ascii")).hexdigest(),
            "seed_is_identity_binding_only_not_RNG_seed": True,
            "active_scan_indices": [2], "drift_hz_s": 0.,
            "intrinsic_width_channels": 1, "RNG_called": False,
            "noise_law": "DETERMINISTIC_INDEX_AVALANCHE_NOT_CALIBRATED_NOISE",
            "study_bank_member": False, "scientific_admission": False}


def truths(contract, canonical_truth, authenticated_arrays):
    metadata = contract["geometry"]["scan_metadata"]
    corefirst = contract["geometry"]["reference_source_channel_interval"][0]
    def track(scan_index, offset, name):
        scan_id = metadata[scan_index]["scan_id"]
        return canonical_truth({
            "case_id": IDENTITY, "truth_id": IDENTITY + ":" + name,
            "seed_sha256": recipe()["seed_sha256"],
            "seed_is_identity_binding_only_not_RNG_seed": True,
            "synthetic_injection": True, "deterministic_engineering_fixture": True,
            "active_scan_indices": [scan_index], "primary_active_scan_indices": [scan_index],
            "active_ON_scan_ids": [scan_id], "reference_source_channel": corefirst + offset,
            "drift_hz_s": 0., "intrinsic_width_channels": 1,
            "flux_by_scan": {scan_id: {"truth_window_source_rows": list(WINDOW),
                "active_source_rows": list(WINDOW), "injection_oracle_width_channels": 1,
                "raw_power_excess_per_selected_cell": RAW_EXCESS}},
            "authenticated_input_arrays": authenticated_arrays,
            "raw_probe_prescription_is_not_calibrated_SNR_or_flux": True,
            "generated_exactly_once": True, "RNG_called": False,
            "scientific_admission": False, "qualified_SETI_detection": False})
    return track(2, 3072, "primary"), {"matched": track(0, 1024, "matched")}
