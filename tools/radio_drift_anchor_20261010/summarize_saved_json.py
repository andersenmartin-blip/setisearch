#!/usr/bin/env python3
"""Serialize a descriptive report from completed JSON only; no NPZ or science rerun."""
import time
CPU0 = time.process_time()
WALL0 = time.monotonic()
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/radio_drift_anchor_20261010/measurement"
REPORT = ROOT / "RADIO_DRIFT_ANCHOR_REPORT_2026-10-10.md"
FREEZE = "ada64c4d46ead59b92f8e65ae2ce6aa4d13d0759"
SCRIPT_SHA = "930a89ee67b4a417917e1874629a595a644f0727077af02bfb370f7f18f0dbb5"
SCOPE_SHA = "f037f6b838ae964047584595b5ce79c5a3b7df4f2316c381c266c1c0d154ae0c"
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
LABEL = dict(zip(SCANS, ("ON1", "OFF1", "ON2", "OFF2", "ON3", "OFF3")))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def f(value):
    return f"{value:.6f}".replace(".", ",")


def aggregate(values):
    return {"count": len(values), "positive": sum(v > 0 for v in values),
            "zero": sum(v == 0 for v in values), "negative": sum(v < 0 for v in values),
            "mean": statistics.mean(values), "median": statistics.median(values),
            "minimum": min(values), "maximum": max(values)}


