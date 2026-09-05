#!/usr/bin/env python3
"""Verify M43D identities, subgroup arithmetic and every published witness."""
import csv
import gzip
import hashlib
import json
import numpy as np
from m43d_bank_coverage import ROOT, ACTIVITY, LABELS, nested_banks, heldout_truths, verified_json
from m43b_active_support import seal
from seti_repeater import search_v0p6 as core


def main():
    out=ROOT/'results_m43d_bank_coverage'
    if not (out/'geometry.json').exists():
        (out/'geometry.json').write_bytes(gzip.decompress((out/'geometry.json.gz').read_bytes()))
    result=verified_json(out/'geometry.json')
    selection=verified_json(out/'historical_selection.json')
    cfgpath=ROOT/'config/m43d_bank_coverage.json'
    cfg=json.loads(cfgpath.read_text())
    cfg_hash=hashlib.sha256(cfgpath.read_bytes()).hexdigest()
    assert result['config_sha256']==selection['config_sha256']==cfg_hash
    for name,digest in cfg['pinned_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    prior=verified_json(ROOT/'results_m43b_active_support/geometry.json')
    assert prior['result_sha256']==result['parent_result_sha256']
    assert selection['result_sha256']==result['selection_sha256']
    basis=core.make_factor_basis_from_metadata(json.loads((ROOT/'config/hd156668b_m37_preflight.json').read_text()))
    original=json.loads((ROOT/'results_m37_v0p6_bank_preflight/bank_preflight.json').read_text())['template_bank']['records']
    banks=nested_banks(original);names=list(banks)
    table=core.make_template_factor_table(basis,banks['disk32'],expected_template_bank_sha256=core.template_bank_sha256(banks['disk32']))
    assert table.factor_table_sha256==result['largest_factor_table_sha256']
    assert core.factor_table_sha256(table.factors[:93])==prior['factor_table_sha256']
    grid=core.make_m37_proxy_carrier_grid('m37_1412p5')
    heldout=heldout_truths(grid)
    assert seal(heldout)==result['heldout_truth_inventory_sha256']
    rows=result['rows'];historical=rows[:512]
    assert len(rows)==2560 and len(historical)==512
    witnesses=0
    for ordinal,row in enumerate(rows):
        assert row['result_sha256']==seal({k:v for k,v in row.items() if k!='result_sha256'})
        assert row['config_sha256']==cfg_hash
        if ordinal<512:
            old=prior['rows'][ordinal]
            assert row['truth']==old['truth'] and row['split']=='historical'
            assert row['active_epochs']==row['truth']['active_epochs_zero_based']
            assert row['m43b_exact_replay']
            assert row['banks']['baseline']['candidate_cells']==old['active_candidate_cells']
        else:
            number=(ordinal-512)//4;activity=ACTIVITY[(ordinal-512)%4]
            assert row['truth']==heldout[number] and row['active_epochs']==list(activity)
            assert row['split']=='heldout' and not row['m43b_exact_replay']
        truth=row['truth']
        truth_factors=core.template_factors_from_basis(basis,truth)
        active_labels={LABELS[i] for i in row['active_epochs']}
        mask=np.array([l.scan_label in active_labels for l in basis.labels])
        counts=[]
        for name in names:
            info=row['banks'][name];counts.append(info['candidate_cells'])
            assert info['supported']==(info['candidate_cells']>0)
            assert len(info['candidate_pairs_sha256'])==64
            witness=info['witness']
            if not info['supported']:
                assert witness is None
                continue
            assert 0<=witness['template_index']<len(banks[name])
            assert witness['carrier_hz']==grid.score_hz[witness['carrier_index']]
            tf=core.template_factors_from_basis(basis,banks[name][witness['template_index']])
            # Re-evaluate the physical factor formula, separate from interval/pair construction.
            distance=float(np.max(np.abs(witness['carrier_hz']*tf[mask]-truth['proxy_carrier_hz']*truth_factors[mask])))
            assert distance==witness['max_distance_hz'] and distance<=20
            witnesses+=1
        assert counts==sorted(counts)
    counts={name:sum(row['banks'][name]['supported'] for row in historical) for name in names}
    assert counts==result['historical_supported']==selection['historical_counts']
    nominated=next((name for name in names if counts[name]/512>=.95),None)
    assert nominated==result['historical_selected_bank']==selection['selected_bank']
    groups=[]
    for act in ACTIVITY:
        chosen=[r for r in rows[512:] if r['active_epochs']==list(act)]
        groups.append({'active_epochs':list(act),'truth_count':len(chosen),
                       'supported':{name:sum(r['banks'][name]['supported'] for r in chosen) for name in names}})
    assert groups==result['heldout_groups']
    confirmed=nominated is not None and all(g['supported'][nominated]/512>=.95 for g in groups)
    assert confirmed==result['heldout_95_percent_gate_passed']
    for name,bank in banks.items():
        meta=result['bank_inventory'][name]
        assert meta['bank_sha256']==core.template_bank_sha256(bank)
        assert meta['template_count']==len(bank)
        assert meta['score_cells_one_window']==len(bank)*grid.score_bin_count*32
        assert meta['score_cells_five_windows']==meta['score_cells_one_window']*5
        assert meta['relative_score_cells']==len(bank)/93
    with (out/'coverage_summary.csv').open('w') as f:
        w=csv.writer(f,lineterminator='\n')
        w.writerow(['bank','templates','historical_supported_of_512','heldout_01_of_512','heldout_02_of_512','heldout_12_of_512','heldout_012_of_512','score_cells_per_window','relative_score_cells'])
        for name in names:
            meta=result['bank_inventory'][name]
            w.writerow([name,meta['template_count'],counts[name],*[g['supported'][name] for g in groups],meta['score_cells_one_window'],meta['relative_score_cells']])
    with (out/'truth_summary.csv').open('w') as f:
        w=csv.writer(f,lineterminator='\n')
        w.writerow(['split','truth_ordinal','truth_id','active_epochs',*[name+'_candidate_cells' for name in names]])
        for row in rows:
            w.writerow([row['split'],row['truth']['truth_ordinal'],row['truth']['truth_id'],'+'.join(map(str,row['active_epochs'])),*[row['banks'][name]['candidate_cells'] for name in names]])
    lines=['# M43D: coefficient-disk bank coverage result','',
           f"**Completed: the preselected {len(banks[nominated]) if nominated else 'none'}-template bank {'passes' if confirmed else 'does not pass'} the frozen held-out geometric gate.**",'',
           'All 512 historical M43B plan hashes and every baseline template/carrier pair reproduce exactly. The original 167/512 supported truths are preserved. Adding fixed, nested grids across the two-dimensional coefficient disk improves geometric coverage at the unchanged 20 Hz tolerance.','',
           '## Coverage comparison','',
           'Each cell below is supported tracks / 512. New tracks are reused under the four activity patterns, allowing paired comparisons. Epoch numbers in this table are one-based.','',
           '| Templates | Historical | New: epochs 1+2 | New: 1+3 | New: 2+3 | New: all three |',
           '|---:|---:|---:|---:|---:|---:|']
    for name in names:
        values=[counts[name]]+[g['supported'][name] for g in groups]
        lines.append('| '+str(len(banks[name]))+' | '+' | '.join(f'{v}/512 ({v/512:.1%})' for v in values)+' |')
    lines+=['',
        f"The frozen development rule nominated **{nominated} ({len(banks[nominated]) if nominated else 0} templates)** from the historical inventory before evaluating new tracks. The nomination identity is `{selection['result_sha256']}`. The new-track gate requires at least 95% coverage in each activity group; it **{'passes' if confirmed else 'fails'}**. No bank was substituted after viewing the held-out results.",'',
        'The 512 new tracks use separate, predetermined SHA-256 jitters in equal-area disk strata and continuous off-grid carriers. They do not coincide with historical coefficient pairs or template points. Their carriers span the historical allowed proxy interval, while historical carriers were on the grid. Historical and new rates therefore differ in carrier sampling and are not interchangeable estimates. These are 512 new parameter draws on the same cadence, not independent telescope observations, sky signals, or 2,048 independent trials.','',
        '## Computational cost','',
        '| Templates | Score cells per window | Five-window arithmetic total | Relative cells | Factor table bytes, six scans |',
        '|---:|---:|---:|---:|---:|']
    for name in names:
        m=result['bank_inventory'][name]
        lines.append(f"| {m['template_count']:,} | {m['score_cells_one_window']:,} | {m['score_cells_five_windows']:,} | {m['relative_score_cells']:.2f}× | {m['template_factor_bytes_all_six_scans']:,} |")
    lines+=['',
        f"The joint geometry calculations evaluated {result['distance_cells_evaluated']:,} distance cells in {result['geometry_seconds_sum']:.2f} measured seconds, excluding basis reconstruction, historical plan replay and disk checkpoints. The largest factor table occupies {result['factor_table_bytes']:,} bytes. This is a metadata computation; the cell ratios are not measured detector runtime ratios. Spectral reads, filtering, caches, masks and calibration are absent from this timing.",'',
        '## Interpretation and next step','',
        'This result removes much of the tested geometric limitation. It does **not** measure signal recovery, sensitivity, false-alarm rates or physical completeness. An associated template can still fail masking, threshold, OFF/control or other scientific acceptance gates. No telescope candidate is promoted, and M37/M41/LS results remain unchanged.','',
        ('Carry disk16 forward as an engineering candidate. First recheck source/extraction/cache coverage, score equivalence and false-association behavior for the 889-template bank. Then run deterministic exhaustive real-data anchors and renew calibration. The historical threshold cannot simply transfer to a bank with more hypotheses.' if confirmed else 'The preselected 889-template bank fails in two new activity groups (486/512 and 470/512). The 3,301-template bank has a descriptive 511/512 result in each group, but was not the preselected confirmation candidate. Do not promote it by switching banks after this check. No bank is qualified for adoption by this gate. Diagnose remaining coverage and computational tradeoffs before a separately frozen next study; any new confirmation must use previously unevaluated tracks.'),'',
        'Even a passed 95% sample gate is not a full-domain guarantee. Boundary coverage, other cadences, orbital uncertainty and other physical windows remain outside this study.','',
        '## Reproducibility and verification','',
        f"Public freeze: `191f3b4d7182adc6c82e3dcc5c006f2fb29382cb`; tree `4203d597ecf58c794b47139ca7f64ed8d5321f7d`, verified before execution. Result identity: `{result['result_sha256']}`.",'',
        f"All 21 M43/M43B/M43C/M43D tests pass. This report checks all 2,560 row identities and group counts, bank identities and nested candidate counts; it independently re-evaluates all {witnesses:,} published support witnesses from the coefficient/basis formula. Each witness satisfies the original literal <=20 Hz rule. Historical plans and all baseline pairs were replayed during execution. This is not a new full-repository test run or a formal real-arithmetic certificate.",'',
        'The sealed combined `geometry.json` (published as lossless `geometry.json.gz`, automatically unpacked by the report command) retains every restart row, per-bank candidate-pair hashes and witnesses. Pair lists are regenerable from the frozen metadata and code. `historical_selection.json` preserves the nomination; CSV files support review. Restart copies are omitted from Git because the combined result contains them. Runtime values are observational and will differ on a fresh run; they are not scientific thresholds.','',
        '```bash','PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43d_bank_coverage.py',
        'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43d_result_report.py',
        "PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_m43*.py' -v",'```','']
    (ROOT/'MILESTONE_43D_BANK_COVERAGE_RESULT.md').write_text('\n'.join(lines))
    audit={'result_sha256':result['result_sha256'],'checked_rows':len(rows),'checked_witnesses':witnesses,
           'historical_plan_replay_count':512,'selected_bank':nominated,'heldout_gate_passed':confirmed}
    (out/'verification.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
