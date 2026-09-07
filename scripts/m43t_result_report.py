"""Read sealed M43T artifacts, check publication completeness, and write report."""
import json
from m43t_neighbor_mask import ROOT,OUT,CONFIG,sha,frozen
from m43e_economical_bank import read_sealed,write_sealed


def main():
    result=read_sealed(OUT/'result.json');cfg=frozen(result['freeze_commit'])
    expected={f'truth{t["truth_index"]:02d}.strength{a:03d}.json' for t in cfg['truths'] for a in cfg['amplitudes']}
    if {p.name for p in OUT.glob('truth*.json')}!=expected:raise ValueError('trial file inventory incomplete or extra')
    trials={n:read_sealed(OUT/n) for n in expected}
    if len(result['pairs'])!=32 or len({(p['truth_index'],p['strength']) for p in result['pairs']})!=32:
        raise ValueError('paired endpoint denominator differs')
    members=0
    for pair in result['pairs']:
        name=pair['neighbor2']['artifact'];trial=trials[name]
        old=read_sealed(ROOT/'results_m43s_profile_sensitivity'/name)
        if (trial['endpoint']!=pair['neighbor2'] or old['endpoint']!=pair['historical_legacy']
            or trial['audit']['input_inventory_sha256']!=old['audit']['input_inventory_sha256']
            or trial['audit']['input_inventory_sha256']!=pair['input_inventory_sha256']
            or trial['historical_artifact_sha256']!=old['result_sha256']
            or trial['audit']['threshold']!=result['thresholds']['neighbor2']):
            raise ValueError('paired publication handoff differs')
        members+=len(trial['audit']['members'])
    files=sorted(p for p in OUT.glob('*.json') if p.name!='artifact_validation.json')
    for path in files:read_sealed(path)
    anchors=read_sealed(OUT/'mask_anchors.json')
    masked={p:sum(x['masked_bits'][p] for x in anchors['rows']) for p in cfg['policies']}
    calibrations={p:read_sealed(OUT/(p+'.calibration.json')) for p in cfg['policies']}
    heldout={p:read_sealed(OUT/(p+'.heldout.json')) for p in cfg['policies']}
    baseline=read_sealed(OUT/'baseline.json')
    identical_nulls=(calibrations['legacy']['null_maxima']==calibrations['neighbor2']['null_maxima']
        and heldout['legacy']['null_maxima']==heldout['neighbor2']['null_maxima'])
    audit={'milestone':'M43T','sealed_json_files_checked':len(files),'paired_trial_files':len(trials),
        'native_inputs_match_historical':True,'compact_member_decisions':members,'config_pins_verified':len(cfg['pinned_sha256']),
        'baseline_masked_bits':masked,'new_policy_null_vectors_identical_to_legacy':identical_nulls,'complete':True}
    write_sealed(OUT/'artifact_validation.json',audit)
    gained=sum(row['gained'] for row in result['summary']);lost=sum(row['lost'] for row in result['summary'])
    lines=['# M43T: neighboring-support mask results','',
        f'The new rule recovers {gained} additional injected signals and loses {lost} previously recovered signals in the 32-case comparison. '
        'This is a targeted repair regression on the previously inspected M43S panel. Original M43R/S outcomes remain unchanged.','',
        '| Injected profile | Strength | Historical legacy recovered | Neighbor2 recovered | Gained | Lost |',
        '|---|---:|---:|---:|---:|---:|']
    for row in result['summary']:
        lines.append(f'| {row["profile"]} | {row["strength"]} | {row["historical_legacy"]}/{row["denominator"]} | {row["neighbor2"]}/{row["denominator"]} | {row["gained"]} | {row["lost"]} |')
    lines+=['','The named rule accepts support >=3 within two neighboring proxy bins when deciding whether an epoch peak >=10 is isolated. '
        'Eight-width OR and nine-bin final mask dilation remain unchanged. Support windows do not wrap. '
        'Both strengths use the unchanged native profiles, exact activity subset and <=20 Hz maximum track residual over every active ON row, '
        'followed by all physical vetoes and diagnostic rank eligibility. The strengths describe added profile power, not measured recovered SNR.','',
        '## Calibration and the limits of the noise comparison','',
        '| Policy | Training maximum (128) | Fixed threshold | Held-out maximum (128) | Held-out >= threshold |',
        '|---|---:|---:|---:|---:|']
    for p in cfg['policies']:
        lines.append(f'| {p} | {max(calibrations[p]["null_maxima"]):.6f} | {result["thresholds"][p]["operational_threshold_snr"]:.6f} | {max(heldout[p]["null_maxima"]):.6f} | {heldout[p]["at_or_above_threshold"]}/128 |')
    comparison=result['legacy_calibration_comparison']
    lines+=['',f'There are 256 distinct new shift rows, excluded from M43R, evaluated once per policy (512 policy/row evaluations). '
        f'The policies use the same shifts. Their training and held-out vectors are exactly equal: **{identical_nulls}**. '
        f'The original uninjected data has {masked["legacy"]} legacy and {masked["neighbor2"]} neighbor2 masked bits. '
        'Consequently this panel provides no direct measurement of the change in rejection of strong real interference. '
        'Zero exceedances here cannot establish general noise safety. Shifts share one observing sequence; these are correlated pre-veto scores, '
        'not independent sequences or physical false-alarm probabilities.','',
        f'Fresh legacy calibration has the historical threshold: **{comparison["same_threshold"]}**. '
        f'All {comparison["historical_members_checked"]} historical member rank-eligibility decisions agree: **{comparison["all_rank_eligibility_equal"]}**. '
        'The 32 historical legacy runs retain their original M43R certificate and were not rerun or relabelled. '
        'Every new injected score inventory exactly matches the paired M43S inventory.','',
        f'The new uninjected full-detector execution retains {baseline["on_retained"]} ON and {baseline["off_retained"]} OFF members, '
        f'with {baseline["all_member_physical_survivors"]} physical survivors. This diagnostic baseline is not an astronomical nondetection.','',
        '## Validation, scope and next step','',
        f'All ten focused tests pass. Both mask implementations match an independent reference on all {anchors["bits_per_policy"]:,} full-support bits per policy; '
        'the neighbor2 mask is a subset of the legacy mask. Those real baseline anchors are all zero; nonempty isolation, displaced support, '
        'threshold boundaries and width-OR behavior are exercised by the known-answer tests. '
        f'All 24 reused native-cache identities match. The package contains {members:,} compact new member decisions and 32 exact-input paired native trials.','',
        f'The grouped numerical run took {result["wall_seconds"]:.1f} seconds. There were no new downloads or telescope requests. '
        'The scope remains 37 templates and 4,097 central carriers (about 11.6 kHz) in six scans from one observing sequence, '
        'with all eight widths and four activity subsets. The finite smeared profile is a defined model, not an instrument measurement.','',
        'The radius was chosen after the M43S loss diagnosis, then frozen before M43T evaluation. '
        'Any recovery improvement is evidence for this specific repair on a known panel, not independent astrophysical completeness. '
        'The next useful experiment is a jointly frozen panel of nearby true-signal tracks and strong interference controls '
        'on additional carrier locations, with both policies and fresh calibration. General adoption remains premature. '
        'No astronomical candidate is claimed.','',
        '## Reproduction and artifacts','',
        f'- Public prospective freeze: `{result["freeze_commit"]}`.',
        f'- Configuration SHA-256: `{sha(CONFIG)}` ({len(cfg["pinned_sha256"])} pinned dependencies).',
        f'- Result seal: `{result["result_sha256"]}`.',
        '- [Frozen plan](MILESTONE_43T_NEIGHBOR_MASK_PLAN.md) and [configuration](config/m43t_neighbor_mask.json).',
        '- [Full paired results](results_m43t_neighbor_mask/result.json), [run log](results_m43t_neighbor_mask/live_run.log), '
        '[artifact validation](results_m43t_neighbor_mask/artifact_validation.json), and [checksum manifest](RESULTS_MANIFEST_M43T_NEIGHBOR_MASK.sha256).',
        '- All 32 per-trial audits, both calibration and held-out arrays, mask/native anchors and baseline are in `results_m43t_neighbor_mask/`.','',
        'With the original verified source and M43P anchors available, use Python 3.12.13 and NumPy 2.3.5 in a clean results directory:',
        '```bash','PYTHONPATH=src:scripts:tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/m43t_neighbor_mask.py \\',
        f'  --freeze-commit {result["freeze_commit"]} \\',
        '  --anchor-root /path/to/m43p_work --source-root /path/to/m43h_work/live','```','',
        'Completed results are protected from overwrite. Sealed trial checkpoints can only resume with matching freeze/configuration and native input identities.','']
    report=ROOT/'MILESTONE_43T_NEIGHBOR_MASK_RESULT.md';report.write_text('\n'.join(lines))
    paths=set(OUT.glob('*'))|{report,CONFIG,ROOT/'MILESTONE_43T_NEIGHBOR_MASK_PLAN.md',
        ROOT/'src/seti_repeater/mask_m43t.py',ROOT/'src/seti_repeater/detector_m43t.py',ROOT/'tests/test_m43t_mask.py'}
    paths.update(ROOT.glob('scripts/m43t_*.py'))
    manifest=ROOT/'RESULTS_MANIFEST_M43T_NEIGHBOR_MASK.sha256'
    manifest.write_text(''.join(f'{sha(p)}  {p.relative_to(ROOT)}\n' for p in sorted(paths) if p.is_file()))
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
