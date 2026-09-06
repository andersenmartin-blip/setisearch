"""M43T named mask experiment; M43R scoring and physical-stage arithmetic unchanged.

Uses the generic v0.6 algorithms with a new, explicitly identified catalogue.
It never creates or impersonates M37 epoch/cache provenance objects. Score
provenance is supplied and checked by the M43 store at each handoff.
"""
import hashlib
import math
import numpy as np
from . import search_v0p6 as core
from .adjacent_v0p6 import _finalize_single_adjacent_off_result
from .alias_v0p6 import match_receiver_frame_aliases
from .significance_v0p6 import evaluate_global_rank_significance
from .mask_m43t import build_mask,validate_scope


def digest(value):return hashlib.sha256(core.canonical_json_bytes(value)).hexdigest()


def catalogue_bridge(parent, indices, basis):
    """Add legacy presentation fields without changing Cartesian coordinates.

    `line_index` is a compatibility identifier, not a common physical line.
    `line_coefficient` is a nonnegative radius along each template's own phase.
    All calculations continue to use the exact original Cartesian coefficients.
    """
    indices=tuple(core._strict_int(i,'parent template') for i in indices)
    if not indices or tuple(sorted(set(indices)))!=indices or indices[0]<0 or indices[-1]>=len(parent):
        raise ValueError('ordered unique parent template selection required')
    parent_sha=core.template_bank_sha256(parent); bank=[]
    for local,i in enumerate(indices):
        p=parent[i];x=float(p['coefficient_x']);y=float(p['coefficient_y'])
        radius=math.hypot(x,y)
        if not math.isfinite(radius):raise ValueError('nonfinite Cartesian template')
        bank.append({'template_index':local,'line_index':i,'line_coefficient':radius,
            'projected_scale':radius,'phase_cycles':0. if radius==0 else math.atan2(y,x)/(2*math.pi)%1.,
            'coefficient_x':x,'coefficient_y':y,'m43_parent_template_index':i,
            'm43_parent_bank_sha256':parent_sha,'schema':'m43q-cartesian-compatibility-v1'})
    table=core.make_template_factor_table(basis,bank,expected_template_bank_sha256=core.template_bank_sha256(bank))
    original=np.stack([core.template_factors_from_basis(basis,parent[i]) for i in indices])
    if not np.array_equal(original.view('<u8'),table.factors.view('<u8')):
        raise ValueError('catalogue bridge changed physical factor bits')
    receipt={'schema':'m43q-catalogue-bridge-v1','parent_bank_sha256':parent_sha,
        'parent_template_indices':list(indices),'catalogue_sha256':table.template_bank_sha256,
        'factor_table_sha256':table.factor_table_sha256,'all_selected_factor_bits_preserved':True,
        'line_fields_are_compatibility_metadata':True}
    receipt['bridge_sha256']=digest(receipt)
    return bank,table,receipt


def checked_vectors(store,kind,t,width,grid,expected_id=None):
    values,identity=store.get(kind,t,width)
    expected_id=store.expected_ids[(kind,t,width)] if expected_id is None else expected_id
    if identity!=expected_id:raise ValueError('score handoff identity changed')
    if (values.dtype!=np.dtype('<f4') or values.shape!=(3,grid.support_bin_count)
            or values.flags.writeable or not np.isfinite(values).all()):
        raise ValueError('immutable finite full-support epoch vectors required')
    return values


def _ledger(window,kind,grid,threshold,bank,table,basis,scans,widths,cap):
    return core.ExhaustiveRetentionLedger(window_id=window,scan_kind=kind,grid=grid,
        threshold_certificate=threshold,maximum_records=cap,template_bank=bank,
        spectral_widths=widths,activity_subsets=core.M37_ACTIVITY_SUBSETS,
        expected_template_bank_sha256=table.template_bank_sha256,factor_basis_sha256=basis.basis_sha256,
        factor_basis_labels_sha256=basis.labels_sha256,scan_inventory_sha256=core.scan_inventory_sha256(scans),
        factor_row_selection_sha256=core.factor_row_selection_sha256(basis,scans,kind),
        factor_table_sha256=table.factor_table_sha256,epoch_count=3,minimum_active_epoch_snr=3.,stack_statistic='sum',
        maximum_record_canonical_bytes=16384,maximum_evidence_canonical_bytes=128_000_000)


