"""Read original retained B maps/dispositions; never generate or rescore power."""
import csv,hashlib,json,math
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write_csv(name,rows):
    assert rows
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def loc(h,t):
    oracle=t['flux_by_scan'][h['scan_id']]['injection_oracle_width_channels'];df=abs(h['df_hz'])
    delta_f=h['reference_frequency_hz']-t['reference_frequency_hz'];dd=h['drift_hz_s']-t['drift_hz_s']
    e=[(delta_f+dd*h[k])/df for k in ('scan_first_time_from_tref_s','scan_last_time_from_tref_s')]
    tol=2+max(h['width_channels'],oracle)/2
    return max(map(abs,e))<=tol,e,tol

def main():
    frozen={'pilot_engine_20261008/detector.py':'1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45','pilot_controls_20261008/generator.py':'3864bd49766f71771ac48cb517eaa516fab0768d3c39f2ed8f07b8f1eed21693','pilot_controls_20261008/control_contract.json':'44854605dbbe40a2c8aa7805433437e7ef03de31db3c76326d235baa88d7406c'}
    for p,h in frozen.items(): assert sha(ROOT/p)==h
    contract=read(ROOT/'pilot_controls_20261008/control_contract.json'); summaries=[];scanrows=[];transientrows=[];witnessrows=[];nearrows=[];bindings=[]
    for i in range(86,142):
        p=ROOT/f'results/radio_pilot_val_b_20261008/case_{i:03d}';c=read(p/'case_definition.json');t=read(p/'truth.json');hlist=read(p/'all_ON_threshold_carriers.json');o=read(p/'outcome.json');r=read(p/'localized_recovery.json');metas=read(p/'scan_map_metadata.json')
        expected='noise' if i<118 else ('single_row_transient' if i<130 else 'near_off_contamination'); assert c['family']==expected and c['case_id']==t['case_id']==o['case_id']
        manifest=read(p/'artifact_manifest.json');marker=read(p/'COMMITTED.json');assert sha(p/'artifact_manifest.json')==marker['artifact_manifest_SHA256'] and marker['status']=='COMPLETED_CASE_ONLY'
        for name,m in manifest.items(): assert (p/name).stat().st_size==m['size_bytes'] and sha(p/name)==m['SHA256'],(i,name)
        bindings.append({'directory':str(p.relative_to(ROOT)),'manifest_sha256':sha(p/'artifact_manifest.json'),'COMMITTED_sha256':sha(p/'COMMITTED.json'),'verified_artifact_count':len(manifest),'case_definition_sha256':sha(p/'case_definition.json'),'truth_sha256':sha(p/'truth.json'),'raw_hits_sha256':sha(p/'all_ON_threshold_carriers.json'),'map_metadata_sha256':sha(p/'scan_map_metadata.json')})
        maps=[]
        for scanindex,m in enumerate(metas):
            with np.load(p/m['array_file'],allow_pickle=False) as z:
                k=int(np.argmax(z['maximum_robust_box_track_score']));score=float(z['maximum_robust_box_track_score'][k]);threshold=10 if m['role']=='ON' else 8
                row={'case_id':c['case_id'],'family':c['family'],'noise_law':c['noise_law'],'scan_index':scanindex,'scan_id':m['scan_id'],'role':m['role'],'is_injected_ON':m['scan_id'] in t['active_ON_scan_ids'],'maximum_original_robust_score':score,'winner_carrier':k,'winner_frequency_hz':float(z['frequency_hz_at_tref'][k]),'winner_drift_hz_s':float(z['winning_drift_hz_s'][k]),'winner_width_channels':int(z['winning_width_channels'][k]),'threshold':threshold,'margin_relative_to_threshold':score-threshold}
                scanrows.append(row);maps.append(row)
                if m['role']=='ON':
                    indices=np.flatnonzero(z['maximum_robust_box_track_score']>=10).tolist();original=[h for h in hlist if h['scan_id']==m['scan_id']]
                    assert indices==[h['reference_carrier_index'] for h in original]
                    for h in original:
                        j=h['reference_carrier_index'];assert h['ON_robust_score']==float(z['maximum_robust_box_track_score'][j]) and h['reference_frequency_hz']==float(z['frequency_hz_at_tref'][j]) and h['drift_hz_s']==float(z['winning_drift_hz_s'][j]) and h['width_channels']==int(z['winning_width_channels'][j])
        survivors=[h for h in hlist if h['disposition']=='SURVIVOR_EXPLORATORY'];assert len(hlist)==o['ON_threshold_carrier_count'] and len(survivors)==o['survivor_count'] and o['data_integrity_ok'] and o['failure'] is None
        active=t['active_ON_scan_ids'];localized=[];final=[]
        for scan in active:
            matched=[h for h in hlist if h['scan_id']==scan and loc(h,t)[0]];surv=[h for h in matched if h['disposition']=='SURVIVOR_EXPLORATORY'];saved=r['per_active_ON_scan'][scan]
            assert len(matched)==saved['pre_OFF_localized_count'] and len(surv)==saved['final_localized_count'];localized+=matched;final+=surv
        summary={'case_index':i,'case_id':c['case_id'],'family':c['family'],'noise_law':c['noise_law'],'eligibility_case':c['eligibility_case'],'active_ON_scans':','.join(active),'ideal_level':c.get('nominal_ideal_box_score'),'intrinsic_width_channels':c.get('intrinsic_width_channels'),'input_drift_hz_s':c.get('drift_hz_s'),'input_reference_native_offset':c.get('reference_native_offset'),'input_transient_row':c.get('transient_row'),'diagnostic_OFF_offset_native_channels':c.get('diagnostic_off_frequency_offset_channels'),'ON_threshold_carriers':len(hlist),'surviving_carriers':len(survivors),'localized_initial_carriers':len(localized),'localized_final_carriers':len(final),'initial_localized_recovery':bool(localized),'final_localized_recovery':bool(final),'maximum_active_ON_score':max([x['maximum_original_robust_score'] for x in maps if x['is_injected_ON']],default=None),'maximum_any_ON_score':max(x['maximum_original_robust_score'] for x in maps if x['role']=='ON'),'miss_stage':('NO_INJECTED_ON' if not active else ('LOCALIZED_SURVIVOR' if final else ('OFF_VETO_LOSS' if localized else ('NO_ON_THRESHOLD_HIT' if not any(h['scan_id'] in active for h in hlist) else 'NO_LOCALIZED_THRESHOLD_HIT'))))}
        summaries.append(summary)
        for h in hlist:
            comps=h['OFF_comparisons'];assert len(comps)==3
            assert h['disposition']==('OFF_MATCHED' if any(v['veto'] for v in comps) else 'SURVIVOR_EXPLORATORY')
            for v in comps:
                if v['veto']: assert not v['family_exhausted'] and v['witness'] is not None and v['witness']['OFF_robust_score']>=8
                else: assert v['family_exhausted'] and v['witness'] is None and v['maximum_checked_score']<8
            if expected=='single_row_transient':
                localized_flag,error,tol=loc(h,t) if h['scan_id'] in active else (False,[None,None],None)
                transientrows.append({'case_id':c['case_id'],'carrier':h['reference_carrier_index'],'ON_scan':h['scan_id'],'ON_score':h['ON_robust_score'],'winning_width_channels':h['width_channels'],'winning_drift_hz_s':h['drift_hz_s'],'frequency_hz_at_tref':h['reference_frequency_hz'],'disposition':h['disposition'],'truth_localized':localized_flag,'first_ON_truth_error_channel_widths':error[0],'last_ON_truth_error_channel_widths':error[1],'truth_tolerance_channel_widths':tol,'all_OFF_families_exhausted':all(v['family_exhausted'] for v in comps),'maximum_original_checked_OFF_score':max(v['maximum_checked_score'] for v in comps)})
            if expected!='near_off_contamination':continue
            injected_ON_index=c['active_scan_indices'][0];following=metas[injected_ON_index+1];native_offset=c['diagnostic_off_frequency_offset_channels'];off_true_f=t['reference_frequency_hz']+native_offset*h['df_hz']
            localized_flag,error,tol=loc(h,t) if h['scan_id'] in active else (False,[None,None],None)
            nearrows.append({'case_id':c['case_id'],'carrier':h['reference_carrier_index'],'ON_scan':h['scan_id'],'ON_score':h['ON_robust_score'],'ON_width_channels':h['width_channels'],'ON_drift_hz_s':h['drift_hz_s'],'ON_frequency_hz_at_tref':h['reference_frequency_hz'],'truth_localized':localized_flag,'disposition':h['disposition'],'declared_OFF_native_offset_channels':native_offset,'declared_OFF_frequency_shift_hz':native_offset*h['df_hz'],'following_contaminated_OFF':following['scan_id'],'veto_OFF_scans':','.join(v['scan_id'] for v in comps if v['veto'])})
            for v in comps:
                if not v['veto']:continue
                w=v['witness'];m=next(m for m in metas if m['scan_id']==v['scan_id']);df=max(abs(h['df_hz']),abs(m['df_hz']));allow=((h['width_channels']+w['width_channels'])/2+2)*df
                ep=[w['reference_frequency_hz']-h['reference_frequency_hz']+(w['drift_hz_s']-h['drift_hz_s'])*h[key] for key in ('scan_first_time_from_tref_s','scan_last_time_from_tref_s')]
                assert max(map(abs,ep))<=allow+1e-6
                assert abs(ep[0]-w['ON_first_endpoint_error_hz'])<1e-6 and abs(ep[1]-w['ON_last_endpoint_error_hz'])<1e-6 and abs(allow-w['endpoint_tolerance_hz'])<1e-6
                # Geometrical comparison with the declared diagnostic OFF line;
                # only its following OFF actually contains that injected line.
                offe=[(w['reference_frequency_hz']-off_true_f+(w['drift_hz_s']-c['drift_hz_s'])*m[key])/df for key in ('scan_first_time_from_tref_s','scan_last_time_from_tref_s')]
                offoracle=t['flux_by_scan'][active[0]]['injection_oracle_width_channels'];offtol=2+max(w['width_channels'],offoracle)/2
                witnessrows.append({'case_id':c['case_id'],'ON_carrier':h['reference_carrier_index'],'ON_truth_localized':localized_flag,'ON_score':h['ON_robust_score'],'ON_width_channels':h['width_channels'],'ON_drift_hz_s':h['drift_hz_s'],'OFF_scan':v['scan_id'],'is_following_contaminated_OFF':v['scan_id']==following['scan_id'],'original_OFF_witness_score':w['OFF_robust_score'],'original_witness_frequency_hz':w['reference_frequency_hz'],'original_witness_drift_hz_s':w['drift_hz_s'],'original_witness_width_channels':w['width_channels'],'OFF_match_tolerance_channel_widths':allow/df,'first_ON_compatibility_error_channel_widths':ep[0]/df,'last_ON_compatibility_error_channel_widths':ep[1]/df,'declared_OFF_frequency_shift_hz':native_offset*h['df_hz'],'first_OFF_declared_line_error_channel_widths':offe[0],'last_OFF_declared_line_error_channel_widths':offe[1],'illustrative_OFF_line_localization_tolerance_channel_widths':offtol,'witness_geometrically_localized_to_declared_following_OFF_line':v['scan_id']==following['scan_id'] and max(map(abs,offe))<=offtol,'checked_template_count_before_stop':v['checked_valid_compatible_templates'],'original_partial_maximum_checked_score':v['maximum_checked_score'],'family_exhausted':v['family_exhausted']})
    assert len(summaries)==56 and len(scanrows)==336
    transient=[s for s in summaries if s['family']=='single_row_transient'];near=[s for s in summaries if s['family']=='near_off_contamination'];noise=[s for s in summaries if s['family']=='noise']
    assert len(transient)==12 and len(near)==12 and len(noise)==32
    assert sum(s['final_localized_recovery'] for s in transient)==12 and sum(s['initial_localized_recovery'] for s in near)==11 and sum(s['final_localized_recovery'] for s in near)==0
    assert all(s['ON_threshold_carriers']==s['surviving_carriers']==0 for s in noise)
    noise_groups=[]
    for law in contract['noise_laws']:
        cells=[s for s in noise if s['noise_law']==law];ons=[s for s in scanrows if s['family']=='noise' and s['noise_law']==law and s['role']=='ON'];assert len(cells)==8 and len(ons)==24
        noise_groups.append({'noise_law':law,'cadences':8,'ON_scans':24,'ON_threshold_carriers':0,'surviving_cadences':0,'minimum_ON_global_maximum':min(s['maximum_original_robust_score'] for s in ons),'median_ON_global_maximum':float(np.median([s['maximum_original_robust_score'] for s in ons])),'maximum_ON_global_maximum':max(s['maximum_original_robust_score'] for s in ons),'minimum_margin_below_ON10':10-max(s['maximum_original_robust_score'] for s in ons),'hypothetical_iid_same_law_95percent_zero_of8_upper_bound':1-math.pow(.05,1/8),'hypothetical_bound_is_not_calibrated_sky_FAP':True})
    write_csv('diagnostic_cases.csv',summaries);write_csv('saved_scan_maxima.csv',scanrows);write_csv('transient_original_carriers.csv',transientrows);write_csv('near_OFF_original_carriers.csv',nearrows);write_csv('near_OFF_original_witnesses.csv',witnessrows);write_csv('noise_law_coverage.csv',noise_groups)
    evidence={'status':'COMPLETE_RETAINED_DIAGNOSTIC_ANALYSIS','source_commit':'13131757641c06d7bfcb10790a79811c750b1178','original_code_sha256':frozen,'original_case_bindings':bindings,'cases':summaries,'scan_maxima':scanrows,'noise_law_groups':noise_groups,'counts':{'cases':56,'maps':336,'artifact_hashes':sum(x['verified_artifact_count'] for x in bindings),'transient_cases':12,'transient_localized_surviving_cases':12,'transient_original_carriers':len(transientrows),'transient_final_carriers':sum(s['surviving_carriers'] for s in transient),'transient_truth_localized_final_carriers':sum(s['localized_final_carriers'] for s in transient),'near_OFF_cases':12,'near_OFF_initial_localized_cases':11,'near_OFF_final_localized_cases':0,'near_OFF_original_carriers':len(nearrows),'near_OFF_original_veto_witnesses':len(witnessrows),'near_OFF_witnesses_in_following_contaminated_OFF':sum(s['is_following_contaminated_OFF'] for s in witnessrows),'near_OFF_witnesses_localized_to_declared_OFF_line':sum(s['witness_geometrically_localized_to_declared_following_OFF_line'] for s in witnessrows),'noise_cases':32,'noise_ON_scans':96,'noise_ON_carriers':0},'qualification':False,'new_draws':0,'new_scores':0,'new_telescope_payloads':0,'A_B_remain_FAIL_CLOSED':True,'witness_localization_is_descriptive_new_geometry_not_original_gate':True}
    (OUT/'DIAGNOSTIC_EVIDENCE.json').write_text(json.dumps(evidence,indent=2)+'\n')
    # Two compact scientific plots from original saved maxima and dispositions.
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for ax,family,title in [(axes[0],'single_row_transient','One-row ON injections: all 12 survive'),(axes[1],'near_off_contamination','Nearby OFF injections: 11 detected, all vetoed')]:
        selected=[s for s in summaries if s['family']==family];values=[s['maximum_active_ON_score'] for s in selected]
        ax.bar(range(12),values,color=['#2563eb' if s['final_localized_recovery'] else '#c2410c' for s in selected]);ax.axhline(10,color='black',ls='--',label='Frozen ON10');ax.set_xticks(range(12),[s['case_id'][-3:] for s in selected],rotation=45);ax.set(xlabel='Original case suffix',ylabel='Saved active-ON global maximum score',title=title);ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    fig.savefig(OUT/'diagnostic_ON_maxima.png',dpi=150);fig.savefig(OUT/'diagnostic_ON_maxima.pdf');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.5),layout='constrained')
    for k,g in enumerate(noise_groups):
        values=[s['maximum_original_robust_score'] for s in scanrows if s['family']=='noise' and s['noise_law']==g['noise_law'] and s['role']=='ON'];x=np.linspace(k-.18,k+.18,len(values));ax.scatter(x,values,s=20,label=f"{g['noise_law']} (8 cadences / 24 ON)")
    ax.axhline(10,color='black',ls='--',label='Frozen ON10');ax.set_xticks(range(4),[g['noise_law'] for g in noise_groups],fontsize=8);ax.set(ylabel='Saved ON global maximum robust score',title='32 retained synthetic noise controls: no ON threshold carrier');ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8,loc='upper center',ncol=2)
    fig.savefig(OUT/'noise_retained_maxima.png',dpi=150);fig.savefig(OUT/'noise_retained_maxima.pdf');plt.close(fig)
    print(json.dumps(evidence['counts']));print(json.dumps({'near_OFF_misses':[s for s in near if not s['initial_localized_recovery']],'noise_groups':noise_groups}))
if __name__=='__main__':main()
