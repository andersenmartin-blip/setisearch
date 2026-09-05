#!/usr/bin/env python3
"""Verify sealed LS6A diagnostics and render a complete four-scan comparison."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ls6_repaired_screen import seal
from ls4b_filterbank_screen import sha256_file


def main():
    out = Path('results_ls6a_scan_end')
    r = json.loads((out / 'diagnostic.json').read_text())
    assert r['result_sha256'] == seal({k:v for k,v in r.items() if k != 'result_sha256'})
    assert r['config_sha256'] == sha256_file(Path('config/ls6a_scan_end.json'))
    cfg = json.loads(Path('config/ls6a_scan_end.json').read_text())
    for path, digest in cfg['pinned_sha256'].items():
        assert sha256_file(Path(path)) == digest
    for s in r['scans']:
        assert s == json.loads((out / (s['label']+'.json')).read_text())
        assert s['checkpoint_sha256'] == seal({k:v for k,v in s.items() if k != 'checkpoint_sha256'})
        assert s['original_screen_exactly_reproduced']
        d = s['diagnostic']
        coarse = np.array(d['coarse_normalized'], dtype=float)
        centered = coarse - np.nanmean(coarse, axis=0)
        with (out / (s['label']+'_centered.csv')).open('w') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(['sample_midpoint_s']+[f'bin_{i:02d}' for i in range(coarse.shape[1])])
            writer.writerows([[t]+row.tolist() for t,row in zip(d['sample_midpoint_s'],centered)])

    plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none', 'svg.hashsalt': 'ls6a'})
    fig, axes = plt.subplots(4, 3, figsize=(14, 11), sharex=True, sharey='col', layout='constrained')
    limit = max(np.nanmax(np.abs(np.array(s['diagnostic']['coarse_normalized'], dtype=float))) for s in r['scans'])
    for row, s in enumerate(r['scans']):
        d = s['diagnostic']; t = np.array(d['sample_midpoint_s']); dt = t[1]-t[0]
        axes[row,0].plot(t, 100*(np.array(d['raw_relative_power_trace'])-1), color='#205b87')
        axes[row,0].axhline(0, color='gray', lw=.6)
        axes[row,0].set_ylabel(s['label']+' ('+s['role']+')\nRelative power (%)')
        axes[row,1].plot(t, d['frequency_median_trace'], color='#205b87', label='Frequency median')
        fit = d['linear_fit']
        axes[row,1].plot(t, fit['intercept']+fit['coefficient']*t, '--', color='#bb6512', label='Linear fit')
        coarse = np.array(d['coarse_normalized'], dtype=float)
        im = axes[row,2].imshow(coarse.T, aspect='auto', origin='lower',
            extent=[0,len(t)*dt,0,64], vmin=-limit, vmax=limit, cmap='RdBu_r', interpolation='nearest')
        axes[row,2].set_ylabel('Frequency bin (low to high)')
        for ax in axes[row]:
            ax.axvline(41*dt, color='#555555', ls=':', lw=.8)
            ax.axvline(49*dt, color='#555555', ls=':', lw=.8)
            ax.set_xlim(0,len(t)*dt)
        for ax in axes[row,:2]:
            ax.grid(alpha=.18)
    axes[0,0].set_title('Unclipped native-power ratio median')
    axes[0,1].set_title('Median of 64 normalized bins')
    axes[0,1].legend(loc='upper left', fontsize=8)
    axes[0,2].set_title('Normalized coarse spectrum')
    for ax in axes[-1]: ax.set_xlabel('Seconds from scan start')
    fig.colorbar(im, ax=axes[:,2], label='Native robust normalized power', shrink=.85)
    fig.suptitle('LS6A | TRAPPIST-1 archive-labelled 9.92 GHz scans\nRetrospective diagnostic; dotted lines mark fixed final 15 and 7 samples', fontsize=14)
    fig.savefig(out / 'scan_end_comparison.svg', metadata={'Date': None})
    svg = out / 'scan_end_comparison.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    fig.savefig('/tmp/ls6a_scan_end_preview.png', dpi=110)
    plt.close(fig)

    lines = ['# LS6A TRAPPIST-1 scan-end diagnostic', '',
        '**Completed: strong shared frequency variation; instrumental origin remains unproven.**', '',
        'All four original files (58,721,848 bytes) match their LS6 SHA-256 digests. Replaying the original screen reproduces every scan record, score and retained window exactly. The 47 primary ON survivors remain unchanged. This is a retrospective diagnostic on previously exposed data, not independent confirmation.', '',
        'Both ON scans have a positive final-window contrast in every one of the 64 frequency bins, for both fixed tail lengths. Shared time variation is also strong in the OFF scans. Subtracting one across-bin median trace removes 87.6–97.2% of the time-centered squared energy across the four scans. This supports the common-mode/baseline concern; zero retained OFF events does not imply a stable OFF baseline.', '',
        '| Scan | Role | Energy removed by common trace | Positive bins, final 7 | Positive bins, final 15 |',
        '|---|---|---:|---:|---:|']
    for s in r['scans']:
        d=s['diagnostic']; a,b=d['tail_comparisons']
        lines.append(f"| {s['label']} | {s['role']} | {100*d['unit_common_trace_energy_reduction']:.2f}% | {a['positive_bin_count']}/64 | {b['positive_bin_count']}/64 |")
    lines += ['', 'The energy fraction uses unit subtraction of the median of time-mean-centered bin traces. It is descriptive, not calibrated variance explained by an instrumental model, and has no detection significance.', '',
        '## Time shape', '',
        '| Scan | Linear R² | Final-7 step R² | Final-15 step R² | Raw relative-power range (%) |',
        '|---|---:|---:|---:|---:|']
    for s in r['scans']:
        d=s['diagnostic']; a,b=d['tail_comparisons']; raw=100*(np.array(d['raw_relative_power_trace'])-1)
        lines.append(f"| {s['label']} | {d['linear_fit']['r_squared']:.3f} | {a['step_fit']['r_squared']:.3f} | {b['step_fit']['r_squared']:.3f} | {raw.min():+.3f} to {raw.max():+.3f} |")
    lines += ['', 'The fixed final-15 step fits A1 better than a straight line (R² 0.855 versus 0.764); the final-7 step fits A2 better than a straight line (0.542 versus 0.134). A simple linear-drift explanation alone is therefore insufficient. These comparisons use two-parameter descriptive fits, with no breakpoint search or inferential model selection. Raw-power ranges refer to the frequency median of each native channel divided by its own temporal median, minus one; they are not calibrated flux changes.', '',
        '![Four-scan raw-power, common-trace and coarse-spectrum comparison](results_ls6a_scan_end/scan_end_comparison.svg)', '',
        'All panels use full scans and shared scales within each column. The heatmap uses all 64 bins, ascending in frequency over 9826.466–10013.963 MHz; it is native robust normalization before the detector’s second temporal normalization. Dotted lines mark final 15 and 7 samples (44.023 and 52.613 seconds).', '',
        '## Scientific disposition', '',
        'The 47 windows are consistent with two scan-ending broadband elevations that warrant baseline and observing-state checks. This diagnostic cannot distinguish instrumental gain, interference, pointing changes, or a true broadband sky variation. A pulse can also continue beyond the recorded boundary. No candidate is promoted, and no additional veto is imposed. Pointing uncertainty and missing conjunction qualification from LS6 remain. No HTR data, other subband, or independent epoch was opened.', '',
        'A useful next step is a separately frozen comparison of other archived medium-resolution X-band subbands at these same scan times, with frequency selection determined from metadata. That could test how far the shared behavior extends; it would still not provide an independent epoch or establish a celestial origin.', '',
        '## Verification and reproduction', '',
        'All 147 LS tests passed, including three synthetic diagnostic checks: shared linear drift, a localized step, and a negative step with an invalid frequency bin. The full repository test suite is not claimed. The report generator verifies configuration/code hashes, the sealed result, and every checkpoint before rendering.', '',
        'Public diagnostic freeze: `b446ae4435f90893fc06bdbcfb322f46f2402021`; tree `28b1d4f0afaa42ee81ddd1b20400db0055dee5e1`. The public branch ref was verified before rereading spectra.', '',
        f"Result identity: `{r['result_sha256']}`.", '',
        'Per-scan JSON checkpoints and the combined diagnostic retain the full 56×64 coarse matrices, signed contrasts, fits, raw-ratio traces, channel-validity counts and original file digests/URLs. Per-scan CSV files export all time-mean-centered coarse traces. Raw files were deleted after processing. The original LS6 files and report were not changed.', '',
        '```bash', "PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_ls*.py' -v",
        'PYTHONPATH=src:scripts python scripts/ls6a_scan_end.py',
        'PYTHONPATH=src:scripts python scripts/ls6a_result_report.py', '```', '']
    Path('LS6A_SCAN_END_RESULT.md').write_text('\n'.join(lines))
    print(json.dumps({'result_identity': r['result_sha256'], 'raw_excluded': {s['label']:s['diagnostic']['raw_ratio_excluded_channels'] for s in r['scans']}, 'raw_nonfinite': {s['label']:s['diagnostic']['raw_nonfinite_samples'] for s in r['scans']}}, indent=2))


if __name__ == '__main__': main()
