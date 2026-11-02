"""Predicted trace-center proximity from A/B FITS headers only; no image values."""
import datetime,hashlib,json,math,tarfile
from pathlib import Path
from astropy.io.fits import Header
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];I=HERE.parent/'inputs'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def first_header(f):
 parts=[]
 while True:
  b=f.read(2880)
  if len(b)!=2880:raise ValueError('Truncated FITS header')
  parts.append(b)
  if any(b[j:j+8]==b'END     ' for j in range(0,2880,80)):break
  if len(parts)*2880>524288:raise ValueError('Header cap')
 raw=b''.join(parts)
 return Header.fromstring(raw.decode('ascii'),sep=''),hashlib.sha256(raw).hexdigest(),len(raw)
anc=I/'source_products/ADP.2023-02-23T01_01_36.792.tar';expected='527f6e8efd09d77a15e923b95a29c919874961b280bd8de2a1b5f5b5184dfe29';assert sha(anc)==expected
headers={};provenance={};coeff={}
with tarfile.open(anc) as archive:
 for fiber in ['A','B']:
  members=[x for x in archive if x.name.endswith('_e2ds_'+fiber+'.fits')];assert len(members)==1
  h,hh,n=first_header(archive.extractfile(members[0]));headers[fiber]=h
  assert h['DATE-OBS']=='2023-02-22T07:40:53.531' and h['INSTRUME']=='HARPS' and h['OBJECT'].replace(' ','')=='HD122640' and h['NAXIS1']==4096
  degree=h['ESO DRS CAL LOC DEG CTR']; count=h['NAXIS2'];assert degree==4 and count=={'A':72,'B':71}[fiber]
  coeff[fiber]=[[float(h['ESO DRS CAL LOC CTR'+str(order*(degree+1)+j)]) for j in range(degree+1)] for order in range(count)]
  assert all(math.isfinite(c) for v in coeff[fiber] for c in v)
  provenance[fiber]={'member':members[0].name,'member_bytes':members[0].size,'header_sha256':hh,'header_bytes':n,'native_order_count':count,'trace_degree':degree,'calibration_trace_file':h['ESO DRS CAL LOC FILE'],'date_obs':h['DATE-OBS'],'dpr_type':h.get('ESO DPR TYPE')}
def poly(c,x):
 val=0.
 for a in reversed(c):val=val*x+a
 return val
assert abs(poly(coeff['A'][50],3139)-2323.7701943175816)<1e-10
# All integer raw rows in the enclosing fixed old-local-control/event span.
rows=range(2859,3420);records=[]
for fiber in ['A','B']:
 for order,c in enumerate(coeff[fiber]):
  if fiber=='A' and order==50:continue
  offsets=[poly(c,row)-poly(coeff['A'][50],row) for row in rows]
  records.append({'fiber':fiber,'order_zero_based':order,'signed_center_offset_at_event':poly(c,3139)-poly(coeff['A'][50],3139),'minimum_signed_offset':min(offsets),'maximum_signed_offset':max(offsets),'minimum_absolute_center_separation':min(map(abs,offsets)),'rows_center_within_pm12':sum(abs(z)<=12 for z in offsets),'rows_center_in_abs9_to12_sidebands':sum(9<=abs(z)<=12 for z in offsets)})
nearest=sorted(records,key=lambda z:z['minimum_absolute_center_separation'])[:4]
out={'schema':'HARPS_SPATIAL0235_HEADER_NEIGHBOR_GEOMETRY_V1','status':'PASS_HEADER_GEOMETRY_NO_CENTER_OVERLAP','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256':sha(Path(__file__)),'ancillary_sha256':expected,'provenance':provenance,'conventions':{'index_origin':0,'orientation':{'row_flip':True,'column_flip':False,'argument_flip':True},'polynomial_argument':'raw_row = 4095 - native_pixel; same detector-coordinate trace polynomial convention for both stored A/B headers, without equal-order-index assumption','raw_rows_checked_half_open':[2859,3420],'native_pixels_equivalent_half_open':[676,1237],'event_raw_row':3139,'A_reference_order':50,'requested_cross_dispersion_offsets':[-12,12],'requested_sidebands_absolute_true_trace_distance':[9,12]},'neighbor_trace_count':len(records),'integer_rows_checked':len(rows),'nearest_traces':nearest,'all_center_overlaps_pm12':[x for x in records if x['rows_center_within_pm12']],'fiber_B_nearest_order':nearest[0]['order_zero_based'] if nearest[0]['fiber']=='B' else None,'interpretation':'No predicted neighboring trace center enters the requested ±12-pixel region over the bounded row span. This is a trace-header geometric check, not empirical registration of B or a flux/PSF measurement. B49 is simultaneous FP calibration. Its wings may affect the positive sideband even without center overlap; background contamination is unmeasured and must not be declared absent. Negative sideband is geometrically farther from that nearest trace.','coefficients_ascending':coeff,'network_requests':0,'image_array_values_read':0,'orientation_or_trace_fit_changed':False}
assert not out['all_center_overlaps_pm12']
(HERE/'NEIGHBOR_GEOMETRY_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'nearest':nearest[:2]}))
