"""Build a readable report and artifact manifest from completed sealed results."""
from collections import Counter
from pathlib import Path
from m43r_joint_calibration import ROOT,OUT,CONFIG,sha
from m43e_economical_bank import read_sealed


def main():
    r=read_sealed(OUT/'result.json');h=read_sealed(OUT/'heldout.json');a=read_sealed(OUT/'native_anchors.json')
    b=read_sealed(OUT/'baseline.json');cal=read_sealed(OUT/'calibration.json')
    rows=['| Nominal active-epoch SNR | Endpoints | Retained | Pass physical vetoes | Recovered incl. rank |',
          '|---:|---:|---:|---:|---:|']
    rows += [f'| {x["nominal_epoch_snr"]} | {x["denominator"]} | {x["retained"]} | {x["passes_physical_vetoes"]} | {x["recovered"]} |' for x in r['summary']]
    truth_rows=['| Parent template | Active epochs (1-based) | SNR 8 | SNR 32 | SNR 64 |',
                '|---:|---|---|---|---|']
    for t in range(8):
        es=[e for e in r['endpoints'] if e['truth']['truth_index']==t and e['nominal_epoch_snr']>0]
        truth=es[0]['truth']
        status=lambda e:'recovered' if e['recovered'] else ('physical rejection' if e['retained'] and not e['passes_physical_vetoes'] else ('rank rejection' if e['passes_physical_vetoes'] else 'not retained'))
        truth_rows.append(f'| {truth["parent_template"]} | {", ".join(str(e+1) for e in truth["active_epochs"])} | '+ ' | '.join(status(e) for e in es)+' |')
    dispositions=Counter()
    for p in OUT.glob('truth*.json'):
        audit=read_sealed(p)['audit'];dispositions.update(m['physical_disposition'] for m in audit['members'])
    text=f'''# M43R joint calibration and native-injection pilot

The frozen bounded pilot is complete. It uses 37 selected templates, all eight
widths and four activity subsets over 4,097 central score carriers, approximately
11.6 kHz around 1412.5 MHz. All scans are from one observing sequence. This is
the first measured native-injection recovery exercise of the connected M43 path.
It does not authorize an astronomical candidate or establish a full-search limit.

## Fixed threshold and held-out noise shifts

The frozen rule gives a threshold of
**{r['threshold']['operational_threshold_snr']:.12g}**. The predeclared floor of
10 dominates the calibration maximum of {max(cal['null_maxima']):.9g}; thus the
threshold did not need to rise above that floor. The held-out maximum is
{max(h['null_maxima']):.9g}. The fixed certificate was saved before held-out
evaluation or signal insertion. Of the separate 128 rows,
**{h['at_or_above_threshold']}/128** were at or above that threshold and
**{h['strictly_above_threshold']}/128** strictly above it. These are correlated
within-sequence, pre-veto resampling exceedances, not independent observations
or a measured physical false-alarm probability. The smallest possible calibration
rank p is 1/129, approximately 0.007752; ties use the inherited inclusive rank.

The unmodified background retained {b['on_retained']} ON and {b['off_retained']}
OFF members, with {b['all_member_physical_survivors']} ON members passing the
evaluated physical vetoes. Any background member remains diagnostic only.

## Signal recovery

Eight fixed truths cross parent templates 0 and 1700 with all four activity
subsets at the central carrier. Each has nominal active-epoch SNR 0, 8, 32 and 64.
The zero level reuses one background execution eight times; it is not eight
independent trials. There are 24 nonzero injections and 25 detector executions.

'''+ '\n'.join(rows)+'''

Recovery requires the exact injected template, activity subset and carrier,
at any width, passing all evaluated physical vetoes and the fixed rank cut.
Retention and physical passage are shown separately so losses stay visible.

'''+ '\n'.join(truth_rows)+f'''

Signal samples were added to normalized native channels before filtering and
gathering. Complete affected windows and proxy columns were recomputed; receiver
signatures used the same additions. The original telescope receipts remain
unaltered and each overlay has its own provenance. These idealized, on-template,
single-channel injections do not include fractional leakage, intra-integration
smearing, varied carrier positions or a source population. The table is a small
engineering sensitivity pilot, not an astrophysical completeness curve.

All 24 nonzero injections were recovered, including all eight at nominal SNR 8;
none of the eight reused zero-level endpoints was recovered. The selected
strengths therefore do not locate the transition from missed to recovered
signals. The useful next experiment is a newly frozen extension below SNR 8,
with fractional-channel profiles, integration smearing, off-template truths and
additional carrier positions. The present 24/24 result must not be generalized
to that harder population or compared directly with the older M41 denominator.

## Evidence and reproducibility

- Public pre-evaluation freeze: `{r['freeze_commit']}`.
- Result seal: `{r['result_sha256']}`.
- Threshold certificate: `{r['threshold']['certificate_sha256']}`.
- Config SHA-256: `{r['config_sha256']}`; 219 pinned dependencies.
- Twelve focused tests pass: five new overlay/fixed-calibration tests plus the
  seven unchanged M43Q integration tests. Earlier 165-test evidence is reused
  for unchanged code rather than repeating the full suite.
- All {a['verified_cropped_epoch_score_cells']:,} cropped ON score cells match
  receipt-bound ancestor scores exactly across 24 native caches. The 96 M43P
  arrays were verified before reuse. Zero new telescope data requests.
- Calibration evaluated {cal['calibration']['null_score_cells']:,} scrambled
  score cells; the held-out pass evaluated the same number. Cell counts are
  arithmetic coverage, not independent statistical samples.
- Successful execution took {r['wall_seconds']:.3f} seconds. A first launcher
  reached no evaluation because the public freeze fetch was still pending;
  its `bootstrap_wait.log` is retained. No scientific plan amendment was needed.

All 32 endpoints, all 24 injected compact member inventories, source-overlay
receipts, stage certificates, null maxima and run logs are in
[`results_m43r_joint_calibration/`](results_m43r_joint_calibration/).
Each compact trial includes the hash of the complete in-memory pipeline result;
compact audits are not represented as the full pipeline serialization.
The SHA-256 manifest covers the published report, code, plan and artifacts.

Run from the repository with the same pinned Python/NumPy environment and
verified M43H sources/M43P anchor arrays:

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \\
  .venv/bin/python scripts/m43r_joint_calibration.py \\
  --freeze-commit {r['freeze_commit']} \\
  --anchor-root /path/to/m43p_work --source-root /path/to/m43h_work/live
```

Earlier full-band numerical qualifications and their denominators remain intact.
Fresh independent observing coverage, a broader bank/frequency calibration and
more realistic injections remain necessary before scientific search claims.
'''
    (ROOT/'MILESTONE_43R_JOINT_CALIBRATION_RESULT.md').write_text(text)
    paths=[p for p in OUT.rglob('*') if p.is_file()]
    paths += [CONFIG,ROOT/'MILESTONE_43R_JOINT_CALIBRATION_PLAN.md',ROOT/'MILESTONE_43R_JOINT_CALIBRATION_RESULT.md']
    paths += [ROOT/p for p in ('src/seti_repeater/detector_m43r.py','src/seti_repeater/injection_m43r.py',
        'scripts/m43r_joint_calibration.py','scripts/m43r_freeze_config.py','scripts/m43r_result_report.py','tests/test_m43r_calibration.py')]
    manifest=ROOT/'RESULTS_MANIFEST_M43R_JOINT_CALIBRATION.sha256'
    manifest.write_text(''.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in sorted(paths)))
    print({'manifest_entries':len(paths),'result_sha256':r['result_sha256'],'member_dispositions':dict(dispositions)})


if __name__=='__main__':main()
