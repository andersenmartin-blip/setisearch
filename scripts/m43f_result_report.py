#!/usr/bin/env python3
"""Verify and summarize the sealed M43F source/mapping transfer preflight."""
import csv
import hashlib
import json
import subprocess
import sys
import numpy as np
from m43f_source_cache_preflight import ROOT,OUT,build_context,endpoint_coverage,duplicate_witness,resource_estimate
from m43e_economical_bank import read_sealed
from m43b_active_support import seal
from seti_repeater import search_v0p6 as core
from seti_repeater import source_v0p6 as source


def main():
    path=OUT/'preflight.json'
    original_bytes=path.read_bytes()
    # The preflight is deterministic: re-run the frozen executable, then require
    # byte identity rather than silently replacing a mismatched prior result.
    subprocess.run([sys.executable,str(ROOT/'scripts/m43f_source_cache_preflight.py')],check=True,stdout=subprocess.DEVNULL)
    if path.read_bytes()!=original_bytes:raise RuntimeError('fresh preflight replay differs')
    result=read_sealed(path)
    cfgpath,cfg,confirmed,metadata,basis,bank,table,legacy=build_context()
    assert result['config_sha256']==hashlib.sha256(cfgpath.read_bytes()).hexdigest()
    assert result['m43e_confirmation_sha256']==confirmed['result_sha256']
    assert result['bank_sha256']==core.template_bank_sha256(bank)
    assert result['factor_table_sha256']==table.factor_table_sha256
    assert len(result['rows'])==30 and len(result['windows'])==5
    windows={w['window_id']:w for w in result['windows']}
    scans={s['label']:s for s in metadata['scans']}
    collisions=[]
    for row in result['rows']:
        assert row['row_sha256']==seal({k:v for k,v in row.items() if k!='row_sha256'})
        header=scans[row['scan_label']]['expected_header']
        matrix=core.factor_table_for_scan(table,basis,row['scan_label'])
        grid=core.make_m37_proxy_carrier_grid(row['window_id'])
        interval=row['old_extraction_interval']
        g=core.native_geometry_from_extraction(fch1_mhz=header['fch1_mhz'],foff_mhz=header['foff_mhz'],channel_start=interval[0],channel_stop=interval[1])
        w=row['minimum_factor_mapping'];first=w['first_duplicate']
        assert w==duplicate_witness(g,matrix,grid)
        assert w['factor']==matrix[w['template_index'],w['integration_index']]
        for width in core.M37_SPECTRAL_WIDTHS:
            assert row['width_coverage'][str(width)]==endpoint_coverage(g,matrix,grid,width)
        proposed=windows[row['window_id']]['proposed_interval']
        ng=core.native_geometry_from_extraction(fch1_mhz=header['fch1_mhz'],foff_mhz=header['foff_mhz'],channel_start=proposed[0],channel_stop=proposed[1])
        assert endpoint_coverage(ng,matrix,grid,129)==row['proposed_width129_coverage']
        if first is not None:
            q=np.array(first['proxy_carriers_hz'])
            np.testing.assert_array_equal(grid.support_hz[first['support_indices']],q)
            old_indices=core.nearest_native_indices(g,q*w['factor'])
            np.testing.assert_array_equal(old_indices,first['mapped_native_indices'])
            assert old_indices[0]==old_indices[1]
            new_indices=core.nearest_native_indices(ng,q*w['factor'])
            valid=bool(np.all((new_indices>=64)&(new_indices<ng.channel_count-64)))
            repeated=bool(new_indices[0]==new_indices[1])
            collisions.append({'window_id':row['window_id'],'scan_label':row['scan_label'],
                'template_index':w['template_index'],'integration_index':w['integration_index'],
                'factor':w['factor'],'proxy_carriers_hz':first['proxy_carriers_hz'],
                'old_native_indices':first['mapped_native_indices'],'proposed_native_indices':list(map(int,new_indices)),
                'repeated_inside_proposed_filter_coverage':valid and repeated})
    assert result['all_30_baseline_geometries_exact']
    assert result['distinct_factor_rows_below_one']==int(np.count_nonzero(table.factors<1))
    assert result['distinct_factor_rows_ge_two']==int(np.count_nonzero(table.factors>=2))
    for w in result['windows']:
        n=w['proposed_interval'][1]-w['proposed_interval'][0]
        assert w['resource_estimate_per_scan']==resource_estimate(n,16)
    audit={'result_sha256':result['result_sha256'],'byte_identical_replay':True,'scan_window_rows_verified':30,
           'bank_scan_width_checks_verified':240,'duplicate_mappings_recomputed':len(collisions),
           'same_pairs_repeat_inside_proposed_source':sum(c['repeated_inside_proposed_filter_coverage'] for c in collisions),
           'collision_rechecks':collisions}
    (OUT/'verification.json').write_bytes(core.canonical_json_bytes(audit))
    with (OUT/'scan_summary.csv').open('w') as f:
        writer=csv.writer(f,lineterminator='\n')
        writer.writerow(['window','scan','uncovered_templates_width129','lower_headroom_channels','upper_headroom_channels','factor_min','factor_max','factor_rows_below_legacy_range','duplicate_pairs_in_minimum_factor_row','proposed_minimum_filter_margin','cache_payload_bytes_per_width'])
        for row in result['rows']:
            c=row['width_coverage']['129'];p=row['proposed_width129_coverage']
            writer.writerow([row['window_id'],row['scan_label'],c['uncovered_templates'],c['lower_headroom_channels'],c['upper_headroom_channels'],row['factor_min'],row['factor_max'],row['legacy_factor_range_violating_rows'],row['minimum_factor_mapping']['duplicate_pairs'],min(p['lower_headroom_channels'],p['upper_headroom_channels']),row['estimated_cache_payload_bytes_per_width']])
    with (OUT/'extraction_requirements.csv').open('w') as f:
        writer=csv.writer(f,lineterminator='\n')
        writer.writerow(['window','old_start','old_stop_exclusive','proposed_start','proposed_stop_exclusive','native_channels','additional_channels','raw_bytes_per_scan','product_array_bytes_per_scan','all_six_scans_eight_width_cache_payload_bytes','normalization_block_offset'])
        for w in result['windows']:
            e=w['resource_estimate_per_scan']
            writer.writerow([w['window_id'],*w['old_interval'],*w['proposed_interval'],e['native_channels'],w['channels_added'],e['raw_bytes'],e['raw_normalized_frequency_bytes'],w['estimated_all_six_scans_cache_payload_bytes'],w['normalization_block_offset_mod4096']])
    example=next(r for r in result['rows'] if r['window_id']=='m37_1412p5' and r['scan_label']=='epoch1_on')
    collision=next(c for c in collisions if c['window_id']=='m37_1412p5' and c['scan_label']=='epoch1_on')
    e=example['width_coverage']['129']
    lines=['# M43F: native coverage and channel-mapping transfer result','',
        '**Preflight complete: the fixed M43E bank is incompatible with the existing M37 source/cache contract.**','',
        'The M43E 1,701-template bank retains its passed geometric result. M43F identifies the concrete engineering changes required to score that bank on telescope data. No production detector, source contract or threshold was changed.','',
        '## Gate results','',
        '| Check | Result |','|---|---|',
        '| Original 93-template extraction headrooms | All 30 scan/window geometries reproduce exactly |',
        '| Current extraction covers the 1,701-template bank with width 129 | 0/30 scan/window pairs |',
        '| Current cache factor precondition holds for entire bank | 0/30 scan/window pairs |',
        f"| Unique template/integration factors below 1 | {result['distinct_factor_rows_below_one']:,} / {table.factors.size:,} |",
        f"| Literal duplicate-channel witnesses | {len(collisions)} / 30 selected minimum-factor mappings |",
        '| Proposed wider intervals cover the fixed bank | 30/30, including the 129-channel filter and fixed reserve |','',
        'The same factor table is used across frequency windows, so the 62,800 factor violations are counted once, not multiplied by five. The 30 collision examples are scan/window checks, not independent astronomical events. The unchanged original bank still passes its original extraction checks.','',
        '## Example at 1412.5 MHz','',
        f"In epoch1_on, {e['uncovered_templates']}/1,701 templates extend beyond the old extraction at one or more integrations/carriers for width 129. The worst required extensions are {-e['lower_headroom_channels']:,} channels below and {-e['upper_headroom_channels']:,} above the old filtered range. Even width 1 is not fully covered.",'',
        f"The selected minimum factor is {example['factor_min']:.16f}. Its full proxy-support mapping contains {example['minimum_factor_mapping']['duplicate_pairs']} adjacent pairs mapped to the same native channel. The first pair uses proxy carriers {collision['proxy_carriers_hz'][0]:.7f} and {collision['proxy_carriers_hz'][1]:.7f} Hz. Their indices in the old extraction are {collision['old_native_indices']}; the corresponding indices in the proposed wider extraction are {collision['proposed_native_indices']}.",'',
        f"The verifier checks every frozen collision pair in the proposed geometry as well: {audit['same_pairs_repeat_inside_proposed_source']}/30 remain duplicated while lying inside valid 129-channel filter coverage. Widening the extraction therefore does not by itself solve the mapping incompatibility. The old strict-injectivity requirement must be addressed explicitly before using a new adapter.",'',
        '## Exact extraction and resource requirements','',
        'Archive channel intervals below are descending-frequency, start-inclusive and stop-exclusive. They preserve the old interval and include a fixed two-channel rounding reserve beyond the widest filter. Their endpoints lie inside the frozen remote dataset dimensions. This is metadata verification, not a new remote-file availability check.','',
        '| Window | Proposed archive interval | Native channels | Increase | Raw MiB/scan | Raw+normalized+frequency MiB/scan |',
        '|---|---|---:|---:|---:|---:|']
    for w in result['windows']:
        x=w['resource_estimate_per_scan']
        lines.append(f"| {w['window_id']} | [{w['proposed_interval'][0]}, {w['proposed_interval'][1]}) | {x['native_channels']:,} | {w['relative_source_channel_count']-1:.2%} | {x['raw_bytes']/2**20:.2f} | {x['raw_normalized_frequency_bytes']/2**20:.2f} |")
    lines+=['',
        'All five proposed intervals exceed each of the current per-source limits: 916,947 native channels, 64 MiB raw, 8 MiB frequency coordinates and 140 MiB combined raw/normalized/frequency arrays. These are limits of the frozen software contract, not evidence that the machine lacks enough RAM. Any larger or streaming source factory needs its own verified memory accounting; no cap was raised here.','',
        'Estimated width-specific cache payloads total approximately 3.47–3.49 GB per window across six scans and eight widths. Disk payload totals are not simultaneous resident RAM requirements. The estimate excludes file headers, transport buffers, decompression, filter scratch, masks, operating-system caches and other live arrays. Cache-bank and source identities must be rebuilt; matching dimensions do not authorize reuse of old contents.','',
        'Every proposed extraction shifts the normalization origin by a nonzero amount modulo 4096. The original normalization is anchored to the extracted ascending channel zero, so changing the extraction changes block alignment and can change normalized values. Define the new normalization scope before reading/scoring the new products; never claim old normalized or threshold receipts still apply.','',
        '## Next transfer contract','',
        '1. Freeze a separately named source/normalization adapter for the proposed intervals, with verified payload ancestry and bounded streaming memory.','2. Specify and qualify native-channel gathering when neighboring proxy carriers repeat a raw channel. Preserve the full carrier lattice, native-filter order, OFF controls and explicit repeat correlations; do not silently deduplicate or drop carriers.','3. Give the fixed bank and every source/cache product new identities. Test local and exhaustive score agreement, then execute predetermined real-data anchors and renew null/threshold calibration.','',
        'The immediate next milestone is that transfer adapter and its synthetic qualification. The M43F gate blocks using the old adapter for the new bank; it does not reverse M43E or indicate a sky-signal failure. The existing authorization to continue analysis and publication remains in effect.','',
        '## Verification and limits','',
        'Public freeze `99dfaa5e7c6ce0956ed82eccf99d8473e2bbd17a`, tree `54bc19800e238c9c498a5e3be6d9bd6b7d25baee`, was verified before execution. All 33 M43-family tests pass. This report regenerates the frozen result byte-for-byte, checks all 240 scan/window/width inventories and directly recomputes the 30 full minimum-factor mappings and collision pairs. The endpoint method is checked against exhaustive toy lattices; positive factors make endpoint coverage bound every interior carrier. No broader repository test run is claimed.','',
        f"Result identity: `{result['result_sha256']}`. The source is M43E confirmation `{result['m43e_confirmation_sha256']}` and fixed bank `{result['bank_sha256']}`.",'',
        'No telescope requests, spectral reads, injection trials, cache payloads or scores were evaluated. Proposed geometries are not attested source products. No sensitivity, recovery rate, occurrence rate or technosignature claim follows. All M37/M41/LS results and M43E denominators remain unchanged.','',
        '```bash','PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43f_source_cache_preflight.py',
        'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43f_result_report.py',
        "PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_m43*.py' -q",'```','']
    (ROOT/'MILESTONE_43F_SOURCE_CACHE_PREFLIGHT_RESULT.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in audit.items() if k!='collision_rechecks'},indent=2))


if __name__=='__main__':main()
