#!/usr/bin/env python3
"""Inventory only: validate retrieved Rubin development rows, no dimming search."""
import csv,hashlib,json,math
from collections import Counter,defaultdict
from pathlib import Path
from astropy.time import Time
P=Path(__file__).resolve().parent
F=json.loads((P/'DEVELOPMENT_FREEZE.json').read_text())
IDS=F['selected_ids']

def load(name): return json.loads((P/name).read_text(),parse_int=str)
def finite(x):return isinstance(x,(float,int)) and math.isfinite(x)
def valid(r):return finite(r.get('r:scienceFlux')) and finite(r.get('r:scienceFluxErr')) and r['r:scienceFluxErr']>0
def utc(mjd):return Time(mjd,format='mjd',scale='tai').utc.isot
def write_csv(name,data):
    with (P/name).open('w',newline='') as f:
        w=csv.DictWriter(f,list(data[0]));w.writeheader();w.writerows(data)

sources=load('raw/development_sources.json');forced=load('raw/development_forced.json')
flags=['forced_PsfFlux_flag','forced_PsfFlux_flag_edge','forced_PsfFlux_flag_noGoodPixels','psfFlux_flag','psfFlux_flag_edge','psfFlux_flag_noGoodPixels','centroid_flag','pixelFlags_bad','pixelFlags_crCenter','pixelFlags_edge','pixelFlags_injected','pixelFlags_injectedCenter','pixelFlags_injected_template','pixelFlags_injected_templateCenter','pixelFlags_nodata','pixelFlags_nodataCenter','pixelFlags_offimage','pixelFlags_saturatedCenter','pixelFlags_streakCenter','pixelFlags_suspectCenter','isDipole','glint_trail']
checks=[]
for kind,data,idcol in [('sources',sources,'diaSourceId'),('forced',forced,'diaForcedSourceId')]:
    assert {r['r:diaObjectId'] for r in data}<=set(IDS)
    for r in data:
        for field in ['diaObjectId',idcol,'visit']:
            v=r['r:'+field];assert isinstance(v,str) and v.isdigit() and 0<=int(v)<2**63,(kind,field,v)
        assert finite(r['r:midpointMjdTai']) and r['r:band'] in ('u','g','r','i','z','y')
    identities=Counter(r['r:'+idcol] for r in data)
    checks.append({'stream':kind,'rows':len(data),'distinct_objects':len({r['r:diaObjectId'] for r in data}),
                   'unique_measurement_ids':len(identities),'duplicate_id_rows':sum(n-1 for n in identities.values()),
                   'valid_direct_science_flux_error_rows':sum(valid(r) for r in data),
                   'mjd_tai_min':min(r['r:midpointMjdTai'] for r in data),'mjd_tai_max':max(r['r:midpointMjdTai'] for r in data),
                   'utc_min':utc(min(r['r:midpointMjdTai'] for r in data)),'utc_max':utc(max(r['r:midpointMjdTai'] for r in data)),
                   'input_sha256':hashlib.sha256((P/('raw/development_'+('sources' if kind=='sources' else 'forced')+'.json')).read_bytes()).hexdigest()})

