"""Post-run caption correction only; preserve the public frozen plot outputs.

The original raw-figure suptitle inherited Own0271. Its axes correctly say0289.
Intercept that exact title text while running the same public plotting module
against byte-identical numerical outputs in a separate temporary directory.
Require all three unaffected figures to be byte exact and all raw-figure pixel
differences to lie above the data axes. No numerical calculation is rerun.
"""
from pathlib import Path
import hashlib,importlib.util,json,shutil,tempfile
from PIL import Image,ImageChops
from matplotlib.figure import Figure
HERE=Path(__file__).resolve().parent;PHASE=HERE.parent;A=PHASE/'analysis';OUT=A/'results'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def main():
 plan=read(A/'PLAN.json');original=read(OUT/'PLOT_INDEX.json');hashes=read(OUT/'OUTPUT_HASHES.json');target='figures/PRESERVED_RAW_ORDER_CONTEXT_1.png';corrected=HERE/'PRESERVED_RAW_ORDER_CONTEXT_1.png';assert not corrected.exists()
 assert sha(A/'plot_group.py')==plan['plot_script_sha256']
 initial={r['path']:r['sha256'] for r in original['files']}
 for p,h in initial.items():assert sha(OUT/p)==h
 work=Path(tempfile.mkdtemp(prefix='c035_caption_',dir='/workspace/scratch/415302db46f1'))
 for p in OUT.iterdir():
  if p.name in ['figures','PLOT_INDEX.json']:continue
  if p.is_dir():shutil.copytree(p,work/p.name)
  else:shutil.copyfile(p,work/p.name)
 spec=importlib.util.spec_from_file_location('c035_original_frozen_plot',A/'plot_group.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.OUT=work
 original_title=Figure.suptitle;changes=[]
 def corrected_title(self,text,*args,**kwargs):
  if 'Own0271 mapping history retained' in text:
   changes.append(dict(before=text,after=text.replace('Own0271 mapping history retained','Own0289 mapping history retained')));text=changes[-1]['after']
  return original_title(self,text,*args,**kwargs)
 Figure.suptitle=corrected_title
 try:module.main()
 finally:Figure.suptitle=original_title
 assert len(changes)==1
 rendered=read(work/'PLOT_INDEX.json');checks=[]
 for r in rendered['files']:
  p=work/r['path']
  with Image.open(p) as im:im.verify()
  with Image.open(p) as im:im.load()
  if r['path']!=target:assert r['sha256']==initial[r['path']]
  checks.append(dict(path=r['path'],original_sha256=initial[r['path']],rendered_sha256=r['sha256'],identical=r['sha256']==initial[r['path']]))
 with Image.open(OUT/target) as a,Image.open(work/target) as b:
  assert a.size==b.size;difference=ImageChops.difference(a.convert('RGB'),b.convert('RGB'));bbox=difference.getbbox();assert bbox is not None and bbox[3]<90,bbox
 shutil.copyfile(work/target,corrected)
 for p,h in hashes.items():assert sha(OUT/p)==h
 for p,h in initial.items():assert sha(OUT/p)==h
 receipt=dict(status='PASS_LABEL_ONLY_CORRECTION_DATA_AXES_BYTE_IDENTICAL',changes=changes,original_plot_script_sha256=sha(A/'plot_group.py'),correction_script_sha256=sha(Path(__file__)),original_raw_png_sha256=initial[target],corrected_raw_png_sha256=sha(corrected),changed_pixel_bbox=list(bbox),changed_pixels_entirely_above_data_axes=True,unchanged_other_figures=checks,numerical_production_rerun=False,original_scientific_outputs_unchanged=True,statistical_or_display_scale_variant_added=False)
 (HERE/'CORRECTION_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt,indent=2))
 with Image.open(corrected) as im:im.load();im.convert('RGB').save('/workspace/scratch/415302db46f1/C035_inspection/CORRECTED_RAW.jpg',quality=95)
if __name__=='__main__':main()
