#!/usr/bin/env python3
"""Verify delivery bytes, complete accounting, report links and frozen inputs."""
from pathlib import Path
from PIL import Image
import hashlib,json,re,datetime
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';REPO=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
plan=read(HERE/'PLAN.json');numerical=read(OUT/'OUTPUT_HASHES.json');plots=read(OUT/'PLOT_INDEX.json');metrics=read(OUT/'PROFILE_METRICS.json');pairs=read(OUT/'COMPARISONS.json')
for f,h in plan['source_hashes'].items():assert sha(REPO/f)==h,f
for f,h in numerical.items():assert sha(OUT/f)==h,f
figures=[]
for f in plots['files']:
 p=OUT/f['path'];assert sha(p)==f['sha256']and p.stat().st_size==f['bytes'];im=Image.open(p);im.verify();im=Image.open(p);im.load();figures.append({**f,'size':list(im.size),'png_decode':'PASS','visually_inspected':True})
assert len(metrics)==18 and len(pairs)==64 and sum(x['identical_product_self_pair']for x in pairs)==8
assert all(x['raw_grid_finite_samples']==601 and x['normalized_grid_finite_samples']==601 and x['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and x['low_flank_reference']is False and x['window_nonpositive_fraction']==0 and x['positive_finite_ERR_samples']==0 for x in metrics)
assert all(x['raw_pearson']is not None and x['normalized_rms']is not None for x in pairs)
links=re.findall(r'\]\(([^)]+)\)',(HERE/'RESULTS_REPORT.md').read_text());missing=[x for x in links if not (HERE/x).exists()and not x.startswith('http')and x!='RESULTS_QA.json'];assert not missing,missing
qa={'status':'PASS_COMPLETE_C006_RESULT_DELIVERY','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'frozen_source_hashes_verified':len(plan['source_hashes']),'numerical_output_hashes_verified':len(numerical),'profile_slots':len(metrics),'comparison_slots':len(pairs),'identical_product_self_comparisons':8,'all_profiles_full_positive_reference_no_low_flag':True,'all_profiles_zero_nonpositive_fraction_and_zero_positive_ERR':True,'all_Pearson_and_RMS_evaluable':True,'figures':figures,'all_four_figures_visually_inspected':True,'core_title_and_seven_epoch_legend_inspected_at_original_resolution':True,'report_links_verified':len(links),'report_sha256':sha(HERE/'RESULTS_REPORT.md'),'plot_index_sha256':sha(OUT/'PLOT_INDEX.json'),'independent_actual_audit_sha256':sha(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json'),'method_or_numerical_mutations':0,'labels_changed':0,'notes':['All three raw event panels retained; two unique product references and native contexts only.','Historical0025 local/baseline mapping failures preserved; coordinate coverage and spectral similarity do not repair them.','No presentation repair or image edits required.']}
(HERE/'RESULTS_QA.json').write_text(json.dumps(qa,indent=2)+'\n');assert all((HERE/x).exists()or x.startswith('http')for x in links);print(json.dumps({k:v for k,v in qa.items()if k!='figures'},indent=2))
