"""Serialize completed saved JSON and draft a bounded descriptive report.

No native files, arrays, telescope requests, searches or metric remeasurement.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value, digits=6):
    return f"{value:.{digits}f}".replace("-", "−").replace(".", ",")


def table(headers, rows):
    return "\n".join(["| "+" | ".join(headers)+" |", "| "+" | ".join("---" for _ in headers)+" |"]
        + ["| "+" | ".join(map(str, row))+" |" for row in rows])


def main():
    cpu, wall = time.process_time(), time.monotonic()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--measurement-dir", required=True)
    p.add_argument("--report", required=True)
    args = p.parse_args()
    folder, report = Path(args.measurement_dir), Path(args.report)
    paths = {"rows": folder/"ALL_720_SCAN_PROFILE_ROWS.json", "cases": folder/"ALL_120_STATIONARY_CASES.json",
        "weak": folder/"SIX_FIXED_WEAK_CASES.json", "result": folder/"FAMILY_RESULT.json",
        "receipt": folder/"EXECUTION_RECEIPT.json"}
    data = {k: json.loads(path.read_text()) for k, path in paths.items()}
    rows, weak, result, receipt = data["rows"], data["weak"], data["result"], data["receipt"]
    if result["status"] != "COMPLETED_DESCRIPTIVE_STATIONARY_TOP20_FAMILY" or len(rows) != 720 or len(weak) != 6:
        raise ValueError("Complete saved family result required")
    if len({(r["profile_id"], r["scan_id"]) for r in rows}) != 720 or any(len(r["all_16_center_minus_flank_rows"]) != 16 for r in rows):
        raise ValueError("Unique complete saved scan rows required")
    if result["reused_prior_cases"] != 9 or result["newly_measured_fixed_cases"] != 111:
        raise ValueError("Unexpected reuse/measurement counts")
    scalar_fields = [key for key in rows[0] if key != "all_16_center_minus_flank_rows"]
    scan_path = folder/"ALL_720_SCAN_PROFILE_ROWS.csv"
    with scan_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=scalar_fields+["all_16_center_minus_flank_rows_json"])
        w.writeheader()
        for record in rows:
            w.writerow({**{key: record[key] for key in scalar_fields},
                "all_16_center_minus_flank_rows_json": json.dumps(record["all_16_center_minus_flank_rows"], separators=(",", ":"))})
    time_path = folder/"ALL_11520_TIME_ROW_OCCURRENCES.csv"
    occurrence_fields = ["profile_id", "origin_scan", "origin_role", "original_selected_width",
        "profile_source", "scan_id", "scan_role", "row_index_zero_based", "center_minus_flank"]
    occurrences = 0
    with time_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=occurrence_fields); w.writeheader()
        for record in rows:
            for i, value in enumerate(record["all_16_center_minus_flank_rows"]):
                w.writerow({**{key: record[key] for key in occurrence_fields[:-2]},
                    "row_index_zero_based": i, "center_minus_flank": value})
                occurrences += 1
    if occurrences != 11520:
        raise ValueError("Time-row occurrence serialization incomplete")
    groups = result["summary_by_origin_role_and_original_width"]
    family_table = []
    for name in ("ON_width1", "OFF_width1", "ON_width3", "OFF_width3"):
        group = groups[name]
        role, width = name.split("_width")
        if group["case_count"]:
            fields = group["metrics"]
            family_table.append([role, width, group["case_count"],
                number(fields["mean_center_minus_flank"]["median"]),
                number(fields["minimum_of_half_means"]["median"]),
                number(fields["channel0_minus_immediate_neighbor_mean"]["median"]),
                str(group["all_16_positive_rows_case_count"])+"/"+str(group["case_count"])])
        else:
            family_table.append([role, width, 0, "—", "—", "—", "Tomt stratum"])
    weak_table, half_table, control_table, shape_table = [], [], [], []
    labels = {"epoch1_on": "ON1", "epoch2_on": "ON2", "epoch3_on": "ON3",
        "epoch1_off": "OFF1", "epoch2_off": "OFF2", "epoch3_off": "OFF3"}
    for case in weak:
        label = labels[case["origin_scan"]]+" rang "+str(case["display_rank"])
        m = case["origin_measurements"]
        control_text = "; ".join(labels[s]+": "+number(r["mean_center_minus_flank"]) for s, r in case["fixed_adjacent_controls"].items())
        weak_table.append([label, number(case["frequency_MHz"], 9), number(m["mean_center_minus_flank"]),
            number(m["median_center_minus_flank"]), str(m["positive_rows"])+"/16", control_text])
        half_table.append([label, number(m["first_8_rows_mean"]), number(m["last_8_rows_mean"]),
            number(m["minimum_of_half_means"])])
        for scan, c in case["fixed_adjacent_controls"].items():
            control_table.append([label, labels[scan], number(c["mean_center_minus_flank"]),
                str(c["positive_rows"])+"/16", number(c["first_8_rows_mean"]),
                number(c["last_8_rows_mean"]), number(c["minimum_of_half_means"])])
        shape_table.append([label, number(m["channel0_minus_immediate_neighbor_mean"]),
            number(m["selected_width_center_minus_median_noncentral_profile"]),
            number(m["support_mean_width3"]), number(m["support_mean_width5"]), number(m["support_mean_width9"])])
    prefix = "results/radio_stationary_family_20261010/measurement"
    text = ["# SETI — kontrolpanel og faste tidsvinduer, 10. oktober 2026", "",
        "**Det nye resultat er deskriptiv lighed mellem de valgte ON- og OFF-profiler.** For de oprindeligt valgte bredde1-profiler er medianen af center-minus-flanke **0,116305 i ON** og **0,115910 i OFF**. Medianen af det mindste af de to faste halvmidler er **0,092240 i ON** og **0,092513 i OFF**. Det centrale trekanalsmål har median **0,114243 i ON** og **0,112607 i OFF**. Et smalt centralt overskud og positive faste halvvinduer forekommer således også blandt de udvalgte OFF-profiler.", "",
        "De seks på forhånd udpegede svage ON-profiler har fortsat større faste center-midler end deres tilstødende OFF-profiler ved præcis samme frekvens. Alle seks har positivt middel i begge faste otterækkershalvdele. **Alle seks forbliver uafklarede.** Liggende tæt på et udvalgt kontrolpanels typiske formmål er hverken en støjklassifikation, en falskalarmrate eller bevis for celestial oprindelse. A/B er fortsat **FAIL_CLOSED**; den kvalificerede sky-pilot er fortsat blokeret.", "",
        "## Hvad denne omgang tilføjer", "",
        "Den allerede afsluttede stationære top20-familie fra 9. oktober er udvidet til samme faste tids- og frekvensprojektioner for **alle 120 profil-ID'er**: 20 fra hver af de seks scanninger, 60 valgt i ON og 60 valgt i reciprokke OFF-rangeringer. Alle 120 har forskellige præcise centerkanaler, men er ikke uafhængige signaler. Deres lokale udsnit og kontrolscanninger kan overlappe, og det er ét historisk besøg af HIP98505/HD189733 den **17. marts 2016**.", "",
        "De ni eksisterende stationære ON-profiler med rang 1–3 blev genbrugt uden genmåling: raw-power, normaliseret power, flankmedianer, 16 residualrækker, middelprofiler samt de gamle middel-, median- og positiv-række-tællinger er bevaret. Præcis **111** resterende cases blev målt én gang fra de allerede gemte native chunk151-filer med de allerede gemte full-chunk-rækkemedianer. De nye halvvindue- og frekvensformmål blev afledt for alle 120 cases.", "",
        "Resultatet indeholder **720 scan-profiler** med alle 16 rækker, svarende til **11.520 tidsrække-forekomster**. Forekomsterne er dokumentationsrækker; de er ikke 11.520 uafhængige observationer. Der er ikke hentet nye teleskopdata, genkørt en søgning eller tilpasset frekvens, drift, bredde, kanalskift, tærskel eller tidsvindue.", "",
        "## Hele det valgte panel", "",
        table(["Oprindelse", "Oprindelig bredde", "Antal", "Median, center-minus-flanke", "Median, mindste halvmiddel", "Median, central minus naboer", "16/16 positive rækker"], family_table), "",
        "De oprindelige bredde1-grupper indeholder 58 ON-profiler og 60 OFF-profiler. Bredde3 har kun to ON-profiler og **ingen OFF-profiler**. OFF-bredde3 er derfor eksplicit `EMPTY_UNSUPPORTED_COMPARISON`; der er ingen indsatte nulværdier eller sammenlægning af bredder for at skabe en kunstig sammenligning.", "",
        "Seks af de 58 ON-bredde1-profiler og syv af de 60 OFF-bredde1-profiler har 16 positive residualrækker. ON-bredde3 har én sådan profil blandt to. Disse tal tilhører et udvalgt, korreleret top20-panel. De er ikke binomialforsøg eller en kalibrering af hele den oprindelige millionkanalsøgning.", "",
        "ON og OFF er ikke dokumenteret udskiftelige. Hver oprindelse er valgt af sin egen kontrast-rangering, antallet af tilstødende kontroller varierer, flere cases bruger samme kontrolscanninger, og de individuelle normaliseringer og observationstidspunkter kan påvirke profilerne. OFF er heller ikke certificeret ren støj.", "",
        f"![Middel efter rolle og oprindelig bredde]({prefix}/presentation/ORIGIN_MEAN_BY_ROLE_WIDTH.png)", "",
        f"![Mindste faste halvmiddel efter rolle og bredde]({prefix}/presentation/ORIGIN_MIN_HALF_BY_ROLE_WIDTH.png)", "",
        "## De seks faste svage cases", "",
        "Alle seks har oprindelig bredde 1. Tabellen genbruger deres allerede gemte center-middel, median og antal positive rækker. De tilstødende OFF-værdier gælder præcis samme native kanal og bredde; der er ikke søgt efter et nyt OFF-maksimum.", "",
        table(["Case", "MHz", "ON-middel", "ON-median", "Positive rækker", "Faste tilstødende OFF-midler"], weak_table), "",
        "Den oprindelige stationære udvælgelse brugte derimod et ±32-kanalers kontrol-envelope i en anden fraktionel spektral størrelse. De nye additive center-profiler erstatter ikke den udvælgelsesregel. Større middel i ON ved den valgte kanal kan være en konsekvens af udvælgelsen og afgør ikke oprindelsen.", "",
        "## To faste halvdele", "",
        "Halvdelene er på forhånd defineret som rækker 0–7 og 8–15 i hver enkelt scanning. Der er ingen søgning efter det bedste starttidspunkt eller den bedste varighed. Det mindste af de to halvmidler beholder fortegnet og beskriver kun disse to faste vinduer.", "",
        table(["Case", "Første 8 rækker", "Sidste 8 rækker", "Mindste halvmiddel"], half_table), "",
        "De seks ON-profiler har positive middelværdier i begge halvdele, med mindste halvmiddel fra **0,069296 til 0,130416**. Deres positive rækker er fortsat 13–15 af 16. Nogle profiler ændrer amplitude mellem halvdelene; tabellen estimerer hverken en begivenhedsvarighed eller en sandsynlighed for vedvarende emission.", "",
        table(["Case", "Tilstødende OFF", "OFF-middel", "Positive OFF-rækker", "Første 8", "Sidste 8", "Mindste OFF-halvmiddel"], control_table), "",
        "De tilstødende OFF-profiler ved disse præcise kanaler har små positive eller negative faste halvmidler. Det bredere panel af særskilt udvalgte OFF-cases indeholder samtidig positive og smalle profiler, inklusive 16/16-positive eksempler. Sammenligningen skal derfor fastholde både de konkrete parrede kontroller og udvælgelsesfamilien; ingen af dem er alene en kvalificeret nulmodel.", "",
        f"![Første versus sidste faste halvdel]({prefix}/ORIGIN_FIXED_HALF_COMPARISON.png)", "",
        "## Fast frekvensform", "",
        "Profilen e(offset) er middel over de 16 rækker af række-normaliseret raw power minus hver rækkes faste flankmedian. Den faste flank bruger |offset| > 3 inden for ±64 native kanaler. Alle offsets, de oprindelige centerkanaler og bredder er bevaret.", "",
        "Trekanalsmålet er e(0) minus middel af e(−1) og e(+1) for alle cases. Boxmålet er middel over den oprindeligt valgte bredde minus middel af de to nærmeste kanaler umiddelbart uden for denne bredde. **For bredde 1 er disse to mål algebraisk identiske og dermed samme evidens**, ikke to uafhængige indikatorer. For bredde 3 bruges ydernaboerne ved ±2; bredderne er ikke genrangeret.", "",
        "Et tredje mål er det valgte center-boxmiddel minus medianen af den fulde middelprofils ikke-centrale offsets med |offset| > 3. De faste supportmidler over 3, 5 og 9 kanaler er også gemt. Disse overlappende mål er indbyrdes afhængige; supportbredde9 bruger også offsets, som indgik i flankmedianen. De er ikke fysiske linjebredder.", "",
        table(["Case", "Central minus naboer", "Box minus median af ikke-centrale offsets", "Middel over 3", "Middel over 5", "Middel over 9"], shape_table), "",
        f"![Fast central og box-form efter rolle og bredde]({prefix}/presentation/ORIGIN_SHAPE_BY_ROLE_WIDTH.png)", "",
        "## Tidsfigurer og reproducerbar dokumentation", ""]
    for case in weak:
        name = case["profile_id"]+"_all_six_times.png"
        text.append(f"- `{case['profile_id']}`: [Alle seks scanninger og 16 rækker]({prefix}/{name})")
    text += ["", "Alle raw float32-patches, normaliserede float64-patches, residualer, middelprofiler, metadata, faktiske scan-tider og gemte normaliseringer findes i `ALL_120_FIXED_STATIONARY_PATCHES.npz`. Alle 720 scan-profiler og deres 16 residualrækker er også bevaret i JSON. De to CSV-filer er direkte serialisering af de gemte tal: `ALL_720_SCAN_PROFILE_ROWS.csv` og `ALL_11520_TIME_ROW_OCCURRENCES.csv`.", "",
        "De tre rapporterede summaryfigurer under `measurement/presentation/` er layoutkopier fra allerede gemte data. Oprindelige outputfigurer og arrays er bevaret uændret. Den oprindelige halvdelssammenligning og de seks svage tidsfigurer bruges direkte. Ingen analyse er genkørt for at rette figurernes etiketter eller margener.", "",
        "## Afgrænsning og næste evidenstrin", "",
        "Denne scope var prospective for de nye afledte mål, **efter** at de gamle kildedata og rangeringer allerede var åbnet. Den er ikke blind eller uafhængig validering. Det fulde top20-panel er heller ikke hele den oprindelige søgningshypotesefamilie. Fordelingslighed i det valgte panel gør ikke de seks cases til certificeret støj; individuelle positive forskelle gør dem heller ikke til fund.", "",
        "Det primære næste evidenstrin er fortsat et uafhængigt besøg med frekvensoverlap eller en separat kvalificeret korrelationsbevarende kontrolmodel, som omfatter den relevante fulde udvælgelsesfamilie. De gamle kvalifikationsfejl og holdouts er ikke genåbnet. Der er ikke udledt sky-SNR, falskalarmrate, flux, følsomhedsgrænse eller celestial oprindelse.", "",
        "## Freeze og udførelse", "",
        "Kode, inputhashes, faste cases, metrikker og ressourcegrænser blev offentliggjort og læst tilbage før kørsel i [03de4adda318905f3c0685af827e62a8d1af72a3](https://github.com/andersenmartin-blip/setisearch/commit/03de4adda318905f3c0685af827e62a8d1af72a3). Den autoritative forrige offentliggørelse er `08d0bc6b7a09a4cc6cd238fc9626515eef842398`.", "",
        f"Den ene signalanalyse blev afsluttet på **{number(receipt['process_CPU_seconds_including_imports'], 3)} CPU-sekunder** og {number(receipt['wall_seconds_including_imports'], 3)} vægsekunder; maksimal RSS var {receipt['peak_RSS_bytes']:,} byte. Loftet var 80 CPU-sekunder, 1.800 vægsekunder og 4 GiB. Aktivitetens samlede konservative CPU-reservation var 250 sekunder. Nye teleskopkildebyte: **0**.", "",
        "De komplette afledte artefakter samles i `SETI_STATIONARY_FAMILY_2026-10-10.zip`. Arkivhash og faktisk tilgængelighed dokumenteres særskilt efter afsluttet lagring. De ni genbrugte NPZ-filers inputhashes blev kontrolleret før og efter analysen og forblev uændrede."]
    report.write_text("\n".join(text)+"\n")
    receipt_path = folder/"SERIALIZATION_RECEIPT.json"
    export = {"status": "COMPLETED_SAVED_JSON_CSV_SERIALIZATION_AND_REPORT_DRAFT",
        "saved_input_sha256": {key: sha(path) for key, path in paths.items()}, "scan_CSV_rows": 720,
        "time_CSV_row_occurrences": occurrences, "new_metric_measurements": False,
        "source_HTTP_or_native_array_reads": False, "numbers_written_by_Python_CSV_without_rounding": True,
        "files": [{"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size} for path in (scan_path, time_path, report)],
        "process_CPU_seconds": time.process_time()-cpu, "wall_seconds": time.monotonic()-wall,
        "report_stage": "DRAFT_PENDING_PRESENTATION_LAYOUT_QA_AND_FINAL_ARCHIVE_RECEIPTS"}
    receipt_path.write_text(json.dumps(export, indent=2, allow_nan=False)+"\n")
    print(json.dumps(export, allow_nan=False))


if __name__ == "__main__":
    main()
