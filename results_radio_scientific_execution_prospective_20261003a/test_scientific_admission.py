"""In-memory synthetic evidence; no actual certificate, case, RNG or store."""
import copy
import hashlib
import importlib.util
import json
import io
import os
from pathlib import Path
import socket
import subprocess
import types
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("scientific_admission_tested", Path(__file__).with_name("scientific_admission.py"))
admission = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = admission
spec.loader.exec_module(admission)


def H(text):
    return hashlib.sha256(text.encode()).hexdigest()


def make_fixture():
    """Tiny, clearly fictitious 151 metadata records, never actual outcomes."""
    a = admission
    domain = "synthetic-test-fixture"
    basis = {k:H(k) for k in ("source_inventory_sha256","source_metadata_sha256","window_design_sha256",
        "window_contract_sha256","receiver_bank_records_sha256","proposal_sha256")}
    basis.update(window_identities={r:H("window/"+r) for r in a.ROLES},
        receiver_bank_sha256s={r:H("bank/"+r) for r in a.ROLES},
        receiver_context_sha256s={r:H("context/"+r) for r in ("calibration","validation")},
        ordered_case_identities=[H("case/"+str(i)) for i in range(151)])
    kinds = ["noise_only"]*127 + ["noise_null"]*2 + ["on_signal"]*10 + ["matched_on_off"]*10 + ["single_adjacent_off"]*2
    basis["case_bindings"] = [{"identity":identity,"role":"calibration" if i<127 else "evaluation",
        "context_sha256":basis["receiver_context_sha256s"]["calibration" if i<127 else "validation"],
        "source_contract_sha256":basis["source_metadata_sha256"],"noise_law_sha256":H("noise-law"),
        "seed":10000+i,"recipe_kind":kinds[i],"recipe_sha256":H("recipe/"+str(i))}
        for i,identity in enumerate(basis["ordered_case_identities"])]
    runtime = {"python":"3.12.14","numpy":"2.3.5","h5py":"3.16.0","hdf5":"2.0.0","hdf5plugin":"7.1.0","python_executable_sha256":H("python")}
    def typed(schema, **values):
        return {"schema":schema,"evidence_domain":domain,**copy.deepcopy(values)}
    docs = {"basis":typed("radio-preserved-scientific-basis-v1",basis=copy.deepcopy(basis)),
        "limits":typed("radio-source-scientific-exact-limits-v1",scientific=copy.deepcopy(a.SCIENTIFIC_LIMITS),acquisition=copy.deepcopy(a.ACQUISITION_LIMITS),stop_date="2026-10-09",refund_policy="no-refund-no-retry-no-resume")}
    docs["trial_protocol"] = typed("radio-source-specific-detached-trial-protocol-v1",basis_sha256="",limits_sha256="",
        source_inventory_sha256=basis["source_inventory_sha256"],status="FROZEN_BEFORE_VALUES",
        search={"rate_tenths":list(range(-40,41)),"widths_channels":[1,3,5,9,17,33,65,129],"activity_subsets":[[0,1],[0,2],[1,2],[0,1,2]],"minimum_active_epoch_snr":3,"stack_statistic":"sum","primary":"neighbor9"},
        rank={"reference_count":127,"denominator":128,"floor_snr":10,"inclusive_numerator":"1 + count(reference >= observed member)","ceiling":[1,100],"keep_every_empty":True,"ties_randomized":False},
        evaluation_recipes={"on_signal":10,"matched_on_off":10,"single_adjacent_off":2,"noise_null":2},
        pilot={"source":"HIP98505","cadence_id":85030,"role":"pilot","scans":list(a.LABELS),"maximum_trials":1,"settings_selected_by_evaluation":False,"flux_or_eirp_claim_authorized":False})
    docs["codec_certificate"] = typed("radio-source-specific-codec-runtime-case-law-certificate-v1",basis_sha256="",runtime_identity=runtime,
        source_profile={"shape":[16,1,264503296],"chunks":[1,1,1048576],"dtype":"<f4","filter_pipeline":[[32008,1,[0,3,4,0,2]]]},
        case_laws=[{"name":name,"expected":"accept" if i<4 else "reject","observed":"accept" if i<4 else "reject"} for i,name in enumerate(a.LAW_NAMES)],
        normalization_receiver_handoffs=[{"role":r,"scan":s,"receiver_context_sha256":basis["receiver_context_sha256s"][r],
          "receiver_bank_sha256":basis["receiver_bank_sha256s"][r],"raw_row_sha256s":[H(f"raw/{r}/{s}/{i}") for i in range(16)],
          "normalized_row_sha256s":[H(f"normalized/{r}/{s}/{i}") for i in range(16)]} for r in ("calibration","validation") for s in a.LABELS])
    docs["hosted_transport"] = typed("radio-actual-hosted-native-transport-certificate-v1",basis_sha256="",runtime_identity=runtime,receipt_inventory_sha256=H("host-inventory"),
        profiles=[{"role":r,"outcome":"completed","milliseconds":100,"artifact_bytes":100,"peak_rss_bytes":1000,"sdk_calls":1,"connector_calls":1,"git_processes":1,
          "raw_request_bytes":100,"raw_response_bytes":100,"host_receipts_bytes":100,"native_receipt_sha256":H("native/"+r),"host_receipt_sha256":H("host/"+r),"caller_receipt_sha256":H("caller/"+r)} for r in ("calibration","evaluation")])
    docs["executable_freeze"] = {"schema":"radio-scientific-executable-freeze-v1","domain":domain,"mode":"SCIENTIFIC_EXECUTABLE_ONLY","status":"QUALIFIED",
        "inventory":{},"role_inventories":{},"dependency_edges":{"elf":[],"plugin":["elf"]},"runtime_identity":runtime,
        "limits":{"calibration":{"count":127,"milliseconds":40000,"artifact_bytes":4*a.MIB},"evaluation":{"count":24,"milliseconds":80000,"artifact_bytes":18*a.MIB},
          "overhead_milliseconds":200000,"ledger_bytes":8*a.MIB,"failure_and_summary_bytes":76*a.MIB,"total_milliseconds":7200000,"total_evidence_bytes":1024**3,"rss_bytes":512*a.MIB,"modelled_array_bytes":256*a.MIB},
        "source_contract_sha256":basis["source_metadata_sha256"],"trial_protocol_sha256":"","codec_certificate_sha256":"","scientific_execution_authorized":False,"scientific_allocation_charged":False}
    docs["scientific_allocation"] = typed("radio-fresh-scientific-12724-allocation-v1",basis_sha256="",freeze_commit="",freeze_sha256="",limits_sha256="",protocol_sha256="",namespace="radio-scientific-synthetic-fixture",refund_policy="no-refund-no-retry-no-resume",
        cases=[{"binding":copy.deepcopy(b),"plan_sha256":H("plan/"+str(i)),"milliseconds":40000 if i<127 else 80000,"artifact_bytes":4*a.MIB if i<127 else 18*a.MIB} for i,b in enumerate(basis["case_bindings"])])
    docs["scientific_result"] = typed("radio-complete-scientific-12724-result-certificate-v1",basis_sha256="",allocation_commit="",allocation_sha256="",freeze_sha256="",threshold=10,
        overhead={"milliseconds":100,"ledger_bytes":100,"failure_summary_bytes":100},
        cases=[{"identity":b["identity"],"plan_sha256":H("plan/"+str(i)),"role":b["role"],"outcome":"completed","milliseconds":100,"artifact_bytes":100,"peak_rss_bytes":1000,
          "normal_calls":96,"visited_hypotheses":2592,"scored_cells":209952,"eligible_cells":0,"maximum":{"kind":"empty","value":None},"raw_evidence_sha256":H("evidence/"+str(i))} for i,b in enumerate(basis["case_bindings"])],
        evaluation_gates=[{"identity":b["identity"],"kind":b["recipe_kind"],"final_members":1 if b["recipe_kind"]=="on_signal" else 0,"associated_final_members":1 if b["recipe_kind"]=="on_signal" else 0,
          "unassociated_final_members":0,"final_clusters":1 if b["recipe_kind"]=="on_signal" else 0,"associated_final_clusters":1 if b["recipe_kind"]=="on_signal" else 0,
          "unassociated_final_clusters":0,"width65_unassociated":0,"width129_unassociated":0,"raw_decision_partition_sha256":H("decision/"+b["identity"])} for b in basis["case_bindings"][127:]])
    docs["pilot_contract"] = typed("radio-detached-executable-source-admission-v1",basis_sha256="",result_commit="",result_sha256="",protocol_sha256="",runtime_identity=runtime,
        source_inventory_sha256=basis["source_inventory_sha256"],role="pilot",window_identity=basis["window_identities"]["pilot"],receiver_bank_sha256=basis["receiver_bank_sha256s"]["pilot"],receiver_context_sha256=H("context/pilot"),maximum_trials=1)
    docs["acquisition_ledger"] = typed("radio-fresh-source-acquisition-ledger-v1",pilot_commit="",contract_sha256="",source_inventory_sha256=basis["source_inventory_sha256"],
        location={"kind":"github-published-scientific","repository":"andersenmartin-blip/setisearch","branch":"m43-support-qualification","path":"results_radio_scientific_fixture/acquisition-ledger.json"},
        total_limits=copy.deepcopy(a.ACQUISITION_LIMITS),reservations=[{"ordinal":i,"session_id":H("session/"+r),"role":r,"requests":500,"bytes":512*a.MIB,"seconds":1200,"prior_document_sha256":""} for i,r in enumerate(a.ROLES)])
    docs["trial_allocation"] = typed("radio-fresh-irrevocable-pilot-trial-allocation-v1",acquisition_commit="",pilot_contract_sha256="",acquisition_ledger_sha256="",protocol_sha256="",
        case_identity=H("pilot-trial"),session_id=H("session/pilot"),role="pilot",refund_policy="no-refund-no-retry-no-resume")
    for row,binding in zip(docs["scientific_result"]["cases"],basis["case_bindings"],strict=True):
        if binding["recipe_kind"] == "on_signal":
            row.update(eligible_cells=1,maximum={"kind":"finite","value":15})
    return Fixture(docs,basis)


