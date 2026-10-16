#!/usr/bin/env python3
"""Fixed, descriptive exposure-sweep morphology; no detection or refitting."""
from pathlib import Path
import csv
import hashlib
import io
import json
import math
import resource
import signal
import time
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parent
NORM_FIELDS = ('row_power_median', 'row_residual_MAD_scale', 'row_winsorized_residual_location')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def uniform_convolution_cdf(x, a, b):
    """CDF of independent centered unit-area uniforms of full widths a,b."""
    x = np.asarray(x, dtype=np.float64)
    half = (a + b) / 2
    positive = lambda y: np.maximum(y, 0.) ** 2
    result = (positive(x + half) - positive(x + (a-b)/2)
              - positive(x + (b-a)/2) + positive(x-half)) / (2*a*b)
    return np.where(x <= -half, 0., np.where(x >= half, 1., result))


def statistic(z, kernel, rows):
    z, kernel = z[:, rows, :], kernel[:, rows, :]
    full = kernel.copy()
    central = kernel.copy(); central[:, :, :32] = 0.; central[:, :, 33:] = 0.
    neighbor = kernel.copy(); neighbor[:, :, 32] = 0.
    def score(weights):
        return np.sum(weights*z, axis=(1, 2)) / np.sqrt(np.sum(weights**2, axis=(1, 2)))
    return dict(full_template_unit_L2_score=score(full),
                central_template_unit_L2_score=score(central),
                masked_neighbor_unit_L2_score=score(neighbor),
                original_delta_score=np.sum(z[:, :, 32], axis=1)/math.sqrt(len(rows)),
                central_standardized_mean=np.mean(z[:, :, 32], axis=1),
                neighbor_kernel_weighted_standardized_mean=np.sum(neighbor*z, axis=(1, 2))/np.sum(neighbor, axis=(1, 2)),
                central_template_mass=np.sum(central, axis=(1, 2)),
                neighbor_template_mass=np.sum(neighbor, axis=(1, 2)))


