"""Finalize the complete descriptive visual record without changing source dispositions."""
from pathlib import Path
import csv,json,collections,hashlib
O=Path(__file__).resolve().parent
read=lambda p:list(csv.DictReader(p.open()))
rows=read(O/'REVIEW_INDEX.csv');targets=read(O/'TARGET_COUNTS.csv');s=json.loads((O/'ATLAS_SUMMARY.json').read_text());notes=json.loads((O/'VISUAL_PAGE_NOTES.json').read_text())
assert len(rows)==s['accepted_events'] and set(notes)=={str(i) for i in range(1,s['pages']+1)}
audit=json.loads((O/'NUMERICAL_AUDIT.json').read_text());assert audit['status']=='PASSED'
review={'status':'COMPLETE_DESCRIPTIVE_VISUAL_PASS','reviewer':'epoch_64 agent; not independent human validation','pages_reviewed':s['pages'],'events_reviewed':len(rows),'all_panels_readable':True,'origin_labels_assigned':False,'all_production_origin_statuses_preserved':'UNREVIEWED','events':[{'candidate_id':r['candidate_id'],'atlas_file':r['atlas_file'],'panel':int(r['panel']),'visual_inspected':True,'descriptive_followup_route':r['descriptive_followup_route'],'production_origin_status':'UNREVIEWED'} for r in rows],'page_notes':notes}
(O/'VISUAL_REVIEW.json').write_text(json.dumps(review,indent=2)+'\n')
s['status']='COMPLETE_DESCRIPTIVE_ATLAS_AND_VISUAL_PASS';s['visual_reviewed_events']=len(rows);s['visual_reviewed_pages']=s['pages'];s['numerical_audit']='PASSED: first/middle/last direct FITS and scalar audit'
s['original_two_OI_by_line']={str(w):sum(r['original_two_OI_0p03_flag']=='True' and float(r['nearest_original_two_OI_air_angstrom'])==w for r in rows) for w in [5577.339,6300.304]}
s['OI_flagged_events_also_matching_old333']=sum(r['original_two_OI_0p03_flag']=='True' and int(r['old333_match_count'])>0 for r in rows)
(O/'ATLAS_SUMMARY.json').write_text(json.dumps(s,indent=2)+'\n')
followup=[{k:r[k] for k in ['candidate_id','target','dp_id','date_obs','fitted_center_bary_air_angstrom','descriptive_followup_route','old333_match_count','old333_matched_review_ids','original_two_OI_0p03_flag','posthoc_OI6363_0p03_flag','atlas_file','panel','origin_status']} for r in rows]
with (O/'FOLLOWUP_ROUTES.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(followup[0]) if followup else ['candidate_id','origin_status']);w.writeheader();w.writerows(followup)
table='\n'.join(f"| {r['target']} | {r['analyzed_exposures']} | {r['accepted_V2_events']} | {r['events_with_old333_match']} | {r['original_two_OI_flags']} |" for r in targets)
text=f'''# Første gennemgang af 100 nye HARPS-eksponeringer

Alle **{len(rows)} accepterede V2-hændelser** i den nye prøve er gennemgået i et komplet 1D-atlas: {s['pages']} sider med otte hændelser pr. side. Hændelserne findes i {s['exposures_with_hits']} af de 100 analyserede eksponeringer og på alle {s['targets_with_hits']} stjerner. Alle {len(rows)} produktionsstatusser er fortsat **UNREVIEWED**. Gennemgangen tildeler ingen fysisk oprindelse fra 1D-formen.

**94 hændelser** ligger inden for ±0,03 Å barycentrisk af mindst ét tidligere accepteret hit fra samme stjerne. Der er 341 sådanne parforbindelser. Det er en positionssammenligning mellem udvalgte hits, ikke uafhængig validering eller fuld alle-epoke-kontrol. Et manglende match betyder ikke, at andre epoker mangler struktur på stedet. De gemte tidligere statusser i matchtabellen er kun kontekst fra den oprindelige 333-hændelsers tabel; efterfølgende råpixelopfølgninger ligger særskilt.

**22 hændelser** får det uændrede to-linje-nærhedsflag: 13 nær O I 5577,339 Å og ni nær 6300,304 Å i omtrentlige topocentriske luftkoordinater. 18 af de 22 har også et gammelt accepteret positionsmatch. Ingen af de nye accepterede hændelser ligger inden for det særskilte efterfølgende ±0,03 Å-vindue omkring O I 6363,776 Å. Dette er nærhedsflag, ikke bekræftet nattehimmelsemission eller frasortering.

## Næste evidens, hændelse for hændelse

[Alle opfølgningsruter](FOLLOWUP_ROUTES.csv) følger reglerne, som blev fastlagt før de nye hits blev læst. De er arbejdsruter, ikke en rangering af sandsynligheden for teknologi.

| Arbejdsrute | Hændelser | Nødvendig kontrol |
|---|---:|---|
| Ingen gammel accepteret positionspartner og intet O I-flag | 238 | Dækkende native-ordener, råpixelmorfologi og alle tilgængelige epoker |
| Gammel accepteret positionspartner, uden O I-flag | 76 | Sammenhold tidligere kontekst, og kontrollér den nye eksponering selvstændigt |
| O I-nærhedsflag | 22 | Samtidig skyfiber/kalibrering, flere iltlinjer og epokeadfærd |

Alle 336 paneler er visuelt inspiceret. De viser både brede blå/CH-nabolagsstrukturer, smalle eller asymmetriske kerner og mere jævne profiler. Nogle brede strukturer ligner hinanden på tværs af de accepterede epoker; dette atlas erstatter ikke den separate alle-epoke-metode. Mange spidse kerner er højere eller smallere end den gemte Gaussmodel, men 1D-formen alene afgør ikke, om signalet stammer fra detektoren, himlen, instrumentet eller kilden. Særligt dybe nabotrender er bevaret i figurerne og dokumenteret i [sidenoterne](VISUAL_PAGE_NOTES.json).

## Stjerneoversigt

| Stjerne | Analyserede epoker | Accepterede hændelser | Med gammel positionspartner | O I-to-linje-flag |
|---|---:|---:|---:|---:|
{table}

Hændelsesantal er ikke antal uafhængige kilder eller eksponeringer. HD120411 bidrager eksempelvis med 79 accepterede hændelser i syv eksponeringer. [Eksponeringstællinger](EXPOSURE_COUNTS.csv), [faste 100 Å-bølgelængdeintervaller](WAVELENGTH_COUNTS.csv) og [samtlige 341 positionsforbindelser](OLD_MATCHES.csv) gør tællingerne efterprøvbare.

## Metode og kontrol

[Planen](PLAN.json) blev frosset, før nye hitlister eller fluxværdier blev inspiceret. Atlaset bruger de gemte 101 samples omkring hvert seed, den gemte lineære baggrund og sidebåndets MAD-skala. Den orange kurve er den gemte faste Gaussmodel; der er ingen ny tilpasning af centrum, bredde eller tærskel. Visningen dækker ±0,5 Å. Det lyse felt markerer de centrale ±12 samples, ikke et statistisk konfidensinterval. Scores og A/MAD er ikke kalibreret statistisk signifikans.

Topocentriske koordinater bruger λ_top ≈ λ_bary/(1+BERV/c). Omregningen er en klassisk tilnærmelse og bruges kun til de beskrevne nærhedsflag. Ingen stjerne-RV antages, og ingen ny detektor eller oprindelsesklassifikation indføres.

Alle 336 udtræk har komplet sampleområde og positiv, endelig MAD-skala; ingen hændelser eller paneler blev udeladt. [Inputkontrollen](INPUT_CHECKS.json) verificerer filhash og metadata for alle 93 eksponeringer med hits samt uændrede hit- og dispositionstabeller. [Den numeriske kontrol](NUMERICAL_AUDIT.json) genberegner første, midterste og sidste kandidat direkte fra FITS med skalararitmetik og kontrollerer gamle matches og begge adskilte O I-flag. Den bestod. Dette er samme agents kontrol i en frisk proces, ikke uafhængig menneskelig validering.

[Hændelsesindekset](REVIEW_INDEX.csv) linker hver hændelse til dens panel og gemte NPZ-profil. [Den visuelle kontrol](VISUAL_REVIEW.json) registrerer alle 336 gennemgåede paneler. [Atlasindekset](ATLAS_INDEX.md) giver adgang til alle 42 sider. `build_atlas.py`, `audit_atlas.py` og `finalize_report.py` kan genskabe beregninger og rapport i en separat arbejdskopi med projektets Python-afhængigheder; de manuelle sidenoter indgår som kilde til rapporten. De frosne produktionsresultater og tidligere tabeller ændres ikke.
'''
(O/'README.md').write_text(text)
(O/'ATLAS_INDEX.md').write_text('# Komplet extension02-atlas\n\nAlle hændelser bevarer UNREVIEWED-status.\n\n'+'\n'.join(f'- [Side {i:02d}: V2E2-{(i-1)*8+1:04d}–V2E2-{min(i*8,len(rows)):04d}](atlas/ATLAS_{i:03d}.png)' for i in range(1,s['pages']+1))+'\n')
assert hashlib.sha256((O/'PLAN.json').read_bytes()).hexdigest()=='8505f181cd9e989a928ca86edfbe570de47120cf66bfe06473ca26d4cbd0e5f2'
print('Finalized',len(rows),'events,',len(notes),'visually reviewed pages')
