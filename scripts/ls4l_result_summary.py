#!/usr/bin/env python3
"""Verify measured review evidence without accessing raw observations."""
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from ls4l_v2_vetoed_fragment_diagnostics import ROOT,OUT,load,stage_input,review_annotations
from ls4g_synthetic_recovery import encoded,verify_manifest
from ls4f_v2_native_reanalysis import numeric_agreement
from ls4i_measured_digital_injections import truth_geometry
from seti_repeater.light_sail_residual import channel_indices


def verified():
    verify_manifest(ROOT/'LS4L_FREEZE.sha256')
    verify_manifest(ROOT/'LS4L_V2_FREEZE.sha256')
    config=load('config/ls4l_v2_vetoed_fragment_diagnostics.json')
    for path,expected in config['input_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    result=load('results_ls4l_v2_vetoed_fragment_diagnostics/diagnostics.json.gz')
    identity=result.pop('result_sha256');assert hashlib.sha256(encoded(result)).hexdigest()==identity
    result['result_sha256']=identity
    assert result['status']=='veto-preserving-measured-diagnostic-complete'
    checkpoint=load('results_ls4l_v2_vetoed_fragment_diagnostics/prevalidation.json.gz')
    assert all(result[k]==v for k,v in checkpoint.items())
    assert result['freeze_sha256']==hashlib.sha256((ROOT/'LS4L_V2_FREEZE.sha256').read_bytes()).hexdigest()
    stage=stage_input(config);header=load('config/ls4c_lhs1140_x_htr_followup.json')['expected_filterbank_header']
    assert review_annotations(result,stage,config,header)==result['review_configurations']
    for row in result['paired_configurations']:
        truth=truth_geometry(row,config)
        indices=channel_indices(header['fch1_mhz'],header['foff_mhz'],header['nchans'],truth['frequency_start_mhz'],truth['frequency_stop_mhz'])
        for event in row['events']:
            lo,hi=event['band_indices']
            expected=max(0,min(hi,int(indices[-1])+1)-max(lo,int(indices[0])))/(hi-lo)
            assert event['injected_channel_fraction']==expected
            assert np.isfinite(event['injection_reference_scale_counts']) and event['injection_reference_scale_counts']>0
    previous=load('results_ls4i_measured_digital_injections/injections.json.gz')
    assert numeric_agreement(result['fixed_window_diagnostics'],previous['fixed_window_diagnostics'],**config['replay_tolerance'])
    receipts=load('results_ls4l_v2_vetoed_fragment_diagnostics/source_receipts.json')
    assert len(receipts['sources'])==2
    for receipt,source in zip(receipts['sources'],config['sources']):
        assert receipt['label']==source['label'] and receipt['bytes']==source['source_size_bytes']
        assert receipt['source_sha256']==source['source_sha256'] and receipt['raw_file_deleted']
    assert sum(r['bytes'] for r in receipts['sources'])==result['source_bytes_verified']==18870174378
    assert receipts['charged_download_bytes']==config['prior_charged_download_bytes']+result['source_bytes_verified']
    assert receipts['charged_download_bytes']<=config['resource']['max_total_download_bytes']
    return config,result


def main():
    config,result=verified()
    reviews=result['review_configurations'];paired=result['paired_configurations']
    cells=[];bands=[]
    for fi,center in enumerate(config['frequency_centers_mhz']):
        for medium in config['medium_amplitudes']:
            for htr in config['htr_amplitudes']:
                rows=[r for r in reviews if r['frequency_index']==fi and r['medium_amplitude']==medium and r['htr_amplitude']==htr]
                cells.append({'frequency_center_mhz':center,'medium_amplitude':medium,'htr_amplitude':htr,'configurations':len(rows),
                              'selected_configurations':sum(bool(r['events']) for r in rows),
                              'review_passes':sum(r['review_truth_pass_any'] for r in rows),
                              'review_passes_absent_at_zero':sum(r['review_pass_absent_at_zero_any'] for r in rows)})
        rows=[r for r in paired if r['frequency_index']==fi and r['htr_amplitude']>0]
        events=[e for r in rows for e in r['events']]
        bands.append({'frequency_center_mhz':center,'positive_configurations':len(rows),
                      'selected_positive_configurations':sum(bool(r['events']) for r in rows),
                      'positive_fragment_evaluations':len(events),
                      'cross_scale_supported':sum(e['cross_scale_supported'] for e in events),
                      'off_vetoes':sum(e['off_veto'] for e in events),'reference_vetoes':sum(e['reference_veto'] for e in events),
                      'truth_associated_fragment_passes':sum(e['truth_associated_pass'] for e in events)})
    zero=[e for r in paired if r['htr_amplitude']==0 for e in r['events']]
    tally={'cells':cells,'positive_fragment_counts_by_band':bands,'zero_level_fragment_evaluations':len(zero),
           'zero_level_truth_passes':sum(e['truth_associated_pass'] for e in zero),
           'all_fragment_truth_passes':sum(e['truth_associated_pass'] for r in paired for e in r['events']),
           'review_passing_configurations':sum(r['review_truth_pass_any'] for r in reviews),
           'review_pass_absent_at_zero_configurations':sum(r['review_pass_absent_at_zero_any'] for r in reviews),
           'original_joint_passes':sum(r['joint_digital_pass'] for r in paired),'sky_candidates_promoted':result['sky_candidates_promoted']}
    runtime_summary=load('results_ls4l_v2_vetoed_fragment_diagnostics/summary.json')
    for key in ('review_passing_configurations','review_pass_absent_at_zero_configurations','original_joint_passes','sky_candidates_promoted'):
        assert tally[key]==runtime_summary[key]
    assert runtime_summary['result_sha256']==result['result_sha256']
    (OUT/'accounting.json').write_bytes(encoded(tally))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.hashsalt':'ls4l-v1'})
    fig,axes=plt.subplots(1,2,figsize=(11,5.5))
    fig.subplots_adjust(left=.10,right=.94,top=.70,bottom=.28,wspace=.35)
    fig.suptitle('LS4L · pulse diagnostics behind the retained OFF veto',x=.06,y=.95,ha='left',weight='bold',fontsize=18)
    fig.text(.06,.85,'Actual selected event windows and bands · real archived A1/B1 backgrounds',fontsize=12)
    for fi,ax in enumerate(axes):
        values=np.array([c['review_passes'] for c in cells if c['frequency_center_mhz']==config['frequency_centers_mhz'][fi]]).reshape(3,4)
        ax.imshow(values,cmap='Blues',vmin=0,vmax=6,aspect='auto')
        ax.set_title(f"{config['frequency_centers_mhz'][fi]/1000:g} GHz · review pass count / 6",loc='left',pad=12)
        ax.set_xticks(range(4),['0','4','8','16']);ax.set_yticks(range(3),['1','4','16'])
        ax.set_xlabel('HTR digital amplitude');ax.set_ylabel('Medium digital amplitude')
        for (i,j),v in np.ndenumerate(values):ax.text(j,i,str(v),ha='center',va='center',fontsize=16,color='white' if v>3 else '#172554')
        for spine in ax.spines.values():spine.set_visible(False)
    fig.text(.06,.14,'Each cell has two time placements × three pulse widths. An empty Stage-1 selection cannot pass review.',fontsize=10)
    fig.text(.06,.07,'Separate amplitude units; repeated backgrounds. Original joint passes and new sky candidates remain zero.',fontsize=10,color='#4b5563')
    fig.savefig(OUT/'measured_review.svg',metadata={'Date':None});fig.savefig(OUT/'measured_review.png',dpi=150);plt.close(fig)
    p=OUT/'measured_review.svg';p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
    print(json.dumps(tally,indent=2))

if __name__=='__main__':main()