def calibrate(*,policy,window,grid,bank,table,basis,scans,store,shifts,minimum_shift_bins,progress=lambda m:None):
    """Calibrate only the explicit supplied uninjected score inventory."""
    policy_sha256=validate_scope(window,policy)
    widths=core.M37_SPECTRAL_WIDTHS
    acc=core.CalibrationAccumulator.create(window_id=window,score_bin_count=grid.score_bin_count,
        template_count=len(bank),template_bank_sha256_value=table.template_bank_sha256,
        factor_basis_sha256_value=basis.basis_sha256,factor_basis_labels_sha256_value=basis.labels_sha256,
        scan_inventory_sha256_value=core.scan_inventory_sha256(scans),
        factor_row_selection_sha256_value=core.factor_row_selection_sha256(basis,scans,'on'),
        factor_table_sha256_value=table.factor_table_sha256,spectral_widths=widths,
        activity_subsets=core.M37_ACTIVITY_SUBSETS,minimum_active_epoch_snr=3.,stack_statistic='sum',
        scramble_shifts=shifts,minimum_shift_bins=minimum_shift_bins,
        expected_scramble_sha256=core.scramble_table_sha256(shifts))
    for t in range(len(bank)):
        arrays={w:checked_vectors(store,'on',t,w,grid) for w in widths}
        mask=build_mask(arrays.__getitem__,policy)[:,grid.score_slice]
        for wi,w in enumerate(widths):
            core.update_calibration(acc,arrays[w][:,grid.score_slice],template_index=t,width_index=wi,exclusion_mask=mask)
        progress(f'calibration template {t+1}/{len(bank)}')
    summary=acc.finalize()
    summary['mask_policy']=policy;summary['mask_policy_sha256']=policy_sha256
    return acc,summary


