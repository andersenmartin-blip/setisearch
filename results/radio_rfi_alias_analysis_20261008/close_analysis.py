"""Close conservative analysis accounting and inventory final artifacts."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
resources={p.name:json.loads(p.read_text()) for p in sorted(OUT.glob('resource_*.json'))}
total=sum(r['whole_job_cpu_s'] for r in resources.values())
assert total<=100 and all(r['exit_code']==0 for r in resources.values())
assert json.loads((OUT/'PEER_AUDIT.json').read_text())['status']=='PASS_RETAINED_DERIVATIONS_ONLY'
ledger={'status':'CLOSED_READ_ONLY_RFI_ALIAS_ANALYSIS','prerequisite_post_METHOD_ledger_sha256':hashlib.sha256((ROOT/'pilot_method_study_20261008/post_method_ledger.json').read_bytes()).hexdigest(),'previous_remaining_CPU_s':6612.705144981004,'new_conservative_analysis_reservation_CPU_s':100,'remaining_CPU_after_reservation_s':6512.705144981004,'existing_preparation_reservation_CPU_s':1200,'existing_preparation_reservation_unchanged':True,'retained_report_reproduction_CPU_s':2000,'measured_whole_job_component_CPU_s':total,'measured_component_receipts':resources,'other_setup_publication_CPU_covered_by_new_reservation_not_claimed_fully_measured':True,'reservation_refunded':False,'component_CPU_charged_again_in_addition_to_reservation':False,'new_draws':0,'new_scores':0,'new_telescope_payload_bytes':0,'qualification':False,'A_and_B_remain_FAIL_CLOSED':True}
(OUT/'ANALYSIS_LEDGER.json').write_text(json.dumps(ledger,indent=2)+'\n')
entries=[]
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.name not in {'PUBLICATION_INDEX.json','PUBLICATION_RECEIPT.json'}:
        b=p.read_bytes(); entries.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha1':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()})
(OUT/'PUBLICATION_INDEX.json').write_text(json.dumps({'source_commit':'6b8259099721b3acdb98b604fb5c9ea192577d68','core_file_count':len(entries),'core_bytes':sum(x['bytes'] for x in entries),'entries':entries,'self_index_and_later_publication_receipt_excluded_from_core_inventory':True},indent=2)+'\n')
print(json.dumps({'measured_component_CPU_s':total,'core_files':len(entries),'core_bytes':sum(x['bytes'] for x in entries),'remaining_CPU_s':6512.705144981004}))
