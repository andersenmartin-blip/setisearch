"""Verify C034 source bytes and all72 native order headers without data access."""
from pathlib import Path
import hashlib,json,math
from astropy.io import fits
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PHASE=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 inv=json.loads((PHASE/'inputs/INPUT_INVENTORY.json').read_text());checks=[]
 def ck(v,s):
  if not v:raise AssertionError(s)
  checks.append(s)
 for f in inv['files']:
  p=ROOT/f['path'];ck(p.stat().st_size==f['bytes'] and sha(p)==f['sha256'],'source '+f['path'])
 for p,h in inv['source_hashes'].items():ck(sha(ROOT/p)==h,'metadata '+p)
 ck(len(inv['files'])==9 and len(inv['merged_spectra'])==6 and len(inv['native_products'])==1,'exact own 9/6/1 inputs')
 ck(inv['events']=={'V2E2-0271':'ADP.2025-05-30T01:00:44.357'},'own original record and reference')
 n=inv['native_products'][0];scan=inv['all_order_header_scan'];ck(len(scan)==72,'fresh all72 order scan')
 with fits.open(ROOT/n['file']['path'],memmap=True,do_not_scale_image_data=True) as hd:
  h=hd[0].header;ck(h['NAXIS1']==4096 and h['NAXIS2']==72,'native72x4096 header')
  center=4312.202499999999/(1+h['ESO DRS BERV']/299792.458)
  for order,row in enumerate(scan):
   coeff=[h['ESO DRS CAL TH COEFF LL'+str(order*4+j)] for j in range(4)]
   ends=[coeff[0],sum(c*4095**j for j,c in enumerate(coeff))]
   deriv=[coeff[1],sum(j*c*4095**(j-1) for j,c in enumerate(coeff) if j)]
   vertex=-coeff[2]/(3*coeff[3]) if coeff[3] else -1
   if 0<vertex<4095:deriv.append(coeff[1]+2*coeff[2]*vertex+3*coeff[3]*vertex**2)
   ck(row['order']==order and row['header_endpoint_topocentric_air_angstrom']==ends and min(deriv)>0,'order header '+str(order))
   ck(row['selected_for_profile']==(ends[0]<center<ends[1])==(order==19),'own covering order '+str(order))
 ck(n['covering_orders']==[19] and len(inv['saved_native_raw_cutouts'])==1,'own native and raw19')
 for stage in ['primary','secondary','adopted']:
  ck(len(inv['historical_raw_review_records'][stage])==1 and inv['historical_raw_review_records'][stage][0]['code']=='U','own unchanged review '+stage)
 r=dict(status='PASS_C034_INPUT_HEADER_AUDIT',checks_passed=len(checks),checks=checks,files_verified=9,header_orders_verified=72,observational_array_values_read=0,inventory_sha256=sha(PHASE/'inputs/INPUT_INVENTORY.json'),audit_script_sha256=sha(Path(__file__)))
 (HERE/'INPUT_AUDIT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='checks'}))
if __name__=='__main__':main()
