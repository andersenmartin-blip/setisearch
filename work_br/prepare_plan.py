"""Prospective BR saved-score closure plan; no RNG or association execution."""
from pathlib import Path
import hashlib
import json
import platform
import sys
import numpy as np
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
import closed_association

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def pin(p):return dict(path=str(p.relative_to(REPO)),bytes=p.stat().st_size,sha256=sha(p))

def main():
    bq=json.loads((REPO/'work_bq/BQ_POSTPROCESSING_PLAN.json').read_text())
    effective=json.loads((REPO/'work_bq/EFFECTIVE_STATUS_BQ.json').read_text())
    assert effective['status']=='EVIDENCE_FAIL' and effective['cause']=='UNESTABLISHED'
    source_paths=sorted(set([REPO/p['path'] for p in bq['source_pins']]+list(ROOT.glob('*.py'))+list((ROOT/'tests').glob('*.py'))+[ROOT/'PREREG_BR.md']))
    inputs=[REPO/p['path'] for p in bq['input_pins']]
    inputs += [REPO/'work_bq/BQ_POSTPROCESSING_PLAN.json',REPO/'work_bq/EFFECTIVE_STATUS_BQ.json']
    inputs += sorted(p for p in (REPO/'work_bq/execution/BQ_A04_ASSOC_V1').rglob('*') if p.is_file())
    inputs += sorted(p for p in (REPO/'work_bq/review').glob('*REVIEW*BQ*.json') if p.is_file())
    for previous in bq['input_pins']+bq['source_pins']:
        p=REPO/previous['path'];assert p.stat().st_size==previous['bytes'] and sha(p)==previous['sha256']
    plan=dict(schema='SETI_BR_CLOSED_A04_POSTPROCESSING_V1',
      BP_original_status='FAIL',BP_original_passed_cases=23,BQ_effective_status='EVIDENCE_FAIL',
      cause_of_BQ_stream_change='UNESTABLISHED',
      RNG_authorized=False,new_scan_scores_authorized=False,astronomical_powers_authorized=False,
      case=bq['case'],stream_specification=closed_association.specification(),original_association_specification=bq['original_association_specification'],
      source_pins=[pin(p) for p in source_paths],input_pins=[pin(p) for p in sorted(set(inputs))],
      scan_dirs=bq['scan_dirs'],base_scan_dirs=bq['base_scan_dirs'],
      runtime=dict(python_version=platform.python_version(),numpy_version=np.__version__,python_executable_sha256=sha(sys.executable)),
      caps=dict(cpu_seconds=180,wall_seconds=240,rss_bytes=1<<30,stored_bytes=2<<30),
      output_identity='BR_A04_ASSOC_V1',no_retry=True,
      terminal_policy='Effective PASS requires natural process success AND child manifests AND repeated parent closure, with immutable source and input hashes; independent review remains required.',
      full839_authorized=False,DATA_admission_authorized=False,new_archive_requests=0,new_observations=0,new_coverage_credit=0)
    with (ROOT/'BR_POSTPROCESSING_PLAN.json').open('x') as f:json.dump(plan,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(plan_sha256=sha(ROOT/'BR_POSTPROCESSING_PLAN.json'),source_pins=len(source_paths),input_pins=len(set(inputs)))))

if __name__=='__main__':main()
