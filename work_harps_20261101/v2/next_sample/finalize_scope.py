"""Verify saved metadata responses and emit an enriched, still-unopened scope."""
from pathlib import Path
import csv,json,hashlib,datetime,collections,math
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(p.open()))
def csvout(p,values):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
def main():
    prop=json.loads((OUT/'PROPOSAL.json').read_text());selected=rows(OUT/'PROPOSED100_METADATA.csv')
    for name,digest in prop['input_hashes'].items():assert sha(BASE/name)==digest,name
    for name,digest in prop['output_hashes'].items():assert sha(OUT/name)==digest,name
    query=json.loads((OUT/'METADATA_QUERY_SUMMARY.json').read_text())
    for q in query['queries']:
        name={'RAW_PROVENANCE':None}
        path=next(OUT/n for n in ['RAW_PROVENANCE.csv','PRODUCT_METADATA.csv','CURRENT_OBSCORE.csv'] if sha(OUT/n)==q['sha256'])
        assert len(rows(path))==q['rows']
    provenance=rows(OUT/'RAW_PROVENANCE.csv');products=rows(OUT/'PRODUCT_METADATA.csv');current=rows(OUT/'CURRENT_OBSCORE.csv')
    ids={r['dp_id'] for r in selected};assert len(selected)==len(ids)==100
    assert len(current)==100 and {r['dp_id'] for r in current}==ids
    assert len(provenance)==100 and {r['product_id'] for r in provenance}==ids
    rawids={r['source_file'] for r in provenance};assert len(rawids)==100
    assert not rawids.intersection(prop['previous_raw_ids'])
    compact=json.loads((BASE/'literature/UPSTREAM_REFERENCED_IDS.json').read_text());full=json.loads((BASE/'literature/upstream_referenced_exposure_ids.json').read_text())
    upstream_raw=set(compact['HARPS'])|{k for k in full['records'] if k.startswith('HARPS.')}
    assert not rawids.intersection(upstream_raw)
    cur={r['dp_id']:r for r in current};prov={r['product_id']:r for r in provenance};result=[];checks=[]
    epoch=datetime.datetime(1858,11,17,tzinfo=datetime.timezone.utc)
    for r in selected:
        dp=r['dp_id'];checked={}
        for k,v in cur[dp].items():
            if k not in r:continue
            equal=v==r[k]
            if not equal:
                try:equal=float(v)==float(r[k])
                except ValueError:pass
            assert equal,(dp,k,r[k],v)
            checked[k]=equal
        allproducts=[p for p in products if p['product_id']==dp]
        science=[p for p in allproducts if p['archive_id']==dp and p['extension']=='FITS' and p['eso_category']=='SCIENCE.SPECTRUM']
        ancillary=[p for p in allproducts if p['extension']=='TAR' and p['eso_category']=='ANCILLARY.HARPSTAR']
        assert len(science)==len(ancillary)==1
        raw=prov[dp]['source_file'];assert raw.startswith('HARPS.')
        rawdate=datetime.datetime.fromisoformat(raw[len('HARPS.'):]).replace(tzinfo=datetime.timezone.utc)
        rawmjd=(rawdate-epoch).total_seconds()/86400
        offset=(rawmjd-float(r['t_min']))*86400
        assert abs(offset)<.01,(dp,offset)
        result.append(dict(r,source_url=science[0]['access_url'],raw_progenitor_id=raw,
            raw_source_url='https://dataportal.eso.org/dataPortal/file/'+raw,raw_start_utc=rawdate.isoformat(),
            raw_start_minus_metadata_seconds=offset,ancillary_archive_id=ancillary[0]['archive_id'],
            ancillary_source_url=ancillary[0]['access_url'],ancillary_access_estsize=ancillary[0]['access_estsize'],
            metadata_verification_status='PASS_ADP_RAW_ID_AND_CURRENT_METADATA',known_reference_overlap='NO_MATCH_IN_PINNED_ADP_AND_RAW_REFERENCE_INVENTORY',
            prior_search_coverage='UNKNOWN_OUTSIDE_PINNED_REFERENCE_INVENTORY'))
        checks.append(dict(dp_id=dp,raw_id=raw,current_fields_match=checked,unique_raw=True,no_prior_ADP_or_raw_overlap=True,
            no_pinned_reference_ADP_or_raw_overlap=True,raw_start_minus_metadata_seconds=offset,science_products=1,ancillary_TAR_products=1))
    csvout(OUT/'MAIN100.csv',result)
    summary=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='READY_FOR_ROOT_DECISION_AND_PROSPECTIVE_FREEZE',
        selected_exposures=100,targets=prop['represented_targets'],allocated_targets=prop['allocations'],
        input_scope_excludes=209,unique_raw_ids=100,prior_ADP_raw_matches=0,pinned_reference_ADP_raw_matches=0,
        current_metadata_rows=100,current_metadata_discrepancies=0,provenance_rows=100,science_product_rows=100,ancillary_TAR_rows=100,
        max_abs_raw_start_minus_metadata_seconds=max(abs(c['raw_start_minus_metadata_seconds']) for c in checks),
        proposed_exposure_seconds=prop['proposed_exposure_seconds'],new_target_night_pairs=prop['proposed_new_target_night_pairs'],
        selected_metadata_bytes_estimate=prop['estimated_download_bytes'],ancillary_metadata_bytes_estimate=sum(math.ceil(float(r['ancillary_access_estsize'])*1024) for r in result),
        proposed_actual_payload_estimate_method='Metadata estimates only; future acquisition measures payload and validates FITS headers.',
        metadata_network_bytes=query['total_bytes'],science_files_downloaded=0,science_arrays_opened=0,
        requirements_before_flux_access=['Root assess control workload against107 current unresolved/mapping-limited events.',
          'Freeze this exact MAIN100.csv plus frozen V1/V2 source hashes and the bounded acquisition/analysis rules before downloading or opening new flux.',
          'Keep unsuccessful inputs and all accepted hits with explicit states; do not replace selected exposures or change thresholds after seeing flux.',
          'Perform post-download FITS target/intended-coordinate/unit/BERV/frame/time/raw-provenance/hash checks against the fixed selection before analysis.',
          'Run the already-frozen V2 unchanged; its192-trial validation remains conditional, not a new estimate of sensitivity in these100 exposures.',
          'Use separate next-sample output paths and stable IDs, keeping all existing200-main results intact.'],
        overlap_limit=prop['limitations'][1],frozen_reference_commit=prop['upstream_reference_commit'],
        query_sources=[r['url'] for r in query['queries']],checks=checks,
        source_hashes={p.name:sha(p) for p in [OUT/'PROPOSAL.json',OUT/'PROPOSED100_METADATA.csv',OUT/'RAW_PROVENANCE.csv',OUT/'PRODUCT_METADATA.csv',OUT/'CURRENT_OBSCORE.csv',Path(__file__)]},
        main100_sha256=sha(OUT/'MAIN100.csv'))
    (OUT/'METADATA_VERIFICATION.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['checks','query_sources','source_hashes','requirements_before_flux_access']},indent=2))
if __name__=='__main__':main()
