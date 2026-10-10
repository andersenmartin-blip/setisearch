"""Append delivery metadata without modifying audited scientific tables."""
from pathlib import Path
import hashlib
import json
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/radio_gap_static_context_20261010"

def save(p,j):
    p.write_text(json.dumps(j,ensure_ascii=False,indent=2,allow_nan=False)+"\n")

def main():
    start=time.process_time()
    report=ROOT/"RADIO_GAP_STATIC_CONTEXT_REPORT_2026-10-10.md"
    old=report.read_text()
    before=hashlib.sha256(report.read_bytes()).hexdigest()
    new=old.replace("[Fuld resultat-JSON](results/radio_gap_static_context_20261010/measurement/STATIC_CONTEXT_PROFILES.json)",
        "[Tabsfri gzip af fuld resultat-JSON](results/radio_gap_static_context_20261010/measurement/STATIC_CONTEXT_PROFILES.json.gz)")
    sentence="Rapporten angiver endnu ingen afsluttet arkivlagring eller publiceringskvittering."
    assert sentence in new
    new=new.replace(sentence,"Den samlede resultatpakke er beskrevet nedenfor.")
    new+="""
## Afsluttende kontrol og resultatpakke

[Uafhængig kontrol](results/radio_gap_static_context_20261010/measurement/QA_RECEIPT.json) består for alle 153 uændrede gamle arraykopier, 216 opsummeringer, 3.456 metrik-rækkeforekomster og 6.966 statiske frekvenssamples. Begge CSV-filer bevarer alle 54/864 rækkeidentiteter og flydende værdier ved bitpræcis round-trip. Kontrollen genlæste ingen HDF5-værdier og udførte ingen ny søgning. Kildens 111.456 råcelle-sammenligninger henføres til den eneste afsluttede målekørsel.

`SETI_GAP_STATIC_CONTEXT_2026-10-10.zip` samler rapport, figurer, originale JSON/CSV, den binære NPZ med alle nye og kopierede gamle arrays, alle 15 pinnede kode-/metadata-/profilinputs, scopes, kontrolkode, miljøkvitteringer og det ikke godkendte forslag. [Filmanifestet](results/radio_gap_static_context_20261010/BUNDLE_MANIFEST.json) angiver byteantal og SHA256. Det offentlige store JSON er tabsfrit gzip; pakken indeholder også det oprindelige ukomprimerede JSON. De kompakte HDF5-inputs leveres separat i det allerede gemte `SETI_FRESH_BAND151_RAW_2026-10-09.zip`, 305.428.707 bytes, SHA256 `6696fe54086e019ce966816dc818969ca5f1682e3ff9211326f1a68d2323ef1d`. Hele teleskopfiler og wheels er ikke genpakket.

Pakningen afkoder ingen science-arrays og kontrollerer alle ZIP-medlemmers bytes, hashes og CRC. Den gentager ingen signalanalyse. På en separat reproduktionskopi udtrækkes resultatpakken i `setisearch_checkpoint`, og kun de seks `results/radio_fresh_band_20261009/arrays/*.compact.h5` fra RAW-pakken placeres ved de angivne stier. Installer de to SHA-verificerede wheels fra miljøkvitteringerne med `python3 -m pip install --no-deps --target seti_gap_static_work/deps WHEEL_H5PY WHEEL_HDF5PLUGIN`; NumPy 2.3.5 skal allerede være tilgængelig. Miljøgendannelsesscriptet er den historiske udførte kode med oprindelige arbejdsstier, ikke en generisk ny downloader. Reproduktion kræver en resultatsti, der endnu ikke eksisterer, og separat autoriseret CPU; der blev ikke kørt en reproduktion i dette checkpoint.

[Ressourceoversigten](results/radio_gap_static_context_20261010/RESOURCE_SUMMARY.json) skelner mellem reservationer og målte delprocesser. Plotgrænsen på 6 CPU-s blev overskredet med den bevarede måling 7,613889; ingen ny plotkørsel blev foretaget. Den videnskabelige kørsels 20 CPU-s-grænse blev overholdt. Der hævdes ikke en samlet ende-til-ende CPU-måling.

[Det konkrete næste forslag](results/radio_gap_static_context_20261010/RADIO_NEXT_COMPUTE_PROPOSAL_2026-10-10.md) anmoder om 3.600 ekstra CPU-s, så totalrammen kan blive 46.800 CPU-s efter udtrykkelig godkendelse. Det omfatter de 214 resterende sikre delbånd i to fastlagte grupper på 107. Status er **IKKE GODKENDT · IKKE KØRT**; det nuværende checkpoint udvider ikke CPU-rammen og reserverer ingen tid til forslaget. Omkostningen forbliver 0 DKK, og kvalifikation, holdouts og øvrige grænser ændres ikke.
"""
    report.write_text(new)
    save(OUT/"FINAL_METADATA_AMENDMENT.json",{
        "status":"COMPLETE_METADATA_ONLY_REPORT_AMENDMENT",
        "audited_scientific_report_stage_sha256":before,
        "final_report_sha256":hashlib.sha256(report.read_bytes()).hexdigest(),
        "scientific_tables_or_values_modified":False,
        "changes":["Lossless public JSON gzip link", "Delivery and reproduction metadata", "QA/resource/proposal links"],
        "process_CPU_s":time.process_time(),"metadata_interval_CPU_s":time.process_time()-start})
    def read(name): return json.loads((OUT/name).read_text())
    run=read("measurement/EXECUTION_RECEIPT.json")
    qa=read("measurement/QA_RECEIPT.json")
    env=read("ENVIRONMENT_RESTORATION.json")
    recovery=read("RECOVERY_RECEIPT.json")
    plot=read("figures/PLOTTING_RECEIPT.json")
    report_receipt=read("measurement/REPORT_SERIALIZATION_RECEIPT.json")
    figures=read("FIGURE_QA.json")
    summary={"schema":"SETI_GAP_STATIC_CONTEXT_FINAL_RESOURCE_SUMMARY_V1",
        "activity_reservation_CPU_s":60,"scientific_CPU_cap_s":20,
        "preparation_QA_packaging_publication_reservation_CPU_s":40,
        "total_authorized_CPU_s":43200,"remaining_unreserved_CPU_s":2.705144981004196,
        "protected_final_summary_CPU_s":2,"remaining_unprotected_CPU_s":0.705144981004196,
        "prior_reservations_preserved_no_refund":True,"whole_activity_CPU_measured":False,
        "measured_components_CPU_s":{
            "archive_recovery":recovery["process_CPU_s"],
            "exact_environment_wrapper_and_children":env["sum_measured_local_process_components_CPU_s"],
            "scientific_job":run["process_CPU_seconds_including_imports"],
            "independent_saved_output_QA":qa["process_CPU_s"],
            "report_CSV_serializer":report_receipt["process_CPU_s"],
            "JSON_only_plotting":plot["process_CPU_seconds_including_imports"],
            "plot_receipt_amendment":figures["resource_receipt_amendment_metadata_CPU_seconds"],
            "image_QA_metadata":figures["image_QA_metadata_CPU_seconds"]},
        "scientific_job_caps_status":"PASS",
        "plot_component_resource_status":"CAP_EXCEEDED_NO_RETRY",
        "plot_CPU_cap_s":6,"plot_measured_CPU_s":plot["process_CPU_seconds_including_imports"],
        "plot_overrun_changes_scientific_results":False,
        "overrun_disposition":"Preserved original two figures; no retry. Same prospectively reserved 40 CPU-s preparation envelope and 60 CPU-s total activity charge; no increase or refund.",
        "measurement_limitations":["No whole-session CPU measurement; agent reasoning, tool services and some metadata/preparation processes unmetered", "Stopped pre-existing-file recovery guard CPU not separately metered", "Packaging, claims QA and metadata have separate receipts"],
        "reserved_remaining_not_actual_unused_wall_or_CPU_time":True,
        "new_telescope_HTTP_requests":0,"new_telescope_BODY_bytes":0,
        "received_saved_archive_bytes":311847026,"exact_dependency_wheel_bytes":51507696,
        "conservative_all_source_recovery_dependencies_envelope_bytes":2002313292,
        "all_source_cap_bytes":4563402752,"RAM_cap_bytes":4294967296,
        "workspace_cap_bytes":8589934592,"wall_cap_per_job_s":1800,"cost_DKK":0,
        "future_3600_CPU_proposal_status":"UNAPPROVED_NOT_RUN_NO_RESERVATION",
        "A_B":"FAIL_CLOSED_UNCHANGED","qualified_sky_pilot":False,"old_holdouts_closed":True}
    save(OUT/"RESOURCE_SUMMARY.json",summary)
    print(json.dumps({"status":"FINAL_METADATA_READY","report_sha256":hashlib.sha256(report.read_bytes()).hexdigest(),"process_CPU_s":time.process_time()}))

if __name__=="__main__": main()
