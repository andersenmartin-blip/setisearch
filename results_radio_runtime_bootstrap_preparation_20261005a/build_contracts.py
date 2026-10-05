"""Pure-data construction of the prospective package-bootstrap freeze.

No filesystem, process or network operation is performed by this module.
The caller supplies already retained raw JSON and externally measured source
pins/root identity. Construction is not activation or runtime qualification.
"""

import hashlib
import json
import posixpath
import stat
from urllib.parse import urlsplit

SCHEMA = "radio-runtime-package-bootstrap-supervisor-v1"
PLAN_SHA256 = "fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25"
PREREAD_SHA256 = "3e154b784424c215867b9d3a091e3e92ed8c1229a3b1ba7f838074c6e36bb1dc"
BASIS_SHA256 = "c0736896f9a1aee3598c11e11149057553e30fc4f436a5600086dad51352251c"
ROOT = "/workspace/scratch/d804553c0e89/setisearch-status-20261004"
PLAN_PATH = ROOT + "/results_radio_runtime_materialization_preparation_20261004a/runtime-materialization.plan.json"
PREREAD_PATH = ROOT + "/results_radio_runtime_bootstrap_preparation_20261005a/installer-preread.json"
SITE = "/opt/codex/runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/site-packages"
ACTIVATION_REPOSITORY_PATH = "config/radio_runtime_bootstrap_20261005a.activate.json"
PIN_KEYS = {"path", "bytes", "sha256", "mode"}
CONTRACT_KEYS = {"schema", "bootstrap_identity", "evidence_domain", "source_pins", "runtime_pins",
                 "seed_pins", "python_executable", "python_sha256", "attribution_basis_path",
                 "wheel_io_path", "plan_path", "plan_sha256", "wheel_lock_utf8", "output_root",
                 "output_root_identity", "spent_path", "activation_path", "wheels", "limits",
                 "expected_versions"}
FINAL_LIMITS = {"wall_seconds": 300, "child_seconds": 260, "reap_seconds": 10,
                "artifact_bytes": 1536 * 1024**2, "address_space_bytes": 1024**3,
                "parent_read_bytes": 3 * 1024**3, "child_read_reserve_bytes": 1024**3,
                "joined_read_bytes": 4 * 1024**3, "stream_bytes": 1024**2,
                "sample_count": 1200, "file_bytes": 128 * 1024**2,
                "file_count": 20000, "directory_count": 4096,
                "terminal_reserve_bytes": 8 * 1024**2}
EXPECTED_VERSIONS = {"numpy": "2.3.5", "h5py": "3.16.0", "hdf5plugin": "7.1.0"}
PENDING_FIELDS = ["complete_execution_code_input_runtime_freeze", "hdf5_runtime",
                  "source_specific_codec_runtime_case_law_certificate",
                  "complete_127_24_scientific_certificate", "joined_hosted_transport_certificate",
                  "source_specific_executable_trial_protocol", "cumulative_limits", "reservation_store",
                  "public_acquisition_ledger_revision_and_sha256",
                  "fresh_irrevocable_acquisition_and_trial_allocation",
                  "new_executable_source_contract_sha256"]
AUTHORITY_KEYS = ("scientific_execution_authorized", "source_contract_admitted", "runtime_qualified",
                  "cas_qualified", "certificate_issued", "reservation_authorized",
                  "spectral_access_authorized", "rng_authorized", "hosted_transport_qualified",
                  "activation_created", "allocation_created", "installation_performed")
RETIRED_IDENTITIES = {"fc5773e944ad53fc76a9897906ff38798b169ec7b1ec84ec8c6cb4a5ee910845",
                      "e3d5aae494ef041c668a9fbec11edc2ac821a0e27bef15588181d166e125736c"}


class PreparationError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def hex_value(value, length=64):
    return type(value) is str and len(value) == length and all(c in "0123456789abcdef" for c in value)


