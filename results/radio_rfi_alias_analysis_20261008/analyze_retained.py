"""Analyze saved paths and scores only; no scoring/generator imports."""
import csv, hashlib, json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
def read(p): return json.loads(p.read_text())
def save_csv(name,rows):
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    original_hashes={'pilot_engine_20261008/detector.py':'1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45','pilot_controls_20261008/generator.py':'3864bd49766f71771ac48cb517eaa516fab0768d3c39f2ed8f07b8f1eed21693','pilot_controls_20261008/control_contract.json':'44854605dbbe40a2c8aa7805433437e7ef03de31db3c76326d235baa88d7406c'}
    for p,h in original_hashes.items(): assert sha(ROOT/p)==h,(p,sha(ROOT/p))
    survivors=[]; offs=[]; tracks=[]; global_pairs=[]; context=[]; bindings=[]
    for serial in (64,65):
        p=ROOT/f'results/radio_pilot_val_b_20261008/case_{serial:03d}'
        manifest=read(p/'artifact_manifest.json'); marker=read(p/'COMMITTED.json')
        assert sha(p/'artifact_manifest.json')==marker['artifact_manifest_SHA256']
        assert marker['status']=='COMPLETED_CASE_ONLY'
        for fn,r in manifest.items(): assert (p/fn).stat().st_size==r['size_bytes'] and sha(p/fn)==r['SHA256'],fn
        bindings.append({'case_directory':str(p.relative_to(ROOT)),'artifact_manifest_sha256':sha(p/'artifact_manifest.json'),'verified_artifact_count':len(manifest),'manifest':manifest})
        truth=read(p/'truth.json'); case=read(p/'case_definition.json'); recovery=read(p/'localized_recovery.json'); hits=read(p/'all_ON_threshold_carriers.json'); metas=read(p/'scan_map_metadata.json')
        maps=[]
        for meta in metas:
            with np.load(p/meta['array_file'],allow_pickle=False) as z: maps.append({**meta,**{k:z[k].copy() for k in z.files}})
        leak=[h for h in hits if h['disposition']=='SURVIVOR_EXPLORATORY']
        assert len(leak)==(13 if serial==64 else 1)
        assert truth['drift_hz_s']==-4 and case['intrinsic_width_channels']==1
        assert all(h['scan_id']=='epoch1_on' and h['width_channels']==33 for h in leak)
        assert not recovery['final_any_active_recovery'] and recovery['pre_OFF_all_active_recovery']
        context.append({'case_id':truth['case_id'],'survivors':len(leak),'original_ON_threshold_carriers':len(hits),'localized_recovery':recovery,'global_scan_maxima':[]})
        for m in maps:
            k=int(np.argmax(m['maximum_robust_box_track_score']))
            context[-1]['global_scan_maxima'].append({'scan_id':m['scan_id'],'role':m['role'],'maximum_retained_score':float(m['maximum_robust_box_track_score'][k]),'reference_carrier_index':k,'reference_frequency_hz':float(m['frequency_hz_at_tref'][k]),'winning_drift_hz_s':float(m['winning_drift_hz_s'][k]),'winning_width_channels':int(m['winning_width_channels'][k])})
        for h in leak:
            df=abs(h['df_hz']); first=h['scan_first_time_from_tref_s']; last=h['scan_last_time_from_tref_s']; span=last-first
            dd=h['drift_hz_s']-truth['drift_hz_s']; delta_f=h['reference_frequency_hz']-truth['reference_frequency_hz']
            max_tol=(h['width_channels']+33)/2+2; bound=2*max_tol*df/span
            best_possible_error=abs(dd)*span/(2*df)
            comps=h['OFF_comparisons']; assert len(comps)==3 and all(c['family_exhausted'] and not c['veto'] and c['witness'] is None and c['maximum_checked_score']<8 for c in comps)
            row={'case_id':truth['case_id'],'carrier':h['reference_carrier_index'],'ON_scan':h['scan_id'],'ON_score':h['ON_robust_score'],'ON_margin_above_10':h['ON_robust_score']-10,'frequency_hz_at_tref':h['reference_frequency_hz'],'drift_hz_s':h['drift_hz_s'],'width_channels':h['width_channels'],'truth_drift_difference_hz_s':dd,'ON_span_s':span,'largest_OFF_tolerance_channel_widths':max_tol,'maximum_compatible_drift_difference_hz_s':bound,'drift_exclusion_margin_hz_s':abs(dd)-bound,'minimum_possible_max_endpoint_error_channel_widths':best_possible_error,'minimum_possible_endpoint_excess_channel_widths':best_possible_error-max_tol,'truth_first_ON_error_channel_widths':(delta_f+dd*first)/df,'truth_last_ON_error_channel_widths':(delta_f+dd*last)/df,'truth_localization_tolerance_channel_widths':2+max(h['width_channels'],truth['flux_by_scan'][h['scan_id']]['injection_oracle_width_channels'])/2,'largest_original_compatible_OFF_score':max(c['maximum_checked_score'] for c in comps),'OFF_margin_below_8':8-max(c['maximum_checked_score'] for c in comps),'true_drift_excluded_even_with_free_frequency':abs(dd)>bound}
            assert row['true_drift_excluded_even_with_free_frequency'] and row['minimum_possible_endpoint_excess_channel_widths']>0
            survivors.append(row)
            for c in comps:
                offs.append({'case_id':truth['case_id'],'carrier':h['reference_carrier_index'],'OFF_scan':c['scan_id'],'maximum_original_compatible_OFF_score':c['maximum_checked_score'],'margin_below_8':8-c['maximum_checked_score'],'checked_valid_compatible_templates':c['checked_valid_compatible_templates'],'family_exhausted':c['family_exhausted'],'veto':c['veto']})
            for m in maps:
                tracks.append({'case_id':truth['case_id'],'carrier':h['reference_carrier_index'],'scan_id':m['scan_id'],'role':m['role'],'first_time_from_tref_s':m['scan_first_time_from_tref_s'],'last_time_from_tref_s':m['scan_last_time_from_tref_s'],'first_truth_error_channel_widths':(delta_f+dd*m['scan_first_time_from_tref_s'])/df,'last_truth_error_channel_widths':(delta_f+dd*m['scan_last_time_from_tref_s'])/df})
                if m['role']!='OFF': continue
                k=int(np.argmax(m['maximum_robust_box_track_score'])); w=int(m['winning_width_channels'][k]); f=float(m['frequency_hz_at_tref'][k]); d=float(m['winning_drift_hz_s'][k]); tol=((h['width_channels']+w)/2+2)*max(df,abs(m['df_hz']))
                e0=f-h['reference_frequency_hz']+(d-h['drift_hz_s'])*first; e1=f-h['reference_frequency_hz']+(d-h['drift_hz_s'])*last
                global_pairs.append({'case_id':truth['case_id'],'carrier':h['reference_carrier_index'],'OFF_scan':m['scan_id'],'OFF_global_winner_score':float(m['maximum_robust_box_track_score'][k]),'OFF_global_winner_frequency_hz':f,'OFF_global_winner_drift_hz_s':d,'OFF_global_winner_width_channels':w,'first_ON_endpoint_error_channel_widths':e0/df,'last_ON_endpoint_error_channel_widths':e1/df,'tolerance_channel_widths':tol/df,'global_winner_compatible_with_survivor':abs(e0)<=tol and abs(e1)<=tol})
    assert len(survivors)==14 and len(offs)==42 and len(tracks)==84 and len(global_pairs)==42
    assert not any(x['global_winner_compatible_with_survivor'] for x in global_pairs)
    save_csv('survivors.csv',survivors);save_csv('original_OFF_comparisons.csv',offs);save_csv('truth_track_geometry.csv',tracks);save_csv('OFF_global_winner_compatibility.csv',global_pairs)
    evidence={'status':'COMPLETE_READ_ONLY_RETAINED_RFI_ANALYSIS','source_commit':'6b8259099721b3acdb98b604fb5c9ea192577d68','qualification':False,'detector_or_generator_executed':False,'new_draws_or_scores':False,'thresholds_unchanged':True,'telescope_values_opened':False,'coordinate_units':'signed frequency difference / absolute native-channel spacing; not signed native-channel index','original_code_sha256':original_hashes,'original_input_bindings':bindings,'survivor_count':14,'original_OFF_comparison_count':42,'truth_geometry_rows':84,'global_OFF_winner_pairs':42,'all_14_true_drifts_excluded_for_every_frozen_OFF_width_even_with_free_reference_frequency':True,'all_42_retained_global_OFF_winning_paths_incompatible':True,'all_42_original_compatible_families_exhausted_below_8':True,'cases':context,'survivors':survivors,'OFF_comparisons':offs,'truth_track_geometry':tracks,'global_OFF_winner_compatibility':global_pairs}
    (OUT/'RFI_GEOMETRY_EVIDENCE.json').write_text(json.dumps(evidence,indent=2)+'\n')
    # Scientific figure: deterministic linear geometry and ORIGINAL saved OFF scores.
    fig,axes=plt.subplots(2,1,figsize=(10,7),layout='constrained')
    ax=axes[0]
    for caseid,color in [(context[0]['case_id'],'#2563eb'),(context[1]['case_id'],'#c2410c')]:
        for j,h in enumerate([s for s in survivors if s['case_id']==caseid]):
            ts=np.array([-959.3966807034205,959.3966807034207]); tf=next(c for c in context if c['case_id']==caseid)
            p=ROOT/f"results/radio_pilot_val_b_20261008/case_{64 if caseid==context[0]['case_id'] else 65:03d}"; truth=read(p/'truth.json')
            err=(h['frequency_hz_at_tref']-truth['reference_frequency_hz']+h['truth_drift_difference_hz_s']*ts)/2.835503418452676
            ax.plot(ts,err,color=color,alpha=.5,label=f"RFI{caseid[-3:]} retained alias(es)" if j==0 else None)
    first_case=[x for x in tracks if x['case_id']==context[0]['case_id'] and x['carrier']==771]
    for t in first_case:
        ax.axvspan(t['first_time_from_tref_s'],t['last_time_from_tref_s'],color='#64748b' if t['role']=='ON' else '#e2e8f0',alpha=.18)
        ax.text((t['first_time_from_tref_s']+t['last_time_from_tref_s'])/2,.96,t['scan_id'].replace('epoch',''),ha='center',va='top',fontsize=8,transform=ax.get_xaxis_transform())
    ax.axhline(0,color='black',lw=1,label='Injected true track');ax.set(xlabel='Time from global reference (seconds)',ylabel='Alias − truth frequency\n(channel-width units)',title='Retained ON aliases diverge from the injected RFI track'); ax.legend(loc='lower right',fontsize=8);ax.grid(alpha=.2)
    ax=axes[1]; labels=[f"002:{s['carrier']}" if s['case_id']==context[0]['case_id'] else f"003:{s['carrier']}" for s in survivors]
    for n,scan in enumerate(['epoch1_off','epoch2_off','epoch3_off']):
        vals=[next(x['maximum_original_compatible_OFF_score'] for x in offs if x['case_id']==s['case_id'] and x['carrier']==s['carrier'] and x['OFF_scan']==scan) for s in survivors]
        line,=ax.plot(np.arange(13),vals[:13],marker='o',ms=3,lw=1,label=scan.replace('epoch',''))
        ax.scatter([13],[vals[13]],marker='D',s=18,color=line.get_color())
    ax.axvline(12.5,color='#64748b',lw=1,alpha=.5)
    ax.axhline(8,color='#b91c1c',ls='--',label='Frozen OFF threshold 8'); ax.set_xticks(np.arange(14),labels,rotation=45,ha='right',fontsize=8);ax.set(ylabel='Original maximum compatible OFF score',xlabel='Case suffix : retained first-ON carrier',title='Every original compatible OFF family was exhausted below threshold');ax.set_ylim(2.5,8.5);ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=4,loc='lower right')
    fig.savefig(OUT/'retained_rfi_geometry.png',dpi=160);fig.savefig(OUT/'retained_rfi_geometry.pdf');plt.close(fig)
    print(json.dumps({'survivors':14,'OFF_comparisons':42,'artifact_hashes_verified':sum(len(x['manifest']) for x in bindings),'bound_hz_s':survivors[0]['maximum_compatible_drift_difference_hz_s'],'drift_difference_range_hz_s':[min(x['truth_drift_difference_hz_s'] for x in survivors),max(x['truth_drift_difference_hz_s'] for x in survivors)],'minimum_possible_endpoint_error_range':[min(x['minimum_possible_max_endpoint_error_channel_widths'] for x in survivors),max(x['minimum_possible_max_endpoint_error_channel_widths'] for x in survivors)],'OFF_score_range':[min(x['maximum_original_compatible_OFF_score'] for x in offs),max(x['maximum_original_compatible_OFF_score'] for x in offs)]}))
if __name__=='__main__': main()