def main():
    receipt_path = OUT / "INTERPRETATION_RECEIPT.json"
    if receipt_path.exists():
        raise FileExistsError("Saved-JSON summary already serialized; do not rerun")
    result_path = OUT / "DRIFT_ANCHOR_RESULT.json"
    execution_path = OUT / "EXECUTION_RECEIPT.json"
    result = json.loads(result_path.read_text())
    execution = json.loads(execution_path.read_text())
    assert execution["status"] == "COMPLETE_DESCRIPTIVE_ONLY"
    assert execution["script_sha256"] == SCRIPT_SHA and execution["scope_sha256"] == SCOPE_SHA
    for item in execution["output_files"]:
        assert sha(OUT / item["path"]) == item["sha256"]
    fixed = {(r["width_channels"], r["scan_id"]): r["summary"] for r in result["fixed_reference"]}
    cases = result["original_drift_cases"]
    assert len(fixed) == 24 and len(cases) == 9
    by_role = {"ON": [], "OFF": []}
    nonzero_off, all_values, comparison_rows = [], [], []
    for case in cases:
        track = case["selected_track"]
        assert len(case["scan_comparisons"]) == 6
        for scan in case["scan_comparisons"]:
            role = "ON" if scan["scan_id"].endswith("_on") else "OFF"
            value = scan["stationary_minus_original_drifting"]["mean"]
            all_values.append(value)
            by_role[role].append(value)
            if role == "OFF" and track["drift_hz_s"] != 0:
                nonzero_off.append(value)
            comparison_rows.append({"track_id": track["track_id"], "scan_id": scan["scan_id"],
                "original_width_channels": track["width_channels"], "original_drift_hz_s": track["drift_hz_s"],
                "stationary_mean": scan["fixed_stationary_same_background"]["mean"],
                "original_drifting_mean": scan["original_drifting_same_background"]["mean"],
                "stationary_minus_original_drifting_mean": value,
                "original_saved_mean_different_background": scan["original_saved_mean_different_track_aligned_129_channel_background"]})
    aggregates = {"all_54": aggregate(all_values), "ON_27": aggregate(by_role["ON"]),
                  "OFF_27": aggregate(by_role["OFF"]), "nonzero_drift_OFF_21": aggregate(nonzero_off)}
    summary = {"schema": "SETI_SAVED_JSON_DRIFT_ANCHOR_DESCRIPTIVE_SUMMARY_V1",
               "source_result_sha256": sha(result_path), "public_scientific_freeze_commit": FREEZE,
               "aggregation_unit": "Saved signed mean difference for each selected case × scan; dependent units.",
               "aggregate_signed_mean_differences": aggregates, "all_54_saved_mean_comparisons": comparison_rows,
               "all_24_saved_fixed_reference_summaries": result["fixed_reference"],
               "all_source_values_copied_from_saved_JSON": True,
               "new_NPZ_HDF5_source_reads_or_track_measurement": False}
    summary_path = OUT / "DESCRIPTIVE_SUMMARY.json"
    save(summary_path, summary)

    lines = ["# Fast stationær reference for driftfamilien — 10. oktober 2026", "",
        "Den samme smalle frekvensstruktur er tydelig i alle tre ON-scanninger og alle tre OFF-kontroller, når de undersøges på samme faste fysiske kanaler. Ved bredde 1 er det nye middeloverskud 1,561473 i ON2 og 1,553348 i den tilstødende OFF1; forskellen er kun 0,008125. OFF1 overstiger ON1, og OFF3 overstiger ON3. Små tidligere værdier langs et ekstrapoleret driftspor kan derfor ikke læses som fravær af strukturen i OFF.", "",
        "Dette er en beskrivende diagnose af ni allerede offentliggjorte ON-valgte rang 1–3-spor omkring 1426,282 MHz. De ni er afhængige varianter af samme frekvensområde og genbruger de samme råceller. Diagnosen fastslår ingen astronomisk, teknologisk, jordbaseret eller instrumentel oprindelse og kvalificerer ikke et SETI-fund.", "",
        "## Hvad der blev fastlåst og beregnet", "",
        "Ankeret er den tidligere publicerede ON2 drift rang 01: native kanal 158766416, præcis nul drift, svarende til 1426,2821284465203 MHz. Ankeret og denne nye beregningsafgrænsning blev fastlagt efter eksponering af de gamle værdier og rangeringer, men før den nye diagnose blev kørt. Det er ikke blind eller uafhængig validering.", "",
        "De ni gemte råudsnit leverede hver en kopi af samme fysiske vindue, kanal 158766406–158766426, for alle seks scanninger og alle 16 tidsrækker. Alle ni kopier af de 2.016 float32-råceller og deres normaliserede float64-værdier var byte-identiske. Normalisering med de gemte fuld-bånds rækkemedianer reproducerede de kopierede normaliserede værdier præcist. Alle originale filhashes var uændrede bagefter. Ingen HDF5-fil eller ny teleskopkilde blev læst.", "",
        "For hver række er den nye baggrund medianen af de 14 fysiske kanaler med offset ±4..±10 fra ankeret. Den faste reference er middelværdien af de centrerede bredder 1, 3, 5 eller 9 minus denne baggrund. Originalsporets gemte middel over dets oprindelige bredde 1 eller 3 blev kopieret og fik trukket præcis samme nye fysiske baggrund fra. Der blev ikke søgt, omrangeret eller tilpasset frekvens, drift eller bredde.", "",
        "Alle tal nedenfor er additive forskelle i rækkenormaliseret effekt. De er ikke SNR, flux eller kalibreret følsomhed. Alle fuldpræcisionstal og 16 rækkers forløb findes i resultat-JSON og NPZ.", "",
        "## Fast reference i alle seks scanninger", "",
        "Tabellen viser middel, median og det mindste af de to fastlagte halvmidler, rækker 0–7 og 8–15. Begge bredder har 16/16 strengt positive residualer i hver scanning.", "",
        "| Scan | Bredde 1 middel | Bredde 1 median | Bredde 1 min. halvdel | Bredde 3 middel | Bredde 3 median | Bredde 3 min. halvdel |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for scan in SCANS:
        a, b = fixed[(1, scan)], fixed[(3, scan)]
        lines.append(f"| {LABEL[scan]} | {f(a['mean'])} | {f(a['median'])} | {f(a['minimum_half_mean'])} | {f(b['mean'])} | {f(b['median'])} | {f(b['minimum_half_mean'])} |")
    lines += ["", "Ved bredde 3 spænder alle seks middelværdier kun fra 0,832037 til 0,891072. OFF1 er 0,836950 mod ON1 0,832037; OFF2 er 0,862467 mod ON2 0,891072; OFF3 er 0,859101 mod ON3 0,867187. Kontrollerne indeholder dermed en stærk struktur på samme faste kanaler. ON og OFF kommer fra forskellige pegeretninger og tider; sammenligningen giver ikke en udskiftelig nulfordeling eller en forklaring på oprindelsen.", "",
        "Bredde 5 og 9 var også fastlagt og er bevaret i resultaterne. Deres seks middelværdier ligger henholdsvis mellem 0,506082–0,581185 og 0,288355–0,325009; der vælges ingen vinderbredde. Bredde 9 inkluderer offset ±4, som også indgår i baggrundsflanken, så center og baggrund er afhængige. De fire bredder er i øvrigt overlappende beskrivelser af samme celler.", "",
        "## Stationær minus oprindelig drift, med fælles baggrund", "",
        "Fortegnet er Δ = fast stationær reference minus det kopierede oprindelige driftspor, ved det pågældende spors oprindelige bredde. Tabellen opsummerer de 54 gemte scan-middelforskelle; antal er case×scan-forekomster, ikke uafhængige signaler eller forsøg.", "",
        "| Udvalg | Antal | Δ>0 / Δ=0 / Δ<0 | Middel Δ | Median Δ | Mindste Δ | Største Δ |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for label, key in [("Alle", "all_54"), ("ON", "ON_27"), ("OFF", "OFF_27"), ("OFF, oprindelig drift ≠0", "nonzero_drift_OFF_21")]:
        a = aggregates[key]
        lines.append(f"| {label} | {a['count']} | {a['positive']} / {a['zero']} / {a['negative']} | {f(a['mean'])} | {f(a['median'])} | {f(a['minimum'])} | {f(a['maximum'])} |")
    lines += ["", "For alle 21 OFF-sammenligninger fra de syv oprindelige spor med ikke-nul drift er den faste reference større: Δ=0,511981–0,874247. Det viser, at de oprindelige forudsigelser kan bevæge sig væk fra den fælles struktur ved OFF-tiderne. Det er en konkret geometrisk begrænsning ved at bruge en lille OFF-værdi langs netop det ekstrapolerede spor som fraværstest. De 21 forekomster genbruger tre kontroller og overlappende celler; fortegnene giver ingen falsk-alarm-sandsynlighed.", "",
        "ON2 rang 01 har præcis Δ=0 i alle 16 rækker i alle seks scanninger, fordi dens nul-drift-kanal og bredde 1 er identiske med ankeret. Det er en identitetskontrol, ikke ny evidens. ON3 rang 01 har også nul drift, men centerkanal 158766417 og bredde 3. Dets vindue er forskudt én kanal; dér er Δ=−0,031808 i ON3 og −0,015628 i OFF3. Ankeret blev ikke flyttet for at maksimere værdierne.", "",
        "Alle 54 middelforskelle er vist her, afrundet til seks decimaler. Rækkerne identificeres ved den oprindelige ON-rang og bredde:", "",
        "| Oprindelig case | ON1 | OFF1 | ON2 | OFF2 | ON3 | OFF3 |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for case in cases:
        track = case["selected_track"]
        label = f"{LABEL[track['originating_scan']]} r{track['display_rank']} (w{track['width_channels']})"
        vals = [s["stationary_minus_original_drifting"]["mean"] for s in case["scan_comparisons"]]
        lines.append("| " + label + " | " + " | ".join(f(v) for v in vals) + " |")
    lines += ["", "## Baggrund, figurer og fortolkning", "",
        "De gamle profilmidler brugte en median over track-aligned offset med |offset|>3 i et 129-kanalvindue, ±64. Den nye baggrund bruger 14 faste fysiske kanaler. De gamle middelværdier er bevaret separat og blev ikke genmålt. Eksempelvis var ON2 rang 01 tidligere 1,578749 i ON2 og 1,558537 i OFF1; på den nye fælles baggrund er tallene 1,561473 og 1,553348. En ændret baggrund skal derfor holdes adskilt fra forskellen mellem faste og bevægelige centergeometrier. I Δ-rækkerne bortfalder den fælles baggrund algebraisk.", "",
        "Alle tre originale figurer er kontrolleret visuelt i fuld opløsning: titler, mærkater og farveskalaer er læsbare. Vandfaldet har samme fysiske frekvensakse og farveskala i alle seks paneler; tidsfiguren deler y-område og viser alle 16 rækker. Farver begrænses til de fastlåste visningsintervaller −0,5..3,0 og −2,5..2,5 med markerede farveskalaender; de gemte tal begrænses ikke.", "",
        "- [Fælles fysiske 21-kanal-vandfald](results/radio_drift_anchor_20261010/measurement/COMMON_PHYSICAL_WATERFALL.png)",
        "- [Faste bredder 1 og 3, alle tidsrækker](results/radio_drift_anchor_20261010/measurement/FIXED_REFERENCE_TIME.png)",
        "- [Stationært og oprindeligt driftmiddel på samme baggrund](results/radio_drift_anchor_20261010/measurement/SAME_BACKGROUND_MEAN_DIFFERENCE.png)", "",
        "Alle seks scanninger tilhører én historisk observation af HIP98505/HD189733 den 17. marts 2016, cadence 85030. Ni rangvalgte spor, flere bredder og de gentagne kontroller tilfører ingen uafhængige observationer. Den tidligere A/B-kvalifikation er fortsat FAIL_CLOSED. En ny, uafhængig observation med overlappende frekvensdækning og samtidige kontroloplysninger er den primære vej til stærkere evidens; denne diagnose erstatter den ikke.", "",
        "## Reproduktion og gennemførelse", "",
        f"Den offentlige fastlåsning af kode og afgrænsning var Git-commit `{FREEZE}` og blev læst tilbage med eksakt hashmatch før den eneste autoriserede numeriske kørsel.", "",
        f"- [drift_anchor.py](tools/radio_drift_anchor_20261010/drift_anchor.py): SHA256 `{SCRIPT_SHA}`.",
        f"- [analysis_scope.json](tools/radio_drift_anchor_20261010/analysis_scope.json): SHA256 `{SCOPE_SHA}`; indeholder alle 14 inputfilers størrelse/hash, ni oprindelige spor og de faste definitioner.",
        "- Runtime: numpy 2.3.5 og matplotlib 3.10.8; ingen HDF5-afhængighed i denne diagnose.",
        "- Beregning COMPLETE_DESCRIPTIVE_ONLY: CPU 1,61992847 s, vægtid 1,624173316 s, maksimal RSS 129.560.576 bytes; grænser 40 CPU-s, 1.800 s og 4 GiB. Nye kildedata: 0 bytes.",
        "- [Original resultat-JSON](results/radio_drift_anchor_20261010/measurement/DRIFT_ANCHOR_RESULT.json), [fælles rå-/normaliserings-/sammenlignings-NPZ](results/radio_drift_anchor_20261010/measurement/COMMON_ANCHOR_AND_COMPARISONS.npz) og [eksekveringskvittering](results/radio_drift_anchor_20261010/measurement/EXECUTION_RECEIPT.json).",
        "- [Beskrivende oversigt fra gemt JSON](results/radio_drift_anchor_20261010/measurement/DESCRIPTIVE_SUMMARY.json) og [rapporteringsscript](tools/radio_drift_anchor_20261010/summarize_saved_json.py). Oversigten læser gemte JSON-tal og udfører ingen profilberegning, ny søgning eller NPZ-genmåling.", ""]
    REPORT.write_text("\n".join(lines))
    plots = ("COMMON_PHYSICAL_WATERFALL.png", "FIXED_REFERENCE_TIME.png", "SAME_BACKGROUND_MEAN_DIFFERENCE.png")
    receipt = {"schema": "SETI_DRIFT_ANCHOR_SAVED_JSON_REPORT_RECEIPT_V1",
               "status": "DRAFT_SAVED_JSON_SUMMARY_AND_VISUAL_QA_COMPLETE_PENDING_SCIENTIFIC_REVIEW",
               "public_scientific_freeze_commit": FREEZE, "input_result_sha256": sha(result_path),
               "execution_receipt_sha256": sha(execution_path), "frozen_analysis_script_sha256": SCRIPT_SHA,
               "frozen_analysis_scope_sha256": SCOPE_SHA, "summary_script_sha256": sha(Path(__file__)),
               "summary_sha256": sha(summary_path), "report_sha256": sha(REPORT),
               "summary_cpu_cap_s": 10, "new_numeric_analysis_runs": 0, "new_source_bytes": 0,
               "numeric_input_reads": "Completed JSON only; hashing old scientific outputs does not decode NPZ.",
               "visual_QA": {"method": "All three PNGs viewed with view_image detail original and emitted at original detail.",
                              "status": "PASS", "plot_files": [{"path": p, "sha256": sha(OUT / p)} for p in plots]}}
    receipt["cpu_s"] = time.process_time() - CPU0
    receipt["wall_s"] = time.monotonic() - WALL0
    if receipt["cpu_s"] > 10:
        receipt["status"] = "INCOMPLETE_SUMMARY_CPU_CAP_EXCEEDED"
    save(receipt_path, receipt)
    assert receipt["cpu_s"] <= 10
    print(json.dumps({k: receipt[k] for k in ("status", "cpu_s", "wall_s", "report_sha256", "summary_sha256")}))


if __name__ == "__main__":
    main()
