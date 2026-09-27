#!/usr/bin/env python3
"""Bounded nominal-model geometry from retained metadata; no network/data IO."""
from pathlib import Path
import hashlib
import json
import math

from seti_repeater import source_m43h, calibration_transfer_radio as legacy

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results_radio_alternate_2026-09-27"
OUT = ROOT / "results_radio_hd189733_geometry_2026-09-27"
SOURCE = "config/radio_hd189733_source_preparation_20260927.json"
OFFICIAL = "results_radio_alternate_2026-09-27/attempt01/85030/official_metadata.json"
SCOPE = "RADIO_HD189733_GEOMETRY_2026-09-27_SCOPE.md"
C = 299792458.0
AU = 149597870700.0
REFERENCE_HZ = 1425850000.0


def save(name, value):
    with (OUT/name).open('x') as f:
        json.dump(value,f,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n')


def main():
    OUT.mkdir(exist_ok=False)
    cfg=json.loads((ROOT/SOURCE).read_text())
    row=json.loads((ROOT/OFFICIAL).read_text())[0]
    assert cfg['cadence_id']==85030 and row['pl_name']=='HD 189733 b' and row['pl_orbeccen']==0
    paths=[SOURCE,OFFICIAL,SCOPE,'scripts/radio_hd189733_geometry_20260927.py',
           'src/seti_repeater/calibration_transfer_radio.py','src/seti_repeater/source_m43h.py']
    save('input_pins.json',{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})
    scans=cfg['scans'];h=scans[0]['expected_header'];dt=h['tsamp_s'];df=abs(h['foff_mhz'])*1e6
    origin=h['tstart_mjd']; anchor=dt/2
    times=[]
    for s in scans:
        a=s['expected_header']
        for i in range(a['dataset_shape'][0]):
            times.extend([(a['tstart_mjd']-origin)*86400+(i+f)*a['tsamp_s']-anchor for f in (0,.5,1)])
    period=row['pl_orbper']*86400
    radius=row['pl_orbsmax']*AU
    velocity=2*math.pi*radius/period
    factor=2*REFERENCE_HZ*velocity/(C-velocity)
    displacements=[factor*abs(math.sin(math.pi*t/period)) for t in times]
    max_displacement=max(displacements)
    sweep=factor*abs(math.sin(math.pi*dt/period))
    widths=[{'width_channels':w,'available_hz':w*df,'required_hz':sweep+df,
             'nominal_sweep_plus_one_bin_fits':w*df>=sweep+df} for w in (129,257)]
    width=next((x['width_channels'] for x in widths if x['nominal_sweep_plus_one_bin_fits']),None)
    assert width is not None
    guard=max_displacement+(49+width//2+1)*df
    lengths=[{'native_channels':n,'available_half_guard_hz':(n//2-1)*df,
              'required_half_guard_hz':guard,'nominal_geometry_fits':(n//2-1)*df>=guard} for n in (16384,32768,65536)]
    length=next((x['native_channels'] for x in lengths if x['nominal_geometry_fits']),None)
    assert length is not None
    # Independent trigonometric identity check at the two-point phase witness:
    # max of sin(phi+d)-sin(phi) is achieved at phi=-d/2.
    t=times[displacements.index(max_displacement)];d=2*math.pi*t/period
    diff=velocity*(math.sin(d/2)-math.sin(-d/2))
    assert abs(abs(diff)-2*velocity*abs(math.sin(math.pi*t/period))) < 1e-8
    witness=REFERENCE_HZ*abs(diff)/(C-velocity*math.sin(-d/2))
    assert witness<=max_displacement+1e-8
    chunk=scans[0]['expected_chunks'][2]
    assert all(s['expected_chunks']==[1,1,chunk] for s in scans)
    windows=[]
    for role,anchor_mhz in [('calibration',1400.5),('validation',1412.5),('pilot',1425.0)]:
        choices=[]
        for k in range(h['dataset_shape'][2]//chunk):
            center=k*chunk+chunk//2
            a,z=center-length//2,center+length//2
            low=(h['fch1_mhz']+(z-1)*h['foff_mhz'])*1e6
            high=(h['fch1_mhz']+a*h['foff_mhz'])*1e6
            carrier=(h['fch1_mhz']+center*h['foff_mhz'])*1e6
            if low>=1399650000 and high<=1425850000:
                choices.append((abs(carrier-anchor_mhz*1e6),k,a,z,low,high,carrier))
        _,k,a,z,low,high,carrier=min(choices)
        assert a//chunk==(z-1)//chunk==k
        payload=[{'source_url':s['url'],'source_size_bytes':s['expected_remote_size_bytes'],
                  'etag':s['expected_etag'],'chunk_coordinates_time_feed_frequency':[[i,0,k] for i in range(16)]} for s in scans]
        record={'schema':'radio-hd189733-prospective-window-geometry-v1','role':role,
                'name':'hd189733_'+role+'_geometry','archive_chunk_index':k,
                'archive_interval':[a,z],'native_channel_count':length,
                'native_frequency_low_hz':low,'native_frequency_high_hz':high,
                'proposed_first_on_midpoint_carrier_center_hz':carrier,
                'normalization_blocks_native_channels':[[i,i+4096] for i in range(0,length,4096)],
                'payload_keys':payload,'payload_keys_sha256':source_m43h.digest(payload),
                'source_contract_sha256':hashlib.sha256((ROOT/SOURCE).read_bytes()).hexdigest(),
                'spectral_values_included':False,'spectral_access_authorized':False}
        record['identity']=source_m43h.digest(record)
        windows.append(record)
    assert len({w['archive_chunk_index'] for w in windows})==3
    identities={(p['source_url'],tuple(map(tuple,p['chunk_coordinates_time_feed_frequency']))) for w in windows for p in w['payload_keys']}
    assert len(identities)==18
    try:
        legacy.build_window(windows[0])
    except ValueError as error:
        rejection=str(error)
    else:
        raise AssertionError('Legacy fixed-length contract unexpectedly accepted the new geometry')
    save('window_geometry.json',{'schema':'radio-hd189733-window-geometry-study-v1',
        'status':'PROSPECTIVE_IDENTITIES_ONLY_NOT_AN_EXECUTABLE_PROTOCOL',
        'windows':windows,'primary':'neighbor9','payload_identity_count':len(identities),
        'normalization_block_count':sum(len(w['normalization_blocks_native_channels']) for w in windows),
        'legacy_v1_contract_rejection':rejection,'legacy_v1_modified':False,
        'spectral_access_authorized':False,'physical_bank_qualified':False,
        'new_control_panel_executed':False,'new_control_panel_identities_frozen':False,
        'development_identity_allocated':False,'calibration_numeric_transfer_qualified':False})
    result={'schema':'radio-hd189733-nominal-geometry-result-v1',
        'assumptions':'Nominal circular emitter radius equal to catalogue semimajor axis; all phases, stationary observer, first-order Doppler normalized at first ON midpoint. Not actual-source physical qualification.',
        'source_contract_sha256':hashlib.sha256((ROOT/SOURCE).read_bytes()).hexdigest(),
        'period_seconds':period,'radius_m':radius,'velocity_amplitude_m_s':velocity,
        'reference_frequency_hz':REFERENCE_HZ,'integration_seconds':dt,'channel_width_hz':df,
        'relative_clock_extent_seconds':[min(times),max(times)],'integration_start_mid_end_points':len(times),
        'continuous_phase_displacement_bound_hz':max_displacement,
        'phase_witness_exact_normalized_displacement_hz':witness,
        'continuous_phase_integration_sweep_bound_hz':sweep,
        'sweep_native_channels':sweep/df,'width_comparison':widths,'length_comparison':lengths,
        'smallest_tested_width_for_nominal_sweep':width,'smallest_tested_length_for_nominal_guard':length,
        'decoded_extracted_float32_bytes_all_roles':3*6*16*length*4,
        'decoded_full_chunk_bytes_all_roles':3*6*16*chunk*4,
        'modelled_reader_buffer_bytes':source_m43h.resource_bound(length),
        'modelled_buffer_excludes_native_library_and_os_overhead':True,
        'compressed_wire_bytes_measured':False,'runtime_benchmarked':False,
        'network_requests':0,'telescope_values_opened':False,'scientific_trials':0,
        'full_physical_error_budget_hz':None,'actual_source_coverage_qualified':False,
        'legacy_cross_window_contract_compatible':False,
        'required_next_change':'New explicitly versioned window/control/transfer contract for selected source and length; old v1 remains immutable. Full motion/codec/recovery gates remain required.'}
    save('result.json',result)
    print(json.dumps({**{k:result[k] for k in ['continuous_phase_displacement_bound_hz','continuous_phase_integration_sweep_bound_hz','sweep_native_channels','smallest_tested_width_for_nominal_sweep','smallest_tested_length_for_nominal_guard','decoded_extracted_float32_bytes_all_roles','decoded_full_chunk_bytes_all_roles','modelled_reader_buffer_bytes']},'windows':[{k:w[k] for k in ['role','archive_interval','native_frequency_low_hz','native_frequency_high_hz','archive_chunk_index']} for w in windows],'legacy_rejection':rejection},indent=2))


if __name__=='__main__':main()
