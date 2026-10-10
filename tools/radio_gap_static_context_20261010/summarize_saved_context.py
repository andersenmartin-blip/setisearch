#!/usr/bin/env python3
"""One bounded report/CSV serialization from completed static-context JSON only."""
import time
START_CPU = time.process_time()
START_WALL = time.monotonic()
import argparse
import csv
import hashlib
import json
from pathlib import Path
import resource
import signal
import statistics

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results/radio_gap_static_context_20261010"
OUT = BASE / "measurement"
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
LABEL = dict(zip(SCANS, ("ON1", "OFF1", "ON2", "OFF2", "ON3", "OFF3")))
IDS = tuple(f"{scan}_gap_drift_rank_{rank:02d}" for scan in ONS for rank in (1, 2, 3))
CONTROLS = {"epoch1_on": (None, "epoch1_off"), "epoch2_on": ("epoch1_off", "epoch2_off"),
            "epoch3_on": ("epoch2_off", "epoch3_off")}
METRICS = ("static_center_minus_static_flank", "copied_moving_center_minus_same_static_flank",
           "signed_static_minus_copied_moving_center", "saved_moving_center_minus_original_moving_flank")
SHORT = ("static", "moving_same_static_background", "static_minus_moving", "moving_original_background")
STATISTICS = ("mean", "median", "positive_rows", "first_eight_mean", "last_eight_mean", "minimum_half_mean")
PLOTS = ("STATIC_MOVING_SAME_BACKGROUND_MEANS.png", "STATIC_PHYSICAL_FREQUENCY_PROFILES.png")
REPORT = ROOT / "RADIO_GAP_STATIC_CONTEXT_REPORT_2026-10-10.md"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def f(value):
    return f"{value:.6f}".replace(".", ",")


def case_label(track):
    return f"{LABEL[track['originating_scan']]} r{track['display_rank']} (w{track['width_channels']})"


def group_summary(rows):
    static = [r[METRICS[0]] for r in rows]
    differences = [r[METRICS[2]]["mean"] for r in rows]
    means = [r["mean"] for r in static]
    return {"case_scan_occurrences": len(rows), "static_mean_positive": sum(v > 0 for v in means),
            "static_first_half_positive": sum(r["first_eight_mean"] > 0 for r in static),
            "static_last_half_positive": sum(r["last_eight_mean"] > 0 for r in static),
            "static_both_halves_positive": sum(r["minimum_half_mean"] > 0 for r in static),
            "static_mean_median": statistics.median(means), "static_mean_minimum": min(means),
            "static_mean_maximum": max(means), "signed_mean_positive": sum(v > 0 for v in differences),
            "signed_mean_zero": sum(v == 0 for v in differences), "signed_mean_negative": sum(v < 0 for v in differences),
            "signed_mean_mean": statistics.mean(differences), "signed_mean_median": statistics.median(differences),
            "signed_mean_minimum": min(differences), "signed_mean_maximum": max(differences)}


