#!/usr/bin/env python3
"""Render retained LS4M control measurements; no raw-data access."""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from ls4m_control_morphology import ROOT, OUT, load
from ls4m_result_summary import main as verify_summary


def number_range(values, digits=3):
    return '—' if values is None else f'{values[0]:.{digits}f}–{values[1]:.{digits}f}'


def main():
    verify_summary()
    result=load('results_ls4m_control_morphology/morphology.json.gz')
    summary=load('results_ls4m_control_morphology/summary.json')
    selected=sorted((r for r in result['records'] if r['uses']),
                    key=lambda r:(r['frequency_index'],r['event_window_s'],r['band_indices']))
    widths=[s['requested_width_s'] for s in selected[0]['residual_metrics']['scales']]
    counts=[np.array([[len(s[region]) for s in r['residual_metrics']['scales']] for r in selected])
            for region in ('inside_pulses','reference_pulses')]
    plt.rcParams.update({'font.size':10,'svg.hashsalt':'ls4m-control-morphology-v1'})
    fig,axes=plt.subplots(1,2,figsize=(12,9),sharey=True,layout='constrained')
    maximum=max(1,max(int(x.max()) for x in counts))
    labels=[f"{[8.5,10.5][r['frequency_index']]} GHz | {r['band_indices'][0]}:{r['band_indices'][1]} | "
            f"{r['event_window_s'][0]:.2f}–{r['event_window_s'][1]:.2f} s" for r in selected]
    for ax,data,title in zip(axes,counts,('Inside the selected window','Outside it, in the guarded reference')):
        ax.imshow(data,aspect='auto',vmin=0,vmax=maximum,cmap='Blues')
        for y in range(len(selected)):
            for x in range(len(widths)):
                ax.text(x,y,str(data[y,x]),ha='center',va='center',color='white' if data[y,x]>maximum*.55 else '#172337')
        ax.set_xticks(range(len(widths)),[f'{w*1000:g}' for w in widths])
        ax.set_xlabel('Requested pulse width (ms)')
        ax.set_title(title,fontsize=11,pad=12)
    axes[0].set_yticks(range(len(selected)),labels)
    axes[0].set_ylabel('Selection: frequency group | native channel interval | time window')
    fig.suptitle('LS4M · B1 control pulse records in 17 distinct selected windows\n'
                 'Each cell counts clusters at one scale; windows and scales reuse one observation.',fontsize=13)
    fig.savefig(OUT/'control_windows.svg',metadata={'Date':None})
    fig.savefig(OUT/'control_windows.png',dpi=150)
    plt.close(fig)
    lines=['# LS4M: measured B1 control morphology','',
        '**Completed: one 9,435,087,189-byte B1 HTR file verified; 17 distinct selected windows and four fixed-window controls measured. All 256 selected-fragment and 48 fixed-window OFF count/veto comparisons reproduce LS4L. No sky candidate is promoted.**','',
        '**Main finding:** all nine selected 8.5 GHz windows are HTR-vetoed exclusively by reference-region control pulses; none contains an inside-window control pulse at any tested width. All eight selected 10.5 GHz windows have zero control pulses at these thresholds. This locates the measured HTR veto that blocked the lower-band digital tests. It does not resolve the separate Stage-1 OFF rejection.','',
        '![Control pulse records in the exact selected windows](results_ls4m_control_morphology/control_windows.svg)','',
        '## Selected-window results','',
        '| Frequency group | Distinct windows | OFF-vetoed windows | Windows with inside pulses | Windows with reference pulses | Reused fragment evaluations |',
        '|---|---:|---:|---:|---:|---:|']
    for row in summary['bands']:
        lines.append(f"| {row['band_ghz']} GHz | {row['unique_selected_windows']} | {row['off_veto_windows']} | {row['windows_with_inside_pulses']} | {row['windows_with_reference_pulses']} | {row['reused_fragment_evaluations']} |")
    lines += ['', 'The 256 uses are the 64 LS4L selected fragments crossed with four HTR digital amplitudes. The measured OFF scan is unchanged across those uses. Seventeen distinct band/window selections avoid counting the same numerical extraction repeatedly, but these selections are still correlated measurements of one observation. The four full-truth-band controls are reported separately below.','',
        '## Selected-window pulse measurements by scale','',
        'Counts below sum cluster records over distinct selected windows. A feature can recur at several scales and in several overlapping selections; the sums are not counts of independent physical pulses. Largest-channel fractions describe positive excess above the full guarded per-channel reference mean, which differs from the detector’s local residual baseline.','',
        '| Group | Width (ms) | Inside records | Reference records | Peak-score range | Largest-channel fraction range | Effective positive channels range |',
        '|---|---:|---:|---:|---|---|---|']
    for row in summary['scale_rows']:
        if row['category']!='selected':continue
        lines.append(f"| {row['band_ghz']} GHz | {row['width_s']*1000:g} | {row['inside_pulse_records']} | {row['reference_pulse_records']} | {number_range(row['peak_score_range'],2)} | {number_range(row['largest_channel_fraction_range'])} | {number_range(row['effective_positive_channels_range'],2)} |")
    lines += ['', '## Separately labelled fixed-window controls','',
        '| Group | Width (ms) | Distinct windows | Inside records | Reference records |',
        '|---|---:|---:|---:|---:|']
    for row in summary['scale_rows']:
        if row['category']!='fixed':continue
        lines.append(f"| {row['band_ghz']} GHz | {row['width_s']*1000:g} | {row['unique_windows']} | {row['inside_pulse_records']} | {row['reference_pulse_records']} |")
    lines += ['', '## Interpretation and boundaries','',
        'Across the nine lower-band selections, the 54 pulse-cluster records are dominated by structure around 113.6 s into B1, outside both selected time placements. Additional 1 ms records occur around 242.04 s and 273.55 s. The structure around 113.6 s is represented in all four selected lower-band frequency intervals. The equal-window 30 ms comparisons include six matched pulse records between bands sharing no native channels; these repeated comparisons are not six independent events.','',
        'In the 11-channel selected bands, the largest-channel positive-excess fraction ranges from approximately 0.175 to 0.541, with effective positive-channel counts from 2.92 to 6.20. Thus the retained peak descriptors distribute excess across several channels. No extracted channel records byte values 0 or 255. Neither observation establishes the physical origin of the feature or excludes other instrumental effects.','',
        'The unchanged HTR rule vetoes a window if any selected-width pulse appears anywhere in its OFF inside or guarded reference regions. A reference-region veto does not assert a pulse at the injected ON pulse times. B1 and A1 are separate pointings at different times; LS4M does not test simultaneous ON/OFF emission.','',
        'The retained ledger gives every peak time, score, cluster span and positive channel-excess vector. Cross-band comparisons use identical time windows and equal scales, with shared native channels explicitly labelled. Byte endpoint occupancy is descriptive and does not prove hardware saturation. These measurements cannot by themselves establish interference or celestial origin.','',
        'Original Stage-1 vetoes and both HTR veto definitions remain unchanged. LS4M does not revise LS4F, LS4I, LS4J or LS4L outcomes, fit a diffraction model, calibrate physical sensitivity or false-alarm probability, or promote a sky candidate. Reserved A3/C1/D1 remain unopened.','',
        'The next method-development question is whether reference-only OFF activity should receive a separately calibrated diagnostic category. Any proposed acceptance change needs a new frozen plan and interference/false-admission controls. LS4M itself supplies morphology and exact veto localization, not that calibration.','',
        '## Reproducibility and execution','',
        'The plan, implementation, inputs and 60 passing relevant tests were frozen locally at `74959d3` and published at `669c9c1441b1be275353281108c2eb67543a0b4f` before the B1 spectral read. Only B1 was downloaded; its full checksum and header were verified. A derived checkpoint was saved after each window before final validation. The raw file was deleted; no scan arrays, native submatrices or collapsed time series are published.','',
        f"Verified source bytes: {summary['source_bytes_verified']:,}. Charged download budget: {summary['charged_download_bytes']:,} of 18,870,174,378 bytes. Runtime: Python {result['python_version']}, NumPy {result['numpy_version']}.",'',
        f"Result identity: `{summary['result_sha256']}`.",'',
        '```bash','sha256sum -c LS4M_FREEZE.sha256','sha256sum -c RESULTS_MANIFEST_LS4M.sha256',
        'PYTHONPATH=src:scripts python scripts/ls4m_result_summary.py',
        'PYTHONPATH=src:scripts python scripts/ls4m_write_report.py','```','',
        'The verification and report commands use only retained derived evidence. The spectral runner refuses to overwrite an existing output directory.','']
    (ROOT/'LS4M_CONTROL_MORPHOLOGY_RESULT.md').write_text('\n'.join(lines))


if __name__=='__main__':main()
