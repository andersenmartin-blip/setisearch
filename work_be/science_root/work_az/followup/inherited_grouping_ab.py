"""Separate Python interval/ranking implementation; no production selector imports."""
import math
import numpy as np


def group_catalog(t, scopes):
    n=len(t['seed_ess']); full=np.all(t['forced_status']==1,axis=1)
    flags=t['narrow_off_flag']; eligible=full & ~flags.any(axis=1)
    es=t['forced_center_ess'][:,[0,2,4]]; ns=t['forced_max_ess'][:,[0,2,4]]
    en=(es>=10.).sum(axis=1); nn=(ns>=10.).sum(axis=1)
    if not np.array_equal(flags[:,[1,3,5]], t['forced_max_ess'][:,[1,3,5]]>=5.): raise ValueError('OFF flag mismatch')
    exact=eligible&(en==3); inclusive=eligible&(nn==3)
    if np.any(exact & ~inclusive): raise ValueError('Exact3 outside neighborhood3')
    baseline={'ON_catalog_rows':n,'fully_supported_rows':int(full.sum()),'any_OFF_flag_rows':int(flags.any(axis=1).sum()),'exact_center_all3ON_noOFF_rows':int(exact.sum()),'inclusive_neighborhood_all3ON_noOFF_rows':int(inclusive.sum()),'neighborhood_only_all3ON_noOFF_rows':int((inclusive&~exact).sum())}
    reference=scopes[0]; step=8./838.; members={}
    def rep(seed, intermittent):
        r={'source_scan':int(t['seed_source_scan'][seed]),'channel_at_midpoint':int(t['seed_channel_at_midpoint'][seed]),'width_channels':int(t['seed_width_channels'][seed]),'drift_index':int(t['seed_drift_index'][seed]),'drift_hz_s':float(t['seed_drift_hz_s'][seed]),'frequency_at_midpoint_mhz':float(t['seed_frequency_at_midpoint_mhz'][seed]),'source_ESS':float(t['seed_ess'][seed]),'projected_centers_six_scans':t['predicted_center'][seed].astype(int).tolist(),'forced_center_ESS_six_scans':t['forced_center_ess'][seed].tolist(),'forced_neighborhood_ESS_six_scans':t['forced_max_ess'][seed].tolist(),'narrow_OFF_flags_six_scans':flags[seed].tolist(),'broad_context_max_ESS_six_scans':t['broad_max_ess'][seed].tolist()}
        if intermittent:r['exact_ON_threshold_passing_scans']=[j for j in (0,2,4) if t['forced_center_ess'][seed,j]>=10.]
        return r
    def build(label, rows, intermittent, ess):
        intervals={}
        for seed in rows:
            source=int(t['seed_source_scan'][seed]); width=int(t['seed_width_channels'][seed])
            gap=(reference['tref_midpoint_mjd']-scopes[source]['tref_midpoint_mjd'])*86400
            radius=math.ceil(1+.5*step*abs(gap)/abs(reference['df_hz']))
            center=int(t['predicted_center'][seed,0]); intervals[int(seed)]=(center-width//2-radius, center+width//2+radius, source)
        order=sorted((int(seed) for seed in rows),key=lambda seed:(*intervals[seed],seed))
        components=[]; current=[]; end=None
        for seed in order:
            lo,hi,_=intervals[seed]
            if end is None or lo>end:
                if current:components.append(current)
                current=[seed];end=hi
            else:current.append(seed);end=max(end,hi)
        if current:components.append(current)
        groups=[]
        for gid, component in enumerate(components):
            if intermittent:
                seed=max(component,key=lambda seed:(float(np.max(es[seed])),float(sorted(es[seed])[-2]),float(t['seed_ess'][seed]),-int(t['seed_source_scan'][seed]),-seed))
            else:
                seed=max(component,key=lambda seed:(float(np.min(ess[seed])),float(t['seed_ess'][seed]),-int(t['seed_source_scan'][seed]),-seed))
            lo=min(intervals[v][0] for v in component);hi=max(intervals[v][1] for v in component)
            widths=t['seed_width_channels'][component]; sources=t['seed_source_scan'][component]
            g={'class':label,'group_id':gid,'template_rows':len(component),'reference_channel_interval_inclusive':[lo,hi],'reference_frequency_limits_mhz':sorted([reference['fch1_mhz']+lo*reference['df_hz']/1e6,reference['fch1_mhz']+hi*reference['df_hz']/1e6]),'interval_span_native_channels':hi-lo+1,'width_counts':{str(int(w)):int((widths==w).sum()) for w in np.unique(widths)},'distinct_drift_indices':len(np.unique(t['seed_drift_index'][component])),'source_scan_counts':{str(s):int((sources==s).sum()) for s in (0,2,4)},'representative_global_seed_row':seed,'representative_minimum_ON_ESS':float(np.min(ess[seed])),'representative':rep(seed,intermittent)}
            if intermittent:g.update(exact_ON_count=int(en[seed]),representative_peak_active_ON_ESS=float(max(es[seed])),representative_second_ON_ESS=float(sorted(es[seed])[-2]))
            groups.append(g); namespace='intermittent__' if intermittent else 'all3ON__';members[namespace+label+'_'+str(gid)]=np.asarray(component,dtype=np.int64)
        return groups
    all3=[];s3=[]
    for label,mask,score in [('exact_center',exact,es),('neighborhood_only',inclusive&~exact,ns)]:
        table=build(label,np.flatnonzero(mask),False,score);baseline[label+'_frequency_group_count']=len(table)
        ranked=sorted(table,key=lambda g:(-g['template_rows'],-g['representative_minimum_ON_ESS'],g['reference_channel_interval_inclusive'][0],g['group_id']))
        for g in ranked:
            if len(s3)==3:break
            lo,hi=g['reference_channel_interval_inclusive']
            if label=='neighborhood_only' and any(max(lo,x['reference_channel_interval_inclusive'][0])<=min(hi,x['reference_channel_interval_inclusive'][1]) for x in s3):continue
            s3.append(g)
        all3.extend(table)
    counts=dict(baseline);counts['fully_supported_noOFF_rows']=int(eligible.sum())
    for k in range(4):
        counts[f'fully_supported_noOFF_exact_ON_count_{k}_rows']=int((eligible&(en==k)).sum())
        counts[f'fully_supported_noOFF_neighborhood_ON_count_{k}_rows']=int((eligible&(nn==k)).sum())
    intermittent=[]
    for k in (1,2,3):
        table=build(f'exact_{k}_ON',np.flatnonzero(eligible&(en==k)),True,es)
        counts[f'exact_{k}_ON_frequency_group_count']=len(table);intermittent.extend(table)
    ranked=sorted([g for g in intermittent if g['exact_ON_count'] in (1,2)],key=lambda g:(-g['representative_peak_active_ON_ESS'],-g['exact_ON_count'],-g['representative_second_ON_ESS'],-g['template_rows'],g['reference_channel_interval_inclusive'][0],g['group_id']))
    si=[]
    for g in ranked:
        if len(si)==3:break
        lo,hi=g['reference_channel_interval_inclusive']
        if any(max(lo,x['reference_channel_interval_inclusive'][0])<=min(hi,x['reference_channel_interval_inclusive'][1]) for x in si):continue
        si.append(g)
    counts['selected_intermittent_frequency_groups']=len(si)
    selected=[]
    for origin, groups in [('all3ON',s3),('intermittent1or2ON',si)]:
        for g in groups:
            if len(selected)==3:break
            lo,hi=g['reference_channel_interval_inclusive']
            if any(max(lo,x['group']['reference_channel_interval_inclusive'][0])<=min(hi,x['group']['reference_channel_interval_inclusive'][1]) for x in selected):continue
            selected.append({'origin':origin,'group':g})
    return {'all3ON_counts':baseline,'all3ON_groups':all3,'intermittent_counts':counts,'intermittent_groups':intermittent,'original_all3ON_selected':s3,'original_intermittent_selected':si,'selected':selected},members
