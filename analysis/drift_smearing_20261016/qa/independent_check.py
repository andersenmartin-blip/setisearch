#!/usr/bin/env python3
"""Independent saved-raw reconstruction of the fixed descriptive study.

No production numerical function or production output array is used as an
input to this reconstruction.  Production output is opened only after each
profile has been calculated from the pinned raw archive and metadata.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import io
import json
import math
import resource
import time
import zipfile

import numpy as np

from cdf_integral import channel_masses, convolved_box_cdf, selftest


ROOT = Path(__file__).resolve().parent.parent
QA = Path(__file__).resolve().parent
SOURCE_PREFIX = 'SETI_NATIVE_SPOR_2026-10-14/seti_work/'
EXPECTED_SCOPE_HASH = '115273d98a97fbad32cf6f2969340a73dc517e96d56ad613684bc7c1828079d2'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pin(path):
    content = Path(path).read_bytes()
    return dict(path=str(path), bytes=len(content), sha256=digest(content))


def main():
    start, cpu_start = time.monotonic(), time.process_time()
    scope_bytes = (ROOT/'SCOPE.json').read_bytes()
    assert digest(scope_bytes) == EXPECTED_SCOPE_HASH, 'Scope differs from reviewed frozen scope'
    scope = json.loads(scope_bytes)
    result_bytes = (ROOT/'results/RESULTS.json').read_bytes()
    primary_result = json.loads(result_bytes)
    assert primary_result['scope_sha256'] == EXPECTED_SCOPE_HASH
    assert primary_result['code_sha256'] == digest((ROOT/'primary.py').read_bytes())
    archive_bytes = Path(scope['source_archive']['path']).read_bytes()
    assert len(archive_bytes) == scope['source_archive']['bytes']
    assert digest(archive_bytes) == scope['source_archive']['sha256']
    zfile = zipfile.ZipFile(io.BytesIO(archive_bytes))
    del archive_bytes
    meta_bytes = zfile.read(scope['source_metadata']['member'])
    assert len(meta_bytes) == scope['source_metadata']['bytes']
    assert digest(meta_bytes) == scope['source_metadata']['sha256']
    assert (ROOT/'SOURCE_METADATA.json').read_bytes() == meta_bytes
    metadata = json.loads(meta_bytes)
    old_profiles = {p['profile_id']: p for p in metadata['profiles']}
    old_crops = {p['crop_id']: p for p in metadata['normalization_crops']}
    assert len(old_profiles) == 54 and len(old_crops) == 54
    expected_profile_set = {(p['selected_track']['scan_id'],p['selected_track']['rank'],p['context_scan_id']) for p in metadata['profiles']}
    new_profile_set = {(p['origin_scan_id'],p['origin_rank'],p['context_scan_id']) for p in scope['profiles']}
    assert expected_profile_set == new_profile_set and len(new_profile_set) == 54
    assert len(metadata['selected_tracks']) == len(scope['tracks']) == 9
    assert len(primary_result['profiles']) == 54
    assert scope['offset_channels'] == [0, -1024, -768, -512, -256, 256, 512, 768, 1024]
    assert scope['spectral_relative_bins'] == list(range(-32,33))
    row_count = 0
    cell_count = 0
    scalar_comparisons = 0
    source_pins = []
    profile_receipts = []
    differences = {}
    max_unit_area_error = 0.0
    min_full_l2_squared = math.inf
    min_masked_l2_squared = math.inf
    max_original_score_error = 0.0
    max_phase_order_difference = 0.0
    independent_summaries = []
    primary_profiles = {p['profile_id']: p for p in primary_result['profiles']}

    def compare(name, actual, expected, *, atol=1e-10, exact=False):
        nonlocal scalar_comparisons
        left = np.asarray(actual)
        right = np.asarray(expected)
        assert left.shape == right.shape, (name, left.shape, right.shape)
        scalar_comparisons += int(left.size)
        if exact:
            assert np.array_equal(left,right), name
            differences[name] = max(differences.get(name,0.0),0.0)
        else:
            assert np.isfinite(left).all() and np.isfinite(right).all(), name
            delta = float(np.max(np.abs(left-right))) if left.size else 0.0
            differences[name] = max(differences.get(name,0.0),delta)
            assert delta <= atol, (name,delta,atol)

    def scores(z, kernel, rows):
        output=[]
        for oi in range(9):
            terms = z[oi,rows]
            weights = kernel[oi,rows]
            central_weights = np.zeros_like(weights)
            central_weights[:,32] = weights[:,32]
            remaining_weights = weights.copy();remaining_weights[:,32] = 0.0
            def unit_score(w):
                numerator = math.fsum((w*terms).flat)
                denominator2 = math.fsum((w*w).flat)
                assert denominator2 > 0
                return numerator/math.sqrt(denominator2)
            central_mass = math.fsum(central_weights.flat)
            remaining_mass = math.fsum(remaining_weights.flat)
            output.append(dict(
                full_template_unit_L2_score=unit_score(weights),
                central_template_unit_L2_score=unit_score(central_weights),
                masked_neighbor_unit_L2_score=unit_score(remaining_weights),
                original_delta_score=math.fsum(terms[:,32])/math.sqrt(len(rows)),
                central_standardized_mean=math.fsum(terms[:,32])/len(rows),
                neighbor_kernel_weighted_standardized_mean=math.fsum((remaining_weights*terms).flat)/remaining_mass,
                central_template_mass=central_mass,
                neighbor_template_mass=remaining_mass,
            ))
        return output

    for pi,p in enumerate(scope['profiles']):
        old = old_profiles[p['source_profile_id']]
        selected = old['selected_track']
        crop = old_crops[p['normalization_crop_id']]
        assert p['origin_scan_id'] == selected['scan_id']
        assert p['origin_rank'] == selected['rank']
        assert p['context_scan_id'] == old['context_scan_id']
        assert p['source_reference_channel'] == selected['source_reference_channel']
        assert p['drift_hz_s'] == selected['drift_hz_s']
        assert p['original_four_rows'] == selected['window_source_rows']
        assert p['times_from_primary_reference_s'] == old['times_from_primary_reference_s']
        assert p['df_hz'] == selected['source_header']['foff']*1e6
        assert p['tsamp_s'] == selected['source_header']['tsamp']
        assert p['source_channel_interval_half_open'] == crop['source_channel_interval_half_open']
        assert p['raw'] == crop['raw_crop']
        assert p['normalization'] == crop['normalization']
        input_data = {}
        for field in ('raw','normalization'):
            declaration = p[field]
            content = zfile.read(SOURCE_PREFIX+declaration['path'])
            assert len(content) == declaration['bytes'] and digest(content) == declaration['sha256']
            input_data[field] = content
            source_pins.append(dict(profile=p['source_profile_id'],field=field,**declaration))
        with np.load(io.BytesIO(input_data['raw']),allow_pickle=False) as data:
            raw = np.asarray(data['raw_power']).copy()
            crop_first = int(data['source_channel0'])
            assert raw.shape == (16,12096) and raw.dtype.str == '<f4'
            assert np.isfinite(raw).all() and (raw>0).all()
            assert crop_first == p['source_channel_interval_half_open'][0]
            assert np.array_equal(data['absolute_time_rows'],np.arange(16))
            assert np.array_equal(data['normalization_source_channels'],np.arange(crop_first+4000,crop_first+8096))
        n = json.loads(input_data['normalization'])
        norm_names=('row_power_median','row_residual_MAD_scale','row_winsorized_residual_location')
        normal={key:np.asarray(n[key],dtype=float) for key in norm_names}
        assert all(a.shape==(16,) and np.isfinite(a).all() for a in normal.values())
        levels, scales, locations = (normal[key] for key in norm_names)
        assert np.all(levels>0) and np.all(scales>0)
        raw_spectra=np.zeros((9,16,65),dtype='<f4')
        median=np.zeros((9,16,65),dtype=float)
        z=np.zeros((9,16,65),dtype=float)
        kernels=np.zeros((9,16,65),dtype=float)
        channels=np.zeros((9,16,65),dtype=np.int64)
        continuous=np.zeros((9,16),dtype=float)
        rounded=np.zeros((9,16),dtype=np.int64)
        # Build every value from saved raw, using scalar original-order geometry.
        sweep=abs(p['drift_hz_s'])*p['tsamp_s']/abs(p['df_hz'])
        for oi,offset in enumerate(scope['offset_channels']):
            for row,t in enumerate(p['times_from_primary_reference_s']):
                center=(p['source_reference_channel'] + p['drift_hz_s']*float(t)/p['df_hz']) + offset
                nearest=round(center)
                continuous[oi,row]=center;rounded[oi,row]=nearest
                stable_local=(p['source_reference_channel']-crop_first)+p['drift_hz_s']*float(t)/p['df_hz']+offset
                max_phase_order_difference=max(max_phase_order_difference,abs((center-crop_first)-stable_local))
                all_bins,all_weights=channel_masses(center-nearest,sweep)
                assert all_bins.min()>=-32 and all_bins.max()<=32
                assert abs(math.fsum(all_weights)-1.0)<1e-14
                for si,relative in enumerate(scope['spectral_relative_bins']):
                    channel=nearest+relative
                    index=channel-crop_first
                    assert index-250>=0 and index+251<=12096
                    raw_value=float(raw[row,index])
                    # Positive division preserves rank; the odd raw-window median
                    # is exactly the median order statistic divided by level.
                    median_raw=float(np.partition(raw[row,index-250:index+251],250)[250])
                    baseline=median_raw/levels[row]
                    standardized=(raw_value/levels[row]-baseline-locations[row])/scales[row]
                    x=float(relative+nearest-center)
                    mass=convolved_box_cdf(x+.5,sweep)-convolved_box_cdf(x-.5,sweep)
                    assert mass>=0
                    raw_spectra[oi,row,si]=raw_value
                    median[oi,row,si]=baseline
                    z[oi,row,si]=standardized
                    kernels[oi,row,si]=mass
                    channels[oi,row,si]=channel
                area=math.fsum(kernels[oi,row])
                max_unit_area_error=max(max_unit_area_error,abs(area-1.0))
                assert abs(area-1.0)<1e-14
                assert np.all(kernels[oi,row,:2]==0) and np.all(kernels[oi,row,-2:]==0)
                row_count+=1;cell_count+=65
        masked=kernels.copy();masked[:,:,32]=0
        full_l2=np.sum(kernels*kernels,axis=(1,2))
        masked_l2=np.sum(masked*masked,axis=(1,2))
        min_full_l2_squared=min(min_full_l2_squared,float(np.min(full_l2)))
        min_masked_l2_squared=min(min_masked_l2_squared,float(np.min(masked_l2)))
        assert np.all(masked[:,:,32]==0)
        assert np.array_equal(masked[:,:,:32],kernels[:,:,:32])
        assert np.array_equal(masked[:,:,33:],kernels[:,:,33:])
        four=scores(z,kernels,p['original_four_rows'])
        sixteen=scores(z,kernels,list(range(16)))
        original_score_error=abs(four[0]['original_delta_score']-p['original_fixed4_score'])
        max_original_score_error=max(max_original_score_error,original_score_error)
        assert original_score_error<1e-7
        production=primary_profiles[p['profile_id']]
        assert production['source_profile_id']==p['source_profile_id']
        saved_path=ROOT/production['spectra']['path']
        assert pin(saved_path)['bytes']==production['spectra']['bytes']
        assert pin(saved_path)['sha256']==production['spectra']['sha256']
        with np.load(saved_path,allow_pickle=False) as data:
            for name,independent,exact in (
                ('raw_spectrum',raw_spectra,True),
                ('local_median501_ratio',median,False),
                ('standardized_spectrum',z,False),
                ('kernel_channel_mass',kernels,False),
                ('masked_neighbor_kernel',masked,False),
                ('absolute_channels',channels,True),
                ('continuous_centers',continuous,True),
                ('rounded_centers',rounded,True),
                ('source_row_indices',np.arange(16),True),
                ('original_four_rows',p['original_four_rows'],True),
                ('offset_channels',scope['offset_channels'],True),
                ('relative_spectral_bins',scope['spectral_relative_bins'],True),
                ('per_row_full_weighted_term',np.sum(kernels*z,axis=-1),False),
                ('per_row_neighbor_weighted_term',np.sum(masked*z,axis=-1),False),
                ('per_row_central_standardized',z[:,:,32],False),
            ):
                compare(name,data[name],independent,exact=exact)
            for name in norm_names:
                compare(name,data[name],normal[name],exact=True)
            assert str(data['raw_crop_sha256'])==p['raw']['sha256']
            assert np.all(data['masked_neighbor_kernel'][:,:,32]==0)
        for oi,entry in enumerate(production['offset_results']):
            assert entry['offset_channels']==scope['offset_channels'][oi]
            for window,expected in (('original4',four[oi]),('full16',sixteen[oi])):
                assert set(entry[window])==set(expected)
                for statistic,value in expected.items():
                    compare(window+':'+statistic,entry[window][statistic],value)
        profile_receipts.append(dict(profile=p['source_profile_id'],source_verified=True,
            rows=144,spectral_cells=9360,original_score_error=original_score_error,
            spectra_pin=pin(saved_path)))
        if p['origin_scan_id']==p['context_scan_id']:
            independent_summaries.append(dict(track=f"{p['origin_scan_id']}_rank{p['origin_rank']}",
                original_delta_score=four[0]['original_delta_score'],
                masked_neighbor_unit_L2_score=four[0]['masked_neighbor_unit_L2_score'],
                full_template_unit_L2_score=four[0]['full_template_unit_L2_score'],
                neighboring_template_mass_fraction=four[0]['neighbor_template_mass']/4,
                shifted_controls=[entry['masked_neighbor_unit_L2_score'] for entry in four[1:]]))
        print(json.dumps(dict(independent_profile_complete=pi+1,total=54)),flush=True)
    assert row_count==7776 and cell_count==505440
    assert len(independent_summaries)==9
    assert len(source_pins)==108
    assert len(primary_result['own_ON_summary'])==9
    expected_by_track={s['track']:s for s in independent_summaries}
    for summary in primary_result['own_ON_summary']:
        expected=expected_by_track[summary['track']]
        for name in ('original_delta_score','masked_neighbor_unit_L2_score','full_template_unit_L2_score','neighboring_template_mass_fraction'):
            compare('own_summary:'+name,summary[name],expected[name])
        compare('own_summary:controls',summary['neighboring_control_values'],expected['shifted_controls'])
        compare('own_summary:control_min',summary['shifted_control_neighbor_min'],min(expected['shifted_controls']))
        compare('own_summary:control_max',summary['shifted_control_neighbor_max'],max(expected['shifted_controls']))
    receipt=dict(
        schema='SETI_DRIFT_SMEARING_INDEPENDENT_QA_V1',
        status='PASS_INDEPENDENT_RAW_RECONSTRUCTION',
        scope_sha256=EXPECTED_SCOPE_HASH,
        primary_code_sha256=primary_result['code_sha256'],
        primary_result_pin=pin(ROOT/'results/RESULTS.json'),
        independent_code_pins=[pin(Path(__file__)),pin(QA/'cdf_integral.py')],
        primary_numeric_functions_imported=False,
        production_arrays_used_to_generate_independent_values=False,
        independent_kernel_method='Analytical three-piece trapezoid CDF, distinct from primary positive-part-square expression',
        independent_local_median_method='501-element raw order-statistic via partition, divided by original saved positive row level',
        independent_sum_method='Python math.fsum over independently reconstructed values',
        counts=dict(tracks=9,context_profiles=54,offset_contexts=486,row_spectra=row_count,spectral_cells=cell_count,
            raw_and_normalization_pins_verified=len(source_pins),scalar_comparisons=scalar_comparisons),
        maximum_absolute_differences=differences,
        maximum_unit_area_error=max_unit_area_error,
        maximum_original_delta_score_error=max_original_score_error,
        minimum_full16_full_L2_norm_squared=min_full_l2_squared,
        minimum_full16_masked_L2_norm_squared=min_masked_l2_squared,
        maximum_absolute_center_binary64_vs_local_order_difference_channels=max_phase_order_difference,
        central_selected_bin_direct_weight_zero_in_every_row=True,
        original_and_remaining_mass_add_to_one=True,
        raw_crops_and_metadata_hashes_verified=True,
        original54_profile_geometry_and_pins_match_source_metadata=True,
        source_archive_pin=scope['source_archive'],
        source_metadata_pin=scope['source_metadata'],source_input_pins=source_pins,
        generic_integral_checks=selftest(),profiles=profile_receipts,
        independent_own_ON_summary=independent_summaries,
        qualified_SETI_detection=False,
        calibrated_SNR_or_FAP=False,
        new_observations=False,
        new_fit_or_search=False,
        scientific_review='SCIENTIFIC_REVIEW.md',
        resources=dict(CPU_s=time.process_time()-cpu_start,wall_s=time.monotonic()-start,
            max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),
    )
    with (QA/'QA_RECEIPT.json').open('x') as f:
        json.dump(receipt,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=receipt['status'],counts=receipt['counts'],
        maximum_absolute_differences=differences,resources=receipt['resources'])),flush=True)


if __name__=='__main__':
    main()