def absolute(value):
    if (type(value) is not str or not value.startswith("/") or posixpath.normpath(value) != value
            or value.startswith("//") or "\x00" in value or "\\" in value
            or len(value.encode("utf-8")) > 4096 or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise PreparationError("noncanonical absolute path")
    return value


def relative(value):
    if (type(value) is not str or not value or value.startswith("/") or "\\" in value
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or any(part in ("", ".", "..") for part in value.split("/"))
            or len(value.split("/")) > 64 or len(value.encode("utf-8")) > 4096):
        raise PreparationError("noncanonical relative path")
    return value


def pinned_json(raw, expected_sha256, maximum):
    if type(raw) is not bytes or len(raw) > maximum or not hex_value(expected_sha256) or digest(raw) != expected_sha256:
        raise PreparationError("external raw JSON pin differs")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise PreparationError("duplicate JSON key")
            result[key] = value
        return result

    def constant(value):
        raise PreparationError("nonfinite JSON constant")

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, PreparationError):
            raise
        raise PreparationError("invalid pinned JSON") from exc


def filesystem_mode(value):
    if value in ("0644", "100644") and type(value) is str:
        return "0644"
    if value in ("0755", "100755") and type(value) is str:
        return "0755"
    raise PreparationError("only exact source modes 0644 or 0755 accepted")


def pin(row, *, exact=False):
    if type(row) is not dict or not PIN_KEYS <= set(row) or (exact and set(row) != PIN_KEYS):
        raise PreparationError("selected pin schema")
    if type(row["bytes"]) is not int or row["bytes"] < 0 or row["bytes"] > 128 * 1024**2 or not hex_value(row["sha256"]):
        raise PreparationError("selected pin size/hash")
    result = {"path": absolute(row["path"]), "bytes": row["bytes"],
              "sha256": row["sha256"], "mode": filesystem_mode(row["mode"])}
    if "filesystem_mode" in row and filesystem_mode(row["filesystem_mode"]) != result["mode"]:
        raise PreparationError("Git and filesystem modes differ")
    return result


def source_identity(row, normalized):
    value = row.get("source_identity")
    keys = {"st_dev", "st_ino", "st_mode", "st_size", "st_nlink", "st_mtime_ns", "st_ctime_ns"}
    if type(value) is not dict or set(value) != keys or any(type(v) is not int for v in value.values()):
        raise PreparationError("source identity schema")
    if (value["st_dev"] < 0 or value["st_ino"] <= 0 or value["st_size"] != normalized["bytes"]
            or value["st_nlink"] != 1 or not stat.S_ISREG(value["st_mode"])
            or format(value["st_mode"] & 0o7777, "04o") != normalized["mode"]):
        raise PreparationError("source sole-link regular identity differs")
    if not hex_value(row.get("git_blob"), 40):
        raise PreparationError("raw source Git blob absent")


def row_list(value, expected_count, expected_bytes):
    if type(value) is not list or len(value) != expected_count:
        raise PreparationError("exact retained inventory count differs")
    result = []
    for row in value:
        normalized = pin(row)
        source_identity(row, normalized)
        result.append(normalized)
    paths = [item["path"] for item in result]
    if len(set(paths)) != len(paths) or paths != sorted(paths):
        raise PreparationError("retained inventory paths duplicated or unordered")
    if sum(item["bytes"] for item in result) != expected_bytes:
        raise PreparationError("exact retained inventory byte total differs")
    return result


def checked_limits(value):
    limits = dict(FINAL_LIMITS) if value is None else value
    if (type(limits) is not dict or set(limits) != set(FINAL_LIMITS)
            or any(type(v) is not int or v <= 0 for v in limits.values())
            or limits != FINAL_LIMITS):
        raise PreparationError("fixed final bootstrap ceilings differ")
    if (limits["parent_read_bytes"] + limits["child_read_reserve_bytes"] > limits["joined_read_bytes"]
            or limits["child_seconds"] + limits["reap_seconds"] + 2 > limits["wall_seconds"]
            or limits["terminal_reserve_bytes"] < 1024**2
            or limits["terminal_reserve_bytes"] + 2 * limits["stream_bytes"] >= limits["artifact_bytes"]):
        raise PreparationError("joined or terminal envelope differs")
    return dict(limits)


