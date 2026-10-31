"""Bind closed BP evidence for new BQ saved-association processing; no scores."""
from pathlib import Path
import hashlib
import json
import platform
import sys
import numpy as np

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
BP=REPO/'work_bp'
RUN=BP/'execution/BP_FIXED24_V1'
sys.path.insert(0,str(ROOT))
import stream_association


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def pin(p):return dict(path=str(p.relative_to(REPO)),bytes=p.stat().st_size,sha256=sha(p))


def main():
    bp=json.loads((BP/'BP_FIXED24_PLAN.json').read_text())
    terminal=json.loads((RUN/'TERMINAL.json').read_text())
    review=json.loads((BP/'review/RESULT_REVIEW_BP.json').read_text())
    assert terminal['status']=='FAIL' and terminal['passed_cases']==23
    assert review['status']=='PASS_INDEPENDENT_EVIDENCE_REVIEW' and review['control_phase_status']=='FAIL'
    record={x['path']:x for x in terminal['evidence_files']}
    score_paths=[RUN/case/'payload'/f'scan{i}'/name for case in ['A04','N04'] for i in range(6) for name in ['RESULT.json','arrays.npz']]
    source_paths=sorted(set([REPO/p['path'] for p in bp['source_pins']]+list(ROOT.glob('*.py'))+list((ROOT/'tests').glob('*.py'))+[ROOT/'PREREG_BQ.md']))
    inputs=score_paths+[RUN/'A04/payload'/f'delta_scan{i}.npz' for i in range(6)]+list((RUN/'bases/seed04').glob('scan*'))
    inputs+= [BP/'BP_FIXED24_PLAN.json',BP/'PUBLIC_FREEZE_RECEIPT_BP.json',BP/'review/RESULT_REVIEW_BP.json',RUN/'TERMINAL.json',RUN/'A04/ACTUAL_RECEIPT.json']
    for p in inputs:
        if p.is_relative_to(RUN) and p.name!='TERMINAL.json':
            saved=record[str(p.relative_to(RUN))]
            assert saved['sha256']==sha(p) and saved['bytes']==p.stat().st_size
    plan=dict(schema='SETI_BQ_SAVED_A04_POSTPROCESSING_V1',
      purpose='Finish only saved A04 association in constant memory; preserve BP original FAIL',
      prior_preregistration='ee9ff94abfaa56055f947036b80133393cf209f8',
      BP_original_status='FAIL',BP_original_passed_cases=23,
      BP_failed_capture_reason='CHILD_TREE_RSS_CAP_EXCEEDED',
      RNG_authorized=False,new_scan_scores_authorized=False,astronomical_powers_authorized=False,
      new_normalization_authorized=False,new_tracks_authorized=False,
      case=bp['cases'][-1],original_association_specification=bp['paired_search_specification'],stream_specification=stream_association.specification(),
      source_pins=[pin(p) for p in source_paths],input_pins=[pin(p) for p in sorted(set(inputs))],
      scan_dirs=[str((RUN/'A04/payload'/f'scan{i}').relative_to(REPO)) for i in range(6)],
      base_scan_dirs=[str((RUN/'N04/payload'/f'scan{i}').relative_to(REPO)) for i in range(6)],
      runtime=dict(python_version=platform.python_version(),numpy_version=np.__version__,python_executable_sha256=sha(sys.executable)),
      caps=dict(cpu_seconds=180,wall_seconds=240,rss_bytes=1<<30,stored_bytes=2<<30),
      output_identity='BQ_A04_ASSOC_V1',no_retry=True,
      result_semantics='Separate postprocessing evidence, never BP repair/requalification. All saved associations retained line-by-line; endpoints and thresholds unchanged.',
      full839_authorized=False,DATA_admission_authorized=False,new_archive_requests=0,new_observations=0,new_coverage_credit=0)
    with (ROOT/'BQ_POSTPROCESSING_PLAN.json').open('x') as f:json.dump(plan,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(plan_sha256=sha(ROOT/'BQ_POSTPROCESSING_PLAN.json'),source_pins=len(source_paths),input_pins=len(set(inputs)))))


if __name__=='__main__':main()
