"""Detached, pure admission validation; no acquisition, RNG, store or file API.

The caller supplies complete raw evidence and independently retained trust pins.
Publication anchors are an explicit external trust boundary, not self-issued
GitHub attestations. Positive test evidence is accepted only in its own domain
and never has scientific readiness. No result constructs an execution lease.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import re

DOCUMENTS = frozenset(("basis", "codec_certificate", "executable_freeze",
    "scientific_allocation", "hosted_transport", "scientific_result",
    "acquisition_ledger", "trial_protocol", "limits", "pilot_contract", "trial_allocation"))
STAGES = ("basis", "freeze", "allocation", "result", "pilot", "acquisition", "trial")
STAGE_DOCUMENTS = {
    "basis": {"basis", "codec_certificate", "hosted_transport", "trial_protocol", "limits"},
    "freeze": {"executable_freeze"}, "allocation": {"scientific_allocation"},
    "result": {"scientific_result"}, "pilot": {"pilot_contract"},
    "acquisition": {"acquisition_ledger"}, "trial": {"trial_allocation"}}
MIB = 1024**2
SCIENTIFIC_LIMITS = {"reference_count": 127, "evaluation_count": 24,
    "reference_milliseconds": 40000, "reference_bytes": 4*MIB,
    "evaluation_milliseconds": 80000, "evaluation_bytes": 18*MIB,
    "overhead_milliseconds": 200000, "ledger_bytes": 8*MIB,
    "failure_summary_bytes": 76*MIB, "total_milliseconds": 7200000,
    "total_bytes": 1024**3, "rss_bytes": 512*MIB, "modelled_array_bytes": 256*MIB}
ACQUISITION_LIMITS = {"maximum_sessions": 3, "session_max_requests": 500,
    "session_max_bytes": 512*MIB, "session_max_seconds": 1200,
    "total_max_requests": 1500, "total_max_bytes": 1536*MIB, "total_max_seconds": 3600}
ROLES = ("calibration", "validation", "pilot")
LABELS = tuple(f"epoch{i}_{r}" for i in (1, 2, 3) for r in ("on", "off"))
LAW_NAMES = ("exact_pipeline", "display_name_ignored", "explicit_unfiltered",
    "missing_optional_local_declaration", "missing_required_declaration",
    "pipeline_id_mutation", "pipeline_flags_mutation", "client_datum_0_mutation",
    "client_datum_1_mutation", "client_datum_2_mutation", "client_datum_3_mutation",
    "client_datum_4_mutation", "removed_filter", "extra_filter",
    "invalid_client_datum_type_0", "invalid_client_datum_type_1",
    "invalid_client_datum_type_2", "invalid_client_datum_type_3", "boolean_filter_id",
    "boolean_filter_flags", "nonexplicit_pipeline", "malformed_filter_entry")
RUNTIME_KEYS = {"python", "numpy", "h5py", "hdf5", "hdf5plugin", "python_executable_sha256"}
MAX_DOCUMENT_BYTES = 2*MIB
MAX_TOTAL_BYTES = 8*MIB


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def same(a, b):
    return canonical(a) == canonical(b)


def sha(value, size=64):
    need(type(value) is str and re.fullmatch("[0-9a-f]{"+str(size)+"}", value), "Invalid digest")
    return value


def integer(value, maximum, label, minimum=0):
    need(type(value) is int and minimum <= value <= maximum, "Invalid bounded integer: "+label)


def fields(value, names, label):
    need(type(value) is dict and set(value) == set(names), "Exact fields required: "+label)


def _pairs(items):
    value = {}
    for key, item in items:
        need(key not in value, "Duplicate JSON member")
        value[key] = item
    return value


def parse(raw):
    def invalid(value):
        raise ValueError("Nonfinite JSON: "+value)
    try:
        doc = json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid)
        pending = [doc]
        while pending:
            value = pending.pop()
            if type(value) is float:
                need(math.isfinite(value), "Nonfinite JSON number")
            elif type(value) is list:
                pending.extend(value)
            elif type(value) is dict:
                pending.extend(value.values())
        return doc
    except (RecursionError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Malformed bounded JSON") from error


def _authenticate(raw_documents, expected_raw_pins):
    fields(raw_documents, DOCUMENTS, "raw documents")
    fields(expected_raw_pins, DOCUMENTS, "independent pins")
    docs, total = {}, 0
    for name in sorted(DOCUMENTS):
        raw, pin = raw_documents[name], expected_raw_pins[name]
        need(type(raw) is bytes and 0 < len(raw) <= MAX_DOCUMENT_BYTES, "Bounded raw evidence required")
        fields(pin, {"bytes", "sha256"}, "raw pin")
        need(type(pin["bytes"]) is int and pin["bytes"] == len(raw), "Raw byte count differs")
        need(hashlib.sha256(raw).hexdigest() == sha(pin["sha256"]), "Independent raw pin differs")
        total += len(raw)
        need(total <= MAX_TOTAL_BYTES, "Total metadata budget exceeded")
        docs[name] = parse(raw)
        need(type(docs[name]) is dict, "Typed raw document must be a JSON object")
    return docs


def _basis(value):
    keys = {"source_inventory_sha256", "source_metadata_sha256", "window_design_sha256",
        "window_contract_sha256", "receiver_bank_records_sha256", "proposal_sha256", "window_identities",
        "receiver_bank_sha256s", "receiver_context_sha256s", "ordered_case_identities", "case_bindings"}
    fields(value, keys, "independent preserved basis")
    for key in keys - {"window_identities", "receiver_bank_sha256s", "receiver_context_sha256s",
                       "ordered_case_identities", "case_bindings"}:
        sha(value[key])
    for key in ("window_identities", "receiver_bank_sha256s"):
        fields(value[key], ROLES, key)
        for item in value[key].values():
            sha(item)
        need(len(set(value[key].values())) == 3, "Distinct role identities required")
    fields(value["receiver_context_sha256s"], {"calibration", "validation"}, "preserved receiver contexts")
    for item in value["receiver_context_sha256s"].values():
        sha(item)
    ids = value["ordered_case_identities"]
    need(type(ids) is list and all(type(i) is str for i in ids) and len(ids) == len(set(ids)) == 151, "Exact distinct 151-case basis required")
    for item in ids:
        sha(item)
    bindings = value["case_bindings"]
    need(type(bindings) is list and len(bindings) == 151, "Exact 151-case bindings required")
    seeds = set()
    for ordinal, binding in enumerate(bindings):
        fields(binding, {"identity", "role", "context_sha256", "source_contract_sha256", "noise_law_sha256", "seed", "recipe_kind", "recipe_sha256"}, "basis case")
        role = "calibration" if ordinal < 127 else "evaluation"
        context_role = "calibration" if ordinal < 127 else "validation"
        need(binding["identity"] == ids[ordinal] and binding["role"] == role, "Case order/role substituted")
        need(binding["source_contract_sha256"] == value["source_metadata_sha256"]
             and binding["context_sha256"] == value["receiver_context_sha256s"][context_role], "Case source/context substituted")
        sha(binding["noise_law_sha256"])
        sha(binding["recipe_sha256"])
        need(binding["recipe_kind"] == "noise_only" if ordinal < 127 else binding["recipe_kind"] in
             ("on_signal", "matched_on_off", "single_adjacent_off", "noise_null"), "Fixed recipe kind required")
        integer(binding["seed"], 2**64-1, "seed")
        need(binding["seed"] not in seeds, "Duplicate proposed seed")
        seeds.add(binding["seed"])


def _typed(doc, schema, domain, extra):
    fields(doc, {"schema", "evidence_domain"} | set(extra), schema)
    need(doc["schema"] == schema and doc["evidence_domain"] == domain, "Wrong typed evidence; candidate/engineering evidence refused")


def _runtime(value):
    fields(value, RUNTIME_KEYS, "runtime identity")
    for key in RUNTIME_KEYS - {"python_executable_sha256"}:
        need(type(value[key]) is str and re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", value[key]), "Exact runtime version required")
    sha(value["python_executable_sha256"])


def _public_chain(chain, pins):
    fields(chain, STAGES, "independent publication chain")
    seen = set()
    for ordinal, stage in enumerate(STAGES):
        anchor = chain[stage]
        fields(anchor, {"commit", "tree", "parents", "document_sha256s"}, "external publication anchor")
        sha(anchor["commit"], 40); sha(anchor["tree"], 40)
        need(anchor["commit"] not in seen, "Distinct publication commits required")
        seen.add(anchor["commit"])
        parents = anchor["parents"]
        need(type(parents) is list and len(parents) <= 1, "Single-parent immutable chain required")
        for parent in parents:
            sha(parent, 40)
        if ordinal:
            need(parents == [chain[STAGES[ordinal-1]]["commit"]], "Immutable stage parent differs")
        expected = {name: pins[name]["sha256"] for name in STAGE_DOCUMENTS[stage]}
        need(same(anchor["document_sha256s"], expected), "Externally pinned stage documents differ")


_VERIFICATION_TOKEN = object()


@dataclass(frozen=True, init=False)
class VerifiedClosure:
    """Immutable evidence result, never a reservation or execution capability."""
    payload: bytes

    def __init__(self, payload, *, _permit=None):
        need(_permit is _VERIFICATION_TOKEN, "Only complete validation can issue VerifiedClosure")
        object.__setattr__(self, "payload", bytes(payload))

    def record(self):
        doc = parse(self.payload)
        need(canonical(doc) == self.payload, "Verification receipt changed")
        return doc


def validate_scientific_closure(raw_documents, expected_raw_pins, *, expected_basis, expected_publication_chain,
        expected_execution_inventory, expected_dependency_edges, expected_runtime_identity):
    """Verify one complete detached evidence DAG; no default trust anchors.

    Public anchors must come from an independently authenticated publication
    readback. This function does not fetch GitHub or prove those anchors itself.
    """
    docs = _authenticate(raw_documents, expected_raw_pins)
    _basis(expected_basis)
    _public_chain(expected_publication_chain, expected_raw_pins)
    h = {name: pin["sha256"] for name, pin in expected_raw_pins.items()}
    basis_sha = digest(expected_basis)
    domain = docs["basis"].get("evidence_domain")
    need(domain in ("public-scientific-evidence", "synthetic-test-fixture"), "Scientific evidence domain required")
    b = docs["basis"]
    _typed(b, "radio-preserved-scientific-basis-v1", domain, {"basis"})
    need(same(b["basis"], expected_basis), "Preserved basis differs from independent identities")
    limits = docs["limits"]
    _typed(limits, "radio-source-scientific-exact-limits-v1", domain, {"scientific", "acquisition", "stop_date", "refund_policy"})
    need(same(limits["scientific"], SCIENTIFIC_LIMITS) and same(limits["acquisition"], ACQUISITION_LIMITS), "Exact scientific/acquisition limits changed")
    need(limits["stop_date"] == "2026-10-09" and limits["refund_policy"] == "no-refund-no-retry-no-resume", "Closure boundary changed")
    protocol = docs["trial_protocol"]
    _typed(protocol, "radio-source-specific-detached-trial-protocol-v1", domain,
           {"basis_sha256", "limits_sha256", "source_inventory_sha256", "search", "rank", "evaluation_recipes", "pilot", "status"})
    need(protocol["status"] == "FROZEN_BEFORE_VALUES" and protocol["basis_sha256"] == basis_sha
         and protocol["limits_sha256"] == h["limits"] and protocol["source_inventory_sha256"] == expected_basis["source_inventory_sha256"], "Protocol basis/limits/freeze differs")
    need(same(protocol["search"], {"rate_tenths": list(range(-40,41)), "widths_channels": [1,3,5,9,17,33,65,129],
        "activity_subsets": [[0,1],[0,2],[1,2],[0,1,2]], "minimum_active_epoch_snr":3, "stack_statistic":"sum", "primary":"neighbor9"}), "Search scope changed")
    need(same(protocol["rank"], {"reference_count":127,"denominator":128,"floor_snr":10,"inclusive_numerator":"1 + count(reference >= observed member)",
        "ceiling":[1,100],"keep_every_empty":True,"ties_randomized":False}), "Rank/EMPTY semantics changed")
    need(same(protocol["evaluation_recipes"], {"on_signal":10,"matched_on_off":10,"single_adjacent_off":2,"noise_null":2}), "Evaluation cohort changed")
    need(same(protocol["pilot"], {"source":"HIP98505","cadence_id":85030,"role":"pilot","scans":list(LABELS),
         "maximum_trials":1,"settings_selected_by_evaluation":False,"flux_or_eirp_claim_authorized":False}), "Pilot scope changed")
    codec = docs["codec_certificate"]
    _typed(codec, "radio-source-specific-codec-runtime-case-law-certificate-v1", domain,
        {"basis_sha256","runtime_identity","source_profile","case_laws","normalization_receiver_handoffs"})
    need(codec["basis_sha256"] == basis_sha, "Codec source basis differs")
    _runtime(codec["runtime_identity"])
    need(same(codec["source_profile"], {"shape":[16,1,264503296],"chunks":[1,1,1048576],"dtype":"<f4","filter_pipeline":[[32008,1,[0,3,4,0,2]]]}), "Source codec profile substituted")
    expected_laws = [{"name":name,"expected":"accept" if i<4 else "reject","observed":"accept" if i<4 else "reject"} for i,name in enumerate(LAW_NAMES)]
    need(same(codec["case_laws"], expected_laws), "Complete codec case-law outcomes required")
    handoffs = codec["normalization_receiver_handoffs"]
    need(type(handoffs) is list and len(handoffs) == 12, "Both six-scan receiver handoffs required")
    for row, pair in zip(handoffs, [(r,s) for r in ("calibration","validation") for s in LABELS], strict=True):
        fields(row, {"role","scan","receiver_context_sha256","receiver_bank_sha256","raw_row_sha256s","normalized_row_sha256s"}, "receiver handoff")
        role, scan = pair
        need(row["role"] == role and row["scan"] == scan and row["receiver_context_sha256"] == expected_basis["receiver_context_sha256s"][role]
             and row["receiver_bank_sha256"] == expected_basis["receiver_bank_sha256s"][role], "Receiver handoff ancestry differs")
        for key in ("raw_row_sha256s","normalized_row_sha256s"):
            need(type(row[key]) is list and len(row[key]) == 16, "Complete 16-row handoff required")
            for item in row[key]: sha(item)
    host = docs["hosted_transport"]
    _typed(host, "radio-actual-hosted-native-transport-certificate-v1", domain,
        {"basis_sha256","runtime_identity","profiles","receipt_inventory_sha256"})
    need(host["basis_sha256"] == basis_sha and same(host["runtime_identity"], codec["runtime_identity"]), "Hosted native runtime/basis differs")
    sha(host["receipt_inventory_sha256"])
    need(type(host["profiles"]) is list and len(host["profiles"]) == 2, "Both scientific phase transport profiles required")
    for row, role in zip(host["profiles"], ("calibration","evaluation"), strict=True):
        fields(row, {"role","outcome","milliseconds","artifact_bytes","peak_rss_bytes","sdk_calls","connector_calls","git_processes",
            "raw_request_bytes","raw_response_bytes","host_receipts_bytes","native_receipt_sha256","host_receipt_sha256","caller_receipt_sha256"}, "actual hosted profile")
        need(row["role"] == role and row["outcome"] == "completed", "Hosted profile incomplete")
        integer(row["milliseconds"], SCIENTIFIC_LIMITS["reference_milliseconds" if role=="calibration" else "evaluation_milliseconds"], "host time")
        integer(row["artifact_bytes"], SCIENTIFIC_LIMITS["reference_bytes" if role=="calibration" else "evaluation_bytes"], "host evidence")
        integer(row["peak_rss_bytes"], 512*MIB, "host RSS", 1)
        for key, maximum in (("sdk_calls",64),("connector_calls",64),("git_processes",4),("raw_request_bytes",48*MIB),("raw_response_bytes",64*MIB),("host_receipts_bytes",192*MIB)):
            integer(row[key],maximum,key,1)
        for key in ("native_receipt_sha256","host_receipt_sha256","caller_receipt_sha256"): sha(row[key])
    freeze = docs["executable_freeze"]
    fields(freeze, {"schema","domain","mode","status","inventory","role_inventories","dependency_edges","runtime_identity","limits",
        "source_contract_sha256","trial_protocol_sha256","codec_certificate_sha256","scientific_execution_authorized","scientific_allocation_charged"}, "scientific executable freeze")
    need(freeze["schema"] == "radio-scientific-executable-freeze-v1" and freeze["domain"] == domain
         and freeze["mode"] == "SCIENTIFIC_EXECUTABLE_ONLY" and freeze["status"] == "QUALIFIED"
         and freeze["scientific_execution_authorized"] is False and freeze["scientific_allocation_charged"] is False, "Prospective/engineering freeze refused")
    need(freeze["source_contract_sha256"] == expected_basis["source_metadata_sha256"]
        and freeze["trial_protocol_sha256"] == h["trial_protocol"] and freeze["codec_certificate_sha256"] == h["codec_certificate"]
        and same(freeze["runtime_identity"],codec["runtime_identity"]) and same(freeze["runtime_identity"],expected_runtime_identity), "Complete freeze bindings differ")
    freeze_limits = {"calibration":{"count":127,"milliseconds":40000,"artifact_bytes":4*MIB},
        "evaluation":{"count":24,"milliseconds":80000,"artifact_bytes":18*MIB},"overhead_milliseconds":200000,
        "ledger_bytes":8*MIB,"failure_and_summary_bytes":76*MIB,"total_milliseconds":7200000,
        "total_evidence_bytes":1024**3,"rss_bytes":512*MIB,"modelled_array_bytes":256*MIB}
    need(same(freeze["limits"],freeze_limits), "Executable scientific limits changed")
    need(type(expected_execution_inventory) is dict and expected_execution_inventory and same(freeze["inventory"],expected_execution_inventory)
        and same(freeze["dependency_edges"],expected_dependency_edges), "Independent complete inventory/ELF graph differs")
    inventory = {}
    locations = set()
    for identity,row in freeze["inventory"].items():
        fields(row, {"path","bytes","sha256","role","mode","location"}, "executable inventory")
        need(type(row["role"]) is str and row["role"] in ("code","input","runtime","plugin","elf"), "Exact executable role required")
        need(type(identity) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}",identity),"Plain file identity required")
        need(type(row["path"]) is str and 0 < len(row["path"]) <= 4096 and not any(ord(c)<32 for c in row["path"])
             and "\\" not in row["path"] and all(p not in ("",".","..") for p in row["path"].split('/')[1 if row["path"].startswith('/') else 0:]), "Safe inventory path required")
        need(row["location"] in ("repository","runtime") and row["mode"] in ("100644","100755")
            and row["path"].startswith('/') == (row["location"] == "runtime"),"Ordinary file location/mode required")
        need((row["location"],row["path"]) not in locations,"Aliased inventory locations")
        locations.add((row["location"],row["path"]))
        integer(row["bytes"],2**40,"inventory bytes");sha(row["sha256"])
        inventory[identity] = row
    required_roles = {"code","input","runtime","plugin","elf"}
    need(0 < len(inventory) <= 100000 and {r["role"] for r in inventory.values()} == required_roles, "Transitive runtime/code/input roles incomplete")
    need(same(freeze["role_inventories"],{r:sorted(i for i,row in inventory.items() if row["role"]==r) for r in required_roles}),"Complete role inventory differs")
    native = {i for i,row in inventory.items() if row["role"] in ("elf","plugin")}
    fields(freeze["dependency_edges"],native,"complete ELF/plugin graph")
    for identity,edges in freeze["dependency_edges"].items():
        need(type(edges) is list and all(type(e) is str for e in edges) and edges == sorted(set(edges)) and all(e in native and e != identity for e in edges),"Unresolved/duplicate dependency edge")
        need(inventory[identity]["role"] != "plugin" or edges,"Plugin ELF dependency required")
    input_hashes = {row["sha256"] for row in inventory.values() if row["role"] == "input"}
    need({h["basis"],h["hosted_transport"],h["limits"],h["trial_protocol"],h["codec_certificate"],
          expected_basis["source_metadata_sha256"],expected_basis["window_design_sha256"],expected_basis["window_contract_sha256"],
          expected_basis["receiver_bank_records_sha256"],expected_basis["proposal_sha256"]} <= input_hashes,"All immutable scientific basis and admission inputs must be frozen")
    allocation = docs["scientific_allocation"]
    _typed(allocation, "radio-fresh-scientific-12724-allocation-v1", domain,
        {"basis_sha256","freeze_commit","freeze_sha256","limits_sha256","protocol_sha256","namespace","cases","refund_policy"})
    need(allocation["basis_sha256"] == basis_sha and allocation["freeze_commit"] == expected_publication_chain["freeze"]["commit"]
         and allocation["freeze_sha256"] == h["executable_freeze"] and allocation["limits_sha256"] == h["limits"] and allocation["protocol_sha256"] == h["trial_protocol"], "Fresh allocation freeze differs")
    need(type(allocation["namespace"]) is str and re.fullmatch(r"radio-scientific-[a-z0-9-]{1,80}", allocation["namespace"])
         and allocation["refund_policy"] == "no-refund-no-retry-no-resume", "Fresh allocation domain required")
    need(type(allocation["cases"]) is list and len(allocation["cases"]) == 151, "Complete scientific allocation required")
    for row, binding in zip(allocation["cases"], expected_basis["case_bindings"], strict=True):
        fields(row, {"binding","plan_sha256","milliseconds","artifact_bytes"}, "allocated case")
        need(same(row["binding"],binding), "Allocated preserved case substituted")
        sha(row["plan_sha256"])
        ref = binding["role"] == "calibration"
        need(type(row["milliseconds"]) is int and row["milliseconds"] == (40000 if ref else 80000)
             and type(row["artifact_bytes"]) is int and row["artifact_bytes"] == (4*MIB if ref else 18*MIB), "Scientific quota transferred or enlarged")
    result = docs["scientific_result"]
    _typed(result, "radio-complete-scientific-12724-result-certificate-v1", domain,
        {"basis_sha256","allocation_commit","allocation_sha256","freeze_sha256","cases","overhead","threshold","evaluation_gates"})
    need(result["basis_sha256"] == basis_sha and result["allocation_commit"] == expected_publication_chain["allocation"]["commit"]
        and result["allocation_sha256"] == h["scientific_allocation"] and result["freeze_sha256"] == h["executable_freeze"], "Scientific result provenance differs")
    need(type(result["cases"]) is list and len(result["cases"]) == 151, "All 151 actual cases required")
    maxima = []
    for ordinal, (row, allocated) in enumerate(zip(result["cases"], allocation["cases"], strict=True)):
        fields(row, {"identity","plan_sha256","role","outcome","milliseconds","artifact_bytes","peak_rss_bytes","normal_calls","visited_hypotheses","scored_cells","eligible_cells","maximum","raw_evidence_sha256"}, "scientific outcome")
        binding = allocated["binding"]
        need(row["identity"] == binding["identity"] and row["role"] == binding["role"] and row["plan_sha256"] == allocated["plan_sha256"]
             and row["outcome"] == "completed", "Scientific case incomplete or substituted")
        integer(row["milliseconds"],allocated["milliseconds"],"science time")
        integer(row["artifact_bytes"],allocated["artifact_bytes"],"science evidence")
        integer(row["peak_rss_bytes"],512*MIB,"science RSS",1)
        need(type(row["normal_calls"]) is int and row["normal_calls"] == 96 and type(row["visited_hypotheses"]) is int and row["visited_hypotheses"] == 2592
             and type(row["scored_cells"]) is int and row["scored_cells"] == 209952, "Full native Gaussian score family required")
        integer(row["eligible_cells"],209952,"eligible cells")
        maximum = row["maximum"]
        fields(maximum, {"kind","value"}, "typed maximum")
        if maximum["kind"] == "empty":
            need(maximum["value"] is None and row["eligible_cells"] == 0, "EMPTY differs from complete eligibility")
        else:
            need(maximum["kind"] == "finite" and type(maximum["value"]) in (int,float) and math.isfinite(maximum["value"]) and row["eligible_cells"] > 0, "Finite maximum required")
        sha(row["raw_evidence_sha256"])
        if ordinal < 127: maxima.append(maximum)
    threshold = max([10] + [m["value"] for m in maxima if m["kind"] == "finite"])
    need(type(result["threshold"]) in (int,float) and result["threshold"] == threshold, "Complete empty-aware threshold differs")
    fields(result["overhead"], {"milliseconds","ledger_bytes","failure_summary_bytes"}, "actual overhead")
    for key, maximum in (("milliseconds",200000),("ledger_bytes",8*MIB),("failure_summary_bytes",76*MIB)):
        integer(result["overhead"][key],maximum,"overhead "+key)
    gates = result["evaluation_gates"]
    need(type(gates) is list and len(gates) == 24, "Complete 24-case evaluation gates required")
    need(all(type(row) is dict and type(row.get("kind")) is str for row in gates), "Typed evaluation gate kind required")
    expected_kinds = ["on_signal"]*10 + ["matched_on_off"]*10 + ["single_adjacent_off"]*2 + ["noise_null"]*2
    # Order is authenticated explicitly in the trial protocol and allocation.
    need(sorted(row.get("kind","") for row in gates) == sorted(expected_kinds), "Fixed evaluation kind counts differ")
    for gate_ordinal,(row, case) in enumerate(zip(gates,result["cases"][127:],strict=True)):
        fields(row, {"identity","kind","final_members","associated_final_members","unassociated_final_members","final_clusters","associated_final_clusters","unassociated_final_clusters","width65_unassociated","width129_unassociated","raw_decision_partition_sha256"}, "evaluation gate")
        need(row["identity"] == case["identity"], "Evaluation gate case order differs")
        need(row["kind"] == expected_basis["case_bindings"][127+gate_ordinal]["recipe_kind"], "Frozen per-case truth recipe substituted")
        for key in ("final_members","associated_final_members","unassociated_final_members","final_clusters","associated_final_clusters","unassociated_final_clusters","width65_unassociated","width129_unassociated"):
            integer(row[key],10000,key)
        need(row["associated_final_members"]+row["unassociated_final_members"] == row["final_members"]
             and row["associated_final_clusters"] <= row["final_clusters"] and row["unassociated_final_clusters"] <= row["final_clusters"], "Complete decision counts differ")
        need((row["final_members"] == 0) == (row["final_clusters"] == 0)
            and row["final_clusters"] <= row["final_members"]
            and row["associated_final_clusters"]+row["unassociated_final_clusters"] >= row["final_clusters"], "Complete cluster coverage differs")
        if row["final_members"]:
            need(case["maximum"]["kind"] == "finite" and case["maximum"]["value"] >= threshold
                 and case["eligible_cells"] > 0, "Retained decision contradicts eligible maximum")
            need(all(m["kind"] == "empty" or m["value"] < case["maximum"]["value"] for m in maxima),
                 "Inclusive 1/128 rank rejects a tie with any reference maximum")
        if row["kind"] == "on_signal":
            need(row["associated_final_members"] >= 1 and row["associated_final_clusters"] >= 1, "Recovery gate failed")
        else:
            need(row["final_members"] == row["final_clusters"] == 0 and row["width65_unassociated"] == row["width129_unassociated"] == 0, "RFI/null/broad-width gate failed")
        sha(row["raw_decision_partition_sha256"])
    pilot = docs["pilot_contract"]
    _typed(pilot, "radio-detached-executable-source-admission-v1", domain,
        {"basis_sha256","result_commit","result_sha256","protocol_sha256","runtime_identity","source_inventory_sha256","role","window_identity","receiver_bank_sha256","receiver_context_sha256","maximum_trials"})
    need(pilot["basis_sha256"] == basis_sha and pilot["result_commit"] == expected_publication_chain["result"]["commit"]
         and pilot["result_sha256"] == h["scientific_result"] and pilot["protocol_sha256"] == h["trial_protocol"]
         and same(pilot["runtime_identity"],freeze["runtime_identity"]) and pilot["source_inventory_sha256"] == expected_basis["source_inventory_sha256"]
         and pilot["role"] == "pilot" and pilot["window_identity"] == expected_basis["window_identities"]["pilot"]
         and pilot["receiver_bank_sha256"] == expected_basis["receiver_bank_sha256s"]["pilot"]
         and type(pilot["maximum_trials"]) is int and pilot["maximum_trials"] == 1, "Detached pilot contract ancestry/scope differs")
    sha(pilot["receiver_context_sha256"])
    ledger = docs["acquisition_ledger"]
    _typed(ledger, "radio-fresh-source-acquisition-ledger-v1", domain,
        {"pilot_commit","contract_sha256","source_inventory_sha256","location","total_limits","reservations"})
    need(ledger["pilot_commit"] == expected_publication_chain["pilot"]["commit"] and ledger["contract_sha256"] == h["pilot_contract"]
         and ledger["source_inventory_sha256"] == expected_basis["source_inventory_sha256"], "Acquisition ledger contract differs")
    fields(ledger["location"], {"kind","repository","branch","path"}, "new durable acquisition location")
    need(ledger["location"]["kind"] == "github-published-scientific" and ledger["location"]["repository"] == "andersenmartin-blip/setisearch"
         and ledger["location"]["branch"] == "m43-support-qualification" and type(ledger["location"]["path"]) is str
         and re.fullmatch(r"results_radio_scientific_[a-z0-9_]+/acquisition-ledger.json",ledger["location"]["path"]), "Old/synthetic acquisition store refused")
    ledger_revision = expected_publication_chain["acquisition"]["commit"]
    need(same(ledger["total_limits"], ACQUISITION_LIMITS), "Acquisition ceilings changed")
    need(type(ledger["reservations"]) is list and 1 <= len(ledger["reservations"]) <= 3, "Fresh irrevocable source reservation required")
    sessions, reserved_roles = set(), set()
    for ordinal,row in enumerate(ledger["reservations"]):
        fields(row,{"ordinal","session_id","role","requests","bytes","seconds","prior_document_sha256"},"source reservation")
        need(type(row["ordinal"]) is int and row["ordinal"] == ordinal and row["role"] in ROLES and row["role"] not in reserved_roles, "Distinct source role reservation/order required")
        reserved_roles.add(row["role"])
        sha(row["session_id"]);sha(row["prior_document_sha256"])
        previous = {**ledger,"reservations":ledger["reservations"][:ordinal]}
        need(row["prior_document_sha256"] == digest(previous),"Acquisition reservation parent differs")
        need(row["session_id"] not in sessions,"Duplicate source session");sessions.add(row["session_id"])
        for key,maximum in (("requests",500),("bytes",512*MIB),("seconds",1200)):
            integer(row[key],maximum,"source quota "+key,1)
    trial = docs["trial_allocation"]
    _typed(trial,"radio-fresh-irrevocable-pilot-trial-allocation-v1",domain,
        {"acquisition_commit","pilot_contract_sha256","acquisition_ledger_sha256","protocol_sha256","case_identity","session_id","role","refund_policy"})
    need(trial["acquisition_commit"] == ledger_revision and trial["pilot_contract_sha256"] == h["pilot_contract"]
         and trial["acquisition_ledger_sha256"] == h["acquisition_ledger"] and trial["protocol_sha256"] == h["trial_protocol"]
         and trial["session_id"] == ledger["reservations"][-1]["session_id"] and trial["role"] == ledger["reservations"][-1]["role"] == "pilot"
         and trial["refund_policy"] == "no-refund-no-retry-no-resume", "Pilot allocation/current source session differs")
    sha(trial["case_identity"])
    need(trial["case_identity"] not in expected_basis["ordered_case_identities"], "Scientific case reused as pilot")
    record = {"schema":"radio-detached-scientific-admission-verification-v1","evidence_domain":domain,
        "evidence_closure_verified":True,"scientific_readiness":domain == "public-scientific-evidence",
        "execution_authority_issued":False,"basis_sha256":basis_sha,"basis":expected_basis,
        "document_sha256s":h,"publication_chain_sha256":digest(expected_publication_chain),
        "runtime_identity":freeze["runtime_identity"],"new_executable_source_contract_sha256":h["pilot_contract"],
        "acquisition_ledger_sha256":h["acquisition_ledger"],"acquisition_ledger_revision":ledger_revision,
        "pilot_receiver_context_sha256":pilot["receiver_context_sha256"],
        "acquisition_session_bindings":[{k:r[k] for k in ("ordinal","session_id","role","requests","bytes","seconds")} for r in ledger["reservations"]],
        "trial_case_identity":trial["case_identity"],"trial_session_identity":trial["session_id"],
        "trial_protocol_sha256":h["trial_protocol"],"trial_allocation_sha256":h["trial_allocation"],
        "scientific_limits":SCIENTIFIC_LIMITS,"acquisition_limits":ACQUISITION_LIMITS}
    return VerifiedClosure(canonical(record), _permit=_VERIFICATION_TOKEN)