def wheels_from_plan(plan, limits):
    if type(plan) is not dict or type(plan.get("materialization")) is not dict:
        raise PreparationError("original materialization fields absent")
    materialization = plan["materialization"]
    rows = materialization.get("official_wheels")
    if type(rows) is not list or len(rows) != 3:
        raise PreparationError("exact three original wheels required")
    keys = {"bytes", "filename", "url", "sha256", "name", "version", "tags"}
    wheels = []
    names = set()
    filenames = set()
    urls = set()
    for row in rows:
        if type(row) is not dict or not keys <= set(row):
            raise PreparationError("original wheel row absent")
        wheel = {key: row[key] for key in keys}
        if (type(wheel["name"]) is not str or wheel["name"] in names
                or EXPECTED_VERSIONS.get(wheel["name"]) != wheel["version"]
                or type(wheel["bytes"]) is not int or wheel["bytes"] <= 0
                or wheel["bytes"] > limits["file_bytes"] or not hex_value(wheel["sha256"])):
            raise PreparationError("original wheel identity/length/hash")
        filename = relative(wheel["filename"])
        if "/" in filename or not filename.endswith(".whl") or filename in filenames:
            raise PreparationError("wheel basename duplicate or invalid")
        if type(wheel["url"]) is not str:
            raise PreparationError("official wheel URL absent")
        url = urlsplit(wheel["url"])
        if (url.scheme != "https" or url.netloc != "files.pythonhosted.org" or url.query or url.fragment
                or not url.path.startswith("/packages/") or not url.path.endswith("/" + filename)
                or wheel["url"] in urls):
            raise PreparationError("exact official wheel URL shape differs")
        if (type(wheel["tags"]) is not list or not wheel["tags"]
                or len(wheel["tags"]) > 16 or len(set(wheel["tags"])) != len(wheel["tags"])
                or any(type(tag) is not str or "x86_64" not in tag or "manylinux" not in tag for tag in wheel["tags"])):
            raise PreparationError("finite original wheel tags differ")
        names.add(wheel["name"])
        filenames.add(filename)
        urls.add(wheel["url"])
        wheels.append(wheel)
    if names != set(EXPECTED_VERSIONS) or sum(wheel["bytes"] for wheel in wheels) != 68409067:
        raise PreparationError("original three wheel set or total differs")
    if materialization.get("wheel_file_bytes") != 68409067 or materialization.get("bootstrap_resources", {}).get("wheel_bytes_only") != 68409067:
        raise PreparationError("original materialization byte accounting differs")
    lock = materialization.get("offline_hash_lock_utf8")
    expected_lock = "".join(wheel["name"] + "==" + wheel["version"] + " --hash=sha256:" + wheel["sha256"] + "\n" for wheel in wheels)
    if type(lock) is not str or len(lock.encode("utf-8")) > 65536 or lock != expected_lock:
        raise PreparationError("exact original offline hash lock differs")
    return wheels, lock