objectrows=[];bandrows=[]
for oid in IDS:
    src=[r for r in sources if r['r:diaObjectId']==oid];fp=[r for r in forced if r['r:diaObjectId']==oid]
    assert src
    objectrows.append({'diaObjectId':oid,'development_only':True,'source_rows':len(src),'forced_rows':len(fp),
                       'source_distinct_visits':len({r['r:visit'] for r in src}),
                       'source_utc_nights':len({utc(r['r:midpointMjdTai'])[:10] for r in src}),
                       'forced_utc_nights':len({utc(r['r:midpointMjdTai'])[:10] for r in fp}),
                       'source_bands':'|'.join(sorted({r['r:band'] for r in src})),
                       'forced_bands':'|'.join(sorted({r['r:band'] for r in fp})),
                       'first_source_utc':utc(min(r['r:midpointMjdTai'] for r in src)),
                       'last_source_utc':utc(max(r['r:midpointMjdTai'] for r in src)),
                       'main_window_source_rows':sum('2026-10-01'<=utc(r['r:midpointMjdTai'])<'2026-11-01' for r in src),
                       'main_window_forced_rows':sum('2026-10-01'<=utc(r['r:midpointMjdTai'])<'2026-11-01' for r in fp),
                       'sources_passing_all_listed_flags_explicit_false':sum(all(r.get('r:'+f) is False for f in flags) for r in src),
                       'valid_gaia_annotations':'|'.join(sorted({r.get('f:xm_gaiadr3_DR3Name','') for r in src if str(r.get('f:xm_gaiadr3_DR3Name','')).startswith('Gaia DR3 ')})),
                       'Gaia_association_independently_verified':False})
    for stream,data in [('source',src),('forced',fp)]:
        for band in sorted({r['r:band'] for r in data}):
            subset=[r for r in data if r['r:band']==band];usable=[r for r in subset if valid(r)]
            positive=[r for r in usable if r['r:scienceFlux']>0]
            bandrows.append({'diaObjectId':oid,'stream':stream,'band':band,'rows':len(subset),
                             'unique_visits':len({r['r:visit'] for r in subset}),
                             'unique_utc_nights':len({utc(r['r:midpointMjdTai'])[:10] for r in subset}),
                             'valid_direct_science_flux_error_rows':len(usable),
                             'positive_direct_science_flux_error_rows':len(positive),
                             'first_utc':utc(min(r['r:midpointMjdTai'] for r in subset)),
                             'last_utc':utc(max(r['r:midpointMjdTai'] for r in subset)),
                             'main_window_rows':sum('2026-10-01'<=utc(r['r:midpointMjdTai'])<'2026-11-01' for r in subset),
                             'positive_science_rows_before_october':sum(utc(r['r:midpointMjdTai'])<'2026-10-01' for r in positive),
                             'quality_flags_available':stream=='source',
                             'passing_all_listed_flags_explicit_false':sum(all(r.get('r:'+f) is False for f in flags) for r in subset) if stream=='source' else '',
                             'readiness_is_sampling_only':True})
write_csv('DEVELOPMENT_OBJECT_INVENTORY.csv',objectrows);write_csv('DEVELOPMENT_BAND_COVERAGE.csv',bandrows)
flagtable={f:dict(Counter('ABSENT' if 'r:'+f not in r else 'null' if r['r:'+f] is None else str(r['r:'+f]) for r in sources)) for f in flags}
summary={'status':'REAL_RUBIN_DEVELOPMENT_ACCESS_VALIDATED_NO_MAIN_SEARCH','selected_objects':20,'retrieved_source_objects':len(objectrows),
         'retrieved_forced_objects':sum(r['forced_rows']>0 for r in objectrows),'streams':checks,
         'source_schema_versions':dict(Counter(r.get('f:lsst_schema_version','ABSENT') for r in sources)),
         'source_observation_reasons':dict(Counter(r.get('r:observation_reason','ABSENT') for r in sources)),
         'source_flag_inventory':flagtable,
         'source_timeWithdrawnMjdTai_presence':dict(Counter('present' if 'r:timeWithdrawnMjdTai' in r else 'absent' for r in sources)),
         'forced_timeWithdrawnMjdTai_presence':dict(Counter('present' if 'r:timeWithdrawnMjdTai' in r else 'absent' for r in forced)),
         'source_objects_with_at_least_one_band_three_positive_pre_october_rows':len({r['diaObjectId'] for r in bandrows if r['stream']=='source' and r['positive_science_rows_before_october']>=3}),
         'forced_objects_with_at_least_one_band_three_positive_pre_october_rows':len({r['diaObjectId'] for r in bandrows if r['stream']=='forced' and r['positive_science_rows_before_october']>=3}),
         'criteria_note':'Three positive pre-October rows is an inventory descriptor only, not a baseline-quality or main eligibility criterion. Final method is separate.',
         'time_conversion':'Astropy Time(mjd, format=mjd, scale=tai).utc; original MJDTAI retained. Flux units nJy from API schema.',
         'flux_handling':'Direct scienceFlux/scienceFluxErr retained separately for source-centroid and object-forced streams; no difference+template reconstruction and no magnitude/dimming search.',
         'ID_handling':'JSON integers parsed to exact decimal strings; validated against64bit range; never float. Original rawresponse preserved.',
         'limitations':['Alert-selected development objects are not yet independentGaia-verified stars.','Forced stream has no returned quality flags; missing flags and withdrawal values are not false.','Instrument/packet provenance is officialFink RubinAPI, lsstschemas, timestamps and injected flags; cutout validation separate.','API catalog completeness and absence of older/missing alerts are not inferred.']}
(P/'DEVELOPMENT_VALIDATION.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('source_flag_inventory','limitations')},indent=2))
