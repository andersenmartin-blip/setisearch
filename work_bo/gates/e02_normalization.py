"""E02: deterministic full-native normalization and independent sample oracles.

No fixture or numerical value is created on import. This gate must only run
after the parent publishes and reads back its immutable engineering plan.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from src import methods

SHAPE = (16,1048576)
BLOCK = 4096
FIXTURE_IDS = ('triangle_v1','step_outliers_v1')
ROWS = (0,7,15)
BLOCKS = (0,1,62,63,64,65,126,127,128,129,254,255)
OUTLIERS = (4096,63*4096-1,64*4096,65*4096+3,127*4096-1,128*4096,129*4096+17,1048576-4097)
NORMALIZED_SAMPLE_ULPS = 1
COEFFICIENT_EPS_FACTOR = 64


def fixture(identifier):
    """Fully specified positive float32 software fixture, with no RNG."""
    c = np.arange(SHAPE[1],dtype=np.float64)
    triangle = (512.0-np.abs(np.remainder(c,1024.0)-512.0))/128.0
    base = 128.0 + 0.25*triangle + c/(4.0*(SHAPE[1]-1))
    raw = np.empty(SHAPE,dtype='<f4')
    if identifier == 'triangle_v1':
        for row in range(SHAPE[0]):
            raw[row] = (base + row/32.0).astype('<f4')
    elif identifier == 'step_outliers_v1':
        gain = np.where(c < 64*BLOCK,1.0,1.25)
        for row in range(SHAPE[0]):
            raw[row] = ((base + row/32.0)*gain).astype('<f4')
            for column in OUTLIERS:
                raw[row,column] = np.float32(raw[row,column] + np.float32(5000+row))
    else:
        raise ValueError('Unknown deterministic fixture identity')
    raw.flags.writeable = False
    return raw


def save_array(path, values):
    methods.require(values.dtype == np.dtype('<f4') and values.shape == SHAPE, 'Fixture geometry differs')
    with Path(path).open('xb') as stream:
        np.save(stream,values,allow_pickle=False)
        stream.flush()
        os.fsync(stream.fileno())
    return methods.file_sha(path)


def median_f32_oracle(values):
    """Independent explicit sort and original float32 two-value mean."""
    ordered = sorted(float(v) for v in values)
    n = len(ordered)
    if n % 2:
        return np.float32(ordered[n//2])
    middle_sum = np.float32(np.float32(ordered[n//2-1])+np.float32(ordered[n//2]))
    return np.float32(middle_sum/np.float32(2))


def anchor_oracle(raw,row,block):
    values = raw[row,block*BLOCK:(block+1)*BLOCK]
    median = median_f32_oracle(values)
    deviations = [np.float32(abs(np.float32(value-median))) for value in values]
    scale = np.float32(median_f32_oracle(deviations)*np.float32(1.4826))
    methods.require(math.isfinite(float(scale)) and scale > 0, 'Oracle fixture MAD invalid')
    return median,scale


def interpolation_oracle(raw,row,x,cache):
    first,last = (BLOCK-1)/2,(SHAPE[1]-BLOCK)+(BLOCK-1)/2
    if x <= first:
        left = right = 0
    elif x >= last:
        left = right = SHAPE[1]//BLOCK-1
    else:
        left = int(math.floor((x-first)/BLOCK))
        right = left+1
    for block in (left,right):
        if (row,block) not in cache:
            cache[row,block] = anchor_oracle(raw,row,block)
    a,b = cache[row,left],cache[row,right]
    weight = 0.0 if left == right else (x-(left*BLOCK+first))/BLOCK
    return (float(a[0])+(float(b[0])-float(a[0]))*weight,
            float(a[1])+(float(b[1])-float(a[1]))*weight)


def oracle_checks(raw,legacy,current,legacy_anchors,anchors,normalizer):
    starts = np.arange(0,SHAPE[1],BLOCK,dtype=np.int64)
    stops = starts+BLOCK
    centers = (starts.astype(np.float64)+stops.astype(np.float64)-1)/2
    methods.require(anchors['block_start'].dtype == np.dtype('int64')
                    and anchors['block_stop'].dtype == np.dtype('int64')
                    and anchors['anchor_channel'].dtype == np.dtype('float64')
                    and np.array_equal(anchors['block_start'],starts)
                    and np.array_equal(anchors['block_stop'],stops)
                    and np.array_equal(anchors['anchor_channel'],centers), 'Complete 256-block anchor geometry differs')
    for key in ['block_median','block_MAD_scale']:
        methods.require(anchors[key].shape == (256,16) and anchors[key].dtype == np.dtype('<f4')
                        and np.isfinite(anchors[key]).all(), 'Full anchor coefficient geometry/dtype differs')
    methods.require((anchors['block_MAD_scale'] > 0).all(), 'Nonpositive fitted anchor scale')
    methods.require(len(legacy_anchors) == 256, 'Full legacy anchor inventory differs')
    for index,record in enumerate(legacy_anchors):
        methods.require(record['channel_lo'] == int(starts[index])
                        and record['channel_hi_exclusive'] == int(stops[index])
                        and len(record['median']) == len(record['mad_scale']) == 16,
                        'Complete legacy block geometry differs')
    cache = {}
    records = []
    for row in ROWS:
        for block in BLOCKS:
            median,scale = anchor_oracle(raw,row,block)
            cache[row,block] = median,scale
            methods.require(anchors['block_median'][block,row] == median
                            and anchors['block_MAD_scale'][block,row] == scale,
                            'Current anchor differs from independent float32 sort oracle')
            methods.require(np.float32(legacy_anchors[block]['median'][row]) == median
                            and np.float32(legacy_anchors[block]['mad_scale'][row]) == scale,
                            'Legacy anchor differs from independent float32 sort oracle')
            records.append(dict(kind='INDEPENDENT_ANCHOR',row=row,block=block,
                                median=float(median),scale=float(scale),pass_=True))
    positions = sorted(set([0.0,float(SHAPE[1]-1)]
                          + [float(block*BLOCK+offset) for block in BLOCKS
                             for offset in [0,2047,2047.5,2048,4095]]))
    medians,scales = normalizer.interpolate_coefficients(anchors,np.asarray(positions,dtype=np.float64))
    maximum_coefficient_error = 0.0
    maximum_current_sample_error = 0.0
    current_nonzero_sample_errors = 0
    for row in ROWS:
        for index,x in enumerate(positions):
            median,scale = interpolation_oracle(raw,row,x,cache)
            for label,got,expected in [('median',medians[row,index],median),('scale',scales[row,index],scale)]:
                error = abs(float(got)-expected)
                bound = COEFFICIENT_EPS_FACTOR*np.finfo(np.float64).eps*max(1.0,abs(expected),abs(float(got)))
                methods.require(error <= bound,'Interpolation coefficient differs from independent bracketing oracle')
                maximum_coefficient_error = max(maximum_coefficient_error,error)
                records.append(dict(kind='INDEPENDENT_INTERPOLATION',row=row,x=x,coefficient=label,
                                    absolute_error=error,bound=float(bound),pass_=True))
            if x.is_integer():
                channel = int(x)
                expected = np.float32((float(raw[row,channel])-median)/scale)
                got = current[row,channel]
                error = abs(float(got)-float(expected))
                ulp = abs(float(np.spacing(expected)))
                methods.require(error <= NORMALIZED_SAMPLE_ULPS*ulp,'Current normalized sample exceeds independent one-ULP oracle bound')
                maximum_current_sample_error = max(maximum_current_sample_error,error)
                current_nonzero_sample_errors += int(error != 0)
                block = channel//BLOCK
                if (row,block) not in cache:
                    cache[row,block] = anchor_oracle(raw,row,block)
                lm,ls = cache[row,block]
                expected_legacy = np.float32(np.float32(raw[row,channel]-lm)/ls)
                methods.require(legacy[row,channel].tobytes() == expected_legacy.tobytes(),
                                'Legacy normalized sample differs from explicit float32 oracle')
                records.append(dict(kind='INDEPENDENT_NORMALIZED_SAMPLE',row=row,channel=channel,
                                    current_absolute_error=error,current_one_ULP_bound=ulp,
                                    legacy_bit_exact=True,pass_=True))
    return dict(checks=records,independent_anchor_count=len(ROWS)*len(BLOCKS),
                independent_coefficient_count=len(ROWS)*len(positions)*2,
                independent_normalized_sample_count=sum(v['kind']=='INDEPENDENT_NORMALIZED_SAMPLE' for v in records),
                maximum_coefficient_error=maximum_coefficient_error,
                maximum_current_sample_error=maximum_current_sample_error,
                current_nonzero_sample_errors=current_nonzero_sample_errors,
                current_normalized_oracle_bound='one float32 ULP; no retrospective adjustment',
                coefficient_oracle_bound='64*eps64*max(1,abs(expected),abs(got))')


def fatal_guard_checks(normalizer):
    records = []
    for label,normalize in [('legacy',methods.legacy_normalize),('current',normalizer.normalize)]:
        for kind in ['ZERO_MAD','NONFINITE_RAW']:
            raw = np.full((16,8192),128,dtype='<f4')
            if kind == 'NONFINITE_RAW':
                raw[:] = (128+np.remainder(np.arange(8192),17))[None,:]
                raw[0,4096] = np.float32(np.nan)
            try:
                normalize(raw,BLOCK)
            except ValueError as exc:
                records.append(dict(method=label,fixture=kind,expected='ValueError',
                                    observed_exception=type(exc).__name__,reason=str(exc),status='PASS_EXPECTED_REJECTION'))
            else:
                raise ValueError('Fatal normalization fixture was silently accepted: '+label+'/'+kind)
    return records


def corrupted_anchor_checks(anchors,normalizer):
    records = []
    for value,label in [(0.0,'ZERO_ANCHOR_SCALE'),(-1.0,'NEGATIVE_ANCHOR_SCALE')]:
        corrupt = {key:array.copy() for key,array in anchors.items()}
        corrupt['block_MAD_scale'][64,7] = np.float32(value)
        try:
            normalizer.interpolate_coefficients(corrupt,np.array([64*BLOCK+2047.5],dtype=np.float64))
        except ValueError as exc:
            records.append(dict(fixture=label,expected='ValueError',observed_exception=type(exc).__name__,
                                reason=str(exc),status='PASS_EXPECTED_REJECTION'))
        else:
            raise ValueError('Corrupted anchor scale was silently accepted: '+label)
    return records


def gate(config_path,out):
    config = methods.verify_config(config_path)
    methods.require(Path(config['gate_outputs']['E02']).resolve() == out.resolve(), 'E02 output differs from frozen identity')
    source_check = methods.verify_sources()
    kernel,normalizer = methods.load_current()
    out.mkdir(exist_ok=False)
    fatal_checks = fatal_guard_checks(normalizer)
    records = []
    diagnostics = []
    for identifier in FIXTURE_IDS:
        raw = fixture(identifier)
        input_payload_sha = hashlib.sha256(raw.tobytes(order='C')).hexdigest()
        input_path = out/(identifier+'_raw.npy')
        input_sha = save_array(input_path,raw)
        legacy,legacy_anchors = methods.legacy_normalize(raw,BLOCK)
        current,anchors = normalizer.normalize(raw,BLOCK)
        methods.require(hashlib.sha256(raw.tobytes(order='C')).hexdigest() == input_payload_sha,
                        'Normalization modified raw software fixture')
        methods.require(np.isfinite(current).all() and np.isfinite(legacy).all(), 'Nonfinite normalized fixture')
        checks = oracle_checks(raw,legacy,current,legacy_anchors,anchors,normalizer)
        if identifier == FIXTURE_IDS[0]:
            fatal_checks.extend(corrupted_anchor_checks(anchors,normalizer))
        legacy_path = out/(identifier+'_legacy_normalized.npy')
        current_path = out/(identifier+'_current_normalized.npy')
        legacy_sha = save_array(legacy_path,legacy)
        current_sha = save_array(current_path,current)
        anchor_path = out/(identifier+'_current_anchors.npz')
        with anchor_path.open('xb') as stream:
            np.savez_compressed(stream,**anchors)
            stream.flush()
            os.fsync(stream.fileno())
        diagnostics.append(dict(id=identifier,oracle=checks,current_anchors_path=str(anchor_path.resolve()),
                                current_anchors_sha256=methods.file_sha(anchor_path)))
        records.append(dict(id=identifier,shape=list(SHAPE),dtype='<f4',input_path=str(input_path.resolve()),
                            input_sha256=input_sha,input_payload_sha256=input_payload_sha,
                            current_normalized_path=str(current_path.resolve()),current_normalized_sha256=current_sha,
                            legacy_normalized_path=str(legacy_path.resolve()),legacy_normalized_sha256=legacy_sha))
        del raw,current,legacy,anchors,legacy_anchors
    methods.write_json_exclusive(out/'FIXTURES.json',dict(schema='SETI_BO_DETERMINISTIC_FIXTURE_BINDING_V1',fixtures=records))
    methods.require(len(fatal_checks) == 6, 'Expected six deterministic fatal-guard rejection checks')
    methods.verify_config(config_path)
    result = dict(schema='SETI_BO_E02_NORMALIZATION_RESULT_V1',gate='E02',status='PASS',
                  engineering_only=True,config_sha256=methods.file_sha(config_path),source_check=source_check,
                  fixtures=records,diagnostics=diagnostics,fixture_count=2,
                  full_256_block_geometry_and_dtypes_verified=True,fatal_guard_checks=fatal_checks,
                  full_native_rows_per_fixture=16,full_native_channels_per_fixture=1048576,
                  expected_outcome='All independent anchors, coefficients and normalized samples satisfy frozen bounds; exact immutable software-input binding.',
                  RNG_draws=0,astronomical_powers_opened=False,scientific_scores_computed=False)
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
