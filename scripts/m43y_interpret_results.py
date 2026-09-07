"""Extract fixed-probe stage evidence and component contrasts from sealed Y outputs."""
import gzip,json
import numpy as np
from m43y_response_diagnostic import ROOT,OUT,CONFIG
from m43e_economical_bank import read_sealed,write_sealed
from m43f_source_cache_preflight import build_context
from m43r_joint_calibration import grid_context
from seti_repeater import detector_m43u as detector,search_v0p6 as core

def key(t):return json.dumps(t['coordinate'],sort_keys=True)
def run():
    cfg=json.loads(CONFIG.read_text());result=read_sealed(OUT/'result.json')
    rows=[json.loads(s) for s in gzip.decompress((OUT/'case_audits.jsonl.gz').read_bytes()).splitlines() if s.strip()]
    lookup={r['spec']['name']:r for r in rows};traces={name:{key(t):t for t in r['trace']} for name,r in lookup.items()}
    _,_,_,metadata,basis,parent,_,_=build_context();x=json.loads((ROOT/'config/m43x_confirmation.json').read_text())
    bank,table,_=detector.catalogue_bridge(parent,x['parent_template_indices'],basis)
    factors=core.factor_matrix_for_kind(table,basis,metadata['scans'],'off')
    _,grid,_=grid_context()
    def measured(rowname,k):
        row=lookup[rowname];t=traces[rowname][k];template,q,width,active=t['coordinate']
        same={r['kind']:r for r in t['responses'] if r['width']==width}
        ids={a['record_id'] for a in t['annotated_records']}
        rank={m['record_id']:m['meets_diagnostic_rank_cut'] for m in row['reference_audit']['members']}
        final={p:any(d['record_id'] in ids and d['passes_evaluated_physical_vetoes'] and rank[d['record_id']] for d in ds) for p,ds in row['policy_decisions'].items()}
        coverage={}
        for kind,r in same.items():
            coverage[kind]=[]
            for e,d in enumerate(r['direct_native']):
                sources=[s for s in row['reference_audit']['overlay']['sources'] if s['scan']==f'epoch{e+1}_{kind}']
                coverage[kind].append(sum(any(abs(p['start']-center)<=width//2 for s in sources for j,p in enumerate(s['profiles']) if j==i) for i,center in enumerate(d['native_center_indices'])))
        return dict(retained=t['retained'],final=final,on_scores=same['on']['center'],off_scores=same['off']['center'],
            active_on_mask=t['active_mask'],off_same_width_neighborhood_max=same['off']['maximum'],
            off_same_width_first_max_q=same['off']['first_maximum_proxy_index'],injected_rows_inside_native_window=coverage,
            adjacent_off=t['adjacent_off_evidence'],off_tracks=t['retained_off_track_evidence'],
            receiver_alias=[a['receiver_alias_evidence'] for a in t['annotated_records']])
    evidence=[]
    for i in cfg['selected_cases']:
        name=f'case{i:03d}.original';row=lookup[name];ids=set(cfg['historical_surviving_record_ids'][str(i)])
        off=row['retained_off'];offtracks=np.asarray([r['proxy_carrier_hz']*factors[r['template_index']] for r in off])
        for t in row['trace']:
            found=[r for r in t['annotated_records'] if r['record_id'] in ids]
            if not found:continue
            assert len(found)==1
            template,q,width,active=t['coordinate'];k=key(t)
            names=['baseline',name]+([f'case{i:03d}.on-only',f'case{i:03d}.off-only'] if i in (47,79,111) else [])
            variants={n:measured(n,k) for n in names}
            current=variants[name];background=variants['baseline']
            distance=np.max(np.abs(offtracks-grid.score_hz[q]*factors[template]),axis=1) if off else np.asarray([])
            nearest=None
            if len(distance):
                j=int(distance.argmin());nearest=dict(distance_hz=float(distance[j]),record=off[j])
                assert distance[j]>20.
            assert not any(e['vetoed'] for e in current['adjacent_off'])
            assert all(not a['off_track_evidence'][mode]['matched'] for a in current['off_tracks'] for mode in ('same_hypothesis','local_track'))
            evidence.append(dict(case_index=i,record_id=found[0]['record_id'],coordinate=t['coordinate'],variants=variants,
                on_increment=[a-b for a,b in zip(current['on_scores'],background['on_scores'])],
                off_increment=[a-b for a,b in zip(current['off_scores'],background['off_scores'])],
                maximum_active_exact_OFF=max(current['off_scores'][e] for e in active),
                maximum_active_neighborhood_OFF=max(current['off_same_width_neighborhood_max'][e] for e in active),
                nearest_retained_OFF=nearest))
    assert len(evidence)==34
    groups=[]
    for i in cfg['selected_cases']:
        selected=[e for e in evidence if e['case_index']==i]
        groups.append(dict(case_index=i,members=len(selected),
            exact_OFF_max_range=[min(e['maximum_active_exact_OFF'] for e in selected),max(e['maximum_active_exact_OFF'] for e in selected)],
            neighborhood_OFF_max_range=[min(e['maximum_active_neighborhood_OFF'] for e in selected),max(e['maximum_active_neighborhood_OFF'] for e in selected)],
            members_with_neighborhood_OFF_at_least_5p5=sum(e['maximum_active_neighborhood_OFF']>=5.5 for e in selected),
            nearest_retained_OFF_distance_range_hz=[min(e['nearest_retained_OFF']['distance_hz'] for e in selected if e['nearest_retained_OFF']),max(e['nearest_retained_OFF']['distance_hz'] for e in selected if e['nearest_retained_OFF'])] if any(e['nearest_retained_OFF'] for e in selected) else None))
    write_sealed(OUT/'survivor_response_evidence.json',dict(source_result_sha256=result['result_sha256'],members=evidence,summary=groups))
    print(json.dumps(groups,indent=2))
if __name__=='__main__':run()
