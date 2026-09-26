"""Build a non-executable, metadata-derived extraction/resource proposal.

No telescope values are opened. This is deliberately not a source contract.
Motion, calibration transfer and scientific evaluation gates remain unfrozen.
"""
import hashlib
import gzip
import json
import math
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from seti_repeater import pipeline_radio as pipeline, source_m43h
from seti_repeater.exposure_radio import linear_exposure_profile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_radio_motion_2026-09-26'


def json_write(name,value):
    data=(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    (OUT/name).write_bytes(gzip.compress(data,mtime=0) if name.endswith('.gz') else data)


def spectral_chunks(interval, chunk_width):
    start,stop=interval
    if any(type(x) is not int for x in (start,stop,chunk_width)) or min(start,chunk_width)<0 or chunk_width==0 or stop<=start:
        raise ValueError('positive integer half-open interval/chunk width required')
    return set(range(start//chunk_width,(stop-1)//chunk_width+1))


def assert_disjoint_chunks(windows, chunk_width):
    seen=set()
    for window in windows:
        chunks=spectral_chunks(window['archive_interval'],chunk_width)
        if seen & chunks: raise ValueError('roles expose the same HDF5 spectral payload chunk')
        seen |= chunks


def run():
    source_path=ROOT/'config/radio_hd1461_source_preparation_20260926.json'
    source=json.loads(source_path.read_text())
    motion=json.loads((OUT/'result.json').read_text())
    h=source['scans'][0]['expected_header']; chunk=source['scans'][0]['expected_chunks'][2]
    full_chunks=h['dataset_shape'][2]//chunk
    center_chunk=full_chunks//2
    native_count=16384; half=native_count//2
    df=abs(h['foff_mhz'])*1e6
    windows=[]
    for role,index in zip(('calibration','validation','pilot'),range(center_chunk-1,center_chunk+2)):
        middle=index*chunk+chunk//2
        lo,hi=middle-half,middle+half
        fhigh=(h['fch1_mhz']+lo*h['foff_mhz'])*1e6
        flow=(h['fch1_mhz']+(hi-1)*h['foff_mhz'])*1e6
        windows.append({'name':'radio_hd1461_'+role+'_draft','role':role,'archive_interval':[lo,hi],
            'archive_chunk_index':index,'native_channel_count':native_count,
            'native_frequency_low_hz':flow,'native_frequency_high_hz':fhigh,
            'proposed_first_on_midpoint_carrier_center_hz':(flow+fhigh)/2,
            'payload_keys': [{'source_url':scan['url'],'chunk_coordinates_time_feed_frequency':
                              [[row,0,index] for row in range(16)]} for scan in source['scans']]})
    assert_disjoint_chunks(windows,chunk)
    template_ceiling=128; score_half=256; support_guard=64
    context_model=SimpleNamespace(bank=range(template_ceiling),grid=SimpleNamespace(support_bin_count=2*score_half+1+2*support_guard))
    model_bytes=pipeline.modelled_array_bytes(context_model,16,native_count)
    proposal={
        'artifact_type':'radio-prospective-design-draft-v1','status':'NOT_FROZEN_NOT_EXECUTABLE',
        'spectral_access_authorized':False,'primary':'unchanged neighbor9',
        'source_contract_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),
        'selection_rule':'Three adjacent full HDF5 frequency chunks centered on full_chunk_count//2; roles assigned calibration, validation, pilot in ascending archive-index order; central 16384 channels in each.',
        'selection_inputs':'Retained shape/chunk/frequency metadata only, never spectral amplitudes.',
        'normalization':'Four separate 4096-channel blocks per extraction; no block crosses role boundaries.',
        'windows':windows,'unique_spectral_chunk_payloads_if_acquired':6*16*3,
        'distinct_observing_cadences':1,'roles_are_independent_observations':False,
        'proposed_grid':{'score_half_bins':score_half,'score_bin_count':2*score_half+1,
            'support_guard_bins':support_guard,'carrier_spacing_hz':df,
            'reference_time':'first ON midpoint','reference_frequency_kind':'observed frequency at reference, not emitted/rest frequency'},
        'motion_bank':None,'motion_bank_qualified':False,
        'calibration_transfer_contract':None,'calibration_transfer_qualified':False,
        'recovery_gate':None,'control_gate':None,'scientific_panel':None,
        'required_calibration_behavior':['Disjoint calibration and evaluation spectral payloads, including decoded HDF5 chunks and normalization blocks.',
            'Explicit prospective binding between calibration and evaluation contexts; never relabel the old context hash.',
            'An empty/nonfinite conditional null is insufficient calibration. Do not insert a synthetic comb or invented maxima into telescope calibration.',
            'Scramble counts measure resamples, not independent observing realizations. A rank statistic is conditional diagnostic evidence.'],
        'resource_proposal':{'sessions_maximum':3,'one_session_per_role':True,
            'session_max_requests':500,'session_max_bytes':512*1024**2,'session_max_seconds':1200,
            'cumulative_max_requests':1500,'cumulative_max_bytes':1536*1024**2,'cumulative_max_seconds':3600,
            'retry_policy':'No automatic retry or reservation refund; unused quota of a failed reservation remains spent.',
            'max_templates_for_resource_model_only':template_ceiling,'maximum_records_per_role':10000,
            'modelled_search_arrays_limit_bytes':128*1024**2,'modelled_search_arrays_at_template_ceiling_bytes':model_bytes,
            'modelled_acquisition_buffers_bytes':source_m43h.resource_bound(native_count),
            'raw_plus_normalized_extracted_float32_bytes_all_roles':2*3*6*16*native_count*4,
            'decoded_chunk_bytes_all_roles':3*6*16*chunk*4,
            'compressed_chunk_sizes_and_metadata_overhead_known':False,
            'not_a_process_rss_or_allocation_certificate':True,
            'not_an_executable_resource_freeze':True},
        'advancement_requirements':['Resolve the selected same-scan pointing provenance.',
            'Freeze one source-specific accurate factor table/bank and its literal coverage limits; the old circular phase construction is not admissible at e=0.172.',
            'Qualify finite-exposure digital injections and identify the assumed instrumental channel response.',
            'Qualify explicit disjoint cross-window calibration and the positive telescope codec/receipt handoff.',
            'Freeze exact panel identities, amplitudes, activity patterns, association/recovery/RFI/null gates and attempts before values are opened.',
            'Freeze current code/runtime, physical support bounds, cumulative reservation namespace and new ready source contract, then verify public commit.'],
        'coverage_status':'EXTRACTION_GEOMETRY_PROPOSED; no template/receiver support certification until the actual bank is frozen.'}
    if model_bytes>proposal['resource_proposal']['modelled_search_arrays_limit_bytes']:
        raise ValueError('proposed array ceiling is insufficient')
    json_write('prospective_design.json',proposal)

    kc=motion['keplerian_comparison']
    sweeps=[0.,1.,5.,17.,kc['max_sampled_orbital_exposure_endpoint_sweep_hz']/df,
            kc['all_phase_orbital_exposure_frequency_sweep_upper_bound_native_channels']]
    records=[]
    for width in (0.,1.,3.,9.):
        for sweep in sweeps:
            profile=linear_exposure_profile(512,256-sweep/2,256+sweep/2,width)
            records.append({'intrinsic_width_channels':width,'sweep_channels':sweep,
                'sum_unit_digital_power':float(profile.sum()),'maximum_single_channel_power':float(profile.max()),
                'occupied_channels':int(np.count_nonzero(profile)),
                'ideal_unit_variance_boxcar_responses':{str(w):float(np.convolve(profile,np.ones(w),mode='valid').max()/math.sqrt(w))
                                                       for w in (1,3,5,9,17,33,65,129)},
                'profile':profile.tolist()})
    json_write('exposure_profiles.json.gz',{'schema':'ideal-linear-exposure-development-v1',
        'purpose':'Unit-power engineering response, not sensitivity or detector recovery',
        'real_telescope_samples':0,'cases':records,
        'assumptions':['Constant instantaneous total digital power and constant drift within an integration.',
            'Intrinsic top-hat profile and ideal rectangular native channel response; no GBT bandpass or polyphase leakage model.',
            'Conservation is measured in float64 before float32 raw-power addition and before normalization.',
            'Model-derived sweep sizes do not establish an actual signal or orbital orientation.']})
    print(json.dumps({'window_centers_mhz':[w['proposed_first_on_midpoint_carrier_center_hz']/1e6 for w in windows],
                      'array_model_bytes':model_bytes,'exposure_cases':len(records),'status':proposal['status']},indent=2))


if __name__=='__main__':run()