def serialize_csv(records):
    scan_path = OUT / "STATIC_CONTEXT_54_SCAN_SUMMARIES.csv"
    scan_fields = ["track_id", "scan_id", "original_originating_scan", "fixed_reference_channel", "original_width_channels"]
    scan_fields += [f"{prefix}_{statistic}" for prefix in SHORT for statistic in STATISTICS]
    time_path = OUT / "STATIC_CONTEXT_864_TIME_ROWS.csv"
    time_fields = ["track_id", "scan_id", "time_row", "fixed_reference_channel", "saved_moving_center_channel",
                   "original_width_channels", "static_center_normalized_power", "copied_moving_center_normalized_power",
                   "static_flank_normalized_power", "original_moving_flank_normalized_power"]
    time_fields += [f"{prefix}_residual" for prefix in SHORT]
    scan_count = time_count = 0
    with scan_path.open("w", newline="") as scan_handle, time_path.open("w", newline="") as time_handle:
        sw, tw = csv.DictWriter(scan_handle, scan_fields), csv.DictWriter(time_handle, time_fields)
        sw.writeheader(); tw.writeheader()
        for record in records:
            track = record["selected_track"]
            for scan in record["scan_profiles"]:
                row = {"track_id": track["track_id"], "scan_id": scan["scan_id"],
                       "original_originating_scan": track["originating_scan"],
                       "fixed_reference_channel": record["fixed_physical_reference_channel"],
                       "original_width_channels": record["static_width_channels"]}
                for key, prefix in zip(METRICS, SHORT):
                    row.update({f"{prefix}_{statistic}": scan[key][statistic] for statistic in STATISTICS})
                sw.writerow(row); scan_count += 1
                for i in range(16):
                    row = {"track_id": track["track_id"], "scan_id": scan["scan_id"], "time_row": i,
                           "fixed_reference_channel": record["fixed_physical_reference_channel"],
                           "saved_moving_center_channel": scan["saved_moving_source_channel_centers"][i],
                           "original_width_channels": record["static_width_channels"],
                           "static_center_normalized_power": scan["all_16_static_center_row_normalized_power"][i],
                           "copied_moving_center_normalized_power": scan["all_16_copied_moving_center_row_normalized_power"][i],
                           "static_flank_normalized_power": scan["all_16_static_flank_row_normalized_power"][i],
                           "original_moving_flank_normalized_power": scan["all_16_original_moving_flank_row_normalized_power"][i]}
                    row.update({f"{prefix}_residual": scan[key]["all_16_rows"][i] for key, prefix in zip(METRICS, SHORT)})
                    tw.writerow(row); time_count += 1
    assert scan_count == 54 and time_count == 864
    return scan_path, time_path


