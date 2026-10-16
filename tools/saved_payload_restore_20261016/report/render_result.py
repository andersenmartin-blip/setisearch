#!/usr/bin/env python3
"""Separate supplemental receipt report after exact saved-B06 verification.

Original cohort reports and execution statuses are never written or changed.
Only receipts/metadata are read; there is no payload-array decode or new search.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

IDENTITY='SETI_B06_SAVED_PAYLOAD_RESTORATION_QA_20261016_V1'
TARGET={'bytes':8723230,'sha256':'b96e21059e3d5480c55aad7788488ba5a49f1f4c05bb59ac14224b5cd09a143a'}
CORRUPT={'bytes':7378998,'sha256':'f5332374aff54027ea8e1cfa25738deee7631a61d5a83f88e556b68f4e3f3bed'}
CASE_PASS='COMPLETE_DESCRIPTIVE_REAL_FULLSCAN_QA_VERIFIED'
QA_PASS='PASS_DESCRIPTIVE_REAL_FULLSCAN_QA_ONLY'


def read(path):return json.loads(Path(path).read_text())


def pin(path):
    path=Path(path)
    return {'path':str(path),'bytes':path.stat().st_size,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def humanint(value):return f'{int(value):,}'.replace(',','.')


def save(path,value):Path(path).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')


def csv_write(path,rows,fields):
    with Path(path).open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        writer.writerows({k:r.get(k) for k in fields} for r in rows)


def frequency(scope,meta):
    first,stop=scope['band']['reference_source_channel_interval'];df=meta['df_hz'];fch1=meta['fch1_hz']
    def band(a,b):
        centers=sorted([fch1+a*df,fch1+(b-1)*df])
        return {'source_channel_interval_half_open':[a,b],'reference_carriers':b-a,
            'center_frequencies_hz_ascending':centers,'nominal_reference_bandwidth_hz':(b-a)*abs(df),
            'nominal_bin_edges_hz_ascending':[centers[0]-abs(df)/2,centers[1]+abs(df)/2]}
    return {'signed_df_hz':df,'fch1_hz':fch1,
        'ON_reference':band(first,stop),'OFF_reference':band(first-1278,stop+1278)}


def render_failure(restoration_root,baseline_root,cohort_root,out):
    """Retain the strict failed endpoint, with partial progress kept separate."""
    restoration_root,baseline_root,out=Path(restoration_root),Path(baseline_root),Path(out)
    source=Path(__file__).resolve().parents[3]
    original_report=source/'analysis/real_fullscan_cohort_20261016/report'
    final_path=restoration_root/'RESULT.json';final=read(final_path)
    scope_path=restoration_root/'FROZEN_SCOPE.json';scope=read(scope_path)
    restore_path=restoration_root/'RESTORATION_REPORT.json';restore=read(restore_path)
    qa_path=restoration_root/'SAVED_QA_REPORT.json';qa=read(qa_path)
    numeric_path=restoration_root/'NUMERICAL_QA_REPORT.json';numeric=read(numeric_path)
    assert final['identity']==IDENTITY and final['status']=='STOPPED_RETAINED_NO_RETRY'
    assert restore['status']=='RESTORED_EXACT_ORIGINAL_PAYLOAD_BYTES_ONLY'
    assert {k:restore['restored_archive'][k] for k in TARGET}==TARGET
    assert {k:restore['original_failed_archive'][k] for k in CORRUPT}==CORRUPT
    assert restore['retained_prefix_bytes_match'] is True and restore['raw_source_NPY_members_repacked']==6
    assert restore['numerical_detector_or_QA_invocations']==0 and restore['array_value_decodes']==0
    assert qa['status']=='FAILED_RESTORED_SAVED_DESCRIPTIVE_SEARCH_QA_ONLY'
    assert numeric['status']=='FAILED_DESCRIPTIVE_REAL_FULLSCAN_QA_ONLY'
    assert qa['numerical_report_sha256']==pin(numeric_path)['sha256']
    cohort_root=Path(cohort_root) if cohort_root else Path(scope['original_cohort_result']['path']).parent
    original_result_path=cohort_root/'RESULT.json';original=read(original_result_path)
    case_result_path=cohort_root/'B06/RESULT.json';case_result=read(case_result_path)
    assert original['status']=='INCOMPLETE_COHORT_RETAINED_NO_RETRY' and original['completed_verified_bands']==7
    assert case_result['status']=='STOPPED_RETAINED_NO_RETRY'
    original_aggregate_path=original_report/'AGGREGATE.json';aggregate=read(original_aggregate_path)
    assert aggregate['combined_bands_verified']==8 and aggregate['verified_scan_maps']==48
    band_csv_path=original_report/'ALL_9_BAND_SUMMARY.csv'
    with band_csv_path.open() as stream:band_rows=list(csv.DictReader(stream))
    assert len(band_rows)==9 and sum(r['verified_complete']=='True' for r in band_rows)==8
    producer_path=cohort_root/'B06/observation/PRODUCER.json';producer=read(producer_path)
    c=producer['output_census'];progress=numeric['progress'];scans=progress['full_search_checks']
    assert len(scans)==6 and progress['checks']==847481
    assert all(s['complete_search_recomputed'] and s['complete_retained_maps_checked'] for s in scans)
    primary_max=c['maximum_pre_OFF_ON_score']
    independent_max=max(s['maximum'] for s in scans if s['role']=='ON')
    error=abs(primary_max-independent_max)
    assert error==math.ulp(primary_max)==8.881784197001252e-16
    contract_path=source/'analysis/sixscan_burst_20261015/contract.json';contract=read(contract_path)
    metadata={m['scan_id']:m for m in contract['geometry']['scan_metadata']}
    producer_scans={s['scan_id']:s for s in c['scans']}
    diagnostics=[]
    for s in scans:
        diagnostics.append({'scan_id':s['scan_id'],'role':s['role'],
            'target':metadata[s['scan_id']]['original_header_full']['data_attributes']['source_name'],
            'producer_maximum':producer_scans[s['scan_id']]['maximum_retained_score'],
            'independent_maximum':s['maximum'],
            'complete_scan_map_checked_before_failed_final_gate':True,
            'independent_OFF_ge8_inventory_rows':s['OFF_ge8_inventory_rows'] if s['role']=='OFF' else None,
            'whole_case_QA_status':numeric['status']})
    baseline_result_path=baseline_root/'RESULT.json';baseline=read(baseline_result_path)
    resource_rows=[{'scope':'B00 original analysis','reserved_CPU_s':1300,'measured_whole_children_CPU_s':baseline['whole_children_CPU_s']},
        {'scope':'Original eight-band cohort including failed processes','reserved_CPU_s':10500,'measured_whole_children_CPU_s':original['whole_children_CPU_s']},
        {'scope':'Exact restoration and failed strict saved-result QA','reserved_CPU_s':760,'measured_whole_children_CPU_s':final['whole_children_CPU_s']}]
    total_cpu=math.fsum(r['measured_whole_children_CPU_s'] for r in resource_rows)
    out.mkdir(parents=True,exist_ok=True)
    csv_write(out/'ALL_9_ATTEMPT_STATUS.csv',band_rows,list(band_rows[0]))
    csv_write(out/'B06_SIX_SCAN_DIAGNOSTICS.csv',diagnostics,list(diagnostics[0]))
    csv_write(out/'RESOURCE_SUMMARY.csv',resource_rows,list(resource_rows[0]))
    geometry_source_path=original_report/'REFERENCE_FREQUENCY_GEOMETRY.json'
    freq=read(geometry_source_path)
    freq['qualification']='Nine separated reference cores are defined; only eight complete results are verified. Sum of widths is not a continuous frequency interval, a sensitivity measurement or independent sky trials.'
    freq['planned_nine_ON_reference_carriers']=36864
    freq['planned_nine_nominal_ON_reference_bandwidth_hz']=102996.826171875
    save(out/'REFERENCE_FREQUENCY_GEOMETRY.json',freq)
    failure={'schema':'SETI_STRICT_SAVED_QA_FAILURE_SUPPLEMENT_V1','identity':IDENTITY,
        'status':final['status'],'original_cohort_status':original['status'],
        'original_cohort_completed_new_bands':7,'fully_verified_bands_including_B00':8,
        'fully_verified_scan_maps':48,'verified_only_totals':aggregate['verified_totals'],
        'B06_original_case_status':case_result['status'],'B06_exact_byte_restoration_passed':True,
        'B06_separate_saved_QA_passed':False,'B06_partial_QA_scan_maps_checked':6,
        'B06_partial_QA_checks':progress['checks'],'B06_producer_global_maximum':primary_max,
        'B06_independent_global_maximum':independent_max,'B06_global_max_absolute_difference':error,
        'B06_global_max_difference_ULP':1,'B06_required_global_max_tolerance':0.,
        'B06_producer_diagnostics_not_in_verified_totals':c,
        'exact_restored_NPZ':TARGET,'retained_failed_NPZ':CORRUPT,
        'new_primary_detector_invocations':0,'new_scope_reserved_CPU_s':760,
        'new_scope_measured_whole_children_CPU_s':final['whole_children_CPU_s'],
        'three_current_scope_reserved_CPU_s':12560,'three_current_scope_measured_whole_children_CPU_s':total_cpu,
        'tolerance_retuned':False,'original_failed_endpoints_modified':False,
        'rank_status':'NOT_APPLIED_NO_CALIBRATION','qualified_SETI_detection':False,
        'report_raw_or_payload_arrays_opened':False}
    save(out/'AGGREGATE_FAILURE_SUPPLEMENT.json',failure)
    verified_max=max(float(r['maximum_ON_score']) for r in band_rows if r['verified_complete']=='True')
    lines=['# SETI: B06 er gendannet eksakt, men den strenge QA fejlede','',
        '**Der er fortsat 8/9 fuldt verificerede bånd inklusive B00. Den oprindelige otte-båndskohorte står på7/8; B06 og det separate QA-forløb bevarer deres fejlstatus.**','',
        f'I de otte fuldt verificerede bånd findes **0 bevarede ON-hypoteser med score ≥10** og **0 OFF-nativeidentiteter med score ≥8**. Højeste verificerede ON-score er **{verified_max:.9f}**. B06 tælles ikke som en nulobservation og indgår ikke i disse summer.','',
        'B06s numeriske payload er nu gendannet med **eksakt samme størrelse og SHA-256 som før datatabet**. De454 komplette afledte komprimerede ZIP-poster blev kopieret uændret; kun de seks oprindelige rå inputposter og ZIP-mappen blev genskabt fra autentificerede kildebytes. Der blev udført **0 nye primære detektorkørsler**.','',
        f'Den oprindelige fejlramte fil på **{humanint(CORRUPT["bytes"])} bytes**, SHA-256 `{CORRUPT["sha256"]}`, bevares uændret. Den gendannede fil er **{humanint(TARGET["bytes"])} bytes**, SHA-256 `{TARGET["sha256"]}`. Eksakt gendannelse af bytes er gennemført; den efterfølgende samlede numeriske QA har ikke PASS.','',
        f'Den separate QA genberegnede og kontrollerede **alle seks komplette scanningskort og OFF-inventarer** før stop, med **{humanint(progress["checks"])} kontrolchecks**. Slutkontrollen af det globale ON-maksimum kræver præcis nul afvigelse. Den oprindelige producer havde **{primary_max:.15f}**, og den uafhængige beregning havde **{independent_max:.15f}**. Forskellen er **{error:.15e}**, én ULP i binary64. Det fastlagte nulkrav er dermed ikke opfyldt. Tolerancen er ikke ændret efter udfaldet, og der foretages ingen ny kørsel i dette forløb.','',
        '| B06-scanning | Rolle | Oprindelig retning | Producer-maksimum | Uafhængigt maksimum |',
        '|---|---|---|---:|---:|']
    for d in diagnostics:
        lines.append(f'| {d["scan_id"]} | {d["role"]} | {d["target"]} | {d["producer_maximum"]:.15f} | {d["independent_maximum"]:.15f} |')
    lines += ['',
        f'Tabellen er **delvis kontroldiagnostik for B06**, ikke en bestået samlet verifikation. B06-producerens bevarede ON≥10-antal er **{c["retained_top5_ON_ge10_count"]}**; de tre uafhængigt genberegnede OFF≥8-inventarer har hver0 poster. Disse diagnostikker holdes adskilt fra de otte fuldt verificerede bånd. Der er ingen kalibreret falskalarmrate, SNR, fysisk følsomhed eller målt injektions-recovery-rate.','',
        'Søgningen bruger uændret5.723 drifthastigheder over±4Hz/s, syv fire-række-vinduer og bredder1,3,9 og33 kanaler. ON-antal omfatter de bevarede samlede topfem pr. referencekanal med score≥10, ikke alle afprøvede ON-hypoteser over10. OFF-inventarerne er udtømmende for score≥8-nativeidentiteter og deres aliaser i den erklærede familie. Snittene10 og8 er beskrivende numeriske snit.','',
        'De otte fuldt verificerede referencekerner udgør **32.768 kanaler og91.552734375 kHz**. Alle ni planlagte kerner udgør36.864 kanaler og102.996826171875 kHz, men det er ikke fuldt verificeret dækning. Kernerne ligger i adskilte frekvensintervaller med mellemrum; breddernes sum er ikke et sammenhængende frekvensinterval.','',
        'Alle data stammer fra **ét allerede eksponeret, efterudvalgt besøg den28.april2017**. Tre ON-scanninger er rettet mod HIP98505/HD189733, og de tre OFF-scanninger mod HIP97319, HIP97461 og HIP97663. De fire oprindelige retninger er bevaret; der er ingen ny observation eller uafhængig genobservation af et fund. Tidligere ukendte kørsler kan allerede have forsøgt samme hypotesefamilie.','',
        '| Afgrænset forløb | Reserveret CPU-tid | Målt CPU-tid for hele børneprocesser |',
        '|---|---:|---:|',
        f'| B00 | 1.300 s | {baseline["whole_children_CPU_s"]:.6f} s |',
        f'| Oprindelig kohorte, inklusive fejlede processer | 10.500 s | {original["whole_children_CPU_s"]:.6f} s |',
        f'| Eksakt gendannelse og fejlet streng QA | 760 s | {final["whole_children_CPU_s"]:.6f} s |',
        f'| I alt for disse tre forløb | 12.560 s | {total_cpu:.6f} s |','',
        'Reservationer er forud fastlagte lofter, ikke målte forbrugstal. Ingen gamle reservationer eller fejlede procesomkostninger er frigivet eller genbrugt. Udgiften er0DKK, med0 nye teleskopforespørgsler og0 nye teleskopbytes. Koordinering og rapportering er særskilt fra børneprocessernes målte CPU-tid.','',
        'Dette supplement ændrer ingen tidligere scopes, rapporter eller fejlstatusser. A/B forbliver FAIL_CLOSED,2016-/2019-ruterne forbliver lukkede, og kontrolpunktet er20.oktober2026. Rapporten er afledt af metadata og procesbilag; rapportgeneratoren åbner ingen rå- eller payload-arrays.','']
    text='\n'.join(lines)
    for a,b in {'på7/8':'på 7/8','De454':'De 454','hver0':'hver 0','uændret5.723':'uændret 5.723',
        'over±4Hz/s':'over ±4 Hz/s','bredder1,3,9 og33':'bredder 1, 3, 9 og 33','score≥10':'score ≥10',
        'over10':'over 10','score≥8':'score ≥8','Snittene10 og8':'Snittene 10 og 8',
        'og91.552':'og 91.552','udgør36.864':'udgør 36.864','og102.996':'og 102.996',
        'den28.april2017':'den 28. april 2017','er0DKK':'er 0 DKK','med0 nye':'med 0 nye',
        'og0 nye':'og 0 nye','FAIL_CLOSED,2016':'FAIL_CLOSED, 2016','er20.oktober2026':'er 20. oktober 2026'}.items():
        text=text.replace(a,b)
    (out/'RESULTS_SUPPLEMENT_DA.md').write_text(text)
    files=['RESULTS_SUPPLEMENT_DA.md','ALL_9_ATTEMPT_STATUS.csv','B06_SIX_SCAN_DIAGNOSTICS.csv',
        'RESOURCE_SUMMARY.csv','REFERENCE_FREQUENCY_GEOMETRY.json','AGGREGATE_FAILURE_SUPPLEMENT.json']
    receipt_paths=[final_path,scope_path,restore_path,qa_path,numeric_path,original_result_path,
        case_result_path,original_aggregate_path,band_csv_path,geometry_source_path,producer_path,
        baseline_result_path,contract_path]
    save(out/'REPORT_MANIFEST.json',{'schema':'SETI_FAILED_STRICT_SAVED_QA_SUPPLEMENT_MANIFEST_V1',
        'identity':IDENTITY,'new_study_status':final['status'],'original_cohort_status_unchanged':original['status'],
        'report_generator':pin(__file__),'input_receipts':[pin(p) for p in receipt_paths],
        'outputs':[pin(out/n) for n in files],'fully_verified_bands':8,'new_primary_detector_invocations':0,
        'raw_or_payload_arrays_opened':False,'original_reports_modified':False})
    print(json.dumps({'status':'COMPLETE_TRUTHFUL_FAILED_QA_SUPPLEMENT','fully_verified_bands':8,
        'B06_full_QA_passed':False,'report':pin(out/'RESULTS_SUPPLEMENT_DA.md')},indent=2))


def render(restoration_root,baseline_root,cohort_root,out):
    restoration_root,baseline_root,out=Path(restoration_root),Path(baseline_root),Path(out)
    final_path=restoration_root/'RESULT.json';final=read(final_path)
    if final['status']=='STOPPED_RETAINED_NO_RETRY':
        return render_failure(restoration_root,baseline_root,cohort_root,out)
    assert final['identity']==IDENTITY and final['status']=='COMPLETE_EXACT_RESTORATION_AND_SEPARATE_SAVED_QA'
    assert final['original_cohort_status']=='INCOMPLETE_COHORT_RETAINED_NO_RETRY'
    assert final['original_failure_retained'] is True and final['no_primary_detector_invocation'] is True
    assert len(final['phases'])==2 and all(p['status']=='ACCEPTED_SEPARATE_RESTORATION_STUDY_PHASE' for p in final['phases'])
    scope_path=restoration_root/'FROZEN_SCOPE.json';scope=read(scope_path)
    assert scope['identity']==IDENTITY and scope['canonical_index']==6
    assert scope['expected_restored_array_archive']==TARGET
    assert {k:scope['truncated_array_archive'][k] for k in TARGET}==CORRUPT
    assert scope['no_primary_detector_invocation'] is True
    restored_path=restoration_root/'RESTORATION_REPORT.json';restored=read(restored_path)
    assert restored['status']=='RESTORED_EXACT_ORIGINAL_PAYLOAD_BYTES_ONLY'
    assert {k:restored['restored_archive'][k] for k in TARGET}==TARGET
    assert {k:restored['original_failed_archive'][k] for k in CORRUPT}==CORRUPT
    assert restored['retained_prefix_bytes_match'] is True
    assert restored['raw_source_NPY_members_repacked']==6
    assert restored['numerical_detector_or_QA_invocations']==0 and restored['array_value_decodes']==0
    assert restored['original_failed_case_modified'] is False and restored['original_cohort_failure_reclassified'] is False
    saved_qa_path=restoration_root/'SAVED_QA_REPORT.json';saved_qa=read(saved_qa_path)
    assert saved_qa['status']=='PASS_RESTORED_SAVED_DESCRIPTIVE_SEARCH_QA_ONLY'
    assert saved_qa['exact_restored_array_archive']==TARGET
    assert saved_qa['original_failed_array_archive_retained']==CORRUPT
    assert saved_qa['original_case_status']=='STOPPED_RETAINED_NO_RETRY'
    assert saved_qa['original_cohort_status']=='INCOMPLETE_COHORT_RETAINED_NO_RETRY'
    numeric_path=restoration_root/'NUMERICAL_QA_REPORT.json';numeric=read(numeric_path)
    assert numeric['status']==QA_PASS
    assert saved_qa['numerical_report_sha256']==pin(numeric_path)['sha256']
    cohort_root=Path(cohort_root) if cohort_root else Path(scope['original_cohort_result']['path']).parent
    original_result_path=cohort_root/'RESULT.json';original=read(original_result_path)
    assert original['status']=='INCOMPLETE_COHORT_RETAINED_NO_RETRY' and original['completed_verified_bands']==7
    source=Path(__file__).resolve().parents[3]
    contract_path=source/'analysis/sixscan_burst_20261015/contract.json';contract=read(contract_path)
    inputs=[pin(p) for p in [final_path,scope_path,restored_path,saved_qa_path,numeric_path,original_result_path,contract_path]]
    rows=[];scan_rows=[];qa_rows=[];frequencies=[]
    for index in range(9):
        root=baseline_root if index==0 else cohort_root/f'B{index:02d}'
        case_scope_path=root/'FROZEN_SCOPE.json';case_scope=read(case_scope_path)
        producer_path=root/'observation/PRODUCER.json';producer=read(producer_path)
        case_result_path=root/'RESULT.json';case_result=read(case_result_path)
        assert case_scope['identity']==f'SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B{index:02d}'
        assert producer['identity']==case_scope['identity'] and producer['status']=='PRODUCED_DESCRIPTIVE_REAL_FULLSCAN_ONLY'
        inputs += [pin(p) for p in [case_scope_path,producer_path,case_result_path]]
        if index==6:
            assert case_result['status']=='STOPPED_RETAINED_NO_RETRY'
            qa=numeric;qa_label='PASS_SEPARATE_SAVED_RESULT_QA'
            verification_study=IDENTITY
        else:
            assert case_result['status']==CASE_PASS
            qa_path=root/'QA_REPORT.json';qa=read(qa_path);assert qa['status']==QA_PASS
            inputs.append(pin(qa_path));qa_label='PASS_ORIGINAL_QA';verification_study=case_scope['identity']
        c=producer['output_census'];assert c['rank_status']=='NOT_APPLIED_NO_CALIBRATION'
        assert c['drift_grid_count']==5723 and c['OFF_halo_channels']==1278
        original_manifest_path=root/'observation/payload/MANIFEST.json'
        if index==6:
            original_manifest=read(original_manifest_path)
            assert original_manifest['members']['science_arrays.npz']==TARGET
            inputs.append(pin(original_manifest_path))
        band=case_scope['band'];freq=frequency(case_scope,contract['geometry']['scan_metadata'][0])
        row={'canonical_index':index,'identity':case_scope['identity'],
            'native_chunk_index':band['native_chunk_index'],'core_q':band['core_q'],
            'original_execution_status':case_result['status'],'saved_output_verification':qa_label,
            'verification_study':verification_study,
            'maximum_ON_score':c['maximum_pre_OFF_ON_score'],
            'maximum_OFF_score':max(s['maximum_retained_score'] for s in c['scans'] if s['role']=='OFF'),
            'retained_top5_ON_ge10_count':c['retained_top5_ON_ge10_count'],
            'OFF_ge8_inventory_rows':sum(c['OFF_inventory_rows'].values()),
            'OFF_compatible_retained_ON_count':c['OFF_compatible_retained_ON_count'],
            'no_compatible_OFF_ge8_retained_ON_count':c['no_compatible_OFF_ge8_retained_ON_count'],
            'ON_reference_bandwidth_hz':freq['ON_reference']['nominal_reference_bandwidth_hz'],
            'OFF_reference_bandwidth_hz':freq['OFF_reference']['nominal_reference_bandwidth_hz'],
            'ON_center_frequency_min_hz':freq['ON_reference']['center_frequencies_hz_ascending'][0],
            'ON_center_frequency_max_hz':freq['ON_reference']['center_frequencies_hz_ascending'][1],
            'payload_bytes':producer['payload_receipt']['payload_bytes'],
            'payload_arrays':producer['payload_receipt']['arrays_written']}
        rows.append(row);frequencies.append({'canonical_index':index,'identity':row['identity'],**freq})
        qa_rows.append({'canonical_index':index,'identity':row['identity'],
            'verification_study':verification_study,'qa_path':str(numeric_path if index==6 else root/'QA_REPORT.json'),
            'checks':qa['checks'],'maximum_absolute_errors_json':json.dumps(qa['maximum_absolute_errors'],sort_keys=True)})
        metadata={m['scan_id']:m for m in contract['geometry']['scan_metadata']}
        for s in c['scans']:
            scan_rows.append({'canonical_index':index,'identity':row['identity'],
                'native_chunk_index':band['native_chunk_index'],'core_q':band['core_q'],
                'scan_id':s['scan_id'],'role':s['role'],
                'target':metadata[s['scan_id']]['original_header_full']['data_attributes']['source_name'],
                'reference_carriers':s['retained_shape'][0],
                'maximum_retained_score':s['maximum_retained_score'],
                'OFF_ge8_inventory_rows':c['OFF_inventory_rows'].get(s['scan_id']),
                'saved_output_verification':qa_label})
    assert len(rows)==9 and len(scan_rows)==54
    intervals=sorted(f['ON_reference']['source_channel_interval_half_open'] for f in frequencies)
    assert all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:]))
    total_hz=math.fsum(r['ON_reference_bandwidth_hz'] for r in rows)
    assert total_hz==102996.826171875
    totals={k:sum(r[k] for r in rows) for k in ['retained_top5_ON_ge10_count','OFF_ge8_inventory_rows',
        'OFF_compatible_retained_ON_count','no_compatible_OFF_ge8_retained_ON_count','payload_bytes','payload_arrays']}
    qchecks=sum(r['checks'] for r in qa_rows)
    baseline_result=read(baseline_root/'RESULT.json')
    resource_rows=[{'scope':'B00 original analysis','reserved_CPU_s':1300,'measured_whole_children_CPU_s':baseline_result['whole_children_CPU_s']},
        {'scope':'Original eight-band cohort, including failed processes','reserved_CPU_s':10500,'measured_whole_children_CPU_s':original['whole_children_CPU_s']},
        {'scope':'Separate exact restoration and saved-result QA','reserved_CPU_s':760,'measured_whole_children_CPU_s':final['whole_children_CPU_s']}]
    reserved=sum(r['reserved_CPU_s'] for r in resource_rows)
    measured=math.fsum(r['measured_whole_children_CPU_s'] for r in resource_rows)
    assert reserved==12560
    out.mkdir(parents=True,exist_ok=True)
    csv_write(out/'ALL_9_SAVED_OUTPUTS.csv',rows,list(rows[0]))
    csv_write(out/'ALL_54_SCAN_MAXIMA.csv',scan_rows,list(scan_rows[0]))
    csv_write(out/'QA_SUMMARY.csv',qa_rows,list(qa_rows[0]))
    csv_write(out/'RESOURCE_SUMMARY.csv',resource_rows,list(resource_rows[0]))
    save(out/'REFERENCE_FREQUENCY_GEOMETRY.json',{'schema':'SETI_NINE_VERIFIED_SAVED_RESULTS_REFERENCE_GEOMETRY_V1',
        'bands':frequencies,'disjoint_ON_reference_carriers':36864,
        'total_nominal_ON_reference_bandwidth_hz':total_hz,
        'qualification':'Sum of nine separated reference cores with frequency gaps, at one common cadence midpoint within one already exposed 2017 visit; not one continuous frequency interval, new observing coverage or independent trials.'})
    save(out/'AGGREGATE_SAVED_OUTPUTS.json',{'schema':'SETI_SUPPLEMENTAL_EXACT_RESTORATION_SAVED_OUTPUTS_AGGREGATE_V1',
        'original_cohort_status':original['status'],'original_new_bands_verified_in_original_cohort':7,
        'original_B06_execution_status':'STOPPED_RETAINED_NO_RETRY',
        'separate_restoration_study_status':final['status'],'saved_outputs_verified':9,'scan_maps_verified':54,
        'verified_totals':totals,'numerical_QA_checks':qchecks,'new_primary_detector_invocations':0,
        'report_array_decodes':0,'original_failed_bytes_retained':True,
        'expected_restored_NPZ':TARGET,'retained_failed_NPZ':CORRUPT,
        'separate_scope_reserved_CPU_s':760,'three_current_scope_reservations_total_CPU_s':reserved,
        'three_current_scope_whole_children_CPU_s':measured,
        'rank_status':'NOT_APPLIED_NO_CALIBRATION','qualified_SETI_detection':False,
        'old_failed_and_unknown_bank_statuses_unchanged':True})
    lines=['# SETI: alle ni gemte resultater er nu numerisk verificeret','',
        '**B06 er verificeret i et separat forløb efter eksakt gendannelse af den gemte payload. Alle ni gemte båndresultater har nu uafhængig numerisk kontrol: 54 scanningskort. Den oprindelige otte-båndskohorte forbliver ufuldstændig med7/8 godkendte bånd.**','']
    if totals['retained_top5_ON_ge10_count']==0:
        lines += [f'De ni verificerede gemte resultater indeholder **0 bevarede ON-hypoteser med score ≥10** og **{totals["OFF_ge8_inventory_rows"]} OFF-nativeidentiteter med score ≥8**. Højeste ON-score er **{max(r["maximum_ON_score"] for r in rows):.9f}**. Der er dermed ingen ON-hypotese over det fastlagte snit at følge videre fra disse resultater.','']
    else:
        lines += [f'De ni gemte resultater indeholder **{totals["retained_top5_ON_ge10_count"]} bevarede ON-hypoteser med score ≥10**; **{totals["OFF_compatible_retained_ON_count"]}** har en kompatibel OFF-hypotese over snittet8, og **{totals["no_compatible_OFF_ge8_retained_ON_count"]}** har ingen sådan algoritmisk match. Disse tællinger fastslår ikke fysisk oprindelse.','']
    lines += ['Resultatet beskriver denne afgrænsede søgefamilie i de gemte data. Snittene10 og8 er empiriske numeriske snit, ikke kalibreret sigma, SNR, følsomhed eller falskalarmrate. Svagere eller anderledes signaler er ikke udelukket.','',
        '| Bånd | Native / q | Maks. ON | Maks. OFF | Bevarede ON ≥10 | OFF ≥8-identiteter | Verifikation |',
        '|---|---|---:|---:|---:|---:|---|']
    for r in rows:
        label='Separat QA af eksakt gemt resultat' if r['canonical_index']==6 else 'Oprindelig QA PASS'
        lines.append(f'| B{r["canonical_index"]:02d} | {r["native_chunk_index"]} / {r["core_q"]} | {r["maximum_ON_score"]:.6f} | {r["maximum_OFF_score"]:.6f} | {r["retained_top5_ON_ge10_count"]} | {r["OFF_ge8_inventory_rows"]} | {label} |')
    lines += ['',
        f'B06s oprindelige gemte numeriske NPZ blev registreret med **{humanint(TARGET["bytes"])} bytes** og SHA-256 `{TARGET["sha256"]}`. Den fejlramte kopi på **{humanint(CORRUPT["bytes"])} bytes**, SHA-256 `{CORRUPT["sha256"]}`, bevares uændret sammen med dens oprindelige fejlbilag. Gendannelsen kopierer de **454 komplette afledte komprimerede ZIP-poster uændret** og genskaber kun de seks oprindelige rå inputposter og ZIP-mappen fra allerede autentificerede kildebytes. Den nye kopi er accepteret, fordi dens størrelse og hele SHA-256 er identiske med den oprindeligt registrerede komplette fil.','',
        'Der er udført **0 nye primære detektorkørsler** i gendannelsesforløbet. En separat uafhængig QA har derefter genberegnet og kontrolleret det gemte B06-resultat, inklusive komplette kort, normalisering, aliaser og OFF-inventarer. Det ændrer hverken B06s oprindelige fejlafslutning eller kohortens status `INCOMPLETE_COHORT_RETAINED_NO_RETRY`. Den oprindelige rapport med8/9 verificerede bånd er bevaret; dette dokument er et supplement med en særskilt kontrolhistorik.','',
        f'Alle ni ON-referencekerner er disjunkte: **36.864 referencekanaler**, i alt **102.996826171875 kHz** nominel reference-binbredde. Kernerne ligger i adskilte frekvensintervaller med mellemrum; summen er ikke sammenhængende frekvensdækning. Hvert bånd har4.096 ON-referencekanaler og6.652 OFF-referencekanaler, inklusive1.278 i hver OFF-halo. Det er referencegeometri ved ét fælles referencetidspunkt; driftbaner, læsehaloen og OFF-haloer lægges ikke oven i ON-referencebredden som ny dækning. Præcise centerfrekvenser, binrande og kildeintervaller står i `REFERENCE_FREQUENCY_GEOMETRY.json`.','',
        'Dataene kommer stadig fra **ét allerede eksponeret, efterudvalgt besøg den28.april2017**: tre ON-scanninger mod HIP98505/HD189733 og tre oprindelige OFF-retninger, HIP97319, HIP97461 og HIP97663. Fire retninger er ikke fire uafhængige genobservationer. De ni bånd var tidligere valgt ud fra prominente spor; tidligere ukendte kørsler kan allerede have forsøgt samme hypotesefamilie.','',
        'Den uændrede familie bruger5.723 drifthastigheder over±4Hz/s, syv fire-række-vinduer og bredder1,3,9 og33 kanaler. ON-outputtet omfatter de **bevarede samlede topfem pr. referencekanal**, som når score10; det er ikke alle afprøvede ON-hypoteser over10. OFF-inventaret er udtømmende for score≥8-nativeidentiteter og deres aliaser i den erklærede familie. Bins, vinduer, bredder og aliaser er korrelerede. Der er ingen Gamma16-rang, p-værdi, målt injektions-recovery-rate eller populationskvalifikation.','',
        f'Tilsammen foreligger **{humanint(qchecks)} numeriske QA-checks** for de ni gemte resultater. Det er programkontroller, ikke uafhængige himmelforsøg. `ALL_9_SAVED_OUTPUTS.csv` bevarer både oprindelig kørselsstatus og den kontrol, der nu verificerer hvert gemt resultat. `ALL_54_SCAN_MAXIMA.csv` og `QA_SUMMARY.csv` indeholder alle scanningsmaksima og de enkelte QA-bilags numeriske afvigelser.','',
        '| Afgrænset forløb | Reserveret CPU-tid | Målt CPU-tid for hele børneprocesser |',
        '|---|---:|---:|',
        f'| B00 | 1.300 s | {resource_rows[0]["measured_whole_children_CPU_s"]:.6f} s |',
        f'| Oprindelig otte-båndskohorte, inklusive fejlede processer | 10.500 s | {resource_rows[1]["measured_whole_children_CPU_s"]:.6f} s |',
        f'| Separat gendannelse og QA af gemt B06-resultat | 760 s | {resource_rows[2]["measured_whole_children_CPU_s"]:.6f} s |',
        f'| I alt for disse tre forløb | 12.560 s | {measured:.6f} s |','',
        'Reservationer er forud fastlagte lofter; de er ikke målte forbrugstal. Ingen gammel reservation eller fejlmåling er frigivet eller genbrugt. Udgiften er0DKK, med0 nye teleskopforespørgsler og0 nye teleskopbytes. Koordinering og rapportering er ikke inkluderet i børneprocessernes målte CPU-sum.','',
        'Gamle pensionerede og fejllukkede bankforløb bevares uændrede. A/B er fortsat FAIL_CLOSED,2016-/2019-ruterne er fortsat lukkede, og kontrolpunktet er20.oktober2026. Rapportgeneratoren har ikke åbnet rå- eller payload-arrays og har ikke udført nogen søgning.','']
    text='\n'.join(lines)
    replacements={'med7/8':'med 7/8','med8/9':'med 8/9','snittet8':'snittet 8','Snittene10 og8':'Snittene 10 og 8',
        'har4.096':'har 4.096','og6.652':'og 6.652','inklusive1.278':'inklusive 1.278',
        'den28.april2017':'den 28. april 2017','bruger5.723':'bruger 5.723','over±4Hz/s':'over ±4 Hz/s',
        'bredder1,3,9 og33':'bredder 1, 3, 9 og 33','score10':'score 10','over10':'over 10','score≥8':'score ≥8',
        '1.300 s':'1.300 s','10.500 s':'10.500 s','760 s':'760 s','12.560 s':'12.560 s',
        'er0DKK':'er 0 DKK','med0 nye':'med 0 nye','og0 nye':'og 0 nye','FAIL_CLOSED,2016':'FAIL_CLOSED, 2016',
        'er20.oktober2026':'er 20. oktober 2026'}
    for old,new in replacements.items():text=text.replace(old,new)
    (out/'RESULTS_SUPPLEMENT_DA.md').write_text(text)
    names=['RESULTS_SUPPLEMENT_DA.md','ALL_9_SAVED_OUTPUTS.csv','ALL_54_SCAN_MAXIMA.csv','QA_SUMMARY.csv',
           'RESOURCE_SUMMARY.csv','REFERENCE_FREQUENCY_GEOMETRY.json','AGGREGATE_SAVED_OUTPUTS.json']
    save(out/'REPORT_MANIFEST.json',{'schema':'SETI_SEPARATE_SAVED_QA_SUPPLEMENT_REPORT_MANIFEST_V1',
        'identity':IDENTITY,'original_cohort_status_unchanged':original['status'],
        'report_generator':pin(__file__),'input_receipts':inputs,'outputs':[pin(out/n) for n in names],
        'raw_or_payload_arrays_opened':False,'new_primary_detector_invocations':0,
        'original_reports_modified':False})
    print(json.dumps({'status':'COMPLETE_SEPARATE_SAVED_OUTPUTS_SUPPLEMENT',
        'saved_outputs_verified':9,'scans_verified':54,'totals':totals,
        'report':pin(out/'RESULTS_SUPPLEMENT_DA.md')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restoration-root',type=Path,required=True)
    parser.add_argument('--baseline-root',type=Path,required=True)
    parser.add_argument('--cohort-root',type=Path)
    parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args();render(args.restoration_root,args.baseline_root,args.cohort_root,args.out)