def main():
    started, cpu_started = time.monotonic(), time.process_time()
    scope_path = ROOT / 'SCOPE.json'
    scope_bytes = scope_path.read_bytes(); scope = json.loads(scope_bytes)
    assert scope['study_id'] == 'SETI_DRIFT_SMEARING_20261016'
    resource.setrlimit(resource.RLIMIT_CPU, (300, 300))
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    signal.alarm(600)
    outputs = ROOT/'results'; outputs.mkdir(exist_ok=False)
    spectra_dir = outputs/'spectra'; spectra_dir.mkdir()
    source = Path(scope['source_archive']['path'])
    source_bytes = source.read_bytes()
    assert len(source_bytes) == scope['source_archive']['bytes']
    assert digest(source_bytes) == scope['source_archive']['sha256']
    zfile = zipfile.ZipFile(io.BytesIO(source_bytes)); del source_bytes
    prefix = 'SETI_NATIVE_SPOR_2026-10-14/seti_work/'
    assert digest(zfile.read(scope['source_metadata']['member'])) == scope['source_metadata']['sha256']
    offsets = np.asarray(scope['offset_channels'], dtype=np.int64)
    relative = np.asarray(scope['spectral_relative_bins'], dtype=np.int64)
    profiles = []; input_pins = []; maximum_score_error = 0.
    for pi, profile in enumerate(scope['profiles']):
        inputs = {}
        for name in ('raw', 'normalization'):
            declaration = profile[name]
            raw_bytes = zfile.read(prefix + declaration['path'])
            assert len(raw_bytes) == declaration['bytes'] and digest(raw_bytes) == declaration['sha256']
            input_pins.append(dict(profile_id=profile['profile_id'],field=name,**declaration))
            inputs[name] = raw_bytes
        with np.load(io.BytesIO(inputs['raw']), allow_pickle=False) as archived:
            raw = archived['raw_power']; channel0 = int(archived['source_channel0'])
            assert raw.shape == (16,12096) and raw.dtype == np.dtype('<f4')
            assert np.isfinite(raw).all() and (raw>0).all()
            assert channel0 == profile['source_channel_interval_half_open'][0]
            assert np.array_equal(archived['absolute_time_rows'], np.arange(16))
            assert np.array_equal(archived['normalization_source_channels'], np.arange(channel0+4000,channel0+8096))
        normal = json.loads(inputs['normalization'])
        normal = {name:np.asarray(normal[name],dtype=np.float64) for name in NORM_FIELDS}
        assert all(x.shape == (16,) and np.isfinite(x).all() for x in normal.values())
        assert (normal['row_residual_MAD_scale']>0).all() and (normal['row_power_median']>0).all()
        times = np.asarray(profile['times_from_primary_reference_s'],dtype=np.float64)
        base = profile['source_reference_channel'] + profile['drift_hz_s']*times/profile['df_hz']
        continuous = base[None,:] + offsets[:,None]
        rounded = np.rint(continuous).astype(np.int64)
        channels = rounded[:,:,None] + relative[None,None,:]
        local = channels-channel0
        assert local.min() >= 250 and local.max()+250 < 12096
        raw_spectrum = raw[np.arange(16)[None,:,None],local]
        baseline = np.empty(local.shape,dtype=np.float64)
        for row in range(16):
            ratio = raw[row].astype(np.float64)/normal['row_power_median'][row]
            windows = np.lib.stride_tricks.sliding_window_view(ratio,501)
            baseline[:,row,:] = np.median(windows[local[:,row,:]-250],axis=-1)
        standardized = (raw_spectrum.astype(np.float64)/normal['row_power_median'][None,:,None]
                        -baseline-normal['row_winsorized_residual_location'][None,:,None])/normal['row_residual_MAD_scale'][None,:,None]
        sweep = abs(profile['drift_hz_s'])*profile['tsamp_s']/abs(profile['df_hz'])
        x = (rounded-continuous)[:,:,None] + relative[None,None,:]
        kernel = uniform_convolution_cdf(x+.5,1.,sweep)-uniform_convolution_cdf(x-.5,1.,sweep)
        assert kernel.min() >= -1e-12
        kernel = np.maximum(kernel,0.)
        assert np.max(np.abs(kernel.sum(axis=-1)-1.)) < 1e-12
        assert np.count_nonzero(kernel[:,:,:2]) == np.count_nonzero(kernel[:,:,-2:]) == 0
        four = statistic(standardized,kernel,profile['original_four_rows'])
        sixteen = statistic(standardized,kernel,list(range(16)))
        score_error = abs(float(four['original_delta_score'][0])-profile['original_fixed4_score'])
        assert score_error < 1e-7
        maximum_score_error = max(maximum_score_error,score_error)
        spectrum_path = spectra_dir/f'P{pi:02d}.npz'
        mask = np.ones_like(kernel,dtype=bool);mask[:,:,32] = False
        with spectrum_path.open('xb') as stream:
            np.savez_compressed(stream,raw_spectrum=raw_spectrum,local_median501_ratio=baseline,
                standardized_spectrum=standardized,kernel_channel_mass=kernel,
                masked_neighbor_kernel=kernel*mask,
                raw_crop_sha256=np.asarray(profile['raw']['sha256']),
                absolute_channels=channels,continuous_centers=continuous,rounded_centers=rounded,
                source_row_indices=np.arange(16,dtype=np.int64),original_four_rows=np.asarray(profile['original_four_rows']),
                offset_channels=offsets,relative_spectral_bins=relative,
                row_power_median=normal['row_power_median'],row_residual_MAD_scale=normal['row_residual_MAD_scale'],
                row_winsorized_residual_location=normal['row_winsorized_residual_location'],
                per_row_full_weighted_term=np.sum(kernel*standardized,axis=-1),
                per_row_neighbor_weighted_term=np.sum(kernel*mask*standardized,axis=-1),
                per_row_central_standardized=standardized[:,:,32])
        offset_records = []
        for oi, off in enumerate(offsets):
            offset_records.append(dict(offset_channels=int(off),original4={k:float(v[oi]) for k,v in four.items()},
                                       full16={k:float(v[oi]) for k,v in sixteen.items()}))
        profiles.append(dict(profile_id=profile['profile_id'],source_profile_id=profile['source_profile_id'],
            origin_scan_id=profile['origin_scan_id'],origin_rank=profile['origin_rank'],
            context_scan_id=profile['context_scan_id'],original_acquisition_role=profile['original_acquisition_role'],
            sweep_native_channels=sweep,original_four_rows=profile['original_four_rows'],
            maximum_original_delta_score_error=score_error,
            spectra=dict(path=str(spectrum_path.relative_to(ROOT)),bytes=spectrum_path.stat().st_size,sha256=digest(spectrum_path.read_bytes())),
            offset_results=offset_records))
        print(json.dumps(dict(completed_profile=pi+1,total=54,source_profile=profile['source_profile_id'])),flush=True)
    own = [p for p in profiles if p['origin_scan_id'] == p['context_scan_id']]
    assert len(own) == 9 and len(profiles) == 54
    summary=[]
    for p in own:
        target=p['offset_results'][0]['original4']; controls=[q['original4']['masked_neighbor_unit_L2_score'] for q in p['offset_results'][1:]]
        summary.append(dict(track=f"{p['origin_scan_id']}_rank{p['origin_rank']}",sweep_native_channels=p['sweep_native_channels'],
            original_delta_score=target['original_delta_score'],masked_neighbor_unit_L2_score=target['masked_neighbor_unit_L2_score'],
            full_template_unit_L2_score=target['full_template_unit_L2_score'],
            central_standardized_mean=target['central_standardized_mean'],neighbor_kernel_weighted_standardized_mean=target['neighbor_kernel_weighted_standardized_mean'],
            shifted_control_neighbor_min=min(controls),shifted_control_neighbor_max=max(controls),
            neighboring_template_mass_fraction=target['neighbor_template_mass']/4.,
            neighboring_control_values=controls))
    result=dict(schema='SETI_DESCRIPTIVE_DRIFT_SMEARING_RESULTS_V1',study_id=scope['study_id'],
        status='COMPLETE_PRIMARY_PENDING_INDEPENDENT_QA',scope_sha256=digest(scope_bytes),code_sha256=digest(Path(__file__).read_bytes()),
        source_archive_sha256=scope['source_archive']['sha256'],counts=scope['counts'],
        maximum_original_delta_score_error=maximum_score_error,own_ON_summary=summary,profiles=profiles,
        original_claims_and_closed_studies_unchanged=True,qualified_SETI_detection=False,
        calibrated_SNR_or_FAP=False,postselected_single_visit=True,assumed_ideal_sustained_line_response=True,
        caveats=scope['interpretation'])
    write_json(outputs/'RESULTS.json',result)
    with (outputs/'OWN_ON.csv').open('x',newline='') as stream:
        scalar_rows=[{k:v for k,v in r.items() if not isinstance(v,list)} for r in summary]
        writer=csv.DictWriter(stream,fieldnames=list(scalar_rows[0]));writer.writeheader();writer.writerows(scalar_rows)
    usage=resource.getrusage(resource.RUSAGE_SELF)
    receipt=dict(status=result['status'],wall_s=time.monotonic()-started,CPU_s=time.process_time()-cpu_started,
        maximum_RSS_bytes=usage.ru_maxrss*1024,scope_sha256=digest(scope_bytes),code_sha256=result['code_sha256'],
        inputs=input_pins,output_bytes=sum(p.stat().st_size for p in outputs.rglob('*') if p.is_file()),
        numpy_version=np.__version__,new_telescope_requests=0,cost_DKK=0)
    write_json(outputs/'EXECUTION_RECEIPT.json',receipt)
    print(json.dumps(dict(status=result['status'],own_ON_summary=summary,resources={k:receipt[k] for k in ('CPU_s','wall_s','maximum_RSS_bytes')})),flush=True)


if __name__ == '__main__':
    main()
