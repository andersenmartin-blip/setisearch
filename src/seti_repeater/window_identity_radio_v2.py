"""HD189733's widened metadata identities. No data access or score operation."""
import hashlib
import json

from .source_m43h import digest

SCHEMA = "radio-hd189733-window-identities-v2"
ROLES = ("calibration", "validation", "pilot")
CHANNELS = 65536
BLOCKS = [[i, i+4096] for i in range(0, CHANNELS, 4096)]


def _read(raw, expected):
    if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Input differs from externally supplied publication pin")
    return json.loads(raw)


def build(source_bytes, source_sha256, design_bytes, design_sha256):
    source = _read(source_bytes, source_sha256)
    design = _read(design_bytes, design_sha256)
    if (source.get("cadence_id") != 85030 or source.get("archive_target") != "HIP98505"
            or source.get("stage") != "preparation-only-no-spectral-access"
            or source.get("windows") != []):
        raise ValueError("Wrong source or rewritten preparation contract")
    scans = source["scans"]
    if (len(scans) != 6 or len({s["url"] for s in scans}) != 6
            or [s["label"] for s in scans] != [f"epoch{i}_{r}" for i in (1,2,3) for r in ("on","off")]
            or source["source_inventory_sha256"] != digest(scans)):
        raise ValueError("Source inventory mismatch")
    if (design.get("schema") != "radio-hd189733-window-geometry-study-v1"
            or design.get("status") != "PROSPECTIVE_IDENTITIES_ONLY_NOT_AN_EXECUTABLE_PROTOCOL"
            or design.get("spectral_access_authorized") is not False
            or design.get("physical_bank_qualified") is not False
            or design.get("new_control_panel_executed") is not False):
        raise ValueError("Design cannot assert scientific/admission qualification")
    windows = design["windows"]
    if tuple(w["role"] for w in windows) != ROLES:
        raise ValueError("Role ordering changed")
    flat = set()
    records = []
    for w in windows:
        if w["identity"] != digest({k:v for k,v in w.items() if k != "identity"}):
            raise ValueError("Window identity hash changed")
        if (w["source_contract_sha256"] != source_sha256 or w["native_channel_count"] != CHANNELS
                or w["normalization_blocks_native_channels"] != BLOCKS
                or w.get("spectral_values_included") is not False
                or w.get("spectral_access_authorized") is not False):
            raise ValueError("Window source/length/normalization boundary changed")
        a,z = w["archive_interval"]
        k = w["archive_chunk_index"]
        if any(type(v) is not int for v in (a,z,k)) or a < 0 or z-a != CHANNELS:
            raise ValueError("Invalid integer window interval")
        if len(w["payload_keys"]) != 6 or w["payload_keys_sha256"] != digest(w["payload_keys"]):
            raise ValueError("Payload inventory hash/length changed")
        for s,p in zip(scans,w["payload_keys"]):
            h=s["expected_header"];chunk=s["expected_chunks"][2]
            if (h["dataset_shape"][:2] != [16,1] or z > h["dataset_shape"][2]
                    or s["expected_chunks"][:2] != [1,1] or a//chunk != k or (z-1)//chunk != k):
                raise ValueError("Source interval/chunk geometry mismatch")
            expected={"source_url":s["url"],"source_size_bytes":s["expected_remote_size_bytes"],
                      "etag":s["expected_etag"],
                      "chunk_coordinates_time_feed_frequency":[[i,0,k] for i in range(16)]}
            if p != expected:
                raise ValueError("Payload source/ETag/row/chunk differs from pinned source")
            low=(h["fch1_mhz"]+(z-1)*h["foff_mhz"])*1e6
            high=(h["fch1_mhz"]+a*h["foff_mhz"])*1e6
            center=(h["fch1_mhz"]+((a+z)//2)*h["foff_mhz"])*1e6
            if (w["native_frequency_low_hz"],w["native_frequency_high_hz"],w["proposed_first_on_midpoint_carrier_center_hz"]) != (low,high,center):
                raise ValueError("Frequency endpoints disagree with the pinned header")
            for i in range(16):
                key=(s["url"],s["expected_etag"],i,0,k)
                if key in flat:
                    raise ValueError("Roles share a decoded native chunk")
                flat.add(key)
        records.append({"role":w["role"],"window_identity":w["identity"],
                        "payload_keys_sha256":w["payload_keys_sha256"],
                        "archive_interval":[a,z],"archive_chunk_index":k,
                        "native_channel_count":CHANNELS,"normalization_block_count":len(BLOCKS)})
    if len(flat) != 288:
        raise ValueError("Incomplete six-source/three-role/16-row chunk inventory")
    record={"schema":SCHEMA,"source_contract_sha256":source_sha256,
            "window_design_sha256":design_sha256,"source_inventory_sha256":source["source_inventory_sha256"],
            "primary":"neighbor9","windows":records,"roles":list(ROLES),
            "decoded_payload_groups":18,"distinct_native_chunk_identities":len(flat),
            "normalization_blocks":48,"roles_are_independent_observations":False,
            "spectral_access_authorized":False,"threshold_transfer_authorized":False,
            "status":"IDENTITIES_BOUND_SCIENTIFIC_AND_EXECUTION_GATES_PENDING",
            "remaining_requirements":["qualified source-specific motion/width bank",
                "source codec/runtime evidence and live receipt handoff",
                "fresh disjoint development/calibration/evaluation identity freeze",
                "numeric cross-window transfer and recovery/RFI/null evaluation",
                "integrated prospective protocol and cumulative acquisition/trial ledger"]}
    return {**record,"contract_sha256":digest(record)}
