"""Prepare M43P inputs from frozen metadata and ancestor identities only."""
import hashlib
import json
import numpy as np
from m43f_source_cache_preflight import build_context
from m43p_combined_controls import ROOT, CONFIG
from seti_repeater import search_v0p6 as core


def main():
    parent=json.loads((ROOT/'config/m43o_real_stacks.json').read_text())
    _,_,_,metadata,basis,bank,table,_=build_context()
    grid=core.make_m37_proxy_carrier_grid(parent['window']); n=grid.score_bin_count
    preflight=json.loads((ROOT/'results_m43f_source_cache_preflight/preflight.json').read_text())
    window=next(w for w in preflight['windows'] if w['window_id']==parent['window'])
    queries={};witnesses=[]
    for scan in metadata['scans']:
        label=scan['label'];header=scan['expected_header'];interval=window['proposed_interval']
        geometry=core.native_geometry_from_extraction(fch1_mhz=header['fch1_mhz'],foff_mhz=header['foff_mhz'],
            channel_start=interval[0],channel_stop=interval[1])
        factors=core.factor_table_for_scan(table,basis,label)
        template,row=np.unravel_index(factors.argmin(),factors.shape)
        mapping=np.rint((factors[template,row]*grid.score_hz-geometry.raw_zero_hz)/geometry.channel_width_hz).astype(np.int64)
        first=int(np.flatnonzero(np.diff(mapping)==0)[0])
        queries[label]=[n-1,0,n//2,n//2,9,n-10,n//2+1,first,first+1]
        witnesses.append({'scan':label,'template_index':int(template),'integration_index':int(row),
            'factor':float(factors[template,row]),'score_indices':[first,first+1],
            'native_indices':mapping[first:first+2].tolist()})
    minimum=core.M37_RFI_GUARD_Q_BINS+1
    shifts=np.array([[0,minimum,minimum+1],[0,n-minimum-1,n-minimum-2],
                     [0,n//2,n//3],[0,n//4,3*n//4]],dtype=np.int64)
    core.validate_scramble_shift_table(shifts,epoch_count=3,score_bin_count=n,minimum_shift_bins=minimum)
    paths=set(parent['pinned_sha256'])
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'src').rglob('*.py'))
    paths.update(['config/m43o_real_stacks.json','results_m43o_real_stacks/qualification.json',
        'scripts/m43o_real_stacks.py','scripts/m43o_stack_reference.py',
        'src/seti_repeater/adjacent_v0p6.py','src/seti_repeater/adjacent_m43p.py',
        'scripts/m43p_reference.py','scripts/m43p_combined_controls.py','scripts/m43p_freeze_config.py',
        'tests/test_m43p_controls.py','tests/test_v0p6_core.py','tests/test_v0p6_adjacent.py',
        'tests/test_v0p6_sparse_retention.py','tests/test_v0p6_alias.py','tests/test_v0p6_significance.py',
        'MILESTONE_43P_COMBINED_CONTROLS_PLAN.md','results_m43p_combined_controls/unit_tests.txt'])
    cfg={'milestone':'M43P','numpy_version':np.__version__,'window':parent['window'],
        'bank_sha256':parent['bank_sha256'],'factor_table_sha256':parent['factor_table_sha256'],
        'grid_sha256':parent['grid_sha256'],'support_carriers':grid.support_bin_count,
        'score_carriers':n,'widths':parent['widths'],'source_workers':7,'logic_workers':2,
        'ancestor_batch_indices':[0,53],'template_intervals':[[0,32],[1696,1701]],'anchor_templates':37,
        'query_score_indices':queries,'duplicate_mapping_witnesses':witnesses,
        'minimum_shift_bins':minimum,'scramble_shifts':shifts.tolist(),
        'scramble_table_sha256':core.scramble_table_sha256(shifts),
        'pinned_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}}
    CONFIG.write_text(json.dumps(cfg,indent=2)+'\n')
    print(json.dumps({'config':str(CONFIG),'pins':len(paths),'witnesses':witnesses},indent=2))


if __name__=='__main__':main()
