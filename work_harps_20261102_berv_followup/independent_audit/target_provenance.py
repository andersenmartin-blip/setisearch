#!/usr/bin/env python3
"""Independent local metadata audit; never requests data or opens FITS products.

Only the named JSON report is written. Manifest product hashes are archived
claims, not hashes recomputed from science files. Owner analysis code is not
imported. Angles and date arithmetic below are reconstructed independently.
"""
import csv
import hashlib
import json
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEARCH = HERE.parent / 'metadata_search'
HANDOFF_DIR = ROOT / 'work_harps_20261101/v2/extension02/next_followup_20261102'
SOURCES = [
    ('work_harps_20261101/acquisition/DOWNLOAD_MANIFEST.json', 'main_unopened', 'initial100'),
    ('work_harps_20261101/v2/acquisition/DOWNLOAD_MANIFEST.json', 'v2_main_unopened', 'v2_first100'),
    ('work_harps_20261101/v2/extension02/acquisition/DOWNLOAD_MANIFEST.json', 'extension02_unopened', 'extension02'),
]
TARGETS = ['HD122640', 'HD135204']
checks, source_hashes = [], {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    source_hashes[str(path.relative_to(ROOT))] = sha(path)
    return json.loads(path.read_text())


def check(name, passed, detail=None):
    checks.append(dict(check=name, passed=bool(passed), detail=detail))


def angle_arcsec(ra1, dec1, ra2, dec2):
    a, b, c, d = map(math.radians, [ra1, dec1, ra2, dec2])
    h = math.sin((d-b)/2)**2 + math.cos(b)*math.cos(d)*math.sin((c-a)/2)**2
    return math.degrees(2*math.atan2(math.sqrt(max(0, h)), math.sqrt(max(0, 1-h))))*3600


def sexagesimal(value, hours=False):
    v = abs(float(value))
    major = int(v // 10000)
    minute = int((v-major*10000)//100)
    second = v-major*10000-minute*100
    if not 0 <= minute < 60 or not 0 <= second < 60:
        raise ValueError('invalid sexagesimal value')
    result = (major + minute/60 + second/3600) * (15 if hours else 1)
    return math.copysign(result, value)


def mjd(text):
    dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
    return (dt-datetime(1858, 11, 17, tzinfo=timezone.utc)).total_seconds()/86400


def main():
    rows = []
    for path, role, cohort in SOURCES:
        all_rows = read(ROOT/path)
        main_rows = [r for r in all_rows if r['role'] == role]
        check(cohort+'_exact_main100', len(main_rows) == 100,
              {'total_manifest': len(all_rows), 'role_counts': dict(Counter(r['role'] for r in all_rows))})
        rows += [{**r, '_source': path, '_cohort': cohort} for r in main_rows]
    dp_ids = [r['dp_id'] for r in rows]
    raw_ids = [raw for r in rows for raw in r['raw_progenitor_ids']]
    check('main300_unique_dp_and_single_unique_raw', len(rows)==len(set(dp_ids))==len(raw_ids)==len(set(raw_ids))==300
          and all(len(r['raw_progenitor_ids'])==1 for r in rows))
    check('all300_download_and_header_provenance', all(
        r['download_status']=='DOWNLOADED' and r['header_status']=='PASS_METADATA_ONLY'
        and r['primary_header']['INSTRUME']=='HARPS' and r['primary_header']['NCOMBINE']==1
        and r['provenance_header']['ARCFILE']==r['dp_id']+'.fits'
        and r['provenance_header']['PROV1']==r['raw_progenitor_ids'][0]+'.fits'
        for r in rows))
    handoff = read(HANDOFF_DIR/'HANDOFF.json')
    table_path = HANDOFF_DIR/'EXISTING_TARGET_EXPOSURES.csv'
    source_hashes[str(table_path.relative_to(ROOT))] = sha(table_path)
    handoff_table = list(csv.DictReader(table_path.open()))
    selected = [r for r in rows if r['canonical_target'] in TARGETS]
    check('handoff_exact29_members', len(selected)==len(handoff_table)==29
          and {r['dp_id'] for r in selected}=={r['dp_id'] for r in handoff_table})
    by_dp = {r['dp_id']: r for r in rows}
    check('handoff29_exact_metadata_and_product_claims', all(
        t['target']==by_dp[t['dp_id']]['canonical_target']
        and t['source_manifest']==by_dp[t['dp_id']]['_source']
        and t['observation_utc']==by_dp[t['dp_id']]['primary_header']['DATE-OBS']
        and float(t['mjd'])==by_dp[t['dp_id']]['primary_header']['MJD-OBS']
        and float(t['berv_km_s'])==by_dp[t['dp_id']]['primary_header']['HIERARCH ESO DRS BERV']
        and t['recorded_product_sha256']==by_dp[t['dp_id']]['sha256']
        and t['raw_progenitor_id']==by_dp[t['dp_id']]['raw_progenitor_ids'][0]
        and int(t['product_bytes'])==by_dp[t['dp_id']]['bytes']
        and t['binary_rehashed_in_this_task']=='False'
        for t in handoff_table))
    targets = read(SEARCH/'TARGETS.json')
    check('prospective_fixed_two_targets_order', [t['canonical_target'] for t in targets]==TARGETS)
    target_reports = []
    for target in targets:
        name = target['canonical_target']
        rr = [r for r in rows if r['canonical_target']==name]
        intended = [r for r in rr if 'intended_target_header' in r]
        check(name+'_literal_names', {r['primary_header']['OBJECT'] for r in rr}=={name.replace('HD','HD ')}
              and target['exact_name_aliases']==[name, name.replace('HD','HD ')]
              and all(r['intended_target_header']['HIERARCH ESO OBS TARG NAME']==name.replace('HD','HD ') for r in intended))
        sr = by_dp[target['coordinate_source_dp_id']]
        ih = sr['intended_target_header']
        center = (sexagesimal(ih['HIERARCH ESO TEL TARG ALPHA'], True), sexagesimal(ih['HIERARCH ESO TEL TARG DELTA']))
        check(name+'_coordinate_provenance', sr['canonical_target']==name
              and target['source_manifest']==sr['_source'] and target['source_manifest_sha256']==sha(ROOT/sr['_source'])
              and target['source_product_sha256']==sr['sha256'] and target['intended_header']==ih
              and abs(center[0]-target['ra_deg'])<1e-10 and abs(center[1]-target['dec_deg'])<1e-10)
        coords = [(sexagesimal(r['intended_target_header']['HIERARCH ESO TEL TARG ALPHA'], True),
                   sexagesimal(r['intended_target_header']['HIERARCH ESO TEL TARG DELTA'])) for r in intended]
        check(name+'_sexagesimal_independent_conversion', all(abs(x-r['tel_targ_alpha_decimal_deg'])<1e-10
              and abs(y-r['tel_targ_delta_decimal_deg'])<1e-10 for (x,y),r in zip(coords,intended)))
        check(name+'_frame_epoch_provenance', target['coordinate_frame']=='FK5/J2000' and all(
            r['intended_target_header']['RADECSYS']=='FK5'
            and r['intended_target_header']['EQUINOX']==2000
            and r['intended_target_header']['HIERARCH ESO TEL TARG EPOCH']==2000
            and r['intended_target_header']['HIERARCH ESO TEL TARG EQUINOX']==2000
            and r['intended_target_header']['HIERARCH ESO TEL TARG EPOCHSYSTEM']=='J'
            for r in intended))
        offsets = [{'dp_id': r['dp_id'], 'arcsec': angle_arcsec(*center,r['primary_header']['RA'],r['primary_header']['DEC'])} for r in rr]
        check(name+'_120arcsec_contains_all_historical_pointings', target['cone_radius_arcsec']==120
              and max(o['arcsec'] for o in offsets)<=120)
        check(name+'_prospective_historical_rows_exact', target['existing_target_observations']==[
            dict(dp_id=r['dp_id'],ra_deg=r['primary_header']['RA'],dec_deg=r['primary_header']['DEC'],date_obs=r['primary_header']['DATE-OBS']) for r in rr])
        for scope in ['extension02_only','earlier200_only','all_existing300']:
            subset = [r for r in rr if scope=='all_existing300' or (r['_cohort']=='extension02')==(scope=='extension02_only')]
            berv = [r['primary_header']['HIERARCH ESO DRS BERV'] for r in subset]
            times = [r['primary_header']['DATE-OBS'] for r in subset]
            entry = next(h for h in handoff['coverage'] if h['target']==name and h['scope']==scope)
            check(name+'_'+scope+'_coverage', entry['exposures']==len(subset)
                  and entry['observation_first_utc']==min(times) and entry['observation_last_utc']==max(times)
                  and entry['berv_min_km_s']==min(berv) and entry['berv_max_km_s']==max(berv)
                  and abs(entry['berv_span_km_s']-(max(berv)-min(berv)))<1e-12
                  and abs(entry['nominal_resolution_km_s']-299792.458/115000)<1e-12)
        target_reports.append(dict(target=name,main_exposures=len(rr),cohorts=dict(Counter(r['_cohort'] for r in rr)),
            primary_object_values=sorted({r['primary_header']['OBJECT'] for r in rr}),
            intended_header_exposures=len(intended),intended_center_deg=center,
            intended_coordinates_unique=sorted(set(coords)),
            maximum_intended_coordinate_separation_arcsec=max(angle_arcsec(*a,*b) for a in coords for b in coords),
            primary_ra_range_deg=[min(r['primary_header']['RA'] for r in rr),max(r['primary_header']['RA'] for r in rr)],
            primary_dec_range_deg=[min(r['primary_header']['DEC'] for r in rr),max(r['primary_header']['DEC'] for r in rr)],
            maximum_primary_offset_arcsec=max(o['arcsec'] for o in offsets),
            primary_offsets_beyond60arcsec=[o for o in offsets if o['arcsec']>60],
            recorded_pma_values=sorted({r['intended_target_header']['HIERARCH ESO TEL TARG PMA'] for r in intended}),
            recorded_pmd_values=sorted({r['intended_target_header']['HIERARCH ESO TEL TARG PMD'] for r in intended}),
            recorded_proper_motion_pairs=[dict(pma=a,pmd=b,count=n) for (a,b),n in sorted(Counter(
                (r['intended_target_header']['HIERARCH ESO TEL TARG PMA'],
                 r['intended_target_header']['HIERARCH ESO TEL TARG PMD']) for r in intended).items())],
            coordinate_type_values=sorted({r['intended_target_header']['HIERARCH ESO TEL TARG COORDTYPE'] for r in intended})))

    plan = read(SEARCH/'PLAN.json')
    existing = read(SEARCH/'EXISTING_300.json')
    check('prospective_all300_exclusions_exact', len(existing)==300 and {r['dp_id'] for r in existing}==set(dp_ids)
          and {raw for r in existing for raw in r['raw_progenitor_ids']}==set(raw_ids)
          and all(r['raw_progenitor_ids']==by_dp[r['dp_id']]['raw_progenitor_ids']
                  and r['input_sha256']==by_dp[r['dp_id']]['sha256']
                  and r['canonical_target']==by_dp[r['dp_id']]['canonical_target'] for r in existing))
    check('plan_input_hashes', all(sha(ROOT/p)==h for p,h in plan['source_hashes'].items()))
    check('plan_bounds_inherit_handoff', plan['limits']==dict(target_requests_max=2,attempts_per_target=1,
        wall_seconds_per_target=30,response_bytes_per_target=4194304,rows_per_target=1000,redirects=0,retries=0,science_payload_bytes=0))
    exclusion = plan['observation_time_exclusion']
    check('utc_mjd_half_open_date_range', exclusion['mjd_half_open']==[59994,60005]
          and [mjd(s) for s in exclusion['utc_half_open']]==[59994,60005])
    check('existing29_fully_inside_excluded_days', all(59994<=r['primary_header']['MJD-OBS']
          and r['primary_header']['MJD-OBS']+r['primary_header']['EXPTIME']/86400<60005 for r in selected))
    check('whole_exposure_exclusion_boundary_synthetic', [b<=59994 or a>=60005 for a,b in [
        (59993,59994),(59993,59994.000001),(59994,59994.1),(60004.9,60005.1),(60005,60006)]]==[True,False,False,False,True])
    check('request_fixed_order', [r['target'] for r in plan['requests']]==TARGETS)
    for request,target in zip(plan['requests'],targets):
        path=SEARCH/request['query_file']; query=path.read_text(); source_hashes[str(path.relative_to(ROOT))]=sha(path)
        compact=re.sub(r'\s+','',query)
        name=target['canonical_target']
        check(name+'_query_hash', sha(path)==request['query_sha256'])
        tokens=["o.instrument_name='HARPS'", "o.obs_collection='HARPS'", "o.dataproduct_type='spectrum'",
                'o.n_obs=1',"o.multi_ob='S'",'o.t_exptime>0',"o.obs_release_date<='2026-11-02T00:00:00Z'",
                '(o.t_max<=59994ORo.t_min>=60005)']
        check(name+'_public_single_exposure_full_date_predicates', all(t in compact for t in tokens))
        check(name+'_all300_server_dp_exclusions', set(re.findall(r"'([^']+)'",re.search(r'o\.dp_id NOT IN \(([^)]+)\)',query).group(1)))==set(dp_ids))
        where=query.split('WHERE',1)[1].split('ORDER BY',1)[0]
        check(name+'_all_provenance_preserved_for_group_exclusion', 'LEFT OUTER JOIN phase3v2.provenance' in query
              and 'p.source_file' not in where)
        names="o.target_nameIN("+','.join("'"+s+"'" for s in target['exact_name_aliases'])+")OR1=CONTAINS"
        circle="CIRCLE('J2000',"+f"{target['ra_deg']:.12f},{target['dec_deg']:.12f},{120/3600:.12f}"+")"
        # Compare the literal alias list before whitespace normalization; quoted
        # spaces are meaningful and must not be silently canonicalized away.
        literal_aliases=re.search(r'o\.target_name\s+IN\s*\(([^)]+)\)',query).group(1)
        check(name+'_name_or_fk5_j2000_fixed_cone', re.findall(r"'([^']+)'",literal_aliases)==target['exact_name_aliases']
              and re.sub(r'\s+','',names) in compact and circle in compact)
        check(name+'_no_flux_or_snr_selection_no_top', not re.search(r'\bTOP\b',query,re.I)
              and not re.search(r'\b(snr|flux|berv)\b',where,re.I)
              and request['form']['MAXREC']=='1000' and request['endpoint']=='https://archive.eso.org/tap_obs/sync')
    schema_path=SEARCH/'sources/ESO_TAP_TABLES.xml'
    source_hashes[str(schema_path.relative_to(ROOT))]=sha(schema_path)
    schema={t.findtext('name'): {c.findtext('name'):c.findtext('description','') for c in t.findall('column')} for t in ET.parse(schema_path).getroot().iter('table')}
    check('saved_schema_coordinate_and_single_exposure_contract', all('FK5/J2000' in schema['ivoa.ObsCore'][c] for c in ['s_ra','s_dec'])
          and 'combination of exposures taken during the same visit' in schema['ivoa.ObsCore']['multi_ob']
          and 'Number of observations' in schema['ivoa.ObsCore']['n_obs'])
    for request in plan['requests']:
        query=(SEARCH/request['query_file']).read_text()
        aliases=dict(o='ivoa.ObsCore',f='phase3v2.product_files',p='phase3v2.provenance')
        check(request['target']+'_all_referenced_columns_exist_in_saved_schema', all(col in schema[aliases[a]] for a,col in re.findall(r'\b([ofp])\.(\w+)',query)))
    report={
        'schema':'INDEPENDENT_HARPS_TARGET_PROVENANCE_AUDIT_V1',
        'status':'PASS_WITH_EXPLICIT_LIMITATIONS' if all(c['passed'] for c in checks) else 'FAIL',
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'repo_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'scope':dict(network_requests=0,science_arrays_read=0,science_products_opened=0,owner_files_mutated=0),
        'auditor_script_sha256':sha(Path(__file__)),
        'checks_passed':sum(c['passed'] for c in checks),'checks_total':len(checks),'checks':checks,
        'main_cohort_totals':dict(exposures=300,unique_dp=len(set(dp_ids)),unique_raw=len(set(raw_ids))),
        'target_provenance':target_reports,'source_hashes':source_hashes,
        'limitations':[
            'Coordinates and target names establish internal archived metadata consistency only, not independent absolute pointing, current astrometric identity or photon origin.',
            'Only 19 of the 29 main-exposure manifest rows contain intended-target headers. The other 10 retain primary OBJECT/pointing coordinates and provenance only.',
            'The pair PMA=-0.061981/PMD=0.32138 occurs for both targets, but is not universal: HD122640 also records -0.33536/-0.11001 and HD135204 also records -1.2704/-0.50367. This within-target inconsistency, unknown units and unverified physical validity prohibit treating these values as validated proper motions. No proper motion is propagated.',
            'The fixed 120 arcsec cone contains all 29 historical primary positions, but does not guarantee completeness at other epochs. Exact-name OR cone retrieval reduces this risk; strict name AND cone candidate retention may conservatively exclude real epochs and must retain exclusion reasons.',
            'The two aliases are only the observed spaced name and manifest canonical name. Other physical aliases are unverified and are not added.',
            'n_obs=1 and one unambiguous HARPS raw progenitor support metadata candidacy. multi_ob=S alone permits coaddition within one visit; later header checks must confirm NCOMBINE and identity before scientific admission.',
            'Public release dates are metadata availability evidence, not a successful unauthenticated payload access test. This audit issues no requests.',
            'Observation date does not establish BERV separation. Per-exposure recorded BERV needs a separately frozen header/metadata route before science selection.',
            'Query structure, recorded plan, exclusions and provenance are reviewed here. Runtime parser, group-level raw exclusion, transport, freeze and no-repeat enforcement are independently reviewed by the parent preflight; this report alone does not authorize execution.',
            'No current scientific classification or gate has changed. Archived product hashes were compared as metadata claims; no binary product was rehashed.'
        ]}
    (HERE/'TARGET_PROVENANCE_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','checks_passed','checks_total']}))
    for c in checks:
        if not c['passed']: print(json.dumps(c))
    return 0 if all(c['passed'] for c in checks) else 1


if __name__=='__main__':
    raise SystemExit(main())
