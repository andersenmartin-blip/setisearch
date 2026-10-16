#!/usr/bin/env python3
"""Post-run receipt-only Danish report; no arrays, hypothesis search or fitting."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def pin(path):
    path = Path(path)
    return {'path':str(path),'bytes':path.stat().st_size,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def geometry(scope, contract):
    corefirst,corestop = scope['band']['reference_source_channel_interval']
    df = contract['geometry']['scan_metadata'][0]['df_hz']
    fch1 = contract['geometry']['scan_metadata'][0]['fch1_hz']
    halo = 1278
    def band(first,stop):
        centers = [fch1+first*df,fch1+(stop-1)*df]
        return {'source_channel_interval_half_open':[first,stop],
            'reference_carrier_count':stop-first,
            'reference_center_frequency_hz_ascending':sorted(centers),
            'nominal_reference_bin_edges_hz_ascending':[min(centers)-abs(df)/2,max(centers)+abs(df)/2],
            'nominal_reference_bandwidth_hz':(stop-first)*abs(df)}
    return {'schema':'SETI_RETAINED_BAND_AFFINE_REFERENCE_FREQUENCY_GEOMETRY_V1',
        'signed_native_channel_spacing_hz':df,'fch1_hz':fch1,
        'ON_reference':band(corefirst,corestop),
        'OFF_reference':band(corefirst-halo,corestop+halo),
        'loaded_input':band(*scope['band']['loaded_source_channel_interval']),
        'qualification':'Declared reference carriers at the common cadence midpoint, not full telescope coverage or independent channels; drift paths move outside the reference interval within the loaded halo.'}


def render(root, out, allow_pending):
    root,out = Path(root),Path(out);out.mkdir(parents=True,exist_ok=True)
    producer_path = root/'observation/PRODUCER.json'
    producer = read(producer_path)
    assert producer['status'] == 'PRODUCED_DESCRIPTIVE_REAL_FULLSCAN_ONLY'
    primary_path = root/'PHASE_primary.json';primary = read(primary_path)
    assert primary['status'] == 'ACCEPTED_DESCRIPTIVE_PHASE_ONLY'
    scope = read(root/'FROZEN_SCOPE.json')
    source = Path(__file__).resolve().parents[3]
    contract = read(source/'analysis/sixscan_burst_20261015/contract.json')
    result_path,qa_path = root/'RESULT.json',root/'QA_REPORT.json'
    final = read(result_path) if result_path.exists() else None
    qa = read(qa_path) if qa_path.exists() else None
    complete = (final is not None and final['status']=='COMPLETE_DESCRIPTIVE_REAL_FULLSCAN_QA_VERIFIED'
                and qa is not None and qa['status']=='PASS_DESCRIPTIVE_REAL_FULLSCAN_QA_ONLY')
    assert complete or allow_pending, 'Final report requires complete parent closure and independent QA'
    c = producer['output_census'];assert c['drift_grid_count']==5723 and c['OFF_halo_channels']==1278
    freq = geometry(scope,contract)
    metadata = {m['scan_id']:m for m in contract['geometry']['scan_metadata']}
    scans = []
    for m in c['scans']:
        scans.append({**m,'target':metadata[m['scan_id']]['original_header_full']['data_attributes']['source_name']})
    on = c['retained_top5_ON_ge10_count'];off = c['OFF_inventory_rows']
    lines = ['# SETI: fuld seks-scanningsanalyse af ét gemt 2017-bånd','',
        '**Uafhængig numerisk QA: PASS. Begge procesafslutninger er godkendt.**' if complete
        else '**Primærkørslen er afsluttet. Uafhængig QA og endelig procesafslutning afventes.**','']
    if on == 0 and all(v == 0 for v in off.values()):
        lines += [f'Den gennemførte søgning finder **0 bevarede ON-hypoteser med score ≥10** i dette bånd. Største ON-score er **{c["maximum_pre_OFF_ON_score"]:.9f}**. De tre komplette OFF-inventarer indeholder hver **0 hypoteser med score ≥8**. Der er derfor ingen ON-hypotese over det fastlagte snit at følge videre fra denne kørsel.','']
    else:
        lines += [f'Søgningen bevarer **{on} ON-hypoteser med score ≥10**. Af disse har **{c["OFF_compatible_retained_ON_count"]}** en kompatibel OFF-hypotese over score8, mens **{c["no_compatible_OFF_ge8_retained_ON_count"]}** ikke har en sådan algoritmisk OFF-match i den erklærede familie. Største ON-score er **{c["maximum_pre_OFF_ON_score"]:.9f}**. Dispositionerne klassificerer ikke signalernes fysiske oprindelse.','']
    lines += ['Det er en beskrivende måling på allerede eksponerede data. Scorerne er robuste residualsummer; **10 og 8 er numeriske snit, ikke kalibrerede sigma-, SNR- eller sandsynlighedsniveauer**. Resultatet dokumenterer ikke fravær af svagere eller anderledes signaler.','',
        '| Scanning | Rolle | Oprindelig retning | Referencekanaler | Største score |',
        '|---|---|---|---:|---:|']
    for i,m in enumerate(scans):
        lines.append(f'| {i+1} | {m["role"]} | {m["target"]} | {m["retained_shape"][0]:,}'.replace(',','.')+f' | {m["maximum_retained_score"]:.9f} |')
    cf = freq['ON_reference'];of = freq['OFF_reference']
    lo,hi = cf['reference_center_frequency_hz_ascending'];olo,ohi = of['reference_center_frequency_hz_ascending']
    lines += ['',
        f'Det valgte bånd er **native170 / q131**, det første i den gamle kanonisk sorterede liste over ni bevarede, tidligere efterudvalgte bånd. Den nye kørsel bruger **4.096 ON-referencekanaler**, kildeintervallet `[178794496,178798592)`, ved ét fælles referencetidspunkt. Referencekanalernes centerfrekvenser spænder fra **{lo/1e6:.9f} til {hi/1e6:.9f} MHz**; deres nominelle samlede binbredde er **{cf["nominal_reference_bandwidth_hz"]/1e3:.12f} kHz**.','',
        f'OFF-søgningen har en halo på **1.278 referencekanaler i hver side**, i alt **6.652 kanaler**, med centerfrekvenser **{olo/1e6:.9f}–{ohi/1e6:.9f} MHz** og nominel samlet binbredde **{of["nominal_reference_bandwidth_hz"]/1e3:.12f} kHz**. Drivende spor kan bevæge sig uden for referenceintervallet inden for den gemte inputhalo. Dette er referencegeometri i ét udsnit, ikke ny teleskopdækning eller survey-komplethed. De præcise affine koordinater og binrande er gemt i `FREQUENCY_GEOMETRY.json`.','',
        'Alle seks scanninger kommer fra **ét besøg den 28. april 2017**: tre ON-scanninger mod HIP98505/HD189733 og tre OFF-scanninger mod HIP97319, HIP97461 og HIP97663. De fire retninger er bevaret i deres oprindelige roller. De er ikke nye observationer eller en uafhængig genobservation af et fund. Kun det første af de ni gamle bånd er genberegnet med dette nye dokumenterede scope. Ældre ukendte kørsler kan allerede have forsøgt samme hypotesefamilie.','',
        'Søgningen omfatter alle **5.723 drifthastigheder fra −4 til +4 Hz/s**, syv overlappende fire-række-vinduer og bredder **1, 3, 9 og 33 kanaler**. Hver referencekanal bevarer en samlet topfem af forskellige native spor/bredder/vinduer. ON-listen indeholder alle disse **bevarede topfem-hypoteser**, som når 10; den er ikke en liste over samtlige scorer over 10 blandt alle afprøvede ON-hypoteser. OFF-inventaret er derimod udtømmende for alle score ≥8-nativeidentiteter i den erklærede OFF-familie, inklusive deres driftaliaser. Kanaler, vinduer, bredder og aliaser er korrelerede.','',
        '`rank_status` er **NOT_APPLIED_NO_CALIBRATION**. Ingen Gamma16-rang, p-værdi, injektionsvalidering, fysisk følsomhed, RFI-populationskvalifikation eller dokumenteret himmeloprindelse er etableret. Recovery-metadata angiver alene, at injektions-recovery **ikke er relevant** for de virkelige data. Ingen recovery-rate er målt.','']
    pr = primary['receipt']
    if complete:
        qr = next(p['receipt'] for p in final['phases'] if p['phase']=='qa')
        lines += [f'Uafhængig QA genberegner alle seks komplette søgninger, preprocessing, bevarede kort, OFF-inventarer og relevante matchregler. Primær- og QA-processerne bruger henholdsvis **{pr["whole_child_CPU_s"]:.6f}** og **{qr["whole_child_CPU_s"]:.6f} CPU-sekunder**, i alt **{final["whole_children_CPU_s"]:.6f} CPU-sekunder**. Største målte RSS er **{max(pr["peak_RSS_bytes"],qr["peak_RSS_bytes"]):,} bytes**. Ingen ny teleskopforespørgsel eller teleskopbyte er hentet; udgiften er **0 DKK**.','']
    else:
        lines += [f'Primærprocessens fulde målte CPU-tid er **{pr["whole_child_CPU_s"]:.6f} sekunder**; dens maksimale RSS er **{pr["peak_RSS_bytes"]:,} bytes**. QA er endnu ikke endeligt godkendt.','']
    lines += ['Kildekode og scope blev offentliggjort og læst tilbage før kørslen ved commit `c721a789db23649b85ef8d01a6e5d4b801966679`. Det nye case-ID er `SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B00`. Begge gamle bankforløb, pensionerede eksponerede case-ID’er, A/B-status FAIL_CLOSED og lukkede 2016-/2019-ruter er uændrede. Kontrolpunktet er fortsat 20. oktober 2026.','',
        f'Den bevarede payload indeholder alle **{producer["payload_receipt"]["arrays_written"]} numeriske arrays**, inklusive seks originale rå arrays, fulde søgekort, aliasgeometri og OFF-inventarer; den fylder **{producer["payload_receipt"]["payload_bytes"]:,} bytes**. Payload, præcise kildepins og uafhængige kontrolbilag indgår i reproduktionspakken. `SCAN_MAXIMA.csv` og denne rapport er direkte afledt af procesbilagene; rapportgeneratoren åbner ingen rådata og udfører ingen ny søgning.','']
    (out/'RESULTS_DA.md').write_text('\n'.join(lines))
    (out/'FREQUENCY_GEOMETRY.json').write_text(json.dumps(freq,indent=2,sort_keys=True)+'\n')
    with (out/'SCAN_MAXIMA.csv').open('w',newline='') as stream:
        fields=['scan_id','role','target','reference_carriers','maximum_retained_score']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for m in scans:
            writer.writerow({k:m[k] for k in fields if k!='reference_carriers'}|{'reference_carriers':m['retained_shape'][0]})
    inputs=[pin(producer_path),pin(primary_path),pin(root/'FROZEN_SCOPE.json')]
    if complete:inputs += [pin(result_path),pin(qa_path)]
    report={'status':'COMPLETE_RECEIPT_DERIVED_REPORT' if complete else 'PENDING_QA_RECEIPT_DERIVED_REPORT',
        'identity':scope['identity'],'receipt_inputs':inputs,'report_generator':pin(__file__),
        'raw_arrays_opened':False,'new_searches_or_hypotheses':0,
        'outputs':[pin(out/name) for name in ['RESULTS_DA.md','FREQUENCY_GEOMETRY.json','SCAN_MAXIMA.csv']]}
    (out/'REPORT_MANIFEST.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':report['status'],'outputs':report['outputs']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--allow-pending',action='store_true')
    args=parser.parse_args();render(args.root,args.out,args.allow_pending)
