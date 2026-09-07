"""M43W additive post-retention controls; no upstream detector changes."""
import copy
import numpy as np
from . import search_v0p6 as core

POLICIES=('neighbor9','off_window','epoch_confirmation','combined')
FLOOR=5.5

def off_window(values,grid,q,width,active):
    if width not in core.M37_SPECTRAL_WIDTHS or type(q) is not int or not 0<=q<grid.score_bin_count:
        raise ValueError('invalid retained coordinate')
    if values.dtype!=np.dtype('<f4') or values.shape!=(3,grid.support_bin_count) or not np.isfinite(values).all():
        raise ValueError('finite three-epoch full-support float32 values required')
    if tuple(active) not in core.M37_ACTIVITY_SUBSETS:
        raise ValueError('unknown activity subset')
    center=grid.score_slice.start+q;radius=width//2;lo=center-radius;hi=center+radius+1
    if lo<0 or hi>values.shape[1]:raise core.V0P6CoverageError('complete OFF neighborhood required')
    block=values[list(active),lo:hi]
    offsets=np.argmax(block,axis=1)
    peaks=block[np.arange(len(active)),offsets]
    return {'radius_proxy_bins':radius,'first_support_index':lo,'stop_support_index':hi,
        'active_epochs':list(active),'maxima':peaks.tolist(),
        'argmax_support_indices':(lo+offsets).tolist(),'vetoed':bool(np.any(peaks>=FLOOR))}

def apply_controls(audit,store,grid):
    evidence=[];cache={}
    for m in audit['members']:
        t=m['template_index'];w=m['spectral_width_channels'];active=m['active_epochs_zero_based']
        if (t,w) not in cache:
            values,identity=store.get('off',t,w)
            if identity!=store.expected_ids['off',t,w]:raise ValueError('OFF identity changed')
            cache[t,w]=values
        off=off_window(cache[t,w],grid,m['proxy_carrier_index'],w,active)
        on=np.asarray(m['epoch_values_at_proxy_carrier'],dtype='<f4')
        if on.shape!=(3,) or not np.isfinite(on).all():raise ValueError('invalid ON epoch evidence')
        confirm=bool(np.all(on[active]>=FLOOR))
        evidence.append({'record_id':m['record_id'],'off_window':off,'active_confirmation_passed':confirm,
            'minimum_active_ON_score':float(on[active].min())})
    outputs={}
    for p in POLICIES:
        a=copy.deepcopy(audit);a['confirmation_policy']=p
        for m,e in zip(a['members'],evidence):
            reasons=[]
            if p in ('off_window','combined') and e['off_window']['vetoed']:reasons.append('width_aware_OFF')
            if p in ('epoch_confirmation','combined') and not e['active_confirmation_passed']:reasons.append('active_epoch_below_5p5')
            m['base_physical_disposition']=m['physical_disposition'];m['m43w_rejections']=reasons
            if reasons and m['passes_evaluated_physical_vetoes']:
                m['passes_evaluated_physical_vetoes']=False;m['physical_disposition']='m43w_rejected_'+'_and_'.join(reasons)
        a['final_diagnostic_survivors']=sum(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] for m in a['members'])
        a['all_member_physical_survivors']=sum(m['passes_evaluated_physical_vetoes'] for m in a['members'])
        outputs[p]=a
    return outputs,evidence
