"""Build a prospective BU plan exclusively from retained metadata, never powers."""
from pathlib import Path
import json,sys,platform,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work_bu'))
import partial_search as science
restore=ROOT.parent/'bu_restore'
proofpath=restore/'work_bb/review/PARTIAL_INPUT_PROOF_BB.json'
statepath=restore/'work_bb/review/CACHED_READ_STATE_BB_PARTIAL.json'
proof=json.loads(proofpath.read_text()); state=json.loads(statepath.read_text())
assert proof['detector_searches_executed']==0
scans=[]
for i in range(5):
    prior=state['canonical_closed_scans'][i]; report=proof['scan_reports'][i]
    hp=restore/prior['descriptor_header_path']; h=json.loads(hp.read_text()); a=h['attrs']
    assert science.sha(hp)==prior['descriptor_header_sha256'] and report['canonical_complete'] and report['valid_rows_verified']==16
    scans.append(dict(scan=i,role='ON' if i%2==0 else 'OFF',target=h['archive']['target'],archive_id=h['archive']['id'],
        path=str(restore/prior['array_path']),input_sha256=prior['array_sha256'],input_bytes=prior['bytes'],
        powers_sha256=report['valid_rows_power_sha256'],row_sha256=[r['decoded_row_sha256'] for r in report['rows']],
        nrows=16,nchannels=1048576,dt_seconds=a['tsamp'],df_hz=a['foff']*1e6,
        fch1_mhz=a['fch1']+179306496*a['foff'],header_tstart_mjd=a['tstart'],
        tref_midpoint_mjd=a['tstart']+7.5*a['tsamp']/86400,source_header_first_frequency_mhz=a['fch1'],
        source_nchannels=a['nchans'],header_path=str(hp),header_sha256=prior['descriptor_header_sha256'],
        catalog_tstart_mjd=h['archive']['mjd'],catalog_header_difference_seconds=(a['tstart']-h['archive']['mjd'])*86400))
sources=science.required_source_pins()
for rel in ['work_bu/prepare_plan.py','work_bu/run_stage.py','work_bu/review/audit_partial_bu.py','work_bo/src/capture.py','work_bt/isolated_worker.py']:
    p=ROOT/rel; sources[str(p)]=science.sha(p)
evidence=[proofpath,statepath,restore/'RESTORATION_BU.json',restore/'INVENTORY_BB.json',ROOT/'work_bu/provenance/BB_PUBLIC_EVIDENCE.json',ROOT/'work_bu/provenance/BB_PARTIAL_AUDIT_PUBLIC.json']
plan=dict(schema='SETI_BU_PARTIAL_HIP44295_LOCAL_Q_ESS_V1',identity='BU_PARTIAL_HIP44295_V1',
    created_utc=datetime.now(timezone.utc).isoformat(),target='HIP44295',primary_id=65133,
    native_channel_start=179306496,native_channel_count=1048576,core_width_channels=4096,support_halo_channels=4096,bandpass_block_channels=4096,
    core_q_list=list(range(1,33)),batch_q_lists=science.BATCHES,widths_channels=list(science.WIDTHS),strides=list(science.STRIDES),
    max_abs_drift_hz_s=4,threshold_ess=10,off_flag_threshold_ess=5,calibration_domain=science.CALIBRATION_DOMAIN,
    previously_acquired_data=True,new_independent_observation=False,missing_scan=5,complete_OFF_support=False,
    new_archive_requests_authorized=0,original_coverage_credit=0,scans=scans,source_sha256=sources,
    metadata_evidence=[dict(path=str(p),sha256=science.sha(p)) for p in evidence],scope_numerics=science.SCOPE_NUMERICS,
    runtime=dict(python_version=platform.python_version(),numpy_version=science.np.__version__,python_executable=sys.executable,python_executable_sha256=science.sha(sys.executable)),
    isolation_root='/dev/shm/seti_bu_partial_20261031',caps=dict(wall_seconds=900,cpu_seconds=900,rss_bytes=2147483648,stored_bytes=2147483648),overall_storage_cap_bytes=8589934592,
    interpretation=dict(purpose='First detector search of already acquired 2016 data, partial exploratory identity only.',
        q_selection='Fixed first32 q; no score-based selection or adaptive tuning.',
        association='Exact inherited BN same-q destination calibration, including forced points in halo; descriptive local ESS only.',
        missing_control='OFF5 is absent in every result; never imputed; full-cadence assessment NOT_EVALUABLE_MISSING_OFF5.',
        global_FAP=None,calibrated_sensitivity=None,extraterrestrial_origin_qualified=False,
        historical_authority=dict(unique_archive_ids=486,technical_MHz_visits=268.50128173828125,queue_advanced=False),
        prior_failures='BB/BC/BE incomplete acquisition and BP/BQ/BR/BS historical failures preserved; BT bounded synthetic qualification unchanged.',
        provenance_limit='Exact canonical arrays/row hashes inherited from BB, with shared TREE/codec limitations; no independent original-file decode or MD5 qualification.'))
path=ROOT/'work_bu/BU_PARTIAL_PLAN.json'
science.write(path,plan)
science.validate_plan(plan,path,check_inputs=True)
print(json.dumps(dict(plan_sha256=science.sha(path),sources=len(sources),scans=len(scans),scope=science.SCOPE_NUMERICS,frequency_max_mhz=scans[0]['fch1_mhz']+4096*scans[0]['df_hz']/1e6,frequency_min_mhz=scans[0]['fch1_mhz']+(33*4096-1)*scans[0]['df_hz']/1e6)))
