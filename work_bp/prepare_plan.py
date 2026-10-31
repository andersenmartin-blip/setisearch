"""Create the prospective BP plan without generating or scoring data."""
from pathlib import Path
import hashlib
import json
import platform
import sys
import numpy as np

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
import synthetic
import paired_search


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    sources=sorted(set(list(ROOT.glob('*.py'))+list((ROOT/'tests').glob('*.py'))+
      [REPO/'work_bo/src/methods.py',REPO/'work_bo/src/capture.py']+
      list((REPO/'work_bo/vendor').rglob('*.py'))+
      [REPO/'work_bn/next_scope/HIP45688_PAIRED_CONTROLS_DRAFT.json',ROOT/'PREREG_BP.md']))
    plan=dict(schema='SETI_BP_FIXED24_PLAN_V1',status='FROZEN_BEFORE_RNG_AND_SYNTHETIC_SCORES',
      purpose='24 prospective paired synthetic six-scan controls following BO',
      synthetic_only=True,astronomical_powers_authorized=False,full839_authorized=False,
      prior_engineering_commit='b09768a6cec3a251006482028ed35794dbdf81f4',
      runtime=dict(python_version=platform.python_version(),numpy_version=np.__version__,
                   python_executable_sha256=sha(sys.executable)),
      source_pins=[dict(path=str(p.relative_to(REPO)),bytes=p.stat().st_size,sha256=sha(p)) for p in sources],
      synthetic_specification=synthetic.specification(),paired_search_specification=paired_search.specification(),cases=synthetic.cases(),
      caps=dict(cpu_seconds=1800,wall_seconds=2400,rss_bytes=2<<30,stored_bytes=8<<30),
      maximum_stdout_bytes_per_case=4<<20,failure_footer_bytes=1<<20,
      one_worker=True,thread_environment={k:'1' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']},
      irreversible_reservation='All 24 case identities reserved once; a started failure is retained and the chain stops; no tuning, retry or cap increase.',
      pairing='Identical immutable float32 power bytes go to both methods; full native normalization before crop.',
      legacy_calibration_domain=[4096,1044480],legacy_calibration_includes_q128=True,
      current_local_q=[63,64,65,127,129],rate_indices=[0,209,419,629,838],
      widths=[1,3,9,33],strides=[1,1,2,8],ON_cut=10,OFF_cut=5,
      limited_scope='New prospective association rule: destination physical-q calibration and nearest width grid; not a reproduction of BN source-q forced association.',
      gates=dict(null='No full supported current ON/OFF flag in any of eight null cadences.',
                 strong='All six amplitude256 current truth endpoints recover, and their paired uninjected region does not.',
                 weak='Any legacy-recovered/current-missed amplitude15 endpoint stops for review; no parameter adjustment.',
                 association='All four current association controls reject by supported OFF veto or failed three-ON rule.',
                 numerical='Current selected sums within max(1e-8,64*eps64*sum_abs); legacy exact staged float32 oracle; every old5e-5 failure retained.',
                 capture='Actual exit0, EOF, source pins, complete log/result hash, exact wait and resource limits.'),
      preserved_history=dict(HIP45688_M_raw_sum_failures=24,HIP45688_M_full_QA=False,all_M_raw_sum_failures=142),
      new_archive_requests=0,new_observations=0,new_coverage_credit=0,cost_DKK=0,
      interpretation='PASS is limited synthetic validation only, not FAP, general recovery, SNR/sigma, flux/EIRP, sensitivity or astronomy.',
      subsequent_stages='Independent result review, then separately frozen full839 paired controls, then separate DATA admission and astronomical search plan.')
    with (ROOT/'BP_FIXED24_PLAN.json').open('x') as f:
        json.dump(plan,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps(dict(plan_sha256=sha(ROOT/'BP_FIXED24_PLAN.json'),source_files=len(sources),cases=len(plan['cases']),RNG_draws=0)))


if __name__=='__main__':main()
