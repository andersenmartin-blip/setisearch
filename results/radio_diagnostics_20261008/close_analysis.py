"""Close conservative accounting and inventory the completed analysis only."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
resources={p.name:json.loads(p.read_bytes()) for p in sorted(OUT.glob('resource_*.json'))}
total=sum(r['whole_job_cpu_s'] for r in resources.values()); assert total<=200 and all(r['exit_code']==0 for r in resources.values())
expected={'PEER_DIAGNOSTIC_AUDIT.json':'PASS_INDEPENDENT_RETAINED_DIAGNOSTIC_TABLE_AUDIT','PEER_PULSE_AUDIT.json':'PASS_INDEPENDENT_SAVED_PULSE_GEOMETRY','PEER_METHOD_COVERAGE.json':'PASS_INDEPENDENT_RETAINED_METHOD_COVERAGE_AUDIT'}
for path,status in expected.items():assert json.loads((OUT/path).read_bytes())['review_status']==status
prior=ROOT/'results/radio_rfi_alias_analysis_20261008/ANALYSIS_LEDGER.json'; previous=json.loads(prior.read_bytes());assert previous['remaining_CPU_after_reservation_s']==6512.705144981004
ledger={'status':'CLOSED_RETAINED_DIAGNOSTICS_METHOD_COVERAGE','source_commit':'13131757641c06d7bfcb10790a79811c750b1178','prerequisite_RFI_ledger_sha256':hashlib.sha256(prior.read_bytes()).hexdigest(),'previous_remaining_CPU_s':6512.705144981004,'new_conservative_reservation_CPU_s':200,'remaining_CPU_after_reservation_s':6312.705144981004,'original1200_preparation_reservation_unchanged':True,'prior100_RFI_reservation_unchanged':True,'retained_report_reproduction_CPU_s':2000,'measured_whole_job_component_CPU_s':total,'measured_component_receipts':resources,'unmetered_setup_API_report_preparation_publication_covered_by_new_reservation':True,'all_overhead_or_history_claimed_fully_measured':False,'reservation_refunded':False,'components_charged_again_in_addition_to_reservation':False,'new_draws':0,'new_detector_scores':0,'new_telescope_payload_bytes':0,'qualification':False,'A_B_remain_FAIL_CLOSED':True,'old_period_Oct9_closure_only_draft_asof_Oct8':True,'scheduled_Oct19_saved_result_verification_unchanged':True,'scheduled_Oct20_final_report_unchanged':True}
(OUT/'ANALYSIS_LEDGER.json').write_text(json.dumps(ledger,indent=2)+'\n')
entries=[]
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.name not in {'PUBLICATION_INDEX.json','PUBLICATION_RECEIPT.json'}:
        b=p.read_bytes();entries.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha1':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()})
(OUT/'PUBLICATION_INDEX.json').write_text(json.dumps({'source_commit':'13131757641c06d7bfcb10790a79811c750b1178','core_file_count':len(entries),'core_bytes':sum(x['bytes'] for x in entries),'entries':entries,'self_index_and_later_publication_receipt_excluded':True},indent=2)+'\n')
print(json.dumps({'core_files':len(entries),'core_bytes':sum(x['bytes'] for x in entries),'measured_component_CPU_s':total,'remaining_CPU_s':6312.705144981004}))
