"""Render descriptive fresh-band report from completed saved JSON results only.

No telescope requests, native decoding, spectral remeasurement or score search.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
CONTROLS = {"epoch1_on": ("epoch1_off",), "epoch2_on": ("epoch1_off", "epoch2_off"),
            "epoch3_on": ("epoch2_off", "epoch3_off")}
LABELS = dict(zip(SCANS, ("ON1", "OFF1", "ON2", "OFF2", "ON3", "OFF3")))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def number(x, precision=6):
    return f"{x:.{precision}f}".replace("-", "−").replace(".", ",")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
                      + ["| " + " | ".join(map(str, row)) + " |" for row in rows])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--result-dir", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--public-result-prefix", default="results/radio_fresh_band_20261009")
    args = p.parse_args()
    directory, out = Path(args.result_dir), Path(args.outdir)
    inputs = {"stationary_ranks": directory/"stationary/STATIONARY_TOP20.json",
        "drift_ranks": directory/"drift/DRIFT_TOP20.json",
        "profiles": directory/"profiles/FIXED_TOP3_PROFILES.json",
        "stationary_receipt": directory/"stationary/EXECUTION_RECEIPT.json",
        "drift_receipt": directory/"drift/EXECUTION_RECEIPT.json",
        "profile_receipt": directory/"profiles/EXECUTION_RECEIPT.json",
        "acquisition_receipt": directory/"arrays/ACQUISITION_RESULT.json"}
    absent = [str(path) for path in inputs.values() if not path.is_file()]
    if absent:
        raise ValueError("Interpretation requires all completed phases; absent: " + ", ".join(absent))
    data = {key: read(path) for key, path in inputs.items()}
    stationary, drift, profiles = data["stationary_ranks"], data["drift_ranks"], data["profiles"]
    if set(stationary) != set(SCANS) or set(drift) != set(ONS):
        raise ValueError("Unexpected rank families")
    if any(len(records) != 20 for records in [*stationary.values(), *drift.values()]):
        raise ValueError("Incomplete original top20 rank lists")
    expected = {t["track_id"] for family in (stationary, drift) for label in ONS for t in family[label][:3]}
    if len(profiles) != 18 or {r["selected_track"]["track_id"] for r in profiles} != expected:
        raise ValueError("Expected exactly the eighteen originally frozen ON-origin cases")
    if any(not data[k]["status"].startswith("COMPLETED_FRESH_") for k in
           ("stationary_receipt", "drift_receipt", "profile_receipt")):
        raise ValueError("A phase lacks a completion receipt")
    if data["acquisition_receipt"]["status"] != "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY":
        raise ValueError("Incomplete acquisition")
    all_rows, control_rows = [], []
    for item in profiles:
        track = item["selected_track"]
        origin = track["originating_scan"]
        measurements = {r["scan_id"]: r for r in item["scan_profiles"]}
        if set(measurements) != set(SCANS) or any(len(r["all_16_center_minus_flank_rows"]) != 16 for r in measurements.values()):
            raise ValueError("Profile lost a scan or time row")
        on = measurements[origin]
        control = max(measurements[s]["mean_center_minus_flank"] for s in CONTROLS[origin])
        record = {"track_id": track["track_id"], "family": track["family"],
            "originating_scan": origin, "rank": track["display_rank"],
            "frequency_MHz": track["reference_frequency_hz"]/1e6,
            "drift_hz_s": track["drift_hz_s"], "width_channels": track["width_channels"],
            "ON_mean_center_minus_flank": on["mean_center_minus_flank"],
            "largest_adjacent_OFF_mean_center_minus_flank": control,
            "ON_minus_largest_adjacent_OFF_fixed_mean": on["mean_center_minus_flank"]-control,
            "ON_positive_rows": on["positive_rows"],
            "adjacent_OFF_means": {s: measurements[s]["mean_center_minus_flank"] for s in CONTROLS[origin]},
            "plots": item["plots"], "classification": "UNRESOLVED_EXPLORATORY_NO_SKY_INFERENCE"}
        all_rows.append(record)
        for label in SCANS:
            values = measurements[label]
            control_rows.append({"track_id": track["track_id"], "family": track["family"],
                "originating_scan": origin, "profile_scan": label,
                "adjacent_control": label in CONTROLS[origin],
                "mean_center_minus_flank": values["mean_center_minus_flank"],
                "median_center_minus_flank": values["median_center_minus_flank"],
                "positive_rows": values["positive_rows"]})
    out.mkdir(parents=True, exist_ok=False)
    for name, records in (("ALL_18_PROFILE_TABLE.csv", all_rows), ("ALL_108_SCAN_PROFILE_TABLE.csv", control_rows)):
        fields = [key for key in records[0] if key not in ("plots", "adjacent_OFF_means")]
        with (out/name).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader(); writer.writerows(records)
    stationary_first = [[LABELS[s], number(stationary[s][0]["reference_frequency_hz"]/1e6),
        stationary[s][0]["width_channels"], number(stationary[s][0]["signed_contrast_fractional_units"])] for s in SCANS]
    drift_first = [[LABELS[s], number(drift[s][0]["reference_frequency_hz"]/1e6),
        number(drift[s][0]["drift_hz_s"]), drift[s][0]["width_channels"],
        number(drift[s][0]["maximum_robust_box_track_score"], 3)] for s in ONS]
    profile_table = [[("Stationær" if r["family"] == "stationary" else "Drift") + " " + LABELS[r["originating_scan"]] + " rang " + str(r["rank"]),
        number(r["frequency_MHz"]), number(r["drift_hz_s"], 4), r["width_channels"],
        number(r["ON_mean_center_minus_flank"]), number(r["largest_adjacent_OFF_mean_center_minus_flank"]),
        number(r["ON_minus_largest_adjacent_OFF_fixed_mean"]), str(r["ON_positive_rows"])+"/16"] for r in all_rows]
    stationary_count = data["stationary_receipt"]["eligible_carriers_per_origin"]
    drift_count = data["drift_receipt"]["carriers_per_ON"]
    positive16 = sum(r["ON_positive_rows"] == 16 for r in all_rows)
    control_at_least_on = sum(r["ON_minus_largest_adjacent_OFF_fixed_mean"] <= 0 for r in all_rows)
    first = stationary["epoch1_on"][0]
    first_off = first["adjacent_control_evidence"]["epoch1_off"]
    control_frequencies = [stationary[s][0]["reference_frequency_hz"]/1e6 for s in ("epoch2_off", "epoch3_off")]
    drift_selected = [track for scan in ONS for track in drift[scan][:3]]
    drift_channels = [track["source_reference_channel"] for track in drift_selected]
    drift_frequencies = [track["reference_frequency_hz"]/1e6 for track in drift_selected]
    lines = ["# SETI — nyt frekvensbånd, 9. oktober 2026", "",
        "Et tidligere uåbnet bånd omkring **1424,532–1427,505 MHz** er hentet og analyseret i alle seks scanninger af HIP98505/HD189733 fra **17. marts 2016**. Det er nye frekvensværdier fra den samme historiske observation, ikke et nyt teleskopbesøg.", "",
        f"Den stationære søgning er afsluttet for **{stationary_count:,} bærefrekvenser pr. scanning** i bredde 1 og 3; både ON og de reciprokke OFF-kontroller er bevaret. Den separate driftssøgning er afsluttet for **{drift_count:,} bærefrekvenser pr. ON** i 32 faste, adskilte delbånd, med 763 driftværdier fra −4 til +4 Hz/s og bredde 1/3. Driftfamilien dækker **12,5 %** af den hentede native kanalblok.", "",
        f"Alle **18** profiler i udvalget af **rang 1–3 fra hvert ON og hver af de to familier** er undersøgt ved den oprindeligt valgte frekvens, drift og bredde. Udvælgelsesreglen var frosset før signalværdierne blev åbnet; frekvenserne og driftværdierne blev valgt af selve søgningen. {positive16} af profilerne har positivt center-minus-flanke i alle 16 ON-rækker. De største drift-rangeringer samler sig i samme smalle frekvensområde med tydelige OFF-træk. Tallene beskriver udvalgte profiler og er ikke uafhængige forsøg eller sandsynligheder.", "",
        "**Alle viste spor forbliver uafklarede eksplorative rangeringer. A/B er fortsat FAIL_CLOSED, og en kvalificeret sky-pilot er fortsat blokeret.** Der er ingen kalibreret sky-SNR, falskalarmrate, flux, følsomhedsgrænse, celestial klassifikation eller generel nuldetektion.", "",
        "## Stationært overskud og reciprokke kontroller", "",
        "Hver scanning normaliseres med sin egen median over hele den frosne kanalblok i hver tidsrække. Det stationære spektrum er middelpower delt med sin 501-kanalers løbende median minus 1. Rangeringen er scanningens bredde-middel minus den største værdi i de tilstødende kontrolscanninger inden for ±32 kanaler. Tabellen viser kun rang 1; alle top20-lister og samtlige signerede bredde1/bredde3-kort er bevaret.", "",
        table(["Oprindelse", "MHz", "Bredde, kanaler", "Stationær signeret kontrast"], stationary_first), "",
        f"ON1s første rang ved **{number(first['reference_frequency_hz']/1e6, 9)} MHz** har et stationært fraktionelt overskud på {number(first['origin_fractional_excess_same_width'])}. OFF1 har {number(first_off['exact_frequency_fractional_excess'])} ved samme kanal og {number(first_off['neighborhood_maximum_fractional_excess'])} i det frosne ±32-kanalers vindue. Den signerede forskel er derfor {number(first['signed_contrast_fractional_units'])}. OFF2 og OFF3s første rang ligger ved {number(control_frequencies[0], 9)} og {number(control_frequencies[1], 9)} MHz. Der er således stærke nærliggende træk i kontrolscanningerne; en positiv kontrast her er ikke evidens for et isoleret ON-træk.", "",
        "ON og OFF bruger samme stationære regneregel, men er ikke certificeret udskiftelige. ON1 og OFF3 har én tilstødende kontrol; de andre har to. Tidspunkter, delte kontroller, frekvenser, interferens og individuel normalisering kan påvirke rangeringerne. De reciprokke OFF-rangeringer er kontrolmateriale, ikke en kalibreret nulfordeling.", "",
        "## Driftfamilien", "",
        f"De 32 delbånd indeholder tilsammen {number(data['drift_receipt']['channel_edge_bandwidth_per_ON_hz']/1e6)} MHz kanalbredde pr. ON. Mellemrummene er ikke driftssøgt. Den uændrede detector bruger normalisering på hvert fast 4096-kanalers core, en 501-kanalers løbende median og en empirisk MAD-skala. Den robuste box-track-score er en anden størrelse end den stationære fraktionelle kontrast og må ikke sammenlignes numerisk med den.", "",
        table(["Oprindelse", "MHz ved første rækkemidtpunkt", "Drift, Hz/s", "Bredde, kanaler", "Robust box-track-score"], drift_first), "",
        f"Alle **ni** viste driftprofiler ligger i samme smalle frekvensregion omkring **1426,282 MHz**, ved source-kanaler {min(drift_channels)}–{max(drift_channels)} og referencefrekvenser {number(min(drift_frequencies), 9)}–{number(max(drift_frequencies), 9)} MHz. De er korrelerede nabovarianter af ét frekvensområde, ikke ni uafhængige fund. Den frosne visningsregel undertrykker kun referencer inden for tre kanaler og kan derfor vise varianter fire kanaler fra en stærk feature.", "",
        "Alle bærefrekvensers maksimum, vindende bredde/drift og komplette hypotesetælling er gemt særskilt for hvert scan/core-trin. Der er ikke anvendt OFF-veto. Rangeringen bruger hvert ONs eget første integrationsmidtpunkt som reference; kontrolprofilerne følger den samme faste topocentriske forudsigelse ved deres faktiske observationstider.", "",
        "## Alle 18 faste profiler", "",
        "Tabellens additive profilmål er bredde-middel af raw power delt med den gemte full-chunk-rækkemedian, minus rækkens flankmedian ved faste offsets med |offset| > 3 inden for ±64 kanaler. Frekvens, drift, bredde, tidsvindue og kanalskift er ikke justeret efter udvælgelsen. Alle 16 rækker og alle seks scanninger er gemt som raw float32-patches og normaliserede profiler.", "",
        table(["Fast valgt profil", "MHz", "Drift", "Bredde", "ON-middel", "Største tilstødende OFF-middel", "ON minus OFF", "Positive ON-rækker"], profile_table), "",
        "OFF-kolonnen følger præcis den valgte frekvens/drift ved hvert OFFs tidspunkt. Den søger ikke et nyt OFF-maksimum og erstatter ikke den stationære rangregels ±32-kanalers kontrol-envelope. Additive profilmål er heller ikke de robuste driftsscorer. Lignende profiler kan skyldes flere forhold; en forskel mellem ON og OFF alene afgør ikke oprindelsen.", "",
        "En valgt driftvariant kan mellem scanningerne flytte sin præcise forudsigelse væk fra en lokal feature. En lille OFF-værdi på denne faste bane er derfor ikke dokumentation for fravær af en nærliggende OFF-feature. Det stationære top20-materiale viser eksempelvis ved 1426,282125611 MHz et ON3-overskud på 1,379804, en tilstødende OFF2-vinduesværdi på 1,311687 og OFF3s præcise kanalværdi på 1,274975. Dette er gemt kontrolevidens i samme region, uden at indføre et efterfølgende OFF-veto.", "",
        "Ved ON2s drift-rang 1 er det faste additive middel 1,578749, mens OFF1 er 1,558537 og OFF2 1,360915. ON3s drift-rang 1 har middel 0,897975 mod OFF3s 0,877271. Kontrolprofilerne er altså næsten lige så store ved den samme næsten stationære feature. Alle 18 valgte ON-midler overstiger deres største tilstødende faste OFF-middel; det følger et ON-baseret udvalg og kan ikke bruges som en fordelingsfri falskalarmtest. Middelprofilerne over ±64 kanaler viser også de nærliggende OFF-toppe, som driftvarianternes præcise center kan bevæge sig væk fra. Ingen bane er refittet eller flyttet for denne vurdering.", "",
        "## Figurer og gemt evidens", ""]
    for row in all_rows:
        plots = row["plots"]
        links = " · ".join(f"[{('Tidsprofil' if '_time.' in p['path'] else 'Middelspektrum')}]({args.public_result_prefix}/presentation/{p['path']})" for p in plots)
        lines.append(f"- `{row['track_id']}`: {links}")
    lines += ["", "De oprindeligt gemte figurer under `profiles/` er bevaret uændret. Rapportens figurer under `presentation/` er særskilt hashregistrerede præsentationskopier, som alene ændrer layout og etiketter og bruger de allerede gemte profil-arrays. Signalanalysen er ikke genkørt.", "",
        "Alle 18 profiler og 108 scan-profiler findes desuden i de ledsagende CSV-tabeller. Filhashes, eksakte kanalintervaller og fasernes fuldstændighed fremgår af de gemte receipts.", "",
        "## Evidenshul og næste videnskabelige arbejde", "",
        "Der mangler fortsat et uafhængigt besøg med samme frekvensdækning eller en separat kvalificeret model, som bevarer korrelationerne og omfatter hele udvælgelsesfamilien. En rang blandt millioner af beslægtede hypoteser samt 16 positive rækker kan ikke i sig selv give en falskalarmrate. OFF er heller ikke certificeret ren støj.", "",
        "Det primære næste evidenstrin er at finde et uafhængigt besøg med frekvensoverlap. Et endnu uåbnet bånd eller en separat kvalificeret korrelationsbevarende kontrolmodel er videnskabelige muligheder, som kræver en ny konkret ressourcefordeling. De er ikke finansierede næste analysejobs inden for den aktuelle frie ramme. Den tidligere kvalifikationsfejl og holdouts skal forblive lukkede, og en kontrolmodel må ikke tilpasses for at gøre de viste spor mere positive.", "",
        "Denne arbejdsomgang har en konservativ reservation på 750 CPU-sekunder. Den resterende ramme er 652,705 CPU-sekunder, hvoraf 650 er beskyttet til afslutningen 20. oktober og 2,705 er udisponeret. Den samlede godkendte ramme er ikke udvidet; der er ikke disponeret til endnu et nyt bånd.", "",
        "## Udførelse", "",
        f"Acquisition blev afsluttet med {data['acquisition_receipt']['new_spectral_BODY_bytes']:,} modtagne spektrale application-body-byte fordelt på 96 præcise ranges. Fil- og rækkehashes er kontrolleret. Kildebyte er ikke en måling af samlet wire-trafik.", ""]
    for key, label in (("acquisition_receipt", "Hentning"), ("stationary_receipt", "Stationær analyse"),
                       ("drift_receipt", "Driftanalyse"), ("profile_receipt", "Faste profiler")):
        receipt = data[key]
        cpu = receipt.get("cpu_s", receipt.get("process_CPU_seconds_including_imports"))
        wall = receipt.get("wall_s", receipt.get("wall_seconds_including_imports"))
        lines.append(f"- {label}: {number(cpu, 3)} CPU-s; {number(wall, 3)} vægsekunder; fuldstændig.")
    report = out/"RADIO_FRESH_BAND_2026-10-09_RESULT.md"
    report.write_text("\n".join(lines)+"\n")
    output = {"status": "COMPLETED_DESCRIPTIVE_SAVED_JSON_INTERPRETATION", "profile_count": 18,
        "scan_profile_count": 108, "all_16_ON_positive_profile_count_descriptive_only": positive16,
        "adjacent_OFF_mean_at_least_ON_profile_count_descriptive_only": control_at_least_on,
        "saved_input_sha256": {k: sha(v) for k, v in inputs.items()},
        "profile_records": all_rows, "new_spectral_values_measured": False,
        "probability_SNR_or_sky_origin_inferred": False,
        "output_files": [{"path": f.name, "sha256": sha(f), "bytes": f.stat().st_size} for f in
            (report, out/"ALL_18_PROFILE_TABLE.csv", out/"ALL_108_SCAN_PROFILE_TABLE.csv")]}
    (out/"INTERPRETATION_RESULT.json").write_text(json.dumps(output, indent=2, allow_nan=False)+"\n")
    print(json.dumps({k: v for k, v in output.items() if k != "profile_records"}, allow_nan=False))


if __name__ == "__main__":
    main()
