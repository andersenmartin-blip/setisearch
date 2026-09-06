"""Audit and report the complete M43Q diagnostic run and retained failure."""
import json
from collections import Counter
import numpy as np
from m43q_integrated_detector import ROOT,OUT,CONFIG,sha,frozen
from m43e_economical_bank import read_sealed
from seti_repeater.detector_m43q import digest
from seti_repeater import search_v0p6 as core


def main():
    r=read_sealed(OUT/'qualification.json');cfg=frozen(r['freeze_commit'])
    for name,h in r['artifacts'].items():assert read_sealed(OUT/name)['result_sha256']==h
    p=read_sealed(OUT/'pipeline.json');pipeline=p['pipeline']
    assert digest({k:v for k,v in pipeline.items() if k!='result_sha256'})==r['pipeline_result_sha256']==pipeline['result_sha256']
    assert p['bridge']==cfg['bridge'] and len(p['anchor_inventory'])==96
    assert pipeline['catalogue_sha256']==cfg['bridge']['catalogue_sha256']
    assert pipeline['factor_table_sha256']==cfg['bridge']['factor_table_sha256']
    for kind in ('on','off'):
        cert=pipeline['retention_certificates'][kind]
        core.validate_retention_certificate(cert,expected_certificate_sha256=cert['retention_certificate_sha256'])
        assert cert['records_sha256']==digest(pipeline['retained'][kind])
    expected_null=np.max(np.asarray([x['null_maxima'] for x in read_sealed(ROOT/'results_m43p_combined_controls/on.logic.json')['checks']]),axis=0)
    assert np.array_equal(expected_null,np.asarray(pipeline['null_maxima']))
    assert pipeline['threshold']['operational_threshold_snr']==max(50.,float(expected_null.max()))
    assert len(pipeline['decisions'])==len(pipeline['retained']['on'])==r['summary']['on_retained']
    assert len(pipeline['retained']['off'])==r['summary']['off_retained']
    assert all(not x['scientific_candidate'] and not x['meets_diagnostic_rank_cut'] and x['inclusive_rank_p']>=.2 for x in pipeline['decisions'])
    assert pipeline['receiver_receipt']['signatures_sha256']==digest(pipeline['receiver_signatures'])
    assert pipeline['receiver_receipt']['queries_sha256']==digest(pipeline['receiver_receipt']['queries'])
    anchors=read_sealed(OUT/'receiver_anchors.json')
    assert anchors['complete'] and len(anchors['checks'])==144
    expected={(f'epoch{e}_on',w,t,q) for e in (1,2,3) for w in core.M37_SPECTRAL_WIDTHS
              for t in cfg['receiver_parent_templates'] for q in cfg['receiver_score_indices']}
    assert {(x['scan'],x['width'],x['parent_template'],x['score_index']) for x in anchors['checks']}==expected
    assert all(x['reference_exact'] for x in anchors['checks'])
    syn=read_sealed(OUT/'synthetic.json')
    assert syn['pipeline']['result_sha256']==cfg['synthetic_result_sha256']==r['synthetic_result_sha256']
    assert digest({k:v for k,v in syn['pipeline'].items() if k!='result_sha256'})==cfg['synthetic_result_sha256']
    assert set(syn['known_dispositions'])=={'50','100','150','250','290','350'}
    tests=(OUT/'unit_tests.txt').read_text();assert 'Ran 165 tests' in tests and tests.rstrip().endswith('OK')
    failure=read_sealed(OUT/'initial_attempt/failure.json')
    assert failure['complete'] is False
    # Explicitly verify that the retained original synthetic outer seal is bad.
    initial=json.loads((OUT/'initial_attempt/synthetic.json').read_text())
    assert digest({k:v for k,v in initial.items() if k!='result_sha256'})!=initial['result_sha256']
    counts=Counter(x['physical_disposition'] for x in pipeline['decisions'])
    rows='\n'.join(f'| {k} | {v} |' for k,v in sorted(counts.items())) or '| No diagnostic ON members retained | 0 |'
    s=r['summary']; threshold=pipeline['threshold']['operational_threshold_snr']
    report=f'''# M43Q — the integrated diagnostic detector passes

M43 now has one connected diagnostic entry point from verified epoch scores
through masks, a global threshold handoff, exhaustive ON/OFF retention,
OFF-track matching, paired single-OFF rejection, native receiver signatures,
receiver-alias classification and inclusive rank-p evidence. All declared
integration checks pass after the documented reference/serialization amendment.

**165 tests pass.** The complete 1,701-template catalogue preserves every
one of its 163,296 physical factor values bit for bit. The real diagnostic
run reuses **37 templates, six scans, eight widths and 96 full-support ancestor
arrays**, covering the same 1,328,080,368 per-epoch cells already replayed by
M43P. This reuse is not new independent arithmetic evidence. **144 fixed real
native receiver signatures** match independently summed windows and winner
selection exactly. The synthetic whole-pipeline fixture produces all six
predeclared member outcomes, including a survivor of the physical controls.

## What changed

The Cartesian bank lacked fields required by the old retention record schema.
The new catalogue retains exact original x/y coefficients and explicit parent
identifiers. Radius, phase and legacy line fields are compatibility metadata;
they do not turn the disk bank into a physical line. All tracking uses the
original Cartesian coordinates. The 37-template catalogue has its own identity,
factor-table identity and threshold/retention receipts. Old identities are not
reused under a different catalogue.

At each score handoff, copied template bytes are checked against the inventory
derived from independently retained M43P batch hashes. Expected identities are
snapshotted before execution. The generic legacy numerical/physical algorithms
are unchanged; no M37 cache or epoch-product attestation is forged. Their M37-
specific provenance flags stay false, while the outer M43 inventory explicitly
binds the source/score inputs.

Paired OFF uses the exact values in the already verified native-gather score
vectors. Each width/epoch cache has an explicit M43Q vector plan and an actual
template-major payload hash. This is equivalent to querying those same scores,
not a relabelled M37 native cache. Stationary receiver peaks are newly measured
from receipt-bound M43I native-filter caches using the inherited ±100-Hz window
and ascending-channel tie break. All 144 fixed receiver anchors are evaluated
regardless of how many real diagnostic members pass retention.

## End-to-end diagnostic outcome

| Quantity | Result |
| --- | --- |
| Diagnostic template sample | 37 / 1,701 |
| Reused scramble rows | 4 |
| Diagnostic operational threshold | {threshold:.9g} |
| Retained ON members | {s['on_retained']} |
| Retained OFF members | {s['off_retained']} |
| Final ON member decisions | {s['final_member_decisions']} |
| Members passing evaluated physical vetoes | {s['passes_physical_vetoes']} |
| Scientific candidates selected | 0; selection is disabled |

| Inherited physical disposition | Diagnostic members |
| --- | --- |
{rows}

The four global null maxima exactly equal the maxima of the independently
retained M43P per-template values for the same scramble rows. The threshold
is the frozen engineering rule max(50, maximum of those four global values),
with inclusive retention. It is not a newly established science threshold.
Four null values imply a minimum inclusive rank p of 0.2, so none can meet
the 0.01 scientific cutoff. The retained member counts are pipeline diagnostics,
not a search result, false-alarm measurement or candidate count. An empty real
member inventory, if present, does not by itself exercise nonempty rejection;
the known-answer synthetic fixture explicitly supplies that coverage.

The inherited `pending_receiver_alias_evaluation` label is preserved for
compatibility. After the alias stage, a separate `passes_evaluated_physical_vetoes`
Boolean explains whether a member survived these physical controls. Exact
record IDs join physical dispositions to rank evidence; none is promoted to
a scientific candidate in this qualification.

## Preserved initial failure and amendment

The initial public freeze was
`e9ceca61e8db7c0dca0076e1a8b0c3e1f8e9b17c`. It stopped at the first native
receiver anchor. The reference used Python 3.12's built-in sum instead of
the inherited sequential binary64 reduction, giving a one-ULP midpoint
difference. A second defect affected the synthetic artifact's outer seal:
integer dictionary keys changed canonical ordering after JSON conversion.

Only the reference reduction, pre-seal key normalization and explicit Python
version pin changed. Production scoring, receiver measurement, comparison
strictness, masks, the diagnostic threshold and physical rules did not.
Two regression tests cover the defects. The initial configuration, logs,
failure record and invalid synthetic outer seal are preserved, not replaced.
See MILESTONE_43Q_AMENDMENT.md. The successful rerun used the publicly verified
amended freeze **`{r['freeze_commit']}`** before any rerun evaluation.

## Evidence and reproduction

The successful combined run took **{r['wall_seconds']:.3f} seconds** wall time
in one process, including source/cache validation and the receiver anchors.
There were **zero new telescope requests/downloads**. NumPy {cfg['numpy_version']},
Python {cfg['python_version']}; the configuration pins {len(cfg['pinned_sha256'])} files.

- Result: `{r['result_sha256']}`.
- Configuration: `{r['config_sha256']}`.
- Integrated pipeline: `{r['pipeline_result_sha256']}`.
- Diagnostic catalogue: `{cfg['bridge']['catalogue_sha256']}`.
- Parent catalogue: `{cfg['bridge']['parent_bank_sha256']}`.

`pipeline.json` retains the complete connected outputs and input ancestry;
`receiver_anchors.json` contains every fixed native comparison. `synthetic.json`
contains the nonempty known-answer pipeline and expected outcomes. The full
run log, tests and initial failed attempt are included in the manifest.

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/m43q_integrated_detector.py --freeze-commit {r['freeze_commit']} --anchor-root /path/to/m43p_work --source-root /path/to/m43h_work/live
PYTHONPATH=src:scripts .venv/bin/python scripts/m43q_result_report.py
sha256sum -c RESULTS_MANIFEST_M43Q_INTEGRATED_DETECTOR.sha256
```

The anchor directory contains disposable M43P arrays. If absent, reproduce
M43P from its published protocol first; M43Q refuses missing or changed arrays.
Elapsed time and enclosing run seals may differ on reproduction. The manifest
checks exact published bytes, including the intentionally invalid initial
synthetic artifact as historical evidence.

## Next work and scientific limits

The integration gap is now exercised through every connected stage. This
does not establish a full-bank spectral search, a fresh null distribution,
a native injection/recovery curve or a scientific nondetection. The real
template sample and one frequency window remain the declared scope; the three
epochs are scans in one observing sequence. The synthetic additions were
score-level fixtures, not native telescope injections.

Next: freeze a joint fresh null/native-injection programme using this integrated
path, with explicit search scope, source ancestry, resource caps and recovery
denominators. Reuse the established arithmetic and focus on measured false
alarms and recovery. Earlier scientific endpoints and denominators remain intact.
'''
    target=ROOT/'MILESTONE_43Q_INTEGRATED_DETECTOR_RESULT.md';target.write_text(report)
    files=[ROOT/'MILESTONE_43Q_INTEGRATED_DETECTOR_PLAN.md',ROOT/'MILESTONE_43Q_AMENDMENT.md',target,CONFIG,
        ROOT/'src/seti_repeater/detector_m43q.py',ROOT/'src/seti_repeater/receiver_m43q.py',ROOT/'tests/test_m43q_detector.py']
    files+=sorted((ROOT/'scripts').glob('m43q_*.py'))
    files+=sorted(p for p in OUT.rglob('*') if p.is_file())
    (ROOT/'RESULTS_MANIFEST_M43Q_INTEGRATED_DETECTOR.sha256').write_text(''.join(
        f'{sha(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in sorted(set(files))))
    print(json.dumps({'audit':'pass','summary':s,'manifest_files':len(set(files)),'report':str(target)},indent=2))


if __name__=='__main__':main()
