from pathlib import Path
import csv,json,hashlib,itertools,collections,datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save_csv(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
rows=[]
for file,scope in [('CONTEXT_64.csv','ORIGINAL64'),('CONTEXT_31.csv','NEW31')]:
 for r in csv.DictReader((P/file).open()):
  r['scope']=scope;r['expanded_status']='UNRESOLVED_SPECTRAL_FEATURE'
  for k in ['approx_stellar_air_angstrom','center_bary_air_angstrom','rvc_km_s','rv_mask_span_km_s','context_3_10_p95_adu','peak_over_context_1_5_p95','peak_over_context_3_10_p95']:r[k]=float(r[k])
  rows.append(r)
assert len(rows)==95 and len({r['review_id'] for r in rows})==95
byid={r['review_id']:r for r in rows}
groups=[]
for target in dict.fromkeys(r['target'] for r in rows):
 batch=[]
 for r in sorted([r for r in rows if r['target']==target],key=lambda x:x['approx_stellar_air_angstrom']):
  if batch and r['approx_stellar_air_angstrom']-batch[0]['approx_stellar_air_angstrom']>.06:groups.append(batch);batch=[]
  batch.append(r)
 if batch:groups.append(batch)
gs=[]
for i,g in enumerate(groups):
 x=dict(group_id=f'A{i+1:02d}',target=g[0]['target'],events=[r['review_id'] for r in g],stellar_air_median=float(np.median([r['approx_stellar_air_angstrom'] for r in g])),stellar_air_span=float(np.ptp([r['approx_stellar_air_angstrom'] for r in g])),bary_air_span=float(np.ptp([r['center_bary_air_angstrom'] for r in g])),rv_span=float(np.ptp([r['rvc_km_s'] for r in g])),representative=min(r['review_id'] for r in g))
 gs.append(x)
 for r in g:r['combined_group_id']=x['group_id']
clusters=[];batch=[]
for g in sorted(gs,key=lambda x:x['stellar_air_median']):
 if batch and g['stellar_air_median']-batch[0]['stellar_air_median']>.10:clusters.append(batch);batch=[]
 batch.append(g)
if batch:clusters.append(batch)
cs=[];pairrows=[];multis=[]
for i,cl in enumerate(clusters):
 x=dict(cluster_id=f'X{i+1:02d}',groups=[g['group_id'] for g in cl],targets=list(dict.fromkeys(g['target'] for g in cl)),events=[e for g in cl for e in g['events']],rest_center=float(np.median([g['stellar_air_median'] for g in cl])),group_median_span=float(np.ptp([g['stellar_air_median'] for g in cl])))
 cs.append(x)
 for e in x['events']:
  r=byid[e];r['cross_target_cluster_id']=x['cluster_id'];r['cluster_target_count']=len(x['targets']);r['rest_offset_from_cluster_angstrom']=r['approx_stellar_air_angstrom']-x['rest_center']
 if len(x['targets'])<2:continue
 multis.append(x);grid=x['rest_center']+np.arange(-3,3.001,.01);profiles=[]
 for g in cl:
  r=byid[g['representative']];d=np.load(P/r['profile_file']);wave=d['wave_bary_air']/(1+r['rvc_km_s']/299792.458);flux=d['flux_adu']/r['context_3_10_p95_adu'];profiles.append((g,r,np.interp(grid,wave,flux)))
 for (g1,r1,f1),(g2,r2,f2) in itertools.combinations(profiles,2):
  z=dict(cluster_id=x['cluster_id'],target1=r1['target'],target2=r2['target'],review_id1=r1['review_id'],review_id2=r2['review_id'],group_center_difference_angstrom=g2['stellar_air_median']-g1['stellar_air_median'],rvc_difference_km_s=r2['rvc_km_s']-r1['rvc_km_s'])
  for width in [.6,3.]:
   sel=abs(grid-x['rest_center'])<=width+1e-8;z['pearson_r_halfwidth_'+str(width)+'_angstrom']=float(np.corrcoef(f1[sel],f2[sel])[0,1])
  pairrows.append(z)
 fig,axs=plt.subplots(1,2,figsize=(12,3.7));fig.subplots_adjust(left=.07,right=.98,bottom=.17,top=.8,wspace=.2)
 for g,r,f in profiles:
  for ax,width in zip(axs,[.6,3]):
   sel=abs(grid-x['rest_center'])<=width+.001;ax.plot(grid[sel]-x['rest_center'],f[sel],lw=.9,label=r['target']+f' RV {r["rvc_km_s"]:+.2f}')
 for ax in axs:
  ax.axvline(0,c='k',lw=.5,ls=':');ax.set_xlabel('Approximate stellar-air offset (Å)');ax.set_ylabel('Flux / local wider P95');ax.tick_params(labelsize=8)
 axs[1].legend(fontsize=8)
 fig.suptitle(x['cluster_id']+f' | {x["rest_center"]:.4f} Å | fixed CCF RV alignment, no fitted offset\n'+f'{len(x["targets"])} targets; group-center span {x["group_median_span"]:.5f} Å',fontsize=11)
 fig.savefig(P/'figures'/f'OVERLAY_{x["cluster_id"]}.png',dpi=120);plt.close(fig)
for r in rows:
 r['specific_transition']='UNASSIGNED'
 r['annotation_confidence']='Broad passband context only; individual line identity not established.' if r['broad_region']!='OTHER_OR_UNIDENTIFIED' else 'Context hypothesis only; no individual line or source identity established.'
 r['context_hypothesis']='Common stellar absorption structure / local flux window plausible' if r['broad_region']!='OTHER_OR_UNIDENTIFIED' else 'Unidentified; requires instrumental or atmospheric investigation'
 if r['review_id'] in ['V2-0001','V2-0103','V2-0104']:r['context_hypothesis']='Blue feature in approximate reference-fibre ghost region; observer-frame and calibration tests required; no identification'
 if r['review_id']=='V2-0125':r['context_hypothesis']='Barycentrically persistent spectral structure outside selected CN/CH passbands; observer-wavelength coincidence is not FP evidence; no chemical identity'
 if r['review_id']=='V2-0139':r['context_hypothesis']='Barycentric persistence supported by later epochs; pairwise medians confounded by time clustering; no chemical identity'
 if r['review_id']=='V2-0205':r['context_hypothesis']='Near atmospheric O I6363.776 in topocentric air; see independent doublet followup; no origin assigned here'
 r['origin_disposition_changed']=False
rows=sorted(rows,key=lambda r:r['review_id'])
save_csv(P/'CANDIDATE_CONTEXT_95.csv',rows);save_csv(P/'CROSS_TARGET_PROFILE_PAIRS.csv',pairrows)
(P/'GROUPS_95.json').write_text(json.dumps(dict(groups=gs,clusters=cs),indent=2)+'\n')
summary=dict(events=95,targets=len({r['target'] for r in rows}),groups=len(gs),rest_clusters=len(cs),multi_target_clusters=len(multis),events_in_multi_target_clusters=sum(len(x['events']) for x in multis),max_multitarget_groupcenter_span=max(x['group_median_span'] for x in multis),broad_region_counts=dict(collections.Counter(r['broad_region'] for r in rows)),peak_below_p95_1_5=sum(r['peak_over_context_1_5_p95']<1 for r in rows),peak_below_p95_3_10=sum(r['peak_over_context_3_10_p95']<1 for r in rows),pair_count=len(pairrows),core_correlation_range=[min(r['pearson_r_halfwidth_0.6_angstrom'] for r in pairrows),max(r['pearson_r_halfwidth_0.6_angstrom'] for r in pairrows)],wide_correlation_range=[min(r['pearson_r_halfwidth_3.0_angstrom'] for r in pairrows),max(r['pearson_r_halfwidth_3.0_angstrom'] for r in pairrows)],all_dispositions_unchanged=True,plan_sha256=sha(P/'OVERLAY_PLAN.json'),script_sha256=sha(Path(__file__)))
(P/'SUMMARY_95.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
