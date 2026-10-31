"""Prepare metadata-only prospective q254 scope; do not open power arrays."""
from pathlib import Path
from datetime import datetime, timezone
import json
import sys
import platform

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT/'work_bw'))
import partial_search as science

parentpath = ROOT/'work_bv/BV_PARTIAL_PLAN.json'
assert science.sha(parentpath) == '5c98d2ba7a13842cdf672377c34d98b6652fa130bf7f44d30881da6315487c08'
parent = science.read(parentpath)
summarypath = ROOT/'work_bv/SUMMARY_BV.json'
assert science.sha(summarypath) == '58dbcc526ca70898b2f8e22df6e276ef1424bb00d2a16386a85f65c310827057'
prior = science.read(summarypath)
assert prior['newly_searched_q'] == list(range(33, 254))
assert prior['status'] == 'COMPLETED_FIVE_SCAN_PARTIAL_CONTINUATION'

plan = json.loads(json.dumps(parent))
plan.update(
    schema='SETI_BW_PARTIAL_HIP44295_LOCAL_Q_ESS_V1',
    identity='BW_PARTIAL_HIP44295_FINAL_INTERIOR_Q254_V1',
    created_utc=datetime.now(timezone.utc).isoformat(),
    core_q_list=[254], batch_q_lists=science.BATCHES,
    scope_numerics=science.SCOPE_NUMERICS,
    isolation_root='/dev/shm/seti_bw_partial_20261031',
    overall_runtime_wall_seconds=300,
    overall_storage_cap_bytes=2*1024**3,
    caps={'wall_seconds': 180, 'cpu_seconds': 180,
          'rss_bytes': 2*1024**3, 'stored_bytes': 2*1024**3})
plan['runtime'] = dict(python_version=platform.python_version(),
    numpy_version=science.np.__version__, python_executable=sys.executable,
    python_executable_sha256=science.sha(sys.executable))
sources = science.required_source_pins()
for rel in ['work_bw/prepare_plan.py', 'work_bw/run_stage.py',
            'work_bw/run_remaining.py', 'work_bw/review/audit_partial_bw.py',
            'work_bo/src/capture.py', 'work_bt/isolated_worker.py',
            'work_bv/partial_search.py']:
    path = ROOT/rel
    sources[str(path)] = science.sha(path)
plan['source_sha256'] = sources
for path in [parentpath, summarypath,
             ROOT/'work_bv/review/FINAL_CLOSURE_REVIEW_BV.json',
             ROOT.parent/'bv_delivery/SETI_BV_DELIVERY_INDEX_2026-10-31.json',
             ROOT/'work_bw/review/BOUNDARY_SCOPE_REVIEW_BW.json',
             ROOT/'work_bw/SOURCE_ADAPTATION_BW.json']:
    plan['metadata_evidence'].append(dict(path=str(path), sha256=science.sha(path)))
plan['parent_checkpoint'] = dict(
    index_library_file_id='libfile_16cfac07dd7481919ecbea35c40b0e70',
    result_commit='dc24c8636f8ca3511226007b846dc249e61608d1',
    result_tree='0f7c4faab00d36e5520e4d604536844e75cde35a',
    completed_q=list(range(1,254)), original_coverage_credit=0)
plan['interpretation']['purpose'] = (
    'First detector scoring of q254, the last full-halo interior carrier core, '
    'in five previously decoded and fully normalized2016scans.')
plan['interpretation']['q_selection'] = (
    'q254 selected from metadata-only support geometry before scoring. OriginalBN '
    'explicitly admitted254; completedBV froze33..253. Prior wording thatBV '
    'covered all safe q was overbroad. Its historical scope/results stay unchanged. '
    'This is a small prospective coverage correction, not new observations.')
plan['interpretation']['previous_power_contact'] = (
    'BU andBV normalized all native channels. q254 is not unseen raw data or a '
    'holdout. BU q1..32 andBV q33..253 results are retained and not rescored.')
plan['interpretation']['full_power_authorization'] = (
    'User requested autonomous continuation with priority on data analysis; '
    'this finite remaining full-halo core is selected.')
plan['boundary_geometry'] = dict(
    core_native_channels_half_open=[1040384,1044480],
    support_native_channels_half_open=[1036288,1048576],
    complete_halo_channels_each_side=4096,
    maximum_shift_plus_association_radius_channels=2218,
    excluded_incomplete_halo_q=[0,255],
    combined_BU_BV_BW_if_completed_q=list(range(1,255)),
    combined_carrier_bin_width_mhz_if_completed=2.90679931640625)
plan['execution_policy'] = dict(
    serial_only=True, automatic_retry=False,
    stop_on_any_capture_or_review_failure=True,
    public_freeze_and_exact_readback_before_scoring=True,
    independent_review_after_each_batch=True,
    independent_normalization_review_first_batch=True,
    no_other_executor_commands_during_run=True,
    retain_all_closed_archives=True, overall_wall_cap_seconds=300)
path = ROOT/'work_bw/BW_PARTIAL_PLAN.json'
science.write(path, plan)
science.validate_plan(plan, path, check_inputs=False)
print(json.dumps(dict(plan_sha256=science.sha(path), source_count=len(sources),
    scans=len(plan['scans']), batches=1, first_q=254, last_q=254,
    power_arrays_opened=False, scope=science.SCOPE_NUMERICS)))
