#!/usr/bin/env python3
"""Receipt-only report for the new eight-band cohort plus completed B00.

No raw or payload arrays are opened. Failed/incomplete bands remain in the
planned-case table, with no fabricated zeros and no contribution to verified
scientific totals. This post-run rendering performs no hypothesis search.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

CASE_PASS='COMPLETE_DESCRIPTIVE_REAL_FULLSCAN_QA_VERIFIED'
QA_PASS='PASS_DESCRIPTIVE_REAL_FULLSCAN_QA_ONLY'
COHORT_PASS='COMPLETE_EIGHT_BAND_DESCRIPTIVE_COHORT_QA_VERIFIED'
TERMINAL_COHORT={COHORT_PASS,'INCOMPLETE_COHORT_RETAINED_NO_RETRY'}
PREFIX='SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B'


def read(path):
    return json.loads(Path(path).read_text())


def pin(path):
    path=Path(path)
    return {'path':str(path),'bytes':path.stat().st_size,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def humanint(value):
    return f'{int(value):,}'.replace(',','.')


def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')


def csv_write(path,rows,fields):
    with Path(path).open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader();writer.writerows({k:r.get(k) for k in fields} for r in rows)


def frequency(scope,meta):
    a,b=scope['band']['reference_source_channel_interval'];df=meta['df_hz'];fch1=meta['fch1_hz']
    def interval(first,stop):
        centers=sorted([fch1+first*df,fch1+(stop-1)*df])
        return {'source_channel_interval_half_open':[first,stop],
            'reference_carriers':stop-first,'nominal_bandwidth_hz':(stop-first)*abs(df),
            'center_frequencies_hz_ascending':centers,
            'nominal_bin_edges_hz_ascending':[centers[0]-abs(df)/2,centers[1]+abs(df)/2]}
    return {'ON_reference':interval(a,b),'OFF_reference':interval(a-1278,b+1278),
        'loaded_source':interval(*scope['band']['loaded_source_channel_interval']),
        'signed_df_hz':df,'fch1_hz':fch1}


def collect(case_root,index,contract,input_pins):
    root=Path(case_root);scope_path=root/'FROZEN_SCOPE.json';scope=read(scope_path)
    assert scope['identity']==f'{PREFIX}{index:02d}'
    if index:
        assert scope['canonical_index']==index
    input_pins.append(pin(scope_path))
    result_path=root/'RESULT.json';result=read(result_path) if result_path.exists() else None
    qa_path=root/'QA_REPORT.json';qa=read(qa_path) if qa_path.exists() else None
    producer_path=root/'observation/PRODUCER.json'
    producer=read(producer_path) if producer_path.exists() else None
    for p in [result_path,qa_path,producer_path]:
        if p.exists():input_pins.append(pin(p))
    complete=(result is not None and result['status']==CASE_PASS and
              qa is not None and qa['status']==QA_PASS and producer is not None and
              producer['status']=='PRODUCED_DESCRIPTIVE_REAL_FULLSCAN_ONLY' and
              len(result['phases'])==2 and all(p['status']=='ACCEPTED_DESCRIPTIVE_PHASE_ONLY' for p in result['phases']))
    band=scope['band'];freq=frequency(scope,contract['geometry']['scan_metadata'][0])
    row={'canonical_index':index,'identity':scope['identity'],'native_chunk_index':band['native_chunk_index'],
        'core_q':band['core_q'],'status':result['status'] if result else 'NO_FINAL_RECEIPT',
        'verified_complete':complete,'scope_sha256':pin(scope_path)['sha256'],
        'ON_reference_bandwidth_hz':freq['ON_reference']['nominal_bandwidth_hz'],
        'OFF_reference_bandwidth_hz':freq['OFF_reference']['nominal_bandwidth_hz'],
        'ON_center_frequency_min_hz':freq['ON_reference']['center_frequencies_hz_ascending'][0],
        'ON_center_frequency_max_hz':freq['ON_reference']['center_frequencies_hz_ascending'][1]}
    failure_log=root/'process_qa/stderr.log'
    if not complete and failure_log.exists():
        input_pins.append(pin(failure_log))
        if 'BadZipFile' in failure_log.read_text():
            row['failure_diagnostic']='BadZipFile while opening saved numerical NPZ payload during independent QA'
    scans=[];qrow={'canonical_index':index,'identity':scope['identity'],'verified_complete':complete,
        'qa_status':qa['status'] if qa else 'NO_QA_RECEIPT','checks':None,'maximum_absolute_errors_json':None}
    if complete:
        c=producer['output_census'];assert c['rank_status']=='NOT_APPLIED_NO_CALIBRATION'
        assert c['drift_grid_count']==5723 and c['OFF_halo_channels']==1278
        assert c['ON_ge10_is_retained_per_carrier_top5_not_exhaustive_threshold_census'] is True
        assert c['OFF_ge8_inventory_is_exhaustive_declared_native4_family'] is True
        row.update(maximum_ON_score=c['maximum_pre_OFF_ON_score'],
            maximum_OFF_score=max(s['maximum_retained_score'] for s in c['scans'] if s['role']=='OFF'),
            retained_top5_ON_ge10_count=c['retained_top5_ON_ge10_count'],
            OFF_ge8_inventory_rows=sum(c['OFF_inventory_rows'].values()),
            OFF_compatible_retained_ON_count=c['OFF_compatible_retained_ON_count'],
            no_compatible_OFF_ge8_retained_ON_count=c['no_compatible_OFF_ge8_retained_ON_count'],
            whole_children_CPU_s=result['whole_children_CPU_s'],
            peak_child_RSS_bytes=max(p['receipt']['peak_RSS_bytes'] for p in result['phases']),
            payload_bytes=producer['payload_receipt']['payload_bytes'],
            payload_arrays=producer['payload_receipt']['arrays_written'])
        metas={m['scan_id']:m for m in contract['geometry']['scan_metadata']}
        for s in c['scans']:
            m=metas[s['scan_id']]
            scans.append({'canonical_index':index,'identity':scope['identity'],
                'native_chunk_index':band['native_chunk_index'],'core_q':band['core_q'],
                'scan_id':s['scan_id'],'role':s['role'],
                'target':m['original_header_full']['data_attributes']['source_name'],
                'reference_carriers':s['retained_shape'][0],
                'maximum_retained_score':s['maximum_retained_score'],
                'original_grid_hypotheses':s['original_grid_hypotheses'],
                'unique_native_hypotheses':s['unique_native_hypotheses'],
                'OFF_ge8_inventory_rows':c['OFF_inventory_rows'].get(s['scan_id'])})
        assert len(scans)==6
        qrow.update(checks=qa['checks'],maximum_absolute_errors_json=json.dumps(qa['maximum_absolute_errors'],sort_keys=True))
    return row,scans,qrow,freq


def render(cohort_root,baseline_root,out):
    cohort_root,baseline_root,out=Path(cohort_root),Path(baseline_root),Path(out)
    overall_path=cohort_root/'RESULT.json';overall=read(overall_path)
    assert overall['status'] in TERMINAL_COHORT,'Wait for terminal cohort closure before reporting'
    frozen_path=cohort_root/'FROZEN_COHORT_SCOPE.json';cohort=read(frozen_path)
    assert [c['canonical_index'] for c in cohort['cases']]==list(range(1,9))
    source=Path(__file__).resolve().parents[3]
    contract_path=source/'analysis/sixscan_burst_20261015/contract.json';contract=read(contract_path)
    inputs=[pin(overall_path),pin(frozen_path),pin(contract_path)]
    roots={0:baseline_root}|{c['canonical_index']:Path(c['output_root']) for c in cohort['cases']}
    rows=[];scans=[];qas=[];freqs=[]
    for index in range(9):
        row,scan,qa,freq=collect(roots[index],index,contract,inputs)
        rows.append(row);scans.extend(scan);qas.append(qa);freqs.append({'canonical_index':index,'identity':row['identity'],**freq})
    assert rows[0]['verified_complete'],'Completed B00 prerequisite must remain available and unchanged'
    verified=[r for r in rows if r['verified_complete']];verified_new=[r for r in rows[1:] if r['verified_complete']]
    assert len(verified_new)==overall['completed_verified_bands']
    assert len(scans)==6*len(verified)
    if overall['status']==COHORT_PASS:assert len(verified_new)==8
    totals={k:sum(r[k] for r in verified) for k in ['retained_top5_ON_ge10_count','OFF_ge8_inventory_rows',
        'OFF_compatible_retained_ON_count','no_compatible_OFF_ge8_retained_ON_count','payload_bytes','payload_arrays']}
    on_intervals=[f['ON_reference']['source_channel_interval_half_open'] for f,r in zip(freqs,rows) if r['verified_complete']]
    sorted_intervals=sorted(on_intervals)
    assert all(a[1]<=b[0] for a,b in zip(sorted_intervals,sorted_intervals[1:])), 'ON cores must remain disjoint'
    total_hz=math.fsum(r['ON_reference_bandwidth_hz'] for r in verified)
    new_cpu=overall.get('whole_children_CPU_s')
    all_cpu=math.fsum(r['whole_children_CPU_s'] for r in verified)
    combined_attempt_cpu=(new_cpu+rows[0]['whole_children_CPU_s']) if new_cpu is not None else None
    qchecks=sum(q['checks'] for q in qas if q['verified_complete'])
    out.mkdir(parents=True,exist_ok=True)
    fields=['canonical_index','identity','native_chunk_index','core_q','status','verified_complete',
        'failure_diagnostic','maximum_ON_score','maximum_OFF_score','retained_top5_ON_ge10_count','OFF_ge8_inventory_rows',
        'OFF_compatible_retained_ON_count','no_compatible_OFF_ge8_retained_ON_count','whole_children_CPU_s',
        'peak_child_RSS_bytes','payload_bytes','payload_arrays','ON_reference_bandwidth_hz','OFF_reference_bandwidth_hz',
        'ON_center_frequency_min_hz','ON_center_frequency_max_hz','scope_sha256']
    csv_write(out/'COHORT_8_BAND_SUMMARY.csv',rows[1:],fields)
    csv_write(out/'ALL_9_BAND_SUMMARY.csv',rows,fields)
    csv_write(out/'ALL_SCAN_MAXIMA.csv',scans,['canonical_index','identity','native_chunk_index','core_q','scan_id',
        'role','target','reference_carriers','maximum_retained_score','original_grid_hypotheses',
        'unique_native_hypotheses','OFF_ge8_inventory_rows'])
    csv_write(out/'QA_SUMMARY.csv',qas,['canonical_index','identity','verified_complete','qa_status','checks','maximum_absolute_errors_json'])
    save(out/'REFERENCE_FREQUENCY_GEOMETRY.json',{'schema':'SETI_NINE_RETAINED_BAND_REFERENCE_GEOMETRY_V1',
        'bands':freqs,'verified_band_count':len(verified),'verified_disjoint_ON_reference_carriers':4096*len(verified),
        'verified_total_nominal_ON_reference_bandwidth_hz':total_hz,
        'qualification':'Reference-carrier frequency widths at a common cadence midpoint; not new telescope data, survey completeness or independent trials. OFF search and input halos are not added to ON coverage.'})
    save(out/'AGGREGATE.json',{'schema':'SETI_NINE_BANDS_RECEIPT_DERIVED_DESCRIPTIVE_AGGREGATE_V1',
        'cohort_status':overall['status'],'new_bands_planned':8,'new_bands_verified':len(verified_new),
        'combined_bands_planned':9,'combined_bands_verified':len(verified),
        'verified_scan_maps':len(scans),'verified_QA_checks':qchecks,
        'verified_totals':totals,'new_cohort_whole_children_CPU_s':new_cpu,
        'combined_verified_whole_children_CPU_s':all_cpu,
        'combined_known_whole_children_CPU_s_including_failed_attempts':combined_attempt_cpu,
        'failed_case_costs_in_cohort_whole_CPU_total':new_cpu is not None,
        'raw_or_payload_arrays_opened_for_report':False,'new_hypotheses_searched':0,
        'qualified_SETI_detection':False,'rank_status':'NOT_APPLIED_NO_CALIBRATION'})
    lines=['# SETI: gennemgang af de ni gemte 2017-bånd','']
    if len(verified)==9:
        lines+=['**Alle otte nye bånd og det tidligere afsluttede B00-bånd har bestået uafhængig numerisk QA: 9/9 bånd, 54 komplette scanningskort.**','']
    else:
        lines+=[f'**{len(verified_new)}/8 nye bånd har fuld godkendt afslutning og QA. Sammen med B00 er {len(verified)}/9 bånd verificeret. Ufuldstændige bånd tælles ikke som nulobservationer.**','']
    if totals['retained_top5_ON_ge10_count']==0:
        lines += [f'I de **{len(verified)} verificerede bånd** findes **0 bevarede ON-hypoteser med score ≥10**. Højeste ON-score er **{max(r["maximum_ON_score"] for r in verified):.9f}**. Der er derfor ingen ON-hypotese over det fastlagte snit at følge videre i disse kørsler. De komplette OFF-inventarer indeholder tilsammen **{totals["OFF_ge8_inventory_rows"]} nativeidentiteter med score ≥8**.','']
    else:
        lines += [f'I de **{len(verified)} verificerede bånd** findes **{totals["retained_top5_ON_ge10_count"]} bevarede ON-hypoteser med score ≥10**. Af dem har **{totals["OFF_compatible_retained_ON_count"]}** en kompatibel OFF-hypotese over snittet 8; **{totals["no_compatible_OFF_ge8_retained_ON_count"]}** har ingen sådan algoritmisk match i den erklærede familie. De komplette OFF-inventarer indeholder tilsammen **{totals["OFF_ge8_inventory_rows"]} nativeidentiteter med score ≥8**. Hypoteser og aliaser er korrelerede og er ikke det samme som separate fysiske signaler.','']
    incomplete=[r for r in rows if not r['verified_complete']]
    if incomplete:
        names=', '.join(f"B{r['canonical_index']:02d}" for r in incomplete)
        if any('BadZipFile' in r.get('failure_diagnostic','') for r in incomplete):
            lines += ['QA for B06 stoppede med **BadZipFile**, da den gemte numeriske NPZ-payload skulle åbnes. Det er en fejl i den efterfølgende datakontrol, ikke et målt negativt signalresultat.','']
        lines += [f'**{names} er uverificeret og er ikke med i ovenstående nulantal, maksimum eller øvrige videnskabelige summer.** Primærkørslen kan være afsluttet, selv om efterfølgende payload- eller QA-kontrol fejler; en sådan ufuldstændig dokumentation er ikke en målt nulobservation. Den oprindelige fejlstatus og alle delvise filer bevares uden genkørsel.','']
    lines += ['Scorerne er robuste residualsummer. **Snittene 10 og 8 er ikke kalibrerede sigma-, SNR- eller sandsynlighedsniveauer.** Resultatet dokumenterer ikke fravær af svagere eller anderledes signaler og fastslår ingen fysisk oprindelse.','',
        '| Bånd | Native / q | Maks. ON | Maks. OFF | Bevarede ON ≥10 | OFF ≥8-identiteter | QA |',
        '|---|---|---:|---:|---:|---:|---|']
    for r in rows:
        if r['verified_complete']:
            values=f'{r["maximum_ON_score"]:.6f} | {r["maximum_OFF_score"]:.6f} | {r["retained_top5_ON_ge10_count"]} | {r["OFF_ge8_inventory_rows"]} | PASS'
        else:values='— | — | — | — | Ufuldstændig'
        lines.append(f'| B{r["canonical_index"]:02d} | {r["native_chunk_index"]} / {r["core_q"]} | {values} |')
    lines += ['',f'Hvert bånd indeholder **4.096 ON-referencekanaler** med nominel samlet binbredde **11.444091796875 kHz**, og **6.652 OFF-referencekanaler**, inklusive 1.278 kanaler i hver halo, med samlet binbredde **18.585473299026 kHz**. De verificerede disjunkte ON-referencekerner udgør tilsammen **{humanint(4096*len(verified))} referencekanaler og {total_hz/1e3:.12f} kHz** ved det fælles referencetidspunkt. Det er ikke ekstra dækning, når driftbaner eller læsehaloen overlapper andre frekvenser. Alle præcise centerfrekvenser, binrande og kildeintervaller står i `REFERENCE_FREQUENCY_GEOMETRY.json`.','',
        'Alle data kommer fra **ét allerede eksponeret og efterudvalgt besøg den 28. april 2017**. Tre ON-scanninger er rettet mod HIP98505/HD189733; tre OFF-scanninger mod HIP97319, HIP97461 og HIP97663. Fire retninger og tre gentagelser mod målet er bevaret i deres oprindelige roller; de er ikke nye observationer eller en uafhængig genobservation af et fund. De ni bånd blev tidligere valgt ud fra prominente spor. Den nye gennemgang følger den gamle kanoniske båndrækkefølge; tidligere ukendte kørsler kan allerede have forsøgt samme hypotesefamilie.','',
        'Den uændrede søgning bruger **5.723 drifthastigheder over ±4 Hz/s**, syv overlappende fire-række-vinduer og bredder 1, 3, 9 og 33 kanaler. ON-listen bevarer en samlet topfem pr. referencekanal og tager herfra alle scorer ≥10. Det er **ikke** et udtømmende ON-inventar over alle afprøvede hypoteser ≥10. OFF-inventaret er derimod udtømmende for native-fire-række-identiteter med score ≥8 i den erklærede OFF-familie, inklusive alle relevante driftaliaser.','',
        f'Uafhængig QA har genberegnet alle **{len(scans)} verificerede komplette scanningssøgninger** og kontrolleret preprocessing, søgekort, OFF-inventarer, aliasgeometri og matchregler. Der er **{humanint(qchecks)} registrerede kontrolchecks**; de er ikke uafhængige himmelforsøg. Per-bånds kontroltal og maksimale numeriske afvigelser er bevaret i `QA_SUMMARY.csv` og de originale QA-bilag. Ingen rangkalibrering, p-værdi, injektions-recovery-rate, fysisk følsomhed eller RFI-populationskvalifikation er etableret. Recovery-metadata angiver alene, at injektions-recovery ikke er relevant for disse virkelige data.','']
    if new_cpu is not None:
        lines += [f'Kohortens målte numeriske børneprocesser, inklusive eventuelle fejlede processer, brugte tilsammen **{new_cpu:.6f} CPU-sekunder**. Med B00 er det i alt **{combined_attempt_cpu:.6f} CPU-sekunder**; heraf stammer **{all_cpu:.6f} CPU-sekunder** fra de {len(verified)} fuldt verificerede bånd. Dette er de målte numeriske børneprocesser; koordinering og rapportering er særskilt. Udgiften er **0 DKK**, med **0 nye teleskopforespørgsler og 0 nye teleskopbytes**.','']
    else:
        lines += [f'En fuld CPU-sum for kohorten er ikke dokumenteret. De verificerede bånd har tilsammen **{all_cpu:.6f} CPU-sekunder** i målte numeriske børneprocesser; dette omfatter ikke eventuelle ufuldstændige eller ukendte omkostninger.','']
    lines += [f'Pakken bevarer **{humanint(totals["payload_arrays"])} numeriske payload-arrays** fra de verificerede bånd, herunder {6*len(verified)} originale rå arrays, fulde søgekort, aliaser og OFF-inventarer. De verificerede payloads fylder **{humanint(totals["payload_bytes"])} bytes**. Kildekode, fastlåste scopes, komplette proces- og QA-bilag samt de afledte tabeller gør resultaterne efterprøvelige. Rapportgeneratoren læser kun metadata og procesbilag og udfører ingen ny søgning.','',
        'B00 er ikke kørt igen eller ændret. De tidligere pensionerede og fejllukkede bankforløb forbliver uændrede, A/B er fortsat FAIL_CLOSED, og 2016-/2019-ruterne er fortsat lukkede. Det formelle kontrolpunkt er 20. oktober 2026.','']
    text='\n'.join(lines)
    (out/'RESULTS_DA.md').write_text(text)
    names=['RESULTS_DA.md','COHORT_8_BAND_SUMMARY.csv','ALL_9_BAND_SUMMARY.csv','ALL_SCAN_MAXIMA.csv',
           'QA_SUMMARY.csv','REFERENCE_FREQUENCY_GEOMETRY.json','AGGREGATE.json']
    manifest={'schema':'SETI_NINE_BANDS_POSTRUN_RECEIPT_REPORT_MANIFEST_V1','status':'COMPLETE_RECEIPT_REPORT',
        'cohort_status':overall['status'],'report_generator':pin(__file__),'input_receipts':inputs,
        'outputs':[pin(out/name) for name in names],'raw_arrays_opened':False,'new_hypotheses_searched':0}
    save(out/'REPORT_MANIFEST.json',manifest)
    print(json.dumps({'status':manifest['status'],'verified_bands':len(verified),'scan_maps':len(scans),
        'totals':totals,'report':pin(out/'RESULTS_DA.md')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort-root',type=Path,required=True)
    parser.add_argument('--baseline-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args();render(args.cohort_root,args.baseline_root,args.out)
