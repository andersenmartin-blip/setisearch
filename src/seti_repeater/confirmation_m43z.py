"""M43Z composition of unchanged M43W OFF windows and M43X remaining scores."""
import copy
import numpy as np
from .confirmation_m43w import off_window
from .confirmation_m43x import remaining_evidence
POLICIES=('neighbor9','off_window','remaining_aggregate','combined')

def apply_controls(audit,store,grid):
    evidence=[]
    for m in audit['members']:
        t,q,w=m['template_index'],m['proxy_carrier_index'],m['spectral_width_channels']
        active=m['active_epochs_zero_based'];on,oid=store.get('on',t,w);off,fid=store.get('off',t,w)
        if oid!=store.expected_ids['on',t,w] or fid!=store.expected_ids['off',t,w]:raise ValueError('changed score identity')
        if type(q) is not int or not 0<=q<grid.score_bin_count:raise ValueError('invalid retained carrier')
        if not np.array_equal(on[:,grid.score_slice.start+q],np.asarray(m['epoch_values_at_proxy_carrier'],dtype='<f4')):
            raise ValueError('retained ON scores differ from source')
        evidence.append(dict(record_id=m['record_id'],off_window=off_window(off,grid,q,w,active),
            remaining=remaining_evidence(m['epoch_values_at_proxy_carrier'],active)))
    outputs={}
    for p in POLICIES:
        a=copy.deepcopy(audit);a['confirmation_policy']=p
        for m,e in zip(a['members'],evidence):
            reasons=[]
            if p in ('off_window','combined') and e['off_window']['vetoed']:reasons.append('width_aware_OFF')
            if p in ('remaining_aggregate','combined') and not e['remaining']['remaining_passed']:reasons.append('remaining_aggregate_below_5p5')
            m['base_physical_disposition']=m['physical_disposition'];m['m43z_rejections']=reasons
            if reasons and m['passes_evaluated_physical_vetoes']:
                m['passes_evaluated_physical_vetoes']=False;m['physical_disposition']='m43z_rejected_'+'_and_'.join(reasons)
        a['final_diagnostic_survivors']=sum(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] for m in a['members'])
        a['all_member_physical_survivors']=sum(m['passes_evaluated_physical_vetoes'] for m in a['members'])
        outputs[p]=a
    return outputs,evidence