def execute(*,policy,window,grid,bank,table,basis,scans,store,calibration,threshold,receiver_factory,maximum_records=10000,progress=lambda message:None):
    """Reuse the baseline calibration; run both retention passes and physical stages.

    A qualification caller may use a tiny diagnostic null inventory. The return
    always identifies this entry point as diagnostic, with no scientific claim.
    Injected arrays cannot update the supplied sealed calibration.
    """
    core.validate_factor_basis_scan_inventory(basis,scans)
    core.validate_template_factor_table(table,basis,bank,expected_template_bank_sha256=core.template_bank_sha256(bank))
    policy_sha256=validate_scope(window,policy)
    widths=core.M37_SPECTRAL_WIDTHS
    expected_keys={(kind,t,w) for kind in ('on','off') for t in range(len(bank)) for w in widths}
    if set(store.expected_ids)!=expected_keys:raise ValueError('score store inventory incomplete or contains extras')
    expected_ids=dict(store.expected_ids)
    def get(kind,t,w):return checked_vectors(store,kind,t,w,grid,expected_ids[(kind,t,w)])
    input_root=digest([[kind,t,w,expected_ids[(kind,t,w)]] for kind,t,w in sorted(expected_keys)])
    acc=calibration
    core.validate_threshold_certificate(threshold)
    if threshold.global_null_maxima_sha256!=core.float64_vector_sha256(acc.null_maxima):
        raise ValueError('frozen threshold/null mismatch')
    masks={}; mask_hashes={}
    for kind in ('on','off'):
        for t in range(len(bank)):
            arrays={w:get(kind,t,w) for w in widths}
            mask=build_mask(arrays.__getitem__,policy)[:,grid.score_slice]
            masks[(kind,t)]=np.frombuffer(np.ascontiguousarray(mask).tobytes(),dtype=bool).reshape(mask.shape)
            mask_hashes[f'{kind}:{t}']=hashlib.sha256(masks[(kind,t)].tobytes()).hexdigest()
    ledgers={kind:_ledger(window,kind,grid,threshold,bank,table,basis,scans,widths,maximum_records) for kind in ('on','off')}
    records={};certs={}
    for kind in ('on','off'):
        for t in range(len(bank)):
            for wi,w in enumerate(widths):
                vectors=get(kind,t,w)[:,grid.score_slice]
                for subset in core.M37_ACTIVITY_SUBSETS:
                    ledgers[kind].add_hypothesis(vectors,subset,template=bank[t],width_index=wi,
                                                width_channels=w,exclusion_mask=masks[(kind,t)])
        records[kind]=ledgers[kind].finalize();certs[kind]=ledgers[kind].certificate()
        progress(f'{kind}: {len(records[kind])} diagnostic members retained without truncation')
    off_factors=core.factor_matrix_for_kind(table,basis,scans,'off')
    on_factors=core.factor_matrix_for_kind(table,basis,scans,'on')
    matched=core.match_retained_off_tracks(records['on'],certs['on'],records['off'],certs['off'],grid,off_factors,
        window_order=(window,),tolerance_hz=20.,maximum_bucket_entries=maximum_records,
        maximum_exact_candidate_visits=5_000_000,template_bank=bank)
    on_labels=tuple(str(scans[i]['label']) for i in core.m37_scan_indices_for_kind(scans,'on'))
    off_labels=tuple(str(scans[i]['label']) for i in core.m37_scan_indices_for_kind(scans,'off'))
    measured={};queries=[];plans=[];cache_inventory=[]
    # A named cache of already integrated, receipt-bound native-gather outputs.
    # These are M43 score-vector plans, not M37 native-cache attestations.
    for w in widths:
        for e,label in enumerate(off_labels):
            payload=hashlib.sha256()
            for t in range(len(bank)):
                payload.update(np.ascontiguousarray(get('off',t,w)[e,grid.score_slice]).tobytes())
            plan={'schema':'m43q-integrated-off-vector-cache-v1','scan':label,'width':w,
                'input_root':input_root,'catalogue_sha256':table.template_bank_sha256,
                'grid_sha256':core.proxy_carrier_grid_sha256(grid),'template_count':len(bank),
                'payload_layout':'template-major little-endian float32 score carriers'}
            plans.append(plan)
            cache_inventory.append({'spectral_width_channels':w,'epoch_zero_based':e,'scan_label':label,
                'cache_plan_sha256':digest(plan),'cache_payload_sha256':payload.hexdigest()})
    for ordinal,r in enumerate(records['on']):
        t=r['template_index'];w=r['spectral_width_channels'];q=r['proxy_carrier_index']
        values=get('off',t,w)[:,grid.score_slice]
        for e in r['active_epochs_zero_based']:
            measured[(ordinal,e)]=np.float32(values[e,q])
            queries.append({'record_id':r['record_id'],'epoch_zero_based':e,'paired_off_scan_label':off_labels[e],
                'template_index':t,'spectral_width_index':r['spectral_width_index'],'proxy_carrier_index':q})
    adjacent=_finalize_single_adjacent_off_result(cert=certs['on'],records=records['on'],measured=measured,
        on_labels=on_labels,off_labels=off_labels,floor=5.5,cache_inventory=cache_inventory,query_inventory=queries,
        factor_basis=basis,scan_definitions=scans,maximum_records=maximum_records,maximum_queries=3*maximum_records,
        maximum_evidence_canonical_bytes=128_000_000)
    signatures,receiver_receipt=receiver_factory(records['on'],bank,table)
    if set(signatures)!={r['record_id'] for r in records['on']}:raise ValueError('receiver query inventory differs')
    if receiver_receipt['signatures_sha256']!=digest(signatures):raise ValueError('receiver signature receipt changed')
    aliases=match_receiver_frame_aliases(matched['records'],certs['on'],grid,on_factors,signatures,
        off_match_certificate=matched['certificate'],single_adjacent_off_evidence=adjacent['evidence'],
        single_adjacent_off_certificate=adjacent['certificate'],
        expected_off_match_certificate_sha256=matched['certificate']['off_match_certificate_sha256'],
        expected_single_adjacent_off_certificate_sha256=adjacent['certificate']['single_adjacent_off_certificate_sha256'],
        window_order=(window,),track_tolerance_hz=20.,local_half_width_hz=100.,local_peak_snr_floor=5.5,
        minimum_shared_active_epochs=2,maximum_records=maximum_records,maximum_bucket_entries=maximum_records,
        maximum_identity_track_comparisons=5_000_000,maximum_distinct_candidate_visits_per_window=5_000_000,
        template_bank=bank)
    rank=evaluate_global_rank_significance(records['on'],certs['on'],threshold,acc.null_maxima,grid,bank)
    by_id={x['record_id']:x for x in rank['evidence']}
    if set(by_id)!={x['record_id'] for x in aliases['records']}:raise ValueError('final stage record identities disagree')
    decisions=[{'record_id':r['record_id'],'parent_template_index':bank[r['template_index']]['m43_parent_template_index'],
        'coefficient_x':bank[r['template_index']]['coefficient_x'],'coefficient_y':bank[r['template_index']]['coefficient_y'],
        'physical_disposition':r['member_disposition'],
        'passes_evaluated_physical_vetoes':r['member_disposition']=='pending_receiver_alias_evaluation',
        'inclusive_rank_p':by_id[r['record_id']]['inclusive_global_rank_p'],
        'meets_diagnostic_rank_cut':by_id[r['record_id']]['scientifically_eligible'],
        'scientific_candidate':False} for r in aliases['records']]
    result={'schema':'m43t-mask-comparison-diagnostic-v1','mask_policy':policy,'mask_policy_sha256':policy_sha256,'purpose':'bounded-native-injection-pilot',
        'input_inventory_sha256':input_root,'catalogue_sha256':table.template_bank_sha256,
        'factor_table_sha256':table.factor_table_sha256,'mask_sha256s':mask_hashes,
        'null_maxima':acc.null_maxima.tolist(),'null_count':len(acc.null_maxima),
        'threshold':threshold.as_record(),'retained':records,'retention_certificates':certs,
        'off_track':matched,'adjacent_off':adjacent,'off_vector_cache_plans':plans,
        'receiver_signatures':signatures,'receiver_receipt':receiver_receipt,'receiver_alias':aliases,'rank':rank,'decisions':decisions,
        'scientific_candidate_selection_authorized':False,'fresh_null_calibration':True,
        'native_injection_recovery_measured':False}
    result['result_sha256']=digest(result)
    return result
