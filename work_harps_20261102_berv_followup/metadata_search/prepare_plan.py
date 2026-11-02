"""Create the prospective plan from published metadata; no network or payload reads."""
import hashlib, json, math, xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'work_harps_20261101'
def save(n, d): (HERE/n).write_text(json.dumps(d, indent=2, ensure_ascii=False)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
source_paths = [BASE/'acquisition/DOWNLOAD_MANIFEST.json', BASE/'v2/acquisition/DOWNLOAD_MANIFEST.json', BASE/'v2/extension02/acquisition/DOWNLOAD_MANIFEST.json', BASE/'v2/extension02/next_followup_20261102/HANDOFF.json', BASE/'v2/CURRENT_V2_DISPOSITIONS.csv']
source_hashes = {str(p.relative_to(ROOT)):sha(p) for p in source_paths}
rows=[]
for p, role in zip(source_paths[:3], ['main_unopened','v2_main_unopened','extension02_unopened']):
    selected=[r for r in json.loads(p.read_text()) if r['role']==role]
    assert len(selected)==100
    for r in selected:
        r=dict(r);r['source_manifest']=str(p.relative_to(ROOT));rows.append(r)
assert len({r['dp_id'] for r in rows})==300
known=[dict(dp_id=r['dp_id'], canonical_target=r['canonical_target'], raw_progenitor_ids=r['raw_progenitor_ids'], input_sha256=r['sha256'], observation_utc=r['primary_header']['DATE-OBS'], mjd=r['primary_header']['MJD-OBS'], source_manifest=r['source_manifest']) for r in rows]
assert len({x for r in known for x in r['raw_progenitor_ids']})==300
save('EXISTING_300.json', known)
targets=[]
for name in ['HD122640','HD135204']:
    r=next(x for x in rows if x['canonical_target']==name and 'intended_target_header' in x)
    h=r['intended_target_header'];ra=float(h['HIERARCH ESO TEL TARG ALPHA']);dec=float(h['HIERARCH ESO TEL TARG DELTA'])
    def sex(x):
        a=abs(x);return (1 if x>=0 else -1)*(int(a//10000)+int(a%10000//100)/60+(a%100)/3600)
    target=dict(canonical_target=name, exact_name_aliases=[name, 'HD '+name[2:]],
                ra_deg=sex(ra)*15, dec_deg=sex(dec), coordinate_frame='FK5/J2000', cone_radius_arcsec=120,
                coordinate_source_dp_id=r['dp_id'], source_manifest=r['source_manifest'], source_manifest_sha256=source_hashes[r['source_manifest']],
                source_product_sha256=r['sha256'], intended_header=h,
                identity_limit='Internal historical target/name/intended-coordinate provenance only. The120arcsec cone is an inventory guard, not independent astrometric or photon-origin verification. Identical telescope proper-motion values occur for both targets and are not propagated or accepted as physical measurements.',
                existing_target_observations=[dict(dp_id=x['dp_id'],ra_deg=x['primary_header']['RA'],dec_deg=x['primary_header']['DEC'],date_obs=x['primary_header']['DATE-OBS']) for x in rows if x['canonical_target']==name])
    targets.append(target)
save('TARGETS.json',targets)
fields=['dp_id','obs_publisher_did','obs_id','target_name','s_ra','s_dec','instrument_name','obs_collection','dataproduct_type','t_min','t_max','t_exptime','em_min','em_max','em_res_power','snr','proposal_id','n_obs','multi_ob','obs_release_date','access_url','access_estsize']
schema=ET.fromstring((HERE/'sources/ESO_TAP_TABLES.xml').read_bytes())
contract={}
for t in schema.iter('table'):
    if t.findtext('name') in ['ivoa.ObsCore','phase3v2.product_files','phase3v2.provenance']:
        contract[t.findtext('name')]={c.findtext('name'):{'type':c.findtext('dataType'),'description':c.findtext('description')} for c in t.findall('column')}
assert set(fields)<=set(contract['ivoa.ObsCore'])
save('SCHEMA_CONTRACT.json',contract)
ids=', '.join("'"+r['dp_id']+"'" for r in known)
requests=[]
for t in targets:
    aliases=', '.join("'"+x+"'" for x in t['exact_name_aliases'])
    q='SELECT '+', '.join('o.'+x for x in fields)+', f.archive_id, f.eso_category, p.source_file\n'
    q+='FROM ivoa.ObsCore AS o\nLEFT OUTER JOIN phase3v2.product_files AS f ON o.dp_id=f.product_id AND f.archive_id=f.product_id\nLEFT OUTER JOIN phase3v2.provenance AS p ON f.internal_file_id=p.product_file\n'
    q+="WHERE o.instrument_name='HARPS' AND o.obs_collection='HARPS' AND o.dataproduct_type='spectrum'\n"
    q+="AND o.n_obs=1 AND o.multi_ob='S' AND o.t_exptime>0\nAND o.obs_release_date<='2026-11-02T00:00:00Z'\n"
    q+='AND (o.t_max<=59994 OR o.t_min>=60005)\n'
    q+=f"AND (o.target_name IN ({aliases}) OR 1=CONTAINS(POINT('J2000',o.s_ra,o.s_dec),CIRCLE('J2000',{t['ra_deg']:.12f},{t['dec_deg']:.12f},{120/3600:.12f})))\n"
    q+=f'AND o.dp_id NOT IN ({ids})\nORDER BY o.t_min ASC, o.dp_id ASC, p.source_file ASC\n'
    name=t['canonical_target']+'.adql';(HERE/name).write_text(q)
    requests.append(dict(target=t['canonical_target'],query_file=name,query_sha256=sha(HERE/name),endpoint='https://archive.eso.org/tap_obs/sync',method='POST',form={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','MAXREC':'1000'},expected_columns=fields+['archive_id','eso_category','source_file']))
plan=dict(schema='HARPS_BERV_METADATA_PLAN_V1',status='PROSPECTIVE_NOT_EXECUTED',predecessor_commit='cfc0aa5146237ab82db183008ce8b162ad37c71a',
          scope='Public same-target HARPS single-exposure metadata inventory only, in fixed target order HD122640 then HD135204.',
          requests=requests,limits=dict(target_requests_max=2,attempts_per_target=1,wall_seconds_per_target=30,response_bytes_per_target=4194304,rows_per_target=1000,redirects=0,retries=0,science_payload_bytes=0),
          observation_time_exclusion=dict(utc_half_open=['2023-02-19T00:00:00Z','2023-03-02T00:00:00Z'],mjd_half_open=[59994,60005],predicate='t_max<=59994 OR t_min>=60005; entire exposure must be outside the excluded interval'),
          public_release_cutoff_utc='2026-11-02T00:00:00Z',
          identity='Query exact stored HD names OR120arcsec cone; offline candidates require canonical exact name AND coordinate within120arcsec. All other returned rows remain inventoried with rejection reasons; this guard is not independent target verification.',
          deduplication='All300 DP IDs excluded server-side and rechecked locally. All provenance rows remain joined, without filtering individual progenitors server-side. Offline reject whole DP group if any source_file matches any of300 known raw IDs; also reject absent/non-HARPS/ambiguous provenance. Repeated new raw IDs across products are one exposure, with lexicographically first DP kept only for metadata follow-up.',
          row_limit='MAXREC1000 applies to joined metadata rows, not distinct products. No TOP is used. QUERY_STATUS OVERFLOW, any non-OK QUERY_STATUS or count>=1000 marks incomplete and stops the route; no pagination.',
          failure='Any transport, HTTP, XML, overflow, cap or contract failure stops later target requests. An empty valid first result still permits the one frozen second target query. No automatic retries or alternate requests.',
          parse='Preserve original response bytes. Reject XML DTD/entity declarations and external STREAM URLs. Astropy parses only embedded metadata VOTable values, no spectra. Require one table and exact expected columns.',
          eligibility='Candidates are for separately frozen header identity/BERV checks only; no product is scientifically admitted here. No SNR/flux/morphology ranking, no classifier changes, no claims of BERV span from dates alone.',
          release_guard='ROOT_RELEASE.json must identify the SHA256 of PREFLIGHT_FREEZE.json, a40hex prospective GitHub commit and remote_bytes_verified=true. Exclusive RUN_STARTED.json and per-target markers prevent repeats.',
          source_hashes=source_hashes,science_arrays_read=0,existing_labels_changes=0)
save('PLAN.json',plan)
print('Plan ready:2 queries,300DP/raw exclusions; no target requests executed.')
