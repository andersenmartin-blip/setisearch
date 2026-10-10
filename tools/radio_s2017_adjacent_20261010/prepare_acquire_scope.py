#!/usr/bin/env python3
"""Metadata/code-only scope preparation, no HTTP or dataset values."""
import json
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
d=runpy.run_path(str(HERE/'acquire_driver.py'),run_name='prospective_scope_preparation_only')
source_path='analysis/s2017_next_native/source_manifest_v2.json'
source=json.loads((ROOT/source_path).read_bytes())
scope={'schema':'SETI_S2017_ADJACENT170_172_ACQUISITION_SCOPE_V1','native_chunk_indices':[170,172],
    'scan_order':list(d['SCANS']),'rows_per_scan':16,'native_chunk_count':343,'native_chunk_channels':d['COUNT'],
    'fch1_hz':source['fch1_hz'],'df_hz':source['df_hz'],'tsamp_s':source['tsamp_s'],
    'source_workers_max':d['SOURCE_WORKERS'],'rows_serial_per_source':32,'payload_HTTP_request_cap':192,
    'payload_BODY_cap_bytes':d['BODY_CAP'],'exact_expected_payload_BODY_bytes':597792529,
    'reserved_payload_BODY_upper_bound_bytes':597792721,'acquisition_CPU_cap_s':d['CPU_CAP'],
    'wall_cap_s':d['WALL_CAP'],'memory_cap_bytes':d['MEMORY_CAP'],'workspace_cap_bytes':d['WORKSPACE_CAP'],
    'acquisition_artifact_cap_bytes':2*597792529+64*1024**2,'output_stage':d['STAGE'],'family_lock_path':d['LOCK'],
    'runtime_package_versions':d['VERSIONS'],'hdf5_version':'1.14.6','HDF5_assembly_threads':1,
    'write_decode_interleaving':False,'expected_compact_files':12,'expected_raw_sidecars':192,
    'retry_resume_or_rerun_authorized':False,'repeated_source_GETs_authorized':0,'new_metadata_HTTP_requests':0,
    'new_spectrum_selection':False,'scientific_search_run':False,'original_A_B_status':'FAIL_CLOSED_UNCHANGED',
    'qualified_sky_detection':False,'OFF_veto_applied':False,'calibrated_SNR_FAP':False,'cost_DKK':0,
    'source_manifest_path':source_path,'root_activation_path':'analysis/s2017_next_native/ACTIVATION_SCOPE_V2.json',
    'driver_sha256':d['digest'](HERE/'acquire_driver.py'),
    'code_paths':{'acquire':'analysis/s2017_next_native/raw_acquire.py',
        'reader':'analysis/new_visit_search/dependencies/standard_reader.py',
        'corrected_serial_store':'analysis/new_visit_recovery/raw_acquire.py',
        'reconstruct':'analysis/s2017_next_native/reconstruct_raw_sidecars.py'},
    'selection_rule':source['selection_rule'],
    'run_admission':'Exact public prospective code/source/scope freeze with readback; independent metadata/storage static PASS; actual40-hex freeze argument and rootGO; empty acquisition stage. SourceQA and all search work require separate rootGO.',
    'raw_sidecar_lifecycle':'All192 source bodies fsynced before any H5write, required for actual sourceQA; root may remove only redundant raw sidecars after independentH5integrity and RAWpackage durable save. Future science admits12compact hashes plus rawrecordSHAs and sourceQA; helper reconstructs exactsidecars without HTTP or dataset decode.',
    'limitations':['Coverage extension in the same historical S-band visit. Prior171 results were known; no independent blind validation is claimed.',
        'No full remote telescope file MD5 verification; exactURL, ETag, source size, nativechunk coordinates and storedchunk SHA provenance are used.',
        'No HTTP retry/resume/rerun. Any failed attempt and partial localfiles are preserved; all observed BODY bytes remain charged.',
        'Protected2016 native156/159 and originalA/B controls remain unchanged. No calibratedSNR/FAP, qualifiedsky detection, or OFFveto claim.',
        'H5Dwrite_chunk original171 failure remains preserved; unchanged corrected serial helper has prior positivefixture and completed96row acquisition. All12writers close before anynew value decode.']}
pins={name:dict(value) for name,value in source['code_and_metadata_pins'].items()}
paths=[HERE/'acquire_driver.py',HERE/'raw_acquire.py',HERE/'prepare_acquire_scope.py',HERE/'reconstruct_raw_sidecars.py',
    ROOT/source_path,ROOT/'analysis/s2017_next_native/METADATA_EXTRACTION_RECEIPT_V2.json',ROOT/scope['root_activation_path'],
    ROOT/scope['code_paths']['reader'],ROOT/scope['code_paths']['corrected_serial_store'],
    ROOT/'analysis/storage_diagnostics/CORRECTED_STORAGE_REVIEW.json',
    ROOT/'analysis/storage_diagnostics/corrected_store_fixture/ENGINEERING_RECEIPT.json',
    ROOT/'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json']
for path in paths:pins[path.relative_to(ROOT).as_posix()]={'bytes':path.stat().st_size,'sha256':d['digest'](path)}
scope['pinned_metadata_and_code']=pins
d['contract'](ROOT,scope)
with (HERE/'acquire_scope.json').open('x') as handle:json.dump(scope,handle,indent=2,allow_nan=False);handle.write('\n')
print(json.dumps({'status':'PREPARED_METADATA_CODE_ONLY_NO_HTTP_NO_VALUES','scope_sha256':d['digest'](HERE/'acquire_scope.json'),
    'driver_sha256':scope['driver_sha256'],'acquire_helper_sha256':d['digest'](HERE/'raw_acquire.py'),
    'source_manifest_sha256':pins[source_path]['sha256'],'pinned_file_count':len(pins)}))
