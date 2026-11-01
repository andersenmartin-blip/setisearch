"""Join two agent visual reviews without altering any historical catalog."""
from pathlib import Path
import csv,json,collections,datetime,hashlib,zipfile
OUT=Path(__file__).resolve().parent;V2=OUT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((OUT/'VISUAL_NOTES_PRIMARY.json').read_text());b=json.loads((OUT/'VISUAL_NOTES_SECOND_AGENT.json').read_text());mapping=json.loads((OUT/'MAPPING_AUDIT.json').read_text());plan=json.loads((OUT/'PLAN.json').read_text());hits=list(csv.DictReader((OUT/'SELECTED_HITS.csv').open()));index=json.loads((OUT/'FIGURE_INDEX.json').read_text())
assert set(a)==set(b)=={str(int(h['review_id'][-4:])) for h in hits}
conflicts=[k for k in a if a[k][0]!=b[k][0]];assert not conflicts,conflicts
types={'A':'PROVISIONAL_DETECTOR_ARTIFACT','U':'UNRESOLVED_SPECTRAL_FEATURE','M':'INSUFFICIENT_RAW_MAPPING','O':'PROVISIONAL_ATMOSPHERIC_OI'}
rows=[]
for h in hits:
    k=str(int(h['review_id'][-4:]));ev=next(r for r in mapping['events'] if r['review_id']==h['review_id']);fig=next(r for r in index if r['review_id']==h['review_id']);code,reason=a[k]
    assert (code=='M')==(not ev['mapping_supported'])
    rows.append(dict(review_id=h['review_id'],dp_id=h['dp_id'],canonical_target=h['canonical_target'],fitted_center_bary_air_angstrom=h['fitted_center_bary_air_angstrom'],prior_followup_status='INSUFFICIENT_RAW_MAPPING',followup_status=types[code],evidence=reason,second_reviewer_evidence=b[k][1],reference_mapping_supported=ev['mapping_supported'],covering_orders=json.dumps(ev['covering_orders']),edge_truncated_orders=json.dumps(ev['edge_truncated_orders']),coordinates_changed=False,final_origin_confirmed=False,visual_review_agreement=True,figure=f'figures/REVIEW_{fig["page"]:02d}.png',figure_row=fig['row']))