class Fixture:
    def __init__(self, docs, basis):
        self.docs, self.basis = docs, basis

    def seal(self):
        """Fixture-only coherent repinning, not a production trust producer."""
        a, d = admission, self.docs
        commit = {s:hashlib.sha1(("FAKE TEST COMMIT/"+s).encode()).hexdigest() for s in a.STAGES}
        hs = lambda name: hashlib.sha256(a.canonical(d[name])+b"\n").hexdigest()
        bs = a.digest(self.basis)
        d["trial_protocol"].update(basis_sha256=bs,limits_sha256=hs("limits"))
        d["codec_certificate"]["basis_sha256"] = bs
        d["hosted_transport"]["basis_sha256"] = bs
        freeze = d["executable_freeze"]
        freeze.update(trial_protocol_sha256=hs("trial_protocol"),codec_certificate_sha256=hs("codec_certificate"))
        inputs = {"basis":hs("basis"),"host":hs("hosted_transport"),"limits":hs("limits"),"protocol":hs("trial_protocol"),"codec":hs("codec_certificate")}
        inputs.update({k:self.basis[k] for k in ("source_metadata_sha256","window_design_sha256","window_contract_sha256","receiver_bank_records_sha256","proposal_sha256")})
        inventory = {k:{"role":"input","location":"repository","path":"fixture/"+k+".json","mode":"100644","bytes":1,"sha256":v} for k,v in inputs.items()}
        for role in ("code","runtime","elf","plugin"):
            inventory[role]={"role":role,"location":"repository" if role=="code" else "runtime","path":("fixture/" if role=="code" else "/test/")+role,"mode":"100644","bytes":1,"sha256":H("file/"+role)}
        freeze["inventory"] = inventory
        freeze["role_inventories"] = {r:sorted(i for i,row in inventory.items() if row["role"]==r) for r in ("code","input","runtime","elf","plugin")}
        d["scientific_allocation"].update(basis_sha256=bs,freeze_commit=commit["freeze"],freeze_sha256=hs("executable_freeze"),limits_sha256=hs("limits"),protocol_sha256=hs("trial_protocol"))
        d["scientific_result"].update(basis_sha256=bs,allocation_commit=commit["allocation"],allocation_sha256=hs("scientific_allocation"),freeze_sha256=hs("executable_freeze"))
        d["pilot_contract"].update(basis_sha256=bs,result_commit=commit["result"],result_sha256=hs("scientific_result"),protocol_sha256=hs("trial_protocol"))
        ledger=d["acquisition_ledger"]
        ledger.update(pilot_commit=commit["pilot"],contract_sha256=hs("pilot_contract"))
        for i,row in enumerate(ledger["reservations"]):
            row["prior_document_sha256"] = a.digest({**ledger,"reservations":ledger["reservations"][:i]})
        d["trial_allocation"].update(acquisition_commit=commit["acquisition"],pilot_contract_sha256=hs("pilot_contract"),acquisition_ledger_sha256=hs("acquisition_ledger"),protocol_sha256=hs("trial_protocol"))
        raw = {k:a.canonical(v)+b"\n" for k,v in d.items()}
        pins = {k:{"bytes":len(v),"sha256":hashlib.sha256(v).hexdigest()} for k,v in raw.items()}
        chain = {s:{"commit":commit[s],"tree":hashlib.sha1(("FAKE TEST TREE/"+s).encode()).hexdigest(),"parents":[] if i==0 else [commit[a.STAGES[i-1]]],
            "document_sha256s":{k:pins[k]["sha256"] for k in a.STAGE_DOCUMENTS[s]}} for i,s in enumerate(a.STAGES)}
        return {"raw_documents":raw,"expected_raw_pins":pins,"expected_basis":copy.deepcopy(self.basis),"expected_publication_chain":chain,
            "expected_execution_inventory":copy.deepcopy(inventory),"expected_dependency_edges":copy.deepcopy(freeze["dependency_edges"]),"expected_runtime_identity":copy.deepcopy(freeze["runtime_identity"])}


