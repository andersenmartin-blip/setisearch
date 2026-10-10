"""Summarize saved gap ranks/profiles; never open arrays or repeat detection."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import resource
import signal
import time

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT/"results/radio_gap_drift_20261010"
MEASUREMENT = RESULTS/"measurement"
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
PAIRED_OFF = {"epoch1_on": ("epoch1_off",), "epoch2_on": ("epoch1_off", "epoch2_off"),
              "epoch3_on": ("epoch2_off", "epoch3_off")}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def label(scan):
    return scan.replace("epoch", "").replace("_", " ").upper()


def short(track):
    return label(track["originating_scan"])+"/"+str(track["display_rank"])


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (10, 11))
    signal.alarm(60)
    files = {name: MEASUREMENT/name for name in ("DRIFT_TOP20.json", "FIXED_TOP3_PROFILES.json", "EXECUTION_RECEIPT.json")}
    ranks = json.loads(files["DRIFT_TOP20.json"].read_text())
    profiles = json.loads(files["FIXED_TOP3_PROFILES.json"].read_text())
    execution = json.loads(files["EXECUTION_RECEIPT.json"].read_text())
    if set(ranks) != set(ONS) or any(len(ranks[s]) != 20 for s in ONS) or len(profiles) != 9:
        raise ValueError("Saved gap family incomplete")
    if execution["status"] != "COMPLETED_EIGHT_GAP_DRIFT_CORES_AND_NINE_FIXED_PROFILES_EXPLORATORY_ONLY":
        raise ValueError("Completed single execution required")
    if digest(files["DRIFT_TOP20.json"]) != execution["profile_summary"]["source_top20_sha256"]:
        raise ValueError("Saved rank pin differs")
    flattened = [r for s in ONS for r in ranks[s]]
    if len({r["track_id"] for r in flattened}) != 60:
        raise ValueError("Sixty distinct rank records required")
    for scan in ONS:
        if [r["display_rank"] for r in ranks[scan]] != list(range(1, 21)):
            raise ValueError("Rank display order differs")
    expected_top3 = [r for s in ONS for r in ranks[s][:3]]
    if [p["selected_track"] for p in profiles] != expected_top3:
        raise ValueError("Profiles differ from frozen top-three selection")
    summaries = []
    scan_rows = []
    for p in profiles:
        t = p["selected_track"]
        if [s["scan_id"] for s in p["scan_profiles"]] != list(SCANS):
            raise ValueError("Six-scan profile order differs")
        measurements = {}
        for s in p["scan_profiles"]:
            if len(s["all_16_center_minus_flank_rows"]) != 16 or len(s["frozen_source_channel_centers"]) != 16:
                raise ValueError("Complete stored row evidence required")
            summary = {k: v for k, v in s.items() if not k.startswith("all_16") and k != "frozen_source_channel_centers"}
            summary["minimum_half_mean_center_minus_flank"] = min(
                s["first_eight_mean_center_minus_flank"], s["last_eight_mean_center_minus_flank"])
            measurements[s["scan_id"]] = summary
            scan_rows.append({"track_id": t["track_id"], "originating_scan": t["originating_scan"],
                "display_rank": t["display_rank"], "reference_frequency_hz": t["reference_frequency_hz"],
                "drift_hz_s": t["drift_hz_s"], "width_channels": t["width_channels"],
                "maximum_robust_box_track_score": t["maximum_robust_box_track_score"],
                **summary,
                **{"residual_row_%02d" % i: x for i, x in enumerate(s["all_16_center_minus_flank_rows"])},
                **{"frozen_source_channel_row_%02d" % i: x for i, x in enumerate(s["frozen_source_channel_centers"])}})
        origin = t["originating_scan"]
        summaries.append({"selected_track": t, "origin": measurements[origin],
            "paired_OFF_exact_fixed_track": {s: measurements[s] for s in PAIRED_OFF[origin]},
            "all_six_saved_scan_metrics": measurements,
            "classification": "UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE"})
    global_maximum = max(r["maximum_robust_box_track_score"] for r in flattened)
    findings = {"status": "SAVED_GAP_RESULT_SUMMARY_NO_RESCORING",
        "input_sha256": {name: digest(path) for name, path in files.items()},
        "scope_sha256": execution["scope_sha256"], "script_sha256": execution["script_sha256"],
        "search_summary": execution["search_summary"], "rank_record_count": len(flattened),
        "profile_count": len(summaries), "profile_scan_record_count": len(scan_rows),
        "time_row_occurrences": len(scan_rows)*16,
        "largest_robust_box_track_score_all_new_carriers": global_maximum,
        "per_ON_rank_summary": {s: {
            "rank1_score": ranks[s][0]["maximum_robust_box_track_score"],
            "rank20_score": ranks[s][-1]["maximum_robust_box_track_score"],
            "selected_top20_width_counts": {str(w): sum(r["width_channels"] == w for r in ranks[s]) for w in (1, 3)}} for s in ONS},
        "all_nine_origin_minimum_half_means_positive": all(p["origin"]["minimum_half_mean_center_minus_flank"] > 0 for p in summaries),
        "origin_positive_row_count_range": [min(p["origin"]["positive_rows"] for p in summaries),
                                             max(p["origin"]["positive_rows"] for p in summaries)],
        "profile_summaries": summaries,
        "qualified_sky_pilot": False, "OFF_veto_applied": False,
        "A_B_status": "FAIL_CLOSED_UNCHANGED", "old_holdouts_reopened": False,
        "source_H5_NPZ_values_opened_for_summary": False, "detection_or_profile_measurement_repeated": False,
        "one_historical_visit": True, "source_values_previously_opened_stationary": True,
        "prospective_for_gap_drift_outcomes_only": True,
        "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
        "interpretation": "Nine selected top-three ON-origin profiles show positive mean residual in both origin scan halves, but are post-selection descriptive outcomes of a large correlated drift family. Exact predicted OFF values alone do not establish absence of neighboring OFF features or celestial origin. All cases unresolved."}
    write_json(RESULTS/"FINDINGS.json", findings)
    rank_fields = list(flattened[0])
    with (RESULTS/"DRIFT_TOP20.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rank_fields);w.writeheader();w.writerows(flattened)
    with (RESULTS/"FIXED_PROFILE_SCAN_METRICS.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(scan_rows[0]));w.writeheader();w.writerows(scan_rows)

    lines = [
        "# Otte nye driftkerner i SETI-søgningen — 10. oktober 2026", "",
        "Der er nu søgt efter lineær frekvensdrift i **otte tidligere usøgte carrierkerner** i det allerede hentede frekvensudsnit. De ni faste top-3-profiler har alle et positivt ON-overskud i både første og sidste halvdel af deres oprindelige scanning, med **13–16 positive tidsrækker ud af 16**. Dette er udvalgte maksimumspor fra en stor søgefamilie; resultatet er beskrivende og giver **ingen bekræftet SETI-detektion eller kvalificeret kandidat**.", "",
        "## Dækning og metode", "",
        "De otte nye kerner indeholder hver 4096 referencecarriers. Der er beregnet 32768 nye carriers pr. ON-scanning og 24 scan/kerne-tiles i alt. Kernerne er valgt efter en på forhånd fastlagt regel i kanalindeks og overlapper hverken hinanden eller de 32 tidligere driftkerner. Samlet driftsøgt dækning er nu **163840 carriers pr. ON-scanning: 15,625 % af chunk151**, fordelt på 40 adskilte kerner. Resten af frekvensudsnittet er fortsat ikke driftundersøgt.", "",
        "Den uændrede detektor undersøger 763 lineære driftrater fra −4 til +4 Hz/s og bredder på 1 og 3 native kanaler: 1526 gyldige hypoteser pr. carrier. Hver ON bruger sit eget første integrationsmidtpunkt som reference. Der er gemt alle carrier-maksima, vindende driftrater og bredder, gyldighedstællinger samt den fulde normalisering. Top-20 pr. ON vises med den tidligere afstandsregel på mere end tre kanaler. Der er ikke lavet en tilsvarende driftmaksimering på OFF-scanningerne.", "",
        "Top-3 pr. ON er efterfølgende målt én gang i alle seks scanninger langs den valgte, faste frekvens/drift/bredde. Profilen bruger de tidligere gemte medianer af hele frekvensudsnittets 1048576 kanaler pr. tidsrække. Ingen frekvensforskydning, refit eller ny optimering er udført. Rækkerne indeholder middel af den valgte centralbredde minus medianen af flankekanalerne med absolut kanaloffset >3 inden for ±64 kanaler. Middel, median, positive rækker og begge halvdele er gemt sammen med rå og normaliserede profiler.", "",
        "Kildedata var tidligere åbnet til stationær analyse. Afgrænsningen er prospektiv for **de nye driftudfald**, ikke blind for kildedata og ikke en uafhængig validering. Alle seks scanninger stammer fra samme historiske besøg 17. marts 2016 mod HIP98505/HD189733. Navnene epoch1/2/3 er scanningsetiketter, ikke separate besøg.", "",
        "## De ni faste top-3-profiler", "",
        "Frekvensen er ved det oprindelige ON-referencepunkt. Den robuste score og profiloverskuddet har forskellige definitioner. Scoren er ikke kalibreret SNR eller en sandsynlighed. Profilen er i enheder af rå effekt divideret med den gemte rækkemedian.", "",
        "| Spor | Frekvens (MHz) | Drift (Hz/s) | Bredde | Robust score | ON-middel | ON-positive | ON mindste halvmiddel |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for p in summaries:
        t, o = p["selected_track"], p["origin"]
        lines.append(f"| {short(t)} | {t['reference_frequency_hz']/1e6:.9f} | {t['drift_hz_s']:.9f} | {t['width_channels']} | {t['maximum_robust_box_track_score']:.6f} | {o['mean_center_minus_flank']:.6f} | {o['positive_rows']}/16 | {o['minimum_half_mean_center_minus_flank']:.6f} |")
    lines += ["", "**ON/OFF-midler ved præcis den samme valgte driftbane:** alle seks scanninger er vist. De parrede OFF-kontroller er 1 ON → 1 OFF; 2 ON → 1 OFF og 2 OFF; 3 ON → 2 OFF og 3 OFF. Dette er faste forudsigelser med de faktiske tider, ikke en søgning efter maksimum i hver kontrolscanning.", "",
        "| Spor | 1 ON | 1 OFF | 2 ON | 2 OFF | 3 ON | 3 OFF |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for p in summaries:
        lines.append("| "+short(p["selected_track"])+" | "+" | ".join(f"{p['all_six_saved_scan_metrics'][s]['mean_center_minus_flank']:.6f}" for s in SCANS)+" |")
    lines += ["", "De største robuste scorer er 5,742891 i 1 ON, 5,704613 i 2 ON og 5,982187 i 3 ON. Den største score blandt samtlige nye carriers er dermed 5,982187. Vedholdenheden i de ni udvalgte origin-scanninger er et observeret profiltræk efter udvælgelsen; der er ingen kalibreret falsk-alarmrate, og resultatet kan ikke udlægges som ni uafhængige signalfund.", "",
        "3 ON/2 ved 1427,064185809 MHz har 16 positive origin-rækker ud af 16 og mindste halvmiddel 0,120759. 3 ON/1 har den største robuste score; dens faste 3 OFF-profil har middel 0,046200 og mindste halvmiddel 0,042326. 1 ON/3 har et mindre positivt middel i flere andre scanninger, herunder 1 OFF (0,021380), 2 ON (0,025111), 2 OFF (0,020014) og 3 ON (0,029472). Disse tal er bevaret som kontrolkontekst, uden ny klassifikation.", "",
        "Et lavt eller negativt OFF-middel ved en ikke-nul driftbane viser kun udfaldet ved de forudsagte kanaler. Banen kan i en senere OFF-scanning passere væk fra en nærliggende næsten stationær linje. **Nabofrekvensers OFF-indhold er ikke undersøgt af denne faste profiltest.** Der er derfor hverken dokumenteret fravær af nærliggende OFF-emission, kvalificeret ON/OFF-udvekslelighed eller himmeloprindelse.", "",
        "## Alle seks scanningsprofiler", "",
        "Tabellen fastholder de 54 profil/scanningstilfælde. Halvmiddel er middel af de første eller sidste otte af de 16 gemte tidsrækker. Alle 864 rækkeudfald samt kanalcentrene kan læses i CSV og de oprindelige profilfiler.", "",
        "| Spor | Scanning | Middel | Median | Positive | Første 8 middel | Sidste 8 middel | Mindste halvmiddel |",
        "|---|---|---:|---:|---:|---:|---:|---:|"]
    for p in summaries:
        for s in SCANS:
            v = p["all_six_saved_scan_metrics"][s]
            lines.append(f"| {short(p['selected_track'])} | {label(s)} | {v['mean_center_minus_flank']:.6f} | {v['median_center_minus_flank']:.6f} | {v['positive_rows']}/16 | {v['first_eight_mean_center_minus_flank']:.6f} | {v['last_eight_mean_center_minus_flank']:.6f} | {v['minimum_half_mean_center_minus_flank']:.6f} |")
    lines += ["", "## Ressourcer og sporbarhed", "",
        f"Den ene numeriske kørsel afsluttede alle 24 tiles og ni profiler: **{execution['process_CPU_seconds_including_imports']:.9f} CPU-sekunder**, {execution['wall_seconds_including_imports']:.9f} s vægtid og maksimal RSS {execution['peak_RSS_bytes']} bytes. Den frosne jobgrænse var 90 CPU-sekunder, 1800 s vægtid og 4 GiB RAM. Ingen numerisk gentagelse er tilladt. Aktiviteten reserverede 160 CPU-sekunder i alt, heraf 70 til klargøring, QA, pakning og offentliggørelse; uudnyttet reservation refunderes ikke.", "",
        "**Ingen nye teleskop-HTTP-anmodninger eller kilde-bodybytes. 0 kr.** De allerede bevarede seks kompaktfiler og samtlige 96 dekodede tidsrækker blev hashkontrolleret i kørselens indlæsning.", "",
        f"- Scope SHA-256: `{execution['scope_sha256']}`",
        f"- Script SHA-256: `{execution['script_sha256']}`",
        f"- Uændret detektor SHA-256: `1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45`",
        f"- Kildemanifest SHA-256: `{execution['source_manifest_sha256']}`",
        f"- Acquisition-receipt SHA-256: `{execution['acquisition_summary_sha256']}`", "",
        "Data: `results/radio_gap_drift_20261010/measurement/` indeholder 24 komplette carrier-NPZ'er, `DRIFT_CHECKPOINT.json`, alle 60 rangeringer, ni rå/normaliserede profil-NPZ'er og de fulde seks-scansprofiler. `FINDINGS.json`, `DRIFT_TOP20.csv` og `FIXED_PROFILE_SCAN_METRICS.csv` gengiver de gemte resultater. `SUMMARY_RECEIPT.json` måler denne tekst-/CSV-sammenfatning; den åbner ingen H5/NPZ og gentager ingen detektion eller profilberegning.", "",
        "A/B forbliver **FAIL_CLOSED**, den kvalificerede pilot er fortsat blokeret, og de gamle holdouts er ikke åbnet. Alle nye profiltilfælde er uafklarede, eksplorative. Der er ingen kalibreret sky-SNR/FAP, flux, EIRP, følsomhed, oprindelsesklassifikation eller generel nulkonklusion.", ""]
    report = ROOT/"RADIO_GAP_DRIFT_REPORT_2026-10-10.md"
    report.write_text("\n".join(lines))
    outputs = [report, RESULTS/"FINDINGS.json", RESULTS/"DRIFT_TOP20.csv", RESULTS/"FIXED_PROFILE_SCAN_METRICS.csv"]
    receipt = {"status": "COMPLETED_SAVED_GAP_SUMMARY_NO_RESCORING", "rank_rows": 60,
        "profile_scan_rows": 54, "time_row_occurrences": 864,
        "source_H5_NPZ_values_opened": False, "numeric_detection_or_profile_measurement_repeated": False,
        "input_sha256": findings["input_sha256"],
        "output_files": [{"path": str(p.relative_to(ROOT)), "sha256": digest(p), "bytes": p.stat().st_size} for p in outputs],
        "process_CPU_seconds_including_imports": time.process_time(),
        "wall_seconds_including_imports": time.monotonic()-started,
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        "CPU_cap_s": 10, "wall_cap_s": 60}
    if receipt["process_CPU_seconds_including_imports"] > 10 or receipt["wall_seconds_including_imports"] > 60:
        raise RuntimeError("Summary resource cap exceeded")
    write_json(RESULTS/"SUMMARY_RECEIPT.json", receipt)
    signal.alarm(0)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
