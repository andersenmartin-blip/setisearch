"""Verify C032 byte custody and all 144 native order headers without arrays."""
from pathlib import Path
import hashlib,json
from astropy.io import fits
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PHASE=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 inv=json.loads((PHASE/'inputs/INPUT_INVENTORY.json').read_text());handoff=json.loads((ROOT/'work_harps_20261105_c034_context/NEXT_ACTION.json').read_text());centers={r['candidate_id']:float(r['center_bary_air_angstrom']) for r in handoff['existing_context']};checks=[]
 def ck(v,s):
  if not v:raise AssertionError(s)
  checks.append(s)
 for f in inv['files']:
  p=ROOT/f['path'];ck(p.stat().st_size==f['bytes'] and sha(p)==f['sha256'],'source '+f['path'])
 for p,h in inv['source_hashes'].items():ck(sha(ROOT/p)==h,'metadata '+p)
 ck(len(inv['files'])==14 and len(inv['merged_spectra'])==6 and len(inv['native_products'])==2,'exact 14/6/2 source scope')
 ck(inv['events']=={'V2E2-0278':'ADP.2025-06-28T01:01:54.505','V2E2-0283':'ADP.2025-07-17T01:03:21.039'},'both original records and own references')
 ck(len(inv['all_order_header_scan'])==144,'two fresh 72-order scans')
 for n in inv['native_products']:
  scan=[r for r in inv['all_order_header_scan'] if r['dp_id']==n['dp_id']];ck(len(scan)==72,'own 72-order product scope')
  with fits.open(ROOT/n['file']['path'],memmap=True,do_not_scale_image_data=True) as hd:
   h=hd[0].header;ck(h['NAXIS1']==4096 and h['NAXIS2']==72,'native 72x4096 header')
   original=[centers[e]/(1+h['ESO DRS BERV']/299792.458) for e in n['discovery_for']]
   for order,row in enumerate(scan):
    coeff=[h['ESO DRS CAL TH COEFF LL'+str(order*4+j)] for j in range(4)];ends=[coeff[0],sum(c*4095**j for j,c in enumerate(coeff))];deriv=[coeff[1],sum(j*c*4095**(j-1) for j,c in enumerate(coeff) if j)];vertex=-coeff[2]/(3*coeff[3]) if coeff[3] else -1
    if 0<vertex<4095:deriv.append(coeff[1]+2*coeff[2]*vertex+3*coeff[3]*vertex**2)
    ck(row['order']==order and row['header_endpoint_topocentric_air_angstrom']==ends and min(deriv)>0,'native header '+n['dp_id']+'/'+str(order))
    ck(row['selected_for_profile']==any(ends[0]<c<ends[1] for c in original)==(order in [2,3]),'own line coverage '+n['dp_id']+'/'+str(order))
  ck(n['covering_orders']==[2,3],'both own covering orders retained')
 ck(len(inv['saved_native_raw_cutouts'])==4,'four original raw contexts')
 keys=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
 ck(len(inv['mapping_records'])==4 and all([r[k] for k in keys]==[True,False,False,True] for r in inv['mapping_records']),'original mapping limitations retained separately')
 for stage in ['primary','secondary','adopted']:
  ck(len(inv['historical_raw_review_records'][stage])==2 and all(r['code']=='U' for r in inv['historical_raw_review_records'][stage]),'original U review '+stage)
 ck(all(r['additional_uncertainty'] and not r['contamination_or_blend_caution'] for r in inv['historical_raw_review_records']['secondary']),'own low-blue uncertainty without transferred blend caution')
 report=dict(status='PASS_C032_INPUT_HEADER_AUDIT',checks_passed=len(checks),checks=checks,files_verified=14,header_orders_verified=144,observational_array_values_read=0,inventory_sha256=sha(PHASE/'inputs/INPUT_INVENTORY.json'),audit_script_sha256=sha(Path(__file__)))
 (HERE/'INPUT_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='checks'}))
if __name__=='__main__':main()
