"""Post-hoc same-exposure sky comparison; no fitted efficiency claim or veto."""
from pathlib import Path
import json,csv,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1]
rows=json.loads((OUT/'NATIVE_MEASUREMENTS.json').read_text());inventory=json.loads((OUT/'ANCILLARY_FIBER_INVENTORY.json').read_text())
sky=next(r for r in inventory if r['independent_sky_fiber_available']);dp=sky['dp_id']
by={(r['fiber'],r['line']):r for r in rows if r['dp_id']==dp};lines=['OI5577','OI6300','OI6363']
scales=[by['A',line]['fixed_model_area_adu_angstrom']/by['B',line]['fixed_model_area_adu_angstrom'] for line in lines[:2]]
a6363=by['A','OI6363']['fixed_model_area_adu_angstrom'];b6363=by['B','OI6363']['fixed_model_area_adu_angstrom']
record=dict(dp_id=dp,target=sky['target'],date_obs=sky['date_obs'],dpr_type=sky['raw_context']['ESO DPR TYPE'],fiber_b_selector=sky['raw_context']['ESO INS OPTI6 NAME'],
    empirical_A_over_B_area_scaling_from_5577_and_6300=scales,measured_A_6363_area_adu_angstrom=a6363,measured_B_6363_area_adu_angstrom=b6363,
    scaled_B_6363_area_range_adu_angstrom=[min(scales)*b6363,max(scales)*b6363],residual_A_6363_area_range_adu_angstrom=[a6363-max(scales)*b6363,a6363-min(scales)*b6363],
    line_centers=[dict(line=line,A_offset_angstrom=by['A',line]['best_offset_angstrom'],B_offset_angstrom=by['B',line]['best_offset_angstrom']) for line in lines],
    interpretation='Simultaneous sky supports an atmospheric component at all three positions. V2-0165 has excess beyond scaled sky, consistent with the independently visible compact raw charge hit; a blend is plausible. The two scaling factors form a descriptive bracket, not a calibrated confidence interval or measured fiber response.',
    original_dispositions_changed=False,final_origin_confirmed=False,sky_control_plan_sha256=hashlib.sha256((OUT/'SKY_CONTROL_PLAN.json').read_bytes()).hexdigest())
(OUT/'SKY_CONTROL_RESULT.json').write_text(json.dumps(record,indent=2)+'\n')
fig,axes=plt.subplots(2,3,figsize=(12,8));fig.subplots_adjust(left=.07,right=.98,bottom=.08,top=.87,wspace=.3,hspace=.4)
for i,line in enumerate(lines):
    for fiber,color in [('A','tab:blue'),('B','tab:orange')]:
        r=by[fiber,line];d=np.load(OUT/r['array']);axes[0,i].plot(d['offset_angstrom'],d['flux_adu']-d['baseline_adu'],'.-',ms=3,label=fiber+(' star+sky' if fiber=='A' else ' sky'),color=color)
    axes[0,i].axvline(0,color='grey',ls=':');axes[0,i].axhline(0,color='grey',lw=.5);axes[0,i].set_xlim(-.25,.25);axes[0,i].set_title(line+' · independently scaled raw ADU');axes[0,i].legend(fontsize=8);axes[0,i].set_ylabel('Native flux − baseline (ADU)')
    axes[0,i].set_xlabel('Topocentric air offset (Å)')
    a=np.load(OUT/by['A',line]['array']);b=np.load(OUT/by['B',line]['array']);axes[1,i].plot(a['offset_angstrom'],a['flux_adu']-a['baseline_adu'],'.-',label='A',color='tab:blue')
    for k,scale in enumerate(scales):axes[1,i].plot(b['offset_angstrom'],scale*(b['flux_adu']-b['baseline_adu']),lw=1,label=f'B × {scale:.3f}',color=['tab:green','tab:red'][k])
    axes[1,i].axvline(0,color='grey',ls=':');axes[1,i].axhline(0,color='grey',lw=.5);axes[1,i].set_xlim(-.25,.25);axes[1,i].set_title('Same two empirical A/B scale factors');axes[1,i].legend(fontsize=8);axes[1,i].set_ylabel('Native excess (ADU)');axes[1,i].set_xlabel('Topocentric air offset (Å)')
fig.suptitle('HD119130 · 2023-05-14 · actual simultaneous sky fiber B\nV2-0165 at6363Å contains excess over plausible sky contribution; original artifact judgment preserved.',fontsize=12)
fig.savefig(OUT/'figures/SIMULTANEOUS_SKY_CONTROL.png',dpi=130);plt.close(fig)
catalog=list(csv.DictReader((BASE/'v2/triage_batch02/CUMULATIVE_DISPOSITIONS.csv').open()));events=[]
for h in catalog:
    if h['current_followup_status']!='PROVISIONAL_ATMOSPHERIC_OI':continue
    measurement=[r for r in rows if r['dp_id']==h['dp_id'] and r['fiber']=='A']
    berv=measurement[0]['berv_km_s'];approx=float(h['fitted_center_bary_air_angstrom'])/(1+berv/299792.458)
    nearest=min(measurement,key=lambda r:abs(r['reference_air_angstrom']-approx))
    inv=next(r for r in inventory if r['dp_id']==h['dp_id'])
    events.append(dict(review_id=h['review_id'],dp_id=h['dp_id'],target=h['canonical_target'],line=nearest['line'],
        original_inverse_BERV_offset_angstrom=approx-nearest['reference_air_angstrom'],native_fit_offset_angstrom=nearest['best_offset_angstrom'],
        native_fixed_amplitude_adu=nearest['fixed_amplitude_adu'],native_side_residual_mad_adu=nearest['side_residual_mad_adu'],
        simultaneous_sky_fiber_available=inv['independent_sky_fiber_available'],fiber_B_mode=inv['raw_context']['ESO DPR TYPE'].split(',')[1],
        followup_note='Atmospheric component supported by simultaneous sky; sole origin not established' if inv['independent_sky_fiber_available'] else 'Fixed-line native consistency only; no independent sky fiber for this exposure',
        original_disposition_preserved=True,final_origin_confirmed=False))
with (OUT/'OI25_FOLLOWUP.csv').open('w',newline='') as f:
    wr=csv.DictWriter(f,fieldnames=list(events[0]));wr.writeheader();wr.writerows(events)
(OUT/'OI25_FOLLOWUP.json').write_text(json.dumps(events,indent=2)+'\n')
print(json.dumps(record,indent=2))