def write_report(records, groups, paired, execution, freeze):
    origin = groups["originating_ON_9"]
    adjacent = groups["adjacent_OFF_15"]
    lines = ["# Fast frekvenskontekst for de ni gap-driftprofiler — 10. oktober 2026", "",
        f"Ved de ni oprindelige referencefrekvenser har {origin['static_both_halves_positive']}/9 af origin-ON-profilerne positive faste middelværdier i begge tidsmæssige halvdele. Blandt de 15 forekomster af tilstødende OFF-kontroller gælder det {adjacent['static_both_halves_positive']}/15. De statiske middelværdier spænder fra {f(origin['static_mean_minimum'])} til {f(origin['static_mean_maximum'])} i origin-ON og fra {f(adjacent['static_mean_minimum'])} til {f(adjacent['static_mean_maximum'])} i de tilstødende OFF-forekomster. Det er beskrivende tal efter udvælgelse; positivitet er ikke en kalibreret detektion.", "",
        "Diagnosen undersøger, om en lille tidligere OFF-værdi langs det valgte driftspor overså struktur på dets faste begyndelsesfrekvens. Referencesystemet er hvert spors oprindelige kanal ved origin-ON-scanningens første midpoint, ikke et tilpasset centrum for en stationær linje. De nye faste vinduer dækker derfor en bestemt fysisk kontekst og kan ikke afgøre, om der findes OFF-struktur andre steder langs hele driftsporet.", "",
        "## Beregningen og dens afgrænsning", "",
        "Alle ni tidligere offentliggjorte gap-drift rang 1–3-spor blev medtaget med deres oprindelige referencekanal og bredde 1 eller 3. For hvert spor blev samme 129 fysiske kanaler, reference ±64, udtrukket i alle seks scanninger og alle 16 tidsrækker. Normaliseringen bruger de tidligere gemte fuld-bånds rækkemedianer. Fast baggrund er medianen af de 122 rækkenormaliserede kanaler med absolut offset >3 inden for ±64.", "",
        "S betegner det faste centers middel ved oprindelig bredde minus den faste baggrund. D betegner det uændret kopierede, oprindelige bevægelige centers normaliserede middel minus præcis samme faste baggrund. Den gemte signerede forskel er Δ = statisk center minus kopieret bevægeligt center; fælles baggrund bortfalder algebraisk. Originalsporets residual med dets oprindelige bevægelige baggrund er bevaret separat.", "",
        "Ingen frekvens, drift, bredde, rang, maksimum, tærskel eller lokal forskydning blev søgt eller tilpasset. Kilde- og tidligere gap-værdier/rangeringer var allerede eksponeret; kun denne afledte diagnose blev fastlåst før beregningen. Det er ikke blind eller uafhængig validering. De seks scan-labels betegner ét historisk besøg ved HIP98505/HD189733 den 17. marts 2016, ikke tre uafhængige epoker.", "",
        "## Alle 54 faste scan-midler", "",
        "Tallene er additive forskelle i rækkenormaliseret effekt, afrundet til seks decimaler. Fuldpræcision, medianer, positive rækketal, begge halvdele og alle 16 rækker findes i JSON og CSV. Halvdelene er fast rækker 0–7 og 8–15.", "",
        "| Oprindelig case | Referencekanal | ON1 | OFF1 | ON2 | OFF2 | ON3 | OFF3 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for record in records:
        vals = [s[METRICS[0]]["mean"] for s in record["scan_profiles"]]
        lines.append(f"| {case_label(record['selected_track'])} | {record['fixed_physical_reference_channel']} | " + " | ".join(f(v) for v in vals) + " |")
    lines += ["", "## Origin-ON og de observerede nabokontroller", "",
        "ON1 har ingen forudgående OFF i dette seks-scan-udsnit; det markeres som ikke observeret. ON2 bruger OFF1 og OFF2, og ON3 bruger OFF2 og OFF3. Der vælges ingen efterfølgende kontrol ud fra resultaterne.", "",
        "| Case | Origin S | Origin D | Origin Δ | Origin mindste halvdel | Forudgående OFF S | Efterfølgende OFF S |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for row in paired:
        before = f(row["preceding_OFF"]["static"]["mean"]) if row["preceding_OFF"] else "Ikke observeret"
        after = f(row["following_OFF"]["static"]["mean"])
        lines.append(f"| {row['label']} | {f(row['origin_static']['mean'])} | {f(row['origin_moving_common']['mean'])} | {f(row['origin_signed_difference']['mean'])} | {f(row['origin_static']['minimum_half_mean'])} | {before} | {after} |")
    lines += ["", "## Signeret fast minus bevægelig forskel", "",
        "Alle 54 scan-middelforskelle er bevaret. En positiv Δ fortæller, at det fastlagte statiske center har højere normaliseret effekt end det oprindelige bevægelige center ved denne scanning. En negativ Δ fortæller det modsatte. Forskellen klassificerer ikke et signal og er ikke en signifikansstatistik.", "",
        "| Case | ON1 | OFF1 | ON2 | OFF2 | ON3 | OFF3 |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for record in records:
        vals = [s[METRICS[2]]["mean"] for s in record["scan_profiles"]]
        lines.append("| " + case_label(record["selected_track"]) + " | " + " | ".join(f(v) for v in vals) + " |")
    lines += ["", "| Beskrivende udvalg | Forekomster | S middel >0 | S begge halvdele >0 | Δ>0 / =0 / <0 | Median Δ | Δ min. / maks. |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for label, key in (("Alle", "all_54"), ("ON, alle cases", "all_ON_27"), ("OFF, alle cases", "all_OFF_27"),
                       ("Origin-ON", "originating_ON_9"), ("Tilstødende OFF", "adjacent_OFF_15")):
        g = groups[key]
        lines.append(f"| {label} | {g['case_scan_occurrences']} | {g['static_mean_positive']} | {g['static_both_halves_positive']} | {g['signed_mean_positive']} / {g['signed_mean_zero']} / {g['signed_mean_negative']} | {f(g['signed_mean_median'])} | {f(g['signed_mean_minimum'])} / {f(g['signed_mean_maximum'])} |")
    lines += ["", "Disse udvalg overlapper. De ni rangvalgte cases deler scanninger og normalisering; de 15 nabokontrolforekomster genbruger tre fysiske OFF-scanninger. Antal er derfor case×scan-forekomster, ikke uafhængige forsøg. ON/OFF-pegeretninger og observationstider er forskellige og giver ikke en udskiftelig nulfordeling.", "",
        "## Hvad diagnosen kan og ikke kan afgøre", "",
        "Det faste vindue strækker sig kun ±181,472219 Hz fra den oprindelige reference. De gamle bevægelige centers største udflugter fra disse referencer når 1.833 native kanaler, langt uden for ±64. Et svagt fast OFF-middel fastslår derfor ikke fravær af struktur langs hele det bevægelige spor, og et positivt fast OFF-middel fastslår ikke, at statisk og bevægelig struktur har samme årsag.", "",
        "Baggrundens algebraiske bortfald i Δ retter ikke forskelle i continuum eller bandpass mellem fjerntliggende centerfrekvenser. De nye statiske profiler og de gamle bevægelige profiler skal vurderes med deres forskellige frekvensgeometri. Originalsporets bevægelige flankeresidualer er bevaret som separat kontekst og kan ikke uden videre erstatte den fælles-baggrunds-sammenligning.", "",
        "Der er ingen kalibreret SNR, falsk-alarm-sandsynlighed, RFI-klassifikation, flux, følsomhed eller oprindelsesafgørelse. A/B-status er fortsat FAIL_CLOSED; ingen kvalificeret himmelpilot er optaget, og gamle holdouts er fortsat lukkede. Stærkere evidens kræver nye, uafhængige observationer med overlappende frekvensdækning og relevante kontroloplysninger.", "",
        "## Figurer og reproduktion", "",
        "- [Alle 54 S-, D- og Δ-midler på samme faste baggrund](results/radio_gap_static_context_20261010/figures/STATIC_MOVING_SAME_BACKGROUND_MEANS.png).",
        "- [Alle ni faste 129-kanalprofiler i samtlige seks scanninger](results/radio_gap_static_context_20261010/figures/STATIC_PHYSICAL_FREQUENCY_PROFILES.png). De ni paneler har separate y-skalaer; frekvenserne er fysiske, og alle 129 gemte samples er bevaret.",
        "- [Fuld resultat-JSON](results/radio_gap_static_context_20261010/measurement/STATIC_CONTEXT_PROFILES.json), [54 scan-oversigter](results/radio_gap_static_context_20261010/measurement/STATIC_CONTEXT_54_SCAN_SUMMARIES.csv) og [864 tidsrækker](results/radio_gap_static_context_20261010/measurement/STATIC_CONTEXT_864_TIME_ROWS.csv). CSV bruger Python-floatens round-trip tekstværdi uden afrunding.",
        "- Den binære fil `ALL_NINE_STATIC_AND_COPIED_MOVING_PROFILES.npz` indeholder rå/normaliserede faste profiler og uændrede bevægelige arrays; filens størrelse og SHA256 står i [eksekveringskvitteringen](results/radio_gap_static_context_20261010/measurement/EXECUTION_RECEIPT.json). Binær levering dokumenteres med den afsluttende resultatpakke.", "",
        f"Offentlig fastlåsning før numerisk kørsel: Git-commit `{freeze}`. [Numerisk kode](tools/radio_gap_static_context_20261010/static_context.py), SHA256 `{execution['script_sha256']}`; [scope](tools/radio_gap_static_context_20261010/scope.json), SHA256 `{execution['scope_sha256']}`. Scope indeholder alle input- og afhængighedshashes og de ni uændrede referencekanaler/bredder.", "",
        f"Den eneste numeriske kørsel er COMPLETE: CPU {f(execution['process_CPU_seconds_including_imports'])} s, vægtid {f(execution['wall_seconds_including_imports'])} s og maksimal RSS {execution['peak_RSS_bytes']:,} bytes. Grænser: 20 CPU-s, 1.800 s og 4 GiB; ingen genkørsel. Runtime-pins er numpy 2.3.5, h5py 3.15.1 og hdf5plugin 7.1.0 med den uændrede loader.", "",
        "Reproduktionsgrundlaget er de seks gendannede kompakte chunk151-filer, deres 96 afkodede rækkepins, de gemte normaliseringer, de ni gamle gap-NPZ og kilde-/analysemetadata. Hashverificering af kompaktene og de 96 rækker validerer disse gemte dele. Hele de oprindelige teleskopfiler er ikke gendannet, og deres fulde MD5 er fortsat uverificeret; delvise pins må ikke læses som validering af hele originalkilderne.", "",
        "Arkivgendannelsen hentede 311.847.026 bytes; de samme præcist pinnede afhængighedswheels krævede 51.507.696 bytes. Det konservative samlede kilde-, gendannelses- og afhængighedsregnskab er 2.002.313.292 bytes. Denne aktivitet foretog 0 nye teleskop-HTTP-requests og hentede 0 nye teleskop-body-bytes. Den reserverer 60 CPU-s, heraf 20 til beregning og 40 til klargøring, kontrol og publicering, inden for uændrede 43.200 CPU-s. Tidligere reservationer refunderes ikke; efter reservationen resterer 2,705145 CPU-s.", "",
        "På en separat, komplet kopi med de samme pakkeversioner og verificerede input kan den fastlåste kode køres i en ny tom resultatmappe. Kommandoen nedenfor beskriver reproduktion; den blev ikke kørt igen i dette arbejde.", "", "```bash",
        "PYTHONPATH=seti_gap_static_work/deps python setisearch_checkpoint/tools/radio_gap_static_context_20261010/static_context.py \\",
        "  --scope setisearch_checkpoint/tools/radio_gap_static_context_20261010/scope.json \\",
        f"  --expected-scope-sha256 {execution['scope_sha256']} \\",
        "  --compact-dir setisearch_checkpoint/results/radio_fresh_band_20261009/arrays \\",
        "  --acquisition-summary setisearch_checkpoint/results/radio_fresh_band_20261009/arrays/ACQUISITION_RESULT.json \\",
        "  --outdir NY_TOM_RESULTATMAPPE", "```", "",
        "[Rapport-/CSV-scriptet](tools/radio_gap_static_context_20261010/summarize_saved_context.py) læser kun afsluttet JSON og serialiserer gemte tal; det genmåler ingen science-arrays og udfører ingen ny søgning. [Beskrivende oversigt](results/radio_gap_static_context_20261010/measurement/DESCRIPTIVE_FINDINGS.json) bevarer udvalg og fuldpræcisionstal. Rapporten angiver endnu ingen afsluttet arkivlagring eller publiceringskvittering.", ""]
    REPORT.write_text("\n".join(lines).replace(f"{execution['peak_RSS_bytes']:,}", f"{execution['peak_RSS_bytes']:,}".replace(",", ".")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-freeze-commit", required=True)
    args = parser.parse_args()
    if len(args.public_freeze_commit) != 40 or any(c not in "0123456789abcdef" for c in args.public_freeze_commit):
        raise ValueError("Full public freeze commit required")
    receipt_path = OUT / "REPORT_SERIALIZATION_RECEIPT.json"
    if receipt_path.exists() or REPORT.exists():
        raise FileExistsError("Final report serialization already exists; no rerun")
    def deadline(signum, frame):
        raise TimeoutError("Two-CPU-second report cap")
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (2, 3))
    profile_path = OUT / "STATIC_CONTEXT_PROFILES.json"
    execution_path = OUT / "EXECUTION_RECEIPT.json"
    execution = json.loads(execution_path.read_text())
    if execution["status"] != "COMPLETE_NINE_GAP_STATIC_PHYSICAL_CONTEXT_EXPLORATORY_ONLY":
        raise ValueError("A complete authorized numeric job is required")
    assert digest(profile_path) == execution["summary"]["profile_JSON_sha256"]
    source = json.loads(profile_path.read_text())
    assert source["complete"] and source["completed_cases"] == source["expected_cases"] == 9
    records = source["records"]
    assert [r["selected_track"]["track_id"] for r in records] == list(IDS)
    rows, role_rows, origin_rows, adjacent_rows, paired = [], {"ON": [], "OFF": []}, [], [], []
    for record in records:
        track = record["selected_track"]
        scans = record["scan_profiles"]
        assert [s["scan_id"] for s in scans] == list(SCANS)
        assert record["fixed_physical_reference_channel"] == track["source_reference_channel"]
        assert record["static_width_channels"] == track["width_channels"]
        indexed = {s["scan_id"]: s for s in scans}
        for scan in scans:
            assert all(len(scan[key]["all_16_rows"]) == 16 for key in METRICS)
            rows.append(scan); role_rows["ON" if scan["scan_id"] in ONS else "OFF"].append(scan)
        origin = indexed[track["originating_scan"]]
        origin_rows.append(origin)
        before, after = CONTROLS[track["originating_scan"]]
        item = {"track_id": track["track_id"], "label": case_label(track),
                "origin_static": origin[METRICS[0]], "origin_moving_common": origin[METRICS[1]],
                "origin_signed_difference": origin[METRICS[2]]}
        for key, control in (("preceding_OFF", before), ("following_OFF", after)):
            item[key] = None if control is None else {"scan_id": control, "static": indexed[control][METRICS[0]],
                        "moving_common": indexed[control][METRICS[1]], "signed_difference": indexed[control][METRICS[2]]}
            if control is not None:
                adjacent_rows.append(indexed[control])
        paired.append(item)
    groups = {"all_54": group_summary(rows), "all_ON_27": group_summary(role_rows["ON"]),
              "all_OFF_27": group_summary(role_rows["OFF"]), "originating_ON_9": group_summary(origin_rows),
              "adjacent_OFF_15": group_summary(adjacent_rows)}
    findings = {"schema": "SETI_GAP_STATIC_CONTEXT_SAVED_JSON_FINDINGS_V1", "source_JSON_sha256": digest(profile_path),
                "public_freeze_commit": args.public_freeze_commit, "groups": groups, "origin_and_adjacent_controls": paired,
                "all_counts_are_dependent_case_scan_occurrences": True, "new_array_measurements": 0,
                "threshold_classification_or_probability_estimation": False}
    finding_path = OUT / "DESCRIPTIVE_FINDINGS.json"
    save_json(finding_path, findings)
    csv_paths = serialize_csv(records)
    write_report(records, groups, paired, execution, args.public_freeze_commit)
    outputs = (REPORT, finding_path, *csv_paths)
    receipt = {"schema": "SETI_GAP_STATIC_CONTEXT_REPORT_SERIALIZATION_V1",
               "status": "COMPLETE_SAVED_JSON_REPORT_CSV_PENDING_REVIEW_FIGURES_AND_ARCHIVE",
               "script_sha256": digest(Path(__file__)), "input_JSON_sha256": digest(profile_path),
               "public_freeze_commit": args.public_freeze_commit,
               "CSV_scan_rows": 54, "CSV_time_row_occurrences": 864,
               "CSV_float_serialization": "Python csv default float str preserves round-trip values; no rounding.",
               "new_array_measurements": 0, "numeric_science_reruns": 0, "new_telescope_requests": 0,
               "CPU_cap_s": 2, "output_files": [{"path": str(p.relative_to(ROOT)), "sha256": digest(p),
                                                  "bytes": p.stat().st_size} for p in outputs]}
    receipt["process_CPU_s"] = time.process_time()
    receipt["serialization_CPU_s"] = time.process_time() - START_CPU
    receipt["wall_s"] = time.monotonic() - START_WALL
    if receipt["process_CPU_s"] > 2:
        receipt["status"] = "INCOMPLETE_SERIALIZATION_CPU_CAP_NO_RETRY"
    save_json(receipt_path, receipt)
    assert receipt["process_CPU_s"] <= 2
    print(json.dumps({k: receipt[k] for k in ("status", "process_CPU_s", "serialization_CPU_s", "CSV_scan_rows", "CSV_time_row_occurrences")}))


if __name__ == "__main__":
    main()