class AdmissionTests(unittest.TestCase):
    def refused(self, mutate, pattern=None):
        f=make_fixture();mutate(f);packet=f.seal()
        with self.assertRaisesRegex(ValueError,pattern or ".+"):
            admission.validate_scientific_closure(**packet)

    def test_complete_synthetic_fixture_has_no_scientific_readiness(self):
        record=admission.validate_scientific_closure(**make_fixture().seal()).record()
        self.assertTrue(record["evidence_closure_verified"])
        self.assertFalse(record["scientific_readiness"])
        self.assertFalse(record["execution_authority_issued"])

    def test_coherently_repinned_resource_change_allowed_within_caps(self):
        f=make_fixture();f.docs["scientific_result"]["cases"][0]["milliseconds"]=39999
        self.assertFalse(admission.validate_scientific_closure(**f.seal()).record()["scientific_readiness"])

    def test_all_three_downstream_bindings_have_no_forward_hash_reference(self):
        f=make_fixture();packet=f.seal()
        admission.validate_scientific_closure(**packet)
        self.assertNotIn("revision",f.docs["acquisition_ledger"])
        self.assertNotIn("acquisition_ledger_sha256",f.docs["pilot_contract"])
        self.assertNotIn("result_sha256",f.docs["executable_freeze"])

    def test_raw_pin_and_independent_basis_not_self_derived(self):
        packet=make_fixture().seal();packet["expected_raw_pins"]["basis"]["sha256"]=H("wrong")
        with self.assertRaises(ValueError):admission.validate_scientific_closure(**packet)
        packet=make_fixture().seal();packet["expected_basis"]["source_metadata_sha256"]=H("other-source")
        with self.assertRaises(ValueError):admission.validate_scientific_closure(**packet)

    def test_duplicate_json_and_nonfinite_rejected_even_with_matching_raw_pin(self):
        for raw in (b'{"schema":1,"schema":2}',b'{"x":1e999}',b'{"x":NaN}'):
            p=make_fixture().seal();p["raw_documents"]["basis"]=raw;p["expected_raw_pins"]["basis"]={"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
            with self.assertRaises(ValueError):admission.validate_scientific_closure(**p)

    def test_candidate_and_engineering_types_refused(self):
        for key in ("codec_certificate","hosted_transport","scientific_result","pilot_contract"):
            with self.subTest(key=key):self.refused(lambda f:f.docs[key].update(evidence_domain="candidate-only"))
        self.refused(lambda f:f.docs["executable_freeze"].update(schema="radio-scientific-prospective-executable-freeze-v1",status="PENDING"))

    def test_boolean_limits_and_budget_increase_rejected_after_repinning(self):
        for key,value in (("reference_milliseconds",40001),("evaluation_bytes",19*admission.MIB),("reference_count",True),("total_milliseconds",7200001)):
            with self.subTest(key=key):self.refused(lambda f:f.docs["limits"]["scientific"].update({key:value}))

    def test_incomplete_cases_and_failed_outcomes_refused(self):
        self.refused(lambda f:f.docs["scientific_result"]["cases"].pop())
        self.refused(lambda f:f.docs["scientific_result"]["cases"][0].update(outcome="failed"))

    def test_case_scope_and_plan_substitution_refused(self):
        self.refused(lambda f:f.docs["scientific_allocation"]["cases"][0]["binding"].update(source_contract_sha256=H("substitute")))
        self.refused(lambda f:f.docs["scientific_result"]["cases"][0].update(plan_sha256=H("substitute")))

    def test_actual_case_resource_caps_and_type_preserved(self):
        for key,value in (("milliseconds",40001),("artifact_bytes",4*admission.MIB+1),("normal_calls",True),("peak_rss_bytes",512*admission.MIB+1)):
            with self.subTest(key=key):self.refused(lambda f:f.docs["scientific_result"]["cases"][0].update({key:value}))

    def test_empty_nonempty_and_threshold_semantics(self):
        self.refused(lambda f:f.docs["scientific_result"]["cases"][0].update(eligible_cells=1))
        self.refused(lambda f:f.docs["scientific_result"].update(threshold=11))
        f=make_fixture();f.docs["scientific_result"]["cases"][0].update(eligible_cells=1,maximum={"kind":"finite","value":12})
        f.docs["scientific_result"]["threshold"]=12
        admission.validate_scientific_closure(**f.seal())

    def test_inclusive_rank_ties_are_rejected_without_threshold_adjustment(self):
        f=make_fixture();r=f.docs["scientific_result"]
        r["cases"][0].update(eligible_cells=1,maximum={"kind":"finite","value":15});r["threshold"]=15
        with self.assertRaisesRegex(ValueError,"rank rejects a tie"):
            admission.validate_scientific_closure(**f.seal())
        for row in r["cases"][127:]:
            if row["maximum"]["kind"] == "finite":row["maximum"]["value"]=15.001
        admission.validate_scientific_closure(**f.seal())

    def test_per_case_truth_recipe_cannot_be_swapped_with_same_kind_counts(self):
        def mutate(f):
            g=f.docs["scientific_result"]["evaluation_gates"]
            g[0]["kind"],g[2]["kind"]=g[2]["kind"],g[0]["kind"]
        self.refused(mutate,"truth recipe")

    def test_recovery_and_zero_control_gates_are_computed_not_boolean_flags(self):
        self.refused(lambda f:f.docs["scientific_result"]["evaluation_gates"][2].update(associated_final_members=0,unassociated_final_members=1))
        self.refused(lambda f:f.docs["scientific_result"]["evaluation_gates"][0].update(final_members=1,unassociated_final_members=1))

    def test_runtime_codec_law_and_complete_handoff_binding(self):
        self.refused(lambda f:f.docs["codec_certificate"]["runtime_identity"].update(hdf5="99.0"))
        self.refused(lambda f:f.docs["codec_certificate"]["source_profile"]["filter_pipeline"][0][2].__setitem__(1,4))
        self.refused(lambda f:f.docs["codec_certificate"]["case_laws"][4].update(observed="accept"))
        self.refused(lambda f:f.docs["codec_certificate"]["normalization_receiver_handoffs"].pop())

    def test_offline_mock_cannot_supply_actual_hosted_profile(self):
        self.refused(lambda f:f.docs["hosted_transport"]["profiles"][0].update(connector_calls=0,sdk_calls=0,git_processes=0))

    def test_publication_anchors_and_external_freeze_inventory(self):
        p=make_fixture().seal();p["expected_publication_chain"]["allocation"]["parents"]=[]
        with self.assertRaises(ValueError):admission.validate_scientific_closure(**p)
        p=make_fixture().seal();p["expected_execution_inventory"]["plugin"]["sha256"]=H("other")
        with self.assertRaises(ValueError):admission.validate_scientific_closure(**p)

    def test_fresh_ledger_parent_scope_and_source_allocation(self):
        self.refused(lambda f:f.docs["acquisition_ledger"]["location"].update(path="results_radio_acquisition_2026-09-26/published_fixture_ledger.json"))
        self.refused(lambda f:f.docs["trial_allocation"].update(case_identity=f.basis["ordered_case_identities"][0]))
        self.refused(lambda f:f.docs["trial_allocation"].update(session_id=H("wrong-session")))
        p=make_fixture().seal();doc=json.loads(p["raw_documents"]["acquisition_ledger"]);doc["reservations"][1]["prior_document_sha256"]=H("wrong-parent")
        raw=admission.canonical(doc)+b"\n";p["raw_documents"]["acquisition_ledger"]=raw;p["expected_raw_pins"]["acquisition_ledger"]={"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
        p["expected_publication_chain"]["acquisition"]["document_sha256s"]["acquisition_ledger"]=p["expected_raw_pins"]["acquisition_ledger"]["sha256"]
        with self.assertRaisesRegex(ValueError,"reservation parent"):admission.validate_scientific_closure(**p)

    def test_one_pilot_session_does_not_require_unused_role_reservations(self):
        f=make_fixture();pilot=f.docs["acquisition_ledger"]["reservations"][-1]
        pilot["ordinal"]=0;f.docs["acquisition_ledger"]["reservations"]=[pilot]
        r=admission.validate_scientific_closure(**f.seal()).record()
        self.assertEqual(len(r["acquisition_session_bindings"]),1)

    def test_duplicate_source_role_cannot_create_unbounded_retries(self):
        self.refused(lambda f:f.docs["acquisition_ledger"]["reservations"][1].update(role="calibration"))

    def test_malformed_nested_types_are_explicit_refusals(self):
        self.refused(lambda f:f.docs["scientific_result"]["evaluation_gates"].__setitem__(0,[]))
        self.refused(lambda f:f.docs["acquisition_ledger"]["location"].update(path=123))
        self.refused(lambda f:f.docs["executable_freeze"]["dependency_edges"].update(plugin=[[]]))
        p=make_fixture().seal();p["raw_documents"]["basis"]=b'[]'
        p["expected_raw_pins"]["basis"]={"bytes":2,"sha256":hashlib.sha256(b'[]').hexdigest()}
        with self.assertRaisesRegex(ValueError,"JSON object"):admission.validate_scientific_closure(**p)

    def test_receipt_immutable_defensive_record_and_no_default_trust_api(self):
        result=admission.validate_scientific_closure(**make_fixture().seal());record=result.record();record["basis"]["source_metadata_sha256"]=H("change")
        self.assertNotEqual(result.record()["basis"]["source_metadata_sha256"],H("change"))
        with self.assertRaises(TypeError):admission.validate_scientific_closure({}, {})

    def test_no_direct_construction_can_forge_verified_receipt(self):
        with self.assertRaisesRegex(ValueError,"complete validation"):
            admission.VerifiedClosure(b'{"scientific_readiness":true}')

    def test_production_schema_is_implementable_using_explicit_simulated_anchors(self):
        # Test inputs remain fictitious in-memory records, never saved or sent.
        # Real readiness requires the caller's genuine independent readbacks.
        f=make_fixture()
        for doc in f.docs.values():
            if "evidence_domain" in doc:doc["evidence_domain"]="public-scientific-evidence"
            if "domain" in doc:doc["domain"]="public-scientific-evidence"
        record=admission.validate_scientific_closure(**f.seal()).record()
        self.assertTrue(record["scientific_readiness"])
        self.assertFalse(record["execution_authority_issued"])
        self.assertEqual(record["trial_session_identity"],record["acquisition_session_bindings"][-1]["session_id"])

    def test_import_and_complete_validation_perform_no_io_network_or_process_calls(self):
        packet=make_fixture().seal()
        code=Path(__file__).with_name("scientific_admission.py").read_bytes()
        module=types.ModuleType("scientific_admission_purity_probe")
        sys.modules[module.__name__]=module
        touched=[]
        def forbidden(*args,**kwargs):
            touched.append(True)
            raise AssertionError("Pure admission attempted external access")
        try:
            with patch("builtins.open",forbidden),patch.object(io,"open",forbidden),patch.object(os,"open",forbidden),\
                 patch.object(os,"listdir",forbidden),patch.object(os,"scandir",forbidden),patch.object(socket,"socket",forbidden),\
                 patch.object(subprocess,"Popen",forbidden):
                exec(compile(code,"<held-pure-admission>","exec"),module.__dict__)
                result=module.validate_scientific_closure(**packet).record()
                self.assertFalse(result["scientific_readiness"])
            self.assertEqual(touched,[])
        finally:
            sys.modules.pop(module.__name__,None)


if __name__ == "__main__":
    unittest.main()