def build_contracts(plan_raw, preread_raw, source_pins, *, bootstrap_identity,
                    output_root, output_root_identity, python_executable, gate_path,
                    attribution_basis_path, wheel_io_path, plan_path=PLAN_PATH,
                    preread_path=PREREAD_PATH, activation_path, limits=None):
    """Return inert exact gate contract and its canonical freeze bytes; no I/O.

    Required source pins are exact four-field PIN rows and include gate,
    attribution basis, wheel I/O helper, original plan and prerequisite manifest.
    The caller, not this builder, measures the fresh empty root and publishes
    and reads back both source bodies and subsequent one-file activation.
    """
    plan = pinned_json(plan_raw, PLAN_SHA256, 1024**2)
    preread = pinned_json(preread_raw, PREREAD_SHA256, 4 * 1024**2)
    chosen_limits = checked_limits(limits)
    if not hex_value(bootstrap_identity) or bootstrap_identity in RETIRED_IDENTITIES or bootstrap_identity == "0" * 64:
        raise PreparationError("fresh separate bootstrap identity required")
    paths = {key: absolute(value) for key, value in {
        "output_root": output_root, "python_executable": python_executable, "gate_path": gate_path,
        "attribution_basis_path": attribution_basis_path, "wheel_io_path": wheel_io_path,
        "plan_path": plan_path, "preread_path": preread_path, "activation_path": activation_path}.items()}
    if not paths["activation_path"].endswith("/" + ACTIVATION_REPOSITORY_PATH):
        raise PreparationError("fixed separate activation path required")
    if paths["plan_path"] != PLAN_PATH or paths["preread_path"] != PREREAD_PATH:
        raise PreparationError("fixed retained original plan and prerequisite paths required")
    if (type(output_root_identity) is not dict or set(output_root_identity) != {"device", "inode", "mode"}
            or type(output_root_identity["device"]) is not int or output_root_identity["device"] < 0
            or type(output_root_identity["inode"]) is not int or output_root_identity["inode"] <= 0
            or output_root_identity["mode"] != "0700"):
        raise PreparationError("externally supplied fresh root identity schema")
    authority = plan.get("authority")
    if type(authority) is not dict or not authority or any(value is not False for value in authority.values()):
        raise PreparationError("original inert plan authority changed")
    if plan.get("remaining_authentic_receipt_requirements", {}).get("all_eleven_fields_still_pending") != PENDING_FIELDS:
        raise PreparationError("all eleven pending fields must be preserved")
    if (type(preread) is not dict or preread.get("schema") != "radio-runtime-bootstrap-installer-preread-v1"
            or preread.get("status") != "PREPARED_STATIC_SOURCE_SNAPSHOT_ONLY"
            or preread.get("scientific_authority") is not False or preread.get("new_live_reservation") is not False
            or type(preread.get("scientific_fields_pending")) is not int or preread["scientific_fields_pending"] != 11
            or any(type(preread.get(key)) is not int or preread[key] != 0 for key in
                   ("genuine_bootstrap_invocations", "genuine_installer_invocations", "genuine_capture_invocations"))):
        raise PreparationError("static-only prerequisite authority differs")
    if preread.get("runtime_comparison") != {"same_exact_765_cohort": True, "changed_rows": [], "added_paths": [], "removed_paths": []}:
        raise PreparationError("retained runtime comparison differs")
    runtime = row_list(preread.get("runtime_selected_files"), 765, 53792770)
    installer = row_list(preread.get("installer_source_files"), 479, 5690699)
    if preread.get("runtime_selected_file_count") != 765 or preread.get("runtime_selected_file_bytes") != 53792770 or preread.get("installer_source_file_count") != 479 or preread.get("installer_source_raw_bytes") != 5690699:
        raise PreparationError("prerequisite summary counts differ")
    if preread.get("pip_source_root") != SITE or preread.get("pip_version_static") != "26.2.1" or preread.get("pip_distribution") != "pip-26.2.1.dist-info":
        raise PreparationError("exact statically observed pip identity differs")
    seeds = []
    for row, normalized in zip(preread["installer_source_files"], installer):
        target = relative(row.get("relative_path"))
        if row.get("seed_relative_path") != target or row["path"] != SITE + "/" + target:
            raise PreparationError("installer source/relative-path mapping differs")
        if not target.startswith(("pip/", "pip-26.2.1.dist-info/")) or "__pycache__" in target.split("/") or target.endswith((".pyc", ".pyo")):
            raise PreparationError("only source/data and sole dist-info seed allowed")
        seeds.append(dict(normalized, relative_path=target))
    seeds.sort(key=lambda row: row["relative_path"])
    targets = [row["relative_path"] for row in seeds]
    required_seed = {"pip/__main__.py", "pip/__init__.py", "pip-26.2.1.dist-info/METADATA", "pip-26.2.1.dist-info/WHEEL", "pip-26.2.1.dist-info/RECORD"}
    if len(set(targets)) != 479 or not required_seed <= set(targets):
        raise PreparationError("installer entry point or dist-info seed absent/duplicated")
    runtime = sorted(runtime + installer, key=lambda row: row["path"])
    if len({row["path"] for row in runtime}) != 1244:
        raise PreparationError("runtime and installer source paths overlap")
    if type(source_pins) is not list or not source_pins or len(source_pins) + len(runtime) > 4096:
        raise PreparationError("finite explicit source pin inventory required")
    source = sorted([pin(row, exact=True) for row in source_pins], key=lambda row: row["path"])
    if len({row["path"] for row in source}) != len(source) or set(row["path"] for row in source) & set(row["path"] for row in runtime):
        raise PreparationError("source paths duplicate or overlap selected runtime")
    source_map = {row["path"]: row for row in source}
    required_source = {paths[key] for key in ("gate_path", "attribution_basis_path", "wheel_io_path", "plan_path", "preread_path")}
    if len(required_source) != 5 or not required_source <= set(source_map):
        raise PreparationError("complete distinct gate/helper/plan/prerequisite source pins required")
    if (source_map[paths["plan_path"]]["sha256"] != PLAN_SHA256 or source_map[paths["plan_path"]]["bytes"] != len(plan_raw)
            or source_map[paths["preread_path"]]["sha256"] != PREREAD_SHA256 or source_map[paths["preread_path"]]["bytes"] != len(preread_raw)
            or source_map[paths["attribution_basis_path"]]["sha256"] != BASIS_SHA256):
        raise PreparationError("externally pinned plan/prerequisite/B attribution bytes differ")
    selected = {row["path"]: row for row in source + runtime}
    if paths["python_executable"] not in {row["path"] for row in runtime}:
        raise PreparationError("current interpreter must belong to retained runtime inventory")
    spent_path = paths["output_root"] + "/spent.json"
    if (paths["output_root"] == "/" or paths["output_root"] in selected
            or any(path.startswith(paths["output_root"] + "/") for path in selected)
            or paths["activation_path"] in selected or paths["activation_path"].startswith(paths["output_root"] + "/")):
        raise PreparationError("fresh output/activation must not overlap selected source/runtime")
    wheels, lock = wheels_from_plan(plan, chosen_limits)
    contract = {"schema": SCHEMA, "bootstrap_identity": bootstrap_identity,
                "evidence_domain": "package-bootstrap-only", "source_pins": source,
                "runtime_pins": runtime, "seed_pins": seeds,
                "python_executable": paths["python_executable"],
                "python_sha256": selected[paths["python_executable"]]["sha256"],
                "attribution_basis_path": paths["attribution_basis_path"],
                "wheel_io_path": paths["wheel_io_path"], "plan_path": paths["plan_path"],
                "plan_sha256": PLAN_SHA256, "wheel_lock_utf8": lock,
                "output_root": paths["output_root"], "output_root_identity": dict(output_root_identity),
                "spent_path": spent_path, "activation_path": paths["activation_path"],
                "wheels": wheels, "limits": chosen_limits, "expected_versions": dict(EXPECTED_VERSIONS)}
    if set(contract) != CONTRACT_KEYS:
        raise PreparationError("internal exact gate contract schema differs")
    freeze_raw = canonical(contract)
    return {"contract": contract, "freeze_raw": freeze_raw, "freeze_sha256": digest(freeze_raw),
            "preparation": {"schema": "radio-runtime-package-bootstrap-pure-preparation-v1",
                            "bootstrap_identity": bootstrap_identity,
                            "authority": dict.fromkeys(AUTHORITY_KEYS, False),
                            "scientific_fields_pending": list(PENDING_FIELDS),
                            "plan_sha256": PLAN_SHA256, "preread_sha256": PREREAD_SHA256,
                            "selected_runtime_files": len(runtime),
                            "selected_runtime_bytes": sum(row["bytes"] for row in runtime),
                            "seed_files": len(seeds), "seed_bytes": sum(row["bytes"] for row in seeds),
                            "source_files": len(source), "source_bytes": sum(row["bytes"] for row in source),
                            "freeze_bytes": len(freeze_raw), "freeze_sha256": digest(freeze_raw),
                            "actual_root_read_or_empty_check_performed": False,
                            "runtime_reads_or_installer_invocations_performed": False,
                            "activation_or_allocation_created": False,
                            "caller_full_publication_readback_and_separate_activation_required": True}}
