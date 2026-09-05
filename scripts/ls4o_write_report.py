#!/usr/bin/env python3
"""Render retained metadata, timing and pointing evidence."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime,timedelta,timezone
from ls4o_control_feasibility import ROOT,OUT
from ls4o_result_summary import verified


def main():
    r,receipts=verified();g=r['known_geometry'];scans=g['scans']
    plt.rcParams.update({'font.size':11,'svg.hashsalt':'ls4o-feasibility-v1'})
    fig,ax=plt.subplots(figsize=(12,5.7));fig.subplots_adjust(left=.22,right=.97,top=.76,bottom=.23)
    colors={'development':'#0e7490','unused_bridge':'#64748b','reserved_validation':'#b45309'}
    for i,s in enumerate(scans):
        ax.barh(i,s['duration_s']/60,left=s['start_relative_s']/60,height=.58,color=colors[s['partition']])
        ax.text((s['start_relative_s']+s['duration_s']/2)/60,i,f"{s['duration_s']:.1f} s",ha='center',va='center',color='white',fontsize=10)
    ax.set_yticks(range(6),[f"{s['label']} · {s['role']} · {s['source_name']}" for s in scans]);ax.invert_yaxis()
    ax.set_xlabel('Minutes since the start of A1 (same observing session)')
    ax.spines[['top','right']].set_visible(False);ax.xaxis.grid(True,alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('LS4O · available X-band controls are sequential, not simultaneous',x=.04,y=.96,ha='left',fontsize=17)
    fig.text(.04,.85,'Saved HTR header geometry; no reserved spectrum was opened.',fontsize=12)
    fig.text(.04,.09,'Blue: development A1/B1 · Gray: bridge A2 · Orange: reserved HTR validation',fontsize=11)
    fig.text(.04,.035,'All six medium products were previously searched. Separate files do not establish an independent epoch.',fontsize=10)
    fig.savefig(OUT/'cadence_geometry.svg',metadata={'Date':None});fig.savefig(OUT/'cadence_geometry.png',dpi=150);plt.close(fig)
    p=OUT/'cadence_geometry.svg';p.write_text('\n'.join(x.rstrip() for x in p.read_text().splitlines())+'\n')
    candidates=r['candidate_later_or_earlier_x_scan_groups']
    dates=sorted({(datetime(1858,11,17,tzinfo=timezone.utc)+timedelta(days=s['mjd'])).date().isoformat() for s in r['scan_groups']})
    verdict=(f"The scoped queries identify {len(candidates)} X-center scan groups at least 24 hours from the original X-band start. These are metadata leads requiring separate header and adjacency qualification."
             if candidates else "No X-center scan group at least 24 hours from the original X-band start was found in the returned metadata.")
    lines=['# LS4O: independent-control archive and pointing feasibility','',
        f"**Status: {r['status']}. {r['successful_queries']}/11 metadata queries succeeded; {r['unique_accepted_products']} distinct matching product URLs and {r['unique_scan_frequency_groups']} scan/frequency groups were retained. No new radio spectral values were read.**",'',verdict,'',
        f"The retained scan groups were observed on these UTC dates: {', '.join(dates)}.",'',
        '![Time geometry of the existing six-scan X-band sequence](results_ls4o_control_feasibility/cadence_geometry.svg)','',
        '## Expanded archive query','',
        'Ten frozen aliases from the LS3 configuration were each queried with only `target` and `limit=3000`. A control query repeated the earlier exact-LHS1140 GBT/cadence/primary-target restriction. The target-only requests omit those restrictions explicitly; undocumented API defaults and other archives are outside this study. Returned target names were checked against the normalized frozen alias set.','',
        '| Alias | Query type | Success | Returned rows | Record cap reached |',
        '|---|---|---|---:|---|']
    for p in receipts:lines.append(f"| {p['alias']} | {p['kind']} | {p['successful']} | {len(p.get('response',{}).get('data',[]))} | {p.get('record_limit_reached',False)} |")
    lines += ['',f"Target-only queries expose **{r['target_only_additional_product_urls']}** product URLs beyond the restricted query. Restricted URLs missing from those target-only responses: **{len(r['restricted_products_missing_from_target_queries'])}**. Nonmatching target records excluded: **{r['excluded_nonmatching_records']}**. Metadata conflicts: **{len(r['metadata_conflicts'])}**. Queries reaching the record limit: **{r['record_limit_reached_queries']}**.",'',
        f"Requests began at {receipts[0]['retrieved_utc']} and the final request began at {receipts[-1]['retrieved_utc']}. All response texts and their SHA256 hashes are retained, including failures. The observation dates below refer to the archive observations, not these retrieval timestamps.",'',
        '## Matching scan and product inventory','',
        'The frequency grouping rounds catalog centers to 100 MHz for inventory only. Center frequency alone does not establish signal-band coverage. An interval of at least 24 hours screens possible new epochs; it is not proof of statistical independence.','',
        '| Telescope | Target | Start MJD | Center grouping (GHz) | Products | Medium | HTR | >=24 h X-center lead |',
        '|---|---|---:|---:|---:|---|---|---|']
    for s in r['scan_groups']:
        lines.append(f"| {s['telescope']} | {s['target']} | {s['mjd']:.9f} | {s['frequency_group_anchor_mhz']/1000:g} | {len(s['products'])} | {s['has_medium_product']} | {s['has_htr_product']} | {s['x_center_metadata_candidate'] and s['separated_by_at_least_one_day']} |")
    lines += ['', '## Existing X-band timing and pointing','',
        'The retained LS4A HTR headers, matched to LS4H source names and start times, give the following original ON/OFF adjacencies. Angular distances use the recorded SIGPROC pointing coordinates on the sphere. They are not a beam-response measurement.','',
        '| ON | Adjacent OFF | Angular separation (degrees) | Gap between integrations (s) | Simultaneous integration overlap (s) |',
        '|---|---|---:|---:|---:|']
    for p in g['adjacent_pairs']:lines.append(f"| {p['on']} | {p['off']} | {p['angular_separation_deg']:.4f} | {p['gap_s']:.3f} | {p['overlap_s']:.3f} |")
    lines += ['',f"The three ON starts are {', '.join(f'{v:.3f}' for v in g['on_start_offsets_s'])} seconds relative to A1. There are **{g['simultaneous_on_off_pairs']}** simultaneous adjacent ON/OFF pairs. These same-session revisits can probe temporal behaviour, but source intermittency and changing interference prevent a simple ON/OFF detection pattern from proving origin.",'',
        '## Other known bands and the reserved split','',
        '| Band | HTR native center range (GHz) | Covers 8.5 GHz | Covers 10.5 GHz |',
        '|---|---|---|---|']
    for b in g['known_bands']:lines.append(f"| {b['band']} | {b['native_center_low_mhz']/1000:.3f}–{b['native_center_high_mhz']/1000:.3f} | {b['contains_8500_mhz']} | {b['contains_10500_mhz']} |")
    lines += ['', 'A3 with C1/D1 is reserved for HTR validation; A2 bridges the development and reserved control groups. All six medium products were already searched by LS4B. HTR reservation preserves the future method-development boundary and does not make the medium data unseen or the observations a new epoch.','',
        f"A3/C1/D1 HTR alone would require {g['reserved_htr_full_download_bytes']:,} full-file bytes; medium plus HTR would require {g['reserved_medium_plus_htr_full_download_bytes']:,}. Those files were not downloaded here.",'',
        '## Concrete next boundary','']
    if candidates:
        lines += ['Qualify every identified new-epoch X-center lead with a separately frozen header/cadence preflight. Confirm actual frequency support, target identity, ON/OFF adjacency, duplicate-recording status and resources before spectral access. A catalog lead is not an independent signal confirmation.','']
    elif r['status']=='scoped-metadata-feasibility-complete':
        lines += ['This scoped expansion supplies no new-epoch X-center lead. Opening the reserved A3/C1/D1 HTR set would therefore be a method-transport validation, not independent-epoch confirmation. A separately frozen validation protocol could assess the unchanged detector and labelled diagnostics, but cannot resolve ON-only interference merely by relaxing OFF vetoes.','',
            'For new discovery work, the next useful branch is an additional target or observing cadence selected from metadata with the existing acceptance rules. For a claim about LHS 1140 origin, seek an additional epoch or simultaneous spatial information from a separately qualified archive or observation. The current metadata do not supply a calibrated beam model or simultaneous control.','']
    else:
        lines += ['The scoped inventory is incomplete. Resolve the recorded metadata failures, caps or conflicts before drawing a completed inventory exclusion. No reserved spectrum should be used to compensate for missing metadata.','']
    lines += ['No new sky candidate, independent confirmation, physical sensitivity or false-alarm probability is claimed. The LS4N diagnostic comparison and all original LS4 dispositions remain unchanged.','',
        '## Reproducibility','',
        'All 72 relevant tests passed before local freeze `257352e`, published as `d89909f887c767efe94f3b5fabdd4af8cfdb4c26` before the eleven live requests. Every response was checkpointed before the next request. Prior headers supplied geometry; no new linked radio file or header was opened.','',
        f"Result identity: `{r['result_sha256']}`.",'',
        '```bash','sha256sum -c LS4O_FREEZE.sha256','sha256sum -c RESULTS_MANIFEST_LS4O.sha256',
        'PYTHONPATH=src:scripts python scripts/ls4o_result_summary.py',
        'PYTHONPATH=src:scripts python scripts/ls4o_write_report.py','```','',
        'The verifier checks raw metadata response hashes, query identity, URL deduplication, filters, completeness annotations, all geometry, checkpoints and result identity without network access. The live runner refuses an existing output directory.','']
    (ROOT/'LS4O_CONTROL_FEASIBILITY_RESULT.md').write_text('\n'.join(lines))


if __name__=='__main__':main()
