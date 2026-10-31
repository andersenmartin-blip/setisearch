"""Build the fixed BT two-identity conditional plan without executing either."""
from pathlib import Path
import hashlib
import json
import platform
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def pin(p):
    return dict(path=str(p.relative_to(REPO)),bytes=p.stat().st_size,sha256=sha(p))


def main():
    br=json.loads((REPO/'work_br/BR_POSTPROCESSING_PLAN.json').read_text())
    bs=json.loads((REPO/'work_bs/BS_FILE_STABILITY_PLAN.json').read_text())
    paths={REPO/p['path'] for p in br['source_pins']}
    paths.update(ROOT.glob('*.py'));paths.update((ROOT/'tests').glob('*.py'))
    paths.update([ROOT/'PREREG_BT.md',ROOT/'review/SOURCE_REVIEW_BT.json',
                  ROOT/'review/audit_bt.py',REPO/'work_bp/review/audit_results.py',
                  REPO/'work_bs/diagnostic.py',REPO/'work_br/BR_POSTPROCESSING_PLAN.json'])
    historical={REPO/p['path'] for p in br['input_pins']}
    historical.update([REPO/'work_bs/BS_FILE_STABILITY_PLAN.json',REPO/'work_bs/SUMMARY_BS.json',
                       REPO/'work_bs/review/REVIEW_RESULTS_BS.json',REPO/'work_bs/review/DIAGNOSTIC_FINDINGS_BS.md',
                       REPO/'work_br/SUMMARY_BP_BR.json',REPO/'work_br/review/BR_FAILURE_REVIEW.json'])
    for item in br['source_pins']+br['input_pins']:
        if pin(REPO/item['path'])!=item:raise ValueError('Frozen BR binding changed: '+item['path'])
    plan=dict(schema='SETI_BT_ISOLATED_PLAN_V1',execution_identity='BT_ISOLATED_V1',
        kinds=['fixture','a04'],max_executions=2,no_retry=True,
        isolation_root='/dev/shm/seti_bt_20261031_v1',
        intended_executor_initial_wait_ms=30000,other_executor_overlap_authorized=False,
        conditional_A04_gate='Independent FIXTURE_REVIEW_BT.json status PASS_ISOLATED_FIXTURE; bind same plan, terminal and exported archive; verify 90000 exact fixture records',
        saved_score_associations_authorized_after_fixture_review=True,
        RNG_authorized=False,new_scan_scores_authorized=False,astronomical_powers_authorized=False,
        source_pins=[pin(p) for p in sorted(paths)],historical_pins=[pin(p) for p in sorted(historical)],
        expected_fixture_streams=bs['expected_streams'],
        expected_A04_streams={
          'current':dict(records=43306,bytes=82645873,sha256='c2ac481a772ade86eaeabc3b5fab401faa970cddee0edd261d1cced8e26b163d'),
          'legacy':dict(records=43845,bytes=83501000,sha256='e1af344f12f36f2deb8205943bcb427faa56a14b3a63593fcc52eba2186a6479')},
        A04_case=br['case'],
        caps={'fixture':dict(wall_seconds=60,cpu_seconds=45,rss_bytes=512<<20,stored_bytes=512<<20),
              'a04':dict(wall_seconds=120,cpu_seconds=90,rss_bytes=512<<20,stored_bytes=512<<20)},
        phase_storage_cap_bytes=1<<30,
        runtime=dict(python_version=platform.python_version(),python_executable_sha256=sha(sys.executable)),
        old_statuses={'BP':'FAIL','BQ':'EVIDENCE_FAIL','BR':'FAIL','BS_BR_SERIAL':'FAIL'},
        prior_scientific_qualified_controls=23,prior_A04_qualified=False,
        qualification='New complete paired A04 may qualify only after a new full single-execution pair, exported archive closure and independent review; previous failures remain unchanged.',
        full839_authorized=False,DATA_admission_authorized=False,new_observations=0,
        new_archive_requests=0,new_coverage_credit=0)
    with (ROOT/'BT_ISOLATED_PLAN.json').open('x') as f:json.dump(plan,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(plan_sha256=sha(ROOT/'BT_ISOLATED_PLAN.json'),source_pins=len(paths),historical_pins=len(historical))))


if __name__=='__main__':main()
