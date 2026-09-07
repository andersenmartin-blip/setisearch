"""M43X strongest-active-epoch-excluded additive confirmation."""
import copy
import math
import numpy as np
from . import search_v0p6 as core

POLICIES=('neighbor9','epoch_confirmation','remaining_aggregate')
FLOOR=5.5

def remaining_evidence(values,active):
    v=np.asarray(values,dtype=np.float64)
    if v.shape!=(3,) or not np.isfinite(v).all():
        raise ValueError('three finite epoch scores required')
    if tuple(active) not in core.M37_ACTIVITY_SUBSETS:
        raise ValueError('canonical activity subset required')
    # np.argmax takes the first maximum: canonical ascending epoch tie break.
    selected=v[list(active)];dropped=int(np.argmax(selected))
    remaining=[e for i,e in enumerate(active) if i!=dropped]
    total=float(np.sum(v[remaining],dtype=np.float64))
    statistic=total/math.sqrt(len(remaining))
    return dict(active_epochs=list(active),excluded_epoch=int(active[dropped]),
        remaining_epochs=remaining,remaining_sum=total,remaining_score=statistic,
        remaining_passed=statistic>=FLOOR,
        minimum_active_ON_score=float(selected.min()),
        active_confirmation_passed=bool(np.all(selected>=FLOOR)))

def apply_controls(audit,store,grid):
    evidence=[]
    for m in audit['members']:
        t=m['template_index'];w=m['spectral_width_channels'];q=m['proxy_carrier_index']
        if type(q) is not int or not 0<=q<grid.score_bin_count:
            raise ValueError('invalid retained coordinate')
        v,identity=store.get('on',t,w)
        if identity!=store.expected_ids['on',t,w]:raise ValueError('ON identity changed')
        expected=v[:,grid.score_slice.start+q]
        if not np.array_equal(expected,np.asarray(m['epoch_values_at_proxy_carrier'],dtype='<f4')):
            raise ValueError('retained ON scores differ from source')
        e=remaining_evidence(m['epoch_values_at_proxy_carrier'],m['active_epochs_zero_based'])
        evidence.append(dict(record_id=m['record_id'],**e))
    outputs={}
    for p in POLICIES:
        a=copy.deepcopy(audit);a['confirmation_policy']=p
        for m,e in zip(a['members'],evidence):
            reasons=[]
            if p=='epoch_confirmation' and not e['active_confirmation_passed']:
                reasons.append('active_epoch_below_5p5')
            if p=='remaining_aggregate' and not e['remaining_passed']:
                reasons.append('remaining_aggregate_below_5p5')
            m['base_physical_disposition']=m['physical_disposition'];m['m43x_rejections']=reasons
            if reasons and m['passes_evaluated_physical_vetoes']:
                m['passes_evaluated_physical_vetoes']=False
                m['physical_disposition']='m43x_rejected_'+'_and_'.join(reasons)
        a['final_diagnostic_survivors']=sum(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] for m in a['members'])
        a['all_member_physical_survivors']=sum(m['passes_evaluated_physical_vetoes'] for m in a['members'])
        outputs[p]=a
    return outputs,evidence
