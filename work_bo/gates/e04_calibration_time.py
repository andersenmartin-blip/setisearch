"""E04: whole-domain paired calibration and explicit reference-epoch identities.

Only saved deterministic E02 software matrices are admitted. No RNG or
astronomical powers are read; no computation occurs on import.
"""
from pathlib import Path
import argparse
import json
import math
import os
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from src import methods

START,STOP = 4096,1044480
COEFFICIENT_EPS_FACTOR = 64
MJD_INTERVAL_TOLERANCE_SECONDS = 0.000002
HEADER_TSTARTS = (57642.735972222225,57642.73994212963,57642.74390046296,
                 57642.74791666667,57642.751921296294,57642.75582175926)
HIP45688_FCH1_MHZ = 1422.36328125
PHYSICAL_NATIVE_ORIGIN = 180355072


def median32(ordered):
    n = len(ordered)
    if n % 2:
        return np.float32(ordered[n//2])
    return np.float32(np.float32(np.float32(ordered[n//2-1])+np.float32(ordered[n//2]))/np.float32(2))


def sorted_calibration_oracle(values):
    """Independent sorted scalar medians, with each declared dtype rounding."""
    ordered = sorted(float(value) for value in values)
    if values.dtype == np.dtype('float32'):
        median = median32(ordered)
        deviations = sorted(float(np.float32(abs(np.float32(np.float32(value)-median))))
                            for value in values)
        scale = np.float32(np.float32(1.4826)*median32(deviations))
        return float(median),float(scale)
    methods.require(values.dtype == np.dtype('float64'), 'Unsupported oracle dtype')
    median = float(statistics.median(ordered))
    deviations = [abs(float(value)-median) for value in values]
    return median,float(1.4826*statistics.median(deviations))


def compare_calibration(values,actual,label):
    expected = sorted_calibration_oracle(values)
    checks = []
    for name,got,want in zip(['median','MAD_scale'],actual,expected,strict=True):
        error = abs(got-want)
        bound = 0.0 if values.dtype == np.dtype('float32') else COEFFICIENT_EPS_FACTOR*np.finfo(np.float64).eps*max(1.0,abs(got),abs(want))
        methods.require(error <= bound,'Calibration differs from independent complete-vector sort oracle: '+label+'/'+name)
        checks.append(dict(coefficient=name,actual=got,independent=want,absolute_error=error,bound=float(bound),pass_=True))
    return dict(identity=label,centers=len(values),dtype=str(values.dtype),checks=checks)


def time_and_support_checks():
    rates = methods.legacy_drift_grid(16,methods.DT,methods.DF,4)
    expected = np.linspace(-4,4,839,dtype=np.float64)
    methods.require(np.array_equal(rates,expected),'Legacy/current complete rate-bank identity differs')
    times = (np.arange(16,dtype=np.float64)-7.5)*methods.DT
    current_offsets = np.rint(expected[:,None]*times[None,:]/methods.DF).astype(np.int32)
    legacy_times = (np.arange(16,dtype=np.float64)-(16-1)/2)*methods.DT
    legacy_offsets = np.rint(rates[:,None]*legacy_times[None,:]/methods.DF).astype(np.int32)
    methods.require(np.array_equal(current_offsets,legacy_offsets),'Actual row7.5 track indexing differs')
    ties = np.array([-2.5,-1.5,-0.5,0.5,1.5,2.5],dtype=np.float64)
    methods.require(np.array_equal(np.rint(ties),np.array([-2,-2,0,0,2,2],dtype=np.float64)), 'Nearest-even ties differ')
    records = []
    current_refs,legacy_refs = [],[]
    for scan,start in enumerate(HEADER_TSTARTS):
        new_ref = start+7.5*methods.DT/86400
        legacy_ref = start+16*methods.DT/(2*86400)
        delta = (legacy_ref-new_ref)*86400
        methods.require(abs(delta-methods.DT/2) <= MJD_INTERVAL_TOLERANCE_SECONDS,
                        'Explicit old/new nominal epoch delta differs')
        current_refs.append(new_ref)
        legacy_refs.append(legacy_ref)
        records.append(dict(scan=scan,header_tstart_mjd=start,
                            new_samplecenter_tref_mjd=new_ref,historical_M_nominal_tref_mjd=legacy_ref,
                            observed_nominal_delta_seconds=delta,exact_half_dt_seconds=methods.DT/2,
                            actual_M_internal_index_center=7.5,current_internal_index_center=7.5,
                            historical_fields_modified=False,pass_=True))
    interval_checks = []
    for scan in range(1,6):
        old_gap = (legacy_refs[scan]-legacy_refs[0])*86400
        new_gap = (current_refs[scan]-current_refs[0])*86400
        methods.require(abs(old_gap-new_gap) <= MJD_INTERVAL_TOLERANCE_SECONDS, 'Old/new interscan interval differs beyond metadata rounding bound')
        interval_checks.append(dict(scan=scan,legacy_interval_seconds=old_gap,new_interval_seconds=new_gap,
                                    absolute_error_seconds=abs(old_gap-new_gap),bound_seconds=MJD_INTERVAL_TOLERANCE_SECONDS,pass_=True))
    mid = 64*4096+2048.0
    frequency = HIP45688_FCH1_MHZ+mid*methods.DF/1e6
    mappings = []
    for index in methods.RATE_INDICES:
        rate = float(rates[index])
        transformed_channel = mid+rate*(methods.DT/2)/methods.DF
        new_trajectory = mid+rate*times/methods.DF
        transformed_trajectory = transformed_channel+rate*(times-methods.DT/2)/methods.DF
        error = float(np.max(np.abs(new_trajectory-transformed_trajectory)))
        bound = float(COEFFICIENT_EPS_FACTOR*np.finfo(np.float64).eps*max(1.0,float(np.max(np.abs(new_trajectory)))))
        methods.require(error <= bound,'Separate affine epoch transformation changes physical track')
        methods.require(np.array_equal(np.rint(new_trajectory),np.rint(transformed_trajectory)), 'Separate epoch transform changes selected sample indices')
        mappings.append(dict(identity='BO_NEW_COORDINATE_HYPOTHESIS_RATE_'+str(index),rate_index=index,rate_hz_s=rate,
                             new_frequency_at_sample_center_mhz=frequency,
                             hypothetical_frequency_at_old_nominal_epoch_mhz=frequency+rate*(methods.DT/2)/1e6,
                             hypothetical_channel_at_old_nominal_epoch=transformed_channel,
                             historical_M_reported_frequency_label_retained_mhz=frequency,
                             maximum_channel_error=error,bound=bound,same_rounded_sample_indices=True,
                             old_identity_repaired_or_relabelled=False,pass_=True))
    span = (max(current_refs)-min(current_refs))*86400
    maxshift = math.ceil(4*(span+7.5*methods.DT)/abs(methods.DF))+16
    radius = math.ceil(1+0.5*(rates[1]-rates[0])*span/abs(methods.DF))
    methods.require(maxshift+radius < 4096,'Frozen six-scan halo is insufficient')
    return dict(full_rate_bank_count=839,actual_offset_pairs_compared=839*16,
                nominal_epoch_records=records,interscan_interval_checks=interval_checks,
                separate_coordinate_hypotheses=mappings,nearest_even_ties_checked=True,
                sample_time_convention='Header tstart is explicitly treated as row0 sample time for this engineering hypothesis; no integration-edge semantics claim.',
                historical_M_internal_offsets='row7.5; unchanged',historical_M_nominal_metadata='header+8dt; unchanged',
                new_nominal_metadata='header+7.5dt in a distinct BO hypothesis',
                native_origin=PHYSICAL_NATIVE_ORIGIN,fch1_slice_mhz=HIP45688_FCH1_MHZ,
                fixed_halo_channels=4096,maximum_shift_plus_radius=maxshift+radius,
                metadata_interval_tolerance_seconds=MJD_INTERVAL_TOLERANCE_SECONDS,
                historical_telescope_powers_opened=False)


def explicit_support_rejections(kernel):
    """Guard rejection only; this is not six-scan association qualification."""
    y = np.tile((np.arange(128,dtype=np.float32)/np.float32(16)-np.float32(4))[None,:],(16,1))
    specifications = [
        ('NEGATIVE_CENTER',-1,0,1),('HIGH_CENTER',128,0,1),
        ('NEGATIVE_OFFSET',64,-65,1),('HIGH_OFFSET',64,64,1),
        ('LEFT_SMOOTHING_SUPPORT',15,0,33),('RIGHT_SMOOTHING_SUPPORT',112,0,33)]
    prepared = {width:kernel.boxcars(y,width) for width in [1,33]}
    records = []
    for identity,center,offset,width in specifications:
        centers = np.array([center],dtype=np.int32)
        offsets = np.full(16,offset,dtype=np.int32)
        for mode in ['selected','grid']:
            try:
                if mode == 'selected':
                    kernel.tracks_selected(y,prepared[width],offsets,centers,width)
                else:
                    kernel.tracks_grid(y,prepared[width],offsets,center,center+1,1,width)
            except ValueError as exc:
                methods.require(str(exc) == 'Requested track outside stored support', 'Unexpected error instead of support rejection')
                records.append(dict(case=identity,mode=mode,center=center,offset=offset,width=width,
                                    expected='ValueError: Requested track outside stored support',
                                    observed=str(exc),status='PASS_EXPECTED_SUPPORT_REJECTION'))
            else:
                raise ValueError('Unsupported software track was accepted: '+identity+'/'+mode)
    methods.require(len(records) == 12,'Expected twelve support-guard rejection checks')
    return records


def gate(config_path,out):
    config = methods.verify_config(config_path)
    methods.require(Path(config['gate_outputs']['E04']).resolve() == out.resolve(), 'E04 output identity differs')
    source_check = methods.verify_sources()
    _,fixture_result = methods.resolve_e02(config)
    kernel,normalizer = methods.load_current()
    out.mkdir(exist_ok=False)
    rates = methods.legacy_drift_grid(16,methods.DT,methods.DF,4)
    times = (np.arange(16,dtype=np.float64)-7.5)*methods.DT
    offsets = np.rint(rates[:,None]*times[None,:]/methods.DF).astype(np.int32)
    factorial = []
    independent = []
    global_saved = []
    global_complete_checks = 0
    local_complete_checks = 0
    for fixture in fixture_result['fixtures']:
        for normalization in ['legacy','current']:
            path = Path(fixture[normalization+'_normalized_path'])
            values = np.load(path,mmap_mode='r',allow_pickle=False)
            methods.require(values.shape == (16,1048576) and values.dtype == np.dtype('<f4'), 'E02 normalized software fixture geometry differs')
            for width,stride in zip(methods.WIDTHS,methods.STRIDES,strict=True):
                # Each full-native convolution/prefix is prepared once, then reused.
                old_prepared = methods.legacy_centered_boxcar(values,width)
                new_prepared = kernel.boxcars(values,width)
                for rate_index in methods.RATE_INDICES:
                    off = offsets[rate_index]
                    vectors = {
                        'float32':methods.legacy_track_sum(old_prepared,off,START,STOP,stride),
                        'float64':kernel.tracks_grid(values,new_prepared,off,START,STOP,stride,width)[0]}
                    for accumulation,sums in vectors.items():
                        methods.require(len(sums) == (STOP-START)//stride, 'Global reference is not the complete M interior')
                        global_cal = methods.current_calibration(sums)
                        methods.require(global_cal == methods.legacy_ess_calibration(sums), 'Calibration source formulas differ')
                        identity = fixture['id']+'/'+normalization+'/'+accumulation+'/w'+str(width)+'/r'+str(rate_index)
                        if fixture['id'] == 'triangle_v1' and normalization == 'legacy' and width == 1 and rate_index == 419:
                            independent.append(compare_calibration(sums,global_cal,identity+'/FULL_GLOBAL'))
                            global_complete_checks += 1
                            vector_path = out/('full_global_reference_'+accumulation+'.npy')
                            with vector_path.open('xb') as stream:
                                np.save(stream,sums,allow_pickle=False)
                                stream.flush()
                                os.fsync(stream.fileno())
                            global_saved.append(dict(path=str(vector_path.resolve()),sha256=methods.file_sha(vector_path),
                                                     complete_domain=[START,STOP],stride=stride,centers=len(sums),dtype=str(sums.dtype)))
                        for q in methods.CONTROL_Q:
                            lo = (q*4096-START)//stride
                            hi = ((q+1)*4096-START)//stride
                            local = sums[lo:hi]
                            methods.require(len(local) == 4096//stride, 'Local calibration is not a complete core')
                            local_cal = methods.current_calibration(local)
                            independent.append(compare_calibration(local,local_cal,identity+'/FULL_LOCAL_Q'+str(q)))
                            local_complete_checks += 1
                            selected = np.array([0,len(local)//2,len(local)-1],dtype=np.int64)
                            centers = q*4096+selected*stride
                            if accumulation == 'float64':
                                selected_sums = kernel.tracks_selected(values,new_prepared,off,centers.astype(np.int32),width)[0]
                                methods.require(np.array_equal(selected_sums,local[selected]), 'Selected/grid full-domain carrier mapping differs')
                            for calibration,coeff in [('global',global_cal),('local',local_cal)]:
                                score = (local-coeff[0])/coeff[1]
                                methods.require(np.isfinite(score).all(), 'Nonfinite factorial score')
                                factorial.append(dict(identity=identity+'/q'+str(q)+'/'+calibration,
                                    fixture=fixture['id'],normalization=normalization,accumulation=accumulation,
                                    calibration=calibration,calibration_domain=([START,STOP] if calibration=='global' else [q*4096,(q+1)*4096]),
                                    q=q,width=width,stride=stride,rate_index=rate_index,rate_hz_s=float(rates[rate_index]),
                                    complete_calibration_carriers=((STOP-START)//stride if calibration=='global' else len(local)),
                                    median=coeff[0],MAD_scale=coeff[1],selected_centers=centers.tolist(),
                                    selected_sums=[float(x) for x in local[selected]],selected_ESS=[float(x) for x in score[selected]],
                                    maximum_local_ESS=float(np.max(score)),minimum_local_ESS=float(np.min(score)),
                                    input_normalized_sha256=fixture[normalization+'_normalized_sha256'],
                                    interpretation='Paired deterministic engineering diagnosis; no ranking/adoption or astronomical threshold calibration.'))
                    del vectors
                del old_prepared,new_prepared
            del values
    methods.require(global_complete_checks == 2 and local_complete_checks == 800 and len(factorial) == 1600,
                    'Frozen factorial/oracle case count differs')
    coordinates = time_and_support_checks()
    support_rejections = explicit_support_rejections(kernel)
    methods.verify_config(config_path)
    methods.resolve_e02(config)
    methods.write_json_exclusive(out/'FACTORIAL_DIAGNOSIS.json',dict(schema='SETI_BO_TWO_BY_TWO_BY_TWO_DIAGNOSIS_V1',
        all_factor_combinations=['legacy/current normalization','float32/float64 accumulation','global/local calibration'],
        factorial_records=factorial,records_count=1600,no_after_result_method_selection=True,
        original_M_failures_modified=False,astronomical_powers_opened=False,RNG_draws=0))
    methods.write_json_exclusive(out/'INDEPENDENT_CALIBRATION_ORACLES.json',dict(
        global_complete_vectors=global_complete_checks,local_complete_vectors=local_complete_checks,checks=independent,
        float32_comparison_bound='exact declared float32 median/MAD arithmetic',
        float64_comparison_bound='64*eps64*max(1,abs(actual),abs(oracle))'))
    result = dict(schema='SETI_BO_E04_CALIBRATION_TIME_RESULT_V1',gate='E04',status='PASS',
                  engineering_only=True,config_sha256=methods.file_sha(config_path),source_check=source_check,
                  full_global_reference_vectors=global_saved,complete_global_oracle_checks=global_complete_checks,
                  complete_local_oracle_checks=local_complete_checks,factorial_records=1600,
                  time_and_support=coordinates,RNG_draws=0,astronomical_powers_opened=False,
                  explicit_support_rejections=support_rejections,support_rejection_count=12,
                  support_check_scope='Known invalid selected/grid centers, offsets and smoothing support only; no synthetic six-scan association qualification.',
                  historical_M_requalified=False,original_M_full_QA_status_changed=False,
                  expected_outcome='Full stated global/local domains, independent complete-vector calibration and separate epoch identities satisfy prospectively frozen bounds; no required equality between distinct methods.')
    methods.write_json_exclusive(out/'RESULT.json',result)
    print(json.dumps(dict(event='GATE_TERMINAL_EOF',status='PASS',result_sha256=methods.file_sha(out/'RESULT.json'))),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args = parser.parse_args()
    gate(args.config.resolve(),args.out.resolve())


if __name__ == '__main__':
    main()