with (OUT/'FOLLOWUP_DISPOSITIONS.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
counts=dict(collections.Counter(r['followup_status'] for r in rows))
for rel,digest in plan['input_hashes'].items():assert sha(V2/rel)==digest
summary=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='COMPLETED_WITH_FOUR_MAPPING_LIMITATIONS',events=43,exposures=26,source_products_verified=52,covering_order_records=81,complete_cutouts=80,edge_truncated_orders=1,reference_orders_by_exposure=57,geometry_supported_events=39,remaining_mapping_limited_events=4,remaining_ids=[r['review_id'] for r in rows if not r['reference_mapping_supported']],disposition_counts=counts,all_origins_final_confirmed=False,coordinates_changed=False,original_hashes_unchanged=True,visual_reviewers=2,review_agreement_events=43,independent_human_validation=False,geometry_caveat='Post-hoc broader fixed-reference evidence supplements the failed narrow windows. It does not erase those failures or establish exact wavelength calibration or origin.',comparability_caveat='The broader five-window criteria were applied to all43 selected mapping-limited events only, not retroactively to all333; historical review methods remain heterogeneous.',numerical_verification='All80 wider cutouts preserve original21x25 raw and41-point native arrays exactly; five cutouts from first/middle/last metadata-selected exposures independently rebuilt in a fresh process by this agent.',hashes={str(p.relative_to(OUT)):sha(p) for p in [OUT/'PLAN.json',OUT/'MAPPING_AUDIT.json',OUT/'VISUAL_NOTES_PRIMARY.json',OUT/'VISUAL_NOTES_SECOND_AGENT.json',OUT/'OUTPUT_VERIFICATION.json',Path(__file__)]})
(OUT/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
report='''# Opfølgning på 43 usikre HARPS billedkoblinger

**39 af de 43 hændelser har nu tilstrækkelig støtte fra bredere, faste referenceområder.** Ingen råkoordinater er flyttet. Efter to separate agentgennemgange er udfaldet otte sandsynlige detektorartefakter, 31 uafklarede spektralstrukturer og fire fortsat utilstrækkeligt kortlagte tilfælde. Alle ophavsvurderinger er foreløbige.

| Foreløbig status efter opfølgning | Hændelser |
|---|---:|
| Sandsynlig detektorartefakt | 8 |
| Uafklaret spektralstruktur | 31 |
| Utilstrækkelig råbilledkortlægning | 4 |

[Alle 43 dispositioner med to begrundelser](FOLLOWUP_DISPOSITIONS.csv) · [maskinlæsbar sammenfatning](SUMMARY.json) · [figurer](FIGURES.md).

## Hvad der er undersøgt

Gruppen var fastlagt som alle 43 hændelser med kortlægningsbegrænsning i den tidligere samlede tabel. De stammer fra 26 eksponeringer. Alle 52 tilhørende rå- og native-produkter er hashkontrolleret. Den fastlåste V2-detektor og dens oprindelige resultater er uændrede.

Den gamle lokale kontrol krævede to korte referenceintervaller på hver sin side af en hændelse. Mange lå tæt på en ordensrand eller andre kandidatpositioner, så der manglede referencepixels. Den nye plan blev skrevet før de bredere områder blev undersøgt: fem faste intervaller fordelt over hver dækkende orden, med alle gemte kandidaters nærmeste ±80 pixels udeladt. Mindst tre intervaller skal have tilstrækkelig støtte, median rå/native-korrelation over 0,8 og små kontinuumforskydninger. Fiberprofilen samles ved den flydende polynomiumposition, så skiftende heltalsafrunding ikke flytter den samlede profil. Koordinater og orientering er ikke tilpasset kandidatens kerne. [Plan](PLAN.json) · [alle referenceværdier](MAPPING_AUDIT.json).

Dette er en efterfølgende kontrol af kendte problemer. Den sletter ikke de gamle fejlede intervaller og giver ikke en kalibreret statistisk ophavstest. Kriterierne er kun anvendt på denne gruppe, så forskellige historiske opfølgningsmetoder skal fortsat fremgå af den samlede rapport.

## Resultatet af billedgennemgangen

De otte foreløbige artefakter er V2-0106, 0155, 0186, 0217, 0228, 0235, 0306 og 0326. De har kompakte eller skrå/tværgående råpixelspor og typisk en skarp top i kun den ene overlappende orden. De lyse nabofibersignaler er vist som kontekst og bruges ikke alene som forklaring.

De 31 uafklarede strukturer er hovedsagelig bredere toppe med fiberforenelig råprofil og ofte støtte fra overlappende ordener. Flere blå randudsnit har meget svagt kontinuum; store normaliserede udsving, især V2-0244, betyder derfor ikke tilsvarende stor fysisk emission. De kræver epokesammenligning og konkret naturlig linjeidentifikation. De er ikke påviste teknologiske signaler.

Fire hændelser forbliver kortlægningsusikre efter de fastlagte kriterier:

| Hændelse | Dækkende orden med begrænsning | Median rå/native-korrelation |
|---|---:|---:|
| V2-0149 | 1; orden 0 er randafskåret | 0,547 |
| V2-0231 | 3 | 0,766 |
| V2-0232 | 3 | 0,766 |
| V2-0333 | 70 | 0,768 |

Kontinuumpositionerne i disse bredere områder er tæt på den forudsagte fiber, men spektralkorrelationen opfylder ikke grænsen. Det er ikke bevis for forkerte headerkoordinater; det er en bevaret begrænsning. De fire gamle tilfælde med målt lokal forskydning var en anden delmængde: V2-0149, 0186, 0221 og 0284. De sidste tre støttes nu af de bredere faste referencer uden en koordinatændring.

## Kontrol og reproduktion

Der er 81 dækkende ordensregistreringer: 80 komplette udsnit og én bevaret randbegrænsning. To agenter har hver set samtlige 43 hændelser og alle tilgængelige ordener; alle 43 foreløbige koder stemmer. Det er ikke uafhængig menneskelig validering.

Alle 80 nye, bredere råudsnit indeholder de oprindelige 21×25 råpixels uændret, og alle 41 native spektralværdier/bølgelængder er identiske. En frisk proces genopbyggede fem bredere udsnit fra første, midterste og sidste eksponering i metadatarækkefølgen med præcis samme resultat. [Efterkontrol](OUTPUT_VERIFICATION.json).

Brug en separat arbejdskopi. Input ligger i de tidligere batch02-checkpoints; denne opfølgning henter ingen nye teleskopdata. Kør `python v2/mapping43_followup/run_mapping.py`, derefter `plot_mapping.py` og `verify_outputs.py`. De eksplicitte visuelle noter ligger i `VISUAL_NOTES_PRIMARY.json` og `VISUAL_NOTES_SECOND_AGENT.json`; `finalize.py` samler dem, men udfører ikke en ny automatisk ophavsvurdering. Afhængigheder er Python, NumPy, SciPy, Astropy og Matplotlib som i hovedprojektet.

`MAPPING43_EVIDENCE.zip` indeholder kode, planer, tabeller, noter, verificerede numeriske udsnit og referencekontroller. PNG-figurer publiceres separat. [Arkivmanifest](EVIDENCE_ARCHIVE.json).
'''
(OUT/'README.md').write_text(report)
figs='# Alle 43 kortlægningsopfølgninger\n\nNative profiler, central råfiber og bredere råoverskud. Alle dækkende ordener vises; de fire fortsat begrænsede tilfælde markeres.\n\n'
for n in range(1,12):figs+=f'![Hændelser side {n}](figures/REVIEW_{n:02d}.png)\n\n'
figs+='## Faste kandidatfri referenceprofiler\n\n'
for n in range(1,6):figs+=f'![Referencer side {n}](figures/REFERENCES_{n:02d}.png)\n\n'
(OUT/'FIGURES.md').write_text(figs)
archive=OUT/'MAPPING43_EVIDENCE.zip';files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.zip','.png','.pyc'] and p.name!='EVIDENCE_ARCHIVE.json'];members=[dict(path=str(p.relative_to(V2.parent)),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,p.relative_to(V2.parent))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for m in members:assert hashlib.sha256(z.read(m['path'])).hexdigest()==m['sha256']
(OUT/'EVIDENCE_ARCHIVE.json').write_text(json.dumps(dict(filename=archive.name,bytes=archive.stat().st_size,sha256=sha(archive),members=len(members),files=members),indent=2)+'\n')
print(json.dumps(dict(counts=counts,archive_bytes=archive.stat().st_size,archive_sha256=sha(archive)),indent=2))
