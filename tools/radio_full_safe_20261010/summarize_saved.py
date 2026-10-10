#!/usr/bin/env python3
"""Summarize pinned saved JSON after root GO; never open HDF5 or NPZ values.

This reader preserves batch-local ranks and identities (batch_id, track_id).
It checks metadata consistency, does not rerun a detector or evaluate an OFF
veto, and does not replace independent raw-output QA. Importing reads no files.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import time

SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
SHORT = dict(zip(SCANS, ("ON1", "OFF1", "ON2", "OFF2", "ON3", "OFF3")))
ADJACENT = {
    "epoch1_on": (None, "epoch1_off"),
    "epoch2_on": ("epoch1_off", "epoch2_off"),
    "epoch3_on": ("epoch2_off", "epoch3_off"),
}
ACTIVATION = "tools/radio_full_safe_20261010/ACTIVATION_SCOPE.json"
SCOPE = "tools/radio_full_safe_20261010/scope.json"
SOURCE_CELL_QA = "results/radio_full_safe_20261010/review/SOURCE_CELL_QA_RECEIPT.json"
STAGE = "results/radio_full_safe_20261010"
COMPLETE_STATUS = "COMPLETE_107_FULL_SAFE_CORE_BATCH_EXPLORATORY_ONLY"
SELECTION_SHA = "81bdd9b01d32c5d1fffd54df30d036a2aab29035c8d9e29d21b564e166d67120"
FROZEN_CODE_COMMIT = "73168f5f1b2d9d154b10eb381c17b8185c18a880"
ROOT = Path(__file__).resolve().parents[2]
CPU_CAP, WALL_CAP, MEMORY_CAP = 40, 1800, 4 * 1024**3


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def dump_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(path)


def integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Expected integer: " + label)
    return value


def finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Expected finite scalar: " + label)
    return value


class PinnedJSON:
    def __init__(self, root, pins_path):
        self.root = root.resolve()
        self.pins_path = pins_path.resolve()
        raw = self.pins_path.read_bytes()
        self.pins_sha = sha256(raw)
        self.pins = json.loads(raw)
        self.opened = {}
        if not isinstance(self.pins, dict) or not self.pins:
            raise ValueError("A nonempty root-relative JSON-path to SHA256 map is required")
        for name, expected in self.pins.items():
            relative = Path(name)
            resolved = (self.root / relative).resolve()
            if (relative.is_absolute() or ".." in relative.parts or relative.suffix != ".json"
                    or not resolved.is_relative_to(self.root) or not isinstance(expected, str)
                    or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected)):
                raise ValueError("Invalid pinned JSON path or SHA256: " + name)

    def present(self, name):
        return name in self.pins

    def load(self, name):
        if name not in self.pins:
            raise ValueError("Missing explicit JSON input pin: " + name)
        raw = (self.root / name).read_bytes()
        actual = sha256(raw)
        if actual != self.pins[name]:
            raise ValueError("Pinned JSON differs: " + name)
        self.opened[name] = {"sha256": actual, "bytes": len(raw)}
        return json.loads(raw)

    def unchanged(self):
        if sha256(self.pins_path.read_bytes()) != self.pins_sha:
            raise ValueError("Input pins changed during summarization")
        for name, entry in self.opened.items():
            if sha256((self.root / name).read_bytes()) != entry["sha256"]:
                raise ValueError("Pinned input changed during summarization: " + name)


def geometry(activation, scope):
    selection = activation["immutable_metadata_selection"]
    canonical = (json.dumps(selection, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if (sha256(canonical) != SELECTION_SHA
            or activation["metadata_selection_canonical_SHA256"] != SELECTION_SHA
            or scope["metadata_selection_canonical_SHA256"] != SELECTION_SHA
            or scope["immutable_metadata_selection"] != selection):
        raise ValueError("Immutable prospective selection changed")
    if (selection["core_channel_count"] != 4096
            or selection["source_chunk_channel_count"] != 1048576
            or selection["safe_q_interval_inclusive"] != [1, 254]):
        raise ValueError("Unexpected native geometry")
    groups = [selection["prior_q"], selection["previous_gap_q"], *selection["batch_q"]]
    if [len(g) for g in groups] != [32, 8, 107, 107]:
        raise ValueError("Unexpected old/new core counts")
    for group in groups:
        if group != sorted(set(group)) or any(integer(q, "q") < 1 or q > 254 for q in group):
            raise ValueError("Core lists must be unique, safe and ascending")
    sets = [set(g) for g in groups]
    if (any(a & b for i, a in enumerate(sets) for b in sets[i+1:])
            or set.union(*sets) != set(range(1, 255))):
        raise ValueError("Old and new cores do not partition the safe interior")
    if (scope["expected_scan_tiles_per_batch"] != 321
            or scope["valid_hypotheses_per_carrier"] != 1526
            or scope["widths_channels"] != [1, 3]
            or scope["drift_grid"] != {"first_hz_s": -4, "last_hz_s": 4, "count": 763}):
        raise ValueError("Frozen search grid changed")
    return selection, set(groups[0]) | set(groups[1])


def checkpoint_summary(data, batch, qs, source_first):
    if (data["batch_id"] != batch or data["fixed_batch_q"] != qs
            or data["expected_scan_tiles"] != 321):
        raise ValueError("Checkpoint batch contract changed")
    entries = data["completed_receipts"]
    if data["completed_scan_tiles"] != len(entries):
        raise ValueError("Checkpoint count differs from completed receipts")
    completed = {scan: set() for scan in ONS}
    for entry in entries:
        scan, q = entry["scan_id"], integer(entry["reference_core_q"], "q")
        if scan not in ONS or q not in qs or q in completed[scan]:
            raise ValueError("Unexpected or duplicate completed scan/core")
        first = source_first + q * 4096
        if (entry["tile_index"] != qs.index(q)
                or entry["core_start_relative_channel"] != q * 4096
                or entry["reference_channel_interval_half_open"] != [first, first + 4096]
                or entry["searched_carriers"] != 4096
                or entry["valid_hypotheses_per_carrier"] != 1526):
            raise ValueError("Completed scan/core has an invalid carrier contract")
        completed[scan].add(q)
    all_tiles = all(completed[s] == set(qs) for s in ONS)
    if data["complete"] is not all_tiles:
        raise ValueError("Checkpoint completeness flag disagrees with actual entries")
    if data["completed_q_by_ON"] != {s: sorted(completed[s]) for s in ONS}:
        raise ValueError("Checkpoint ON-core summary differs")
    return {s: sorted(completed[s]) for s in ONS}, all_tiles


def top20_check(top20, batch, qs, source_first):
    if set(top20) != set(ONS):
        raise ValueError("Expected all three ON top20 lists")
    expected = []
    for scan in ONS:
        tracks = top20[scan]
        if len(tracks) != 20:
            raise ValueError("Incomplete saved top20 list")
        for rank, track in enumerate(tracks, 1):
            if (track["batch_id"] != batch or track["originating_scan"] != scan
                    or track["originating_role"] != "ON" or track["display_rank"] != rank
                    or track["reference_core_q"] not in qs or track["width_channels"] not in (1, 3)):
                raise ValueError("Saved batch-local rank geometry changed")
            channel = integer(track["source_reference_channel"], "source_reference_channel")
            q = integer(track["reference_core_q"], "reference_core_q")
            first = source_first + q * 4096
            if not first <= channel < first + 4096:
                raise ValueError("Selected reference channel lies outside its declared core")
            frequency = finite(track["reference_frequency_hz"], "frequency")
            expected_frequency = 1876464843.75 - 2.835503418452676 * channel
            if not math.isclose(frequency, expected_frequency, rel_tol=0, abs_tol=1e-6):
                raise ValueError("Selected scalar frequency differs from the frozen native grid")
            drift = finite(track["drift_hz_s"], "drift")
            finite(track["maximum_robust_box_track_score"], "score")
            if drift < -4 or drift > 4:
                raise ValueError("Saved drift lies outside frozen grid")
        expected.extend(tracks[:3])
    return expected


def profile_summaries(records, expected, batch, batch_complete):
    if len(records) > 9 or [r["selected_track"] for r in records] != expected[:len(records)]:
        raise ValueError("Profiles differ from fixed batch-local top3 ordering")
    summaries = []
    for record in records:
        track = record["selected_track"]
        if (record["fixed_frequency_shift_channels"] != 0
                or record["classification"] != "UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE"):
            raise ValueError("Fixed-profile classification or shift changed")
        scans = record["scan_profiles"]
        if [p["scan_id"] for p in scans] != list(SCANS):
            raise ValueError("Missing or reordered six-scan profile")
        measures = {}
        for scan in scans:
            for field in ("mean_center_minus_flank", "median_center_minus_flank",
                          "first_eight_mean_center_minus_flank", "last_eight_mean_center_minus_flank"):
                finite(scan[field], field)
            count = integer(scan["positive_rows"], "positive_rows")
            if count < 0 or count > 16:
                raise ValueError("Invalid positive-row count")
            for field in ("all_16_center_minus_flank_rows", "all_16_raw_width_mean_power",
                          "frozen_source_channel_centers"):
                if len(scan[field]) != 16:
                    raise ValueError("Incomplete sixteen-row profile field")
                for value in scan[field]:
                    finite(value, field)
            measures[scan["scan_id"]] = {k: v for k, v in scan.items() if k != "scan_id"}
        origin = track["originating_scan"]
        before, after = ADJACENT[origin]
        summaries.append({
            "identity": [batch, track["track_id"]],
            "batch_id": batch,
            "track_id": track["track_id"],
            "originating_scan": origin,
            "display_rank_within_batch_and_ON": track["display_rank"],
            "source_reference_channel": track["source_reference_channel"],
            "reference_core_q": track["reference_core_q"],
            "reference_frequency_hz": track["reference_frequency_hz"],
            "reference_seconds_from_anchor": track["reference_seconds_from_anchor"],
            "drift_hz_s": track["drift_hz_s"],
            "width_channels": track["width_channels"],
            "saved_robust_score": track["maximum_robust_box_track_score"],
            "origin_ON": measures[origin],
            "adjacent_preceding_OFF_scan": before,
            "adjacent_preceding_OFF": measures[before] if before else None,
            "adjacent_following_OFF_scan": after,
            "adjacent_following_OFF": measures[after],
            "all_six_fixed_scan_measures": measures,
            "batch_execution_complete": batch_complete,
            "classification": "UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE",
            "patch_provenance": record["patch"],
        })
    return summaries


def load_batch(reader, scope, batch, selection):
    prefix = f"{STAGE}/batch_{batch:02d}/measurement/"
    qs = selection["batch_q"][batch-1]
    checkpoint_path = prefix + "DRIFT_CHECKPOINT.json"
    result = {"batch_id": batch, "fixed_batch_q": qs,
              "status": "NO_PINNED_RESULT_AVAILABLE", "execution_complete": False,
              "checkpoint_all_tiles_present": False, "completed_scan_tiles": 0,
              "completed_q_by_ON": {s: [] for s in ONS}, "profile_count": 0,
              "QA_status": "NOT_PROVIDED", "profiles": []}
    if not reader.present(checkpoint_path):
        failure_path = prefix + "FAILURE_RECEIPT.json"
        if reader.present(failure_path):
            failure = reader.load(failure_path)
            if failure["batch_id"] != batch or failure["fixed_batch_q"] != qs:
                raise ValueError("Early failure receipt batch identity changed")
            result.update(status=failure["status"], failure_receipt=failure)
        return result
    checkpoint = reader.load(checkpoint_path)
    done, all_tiles = checkpoint_summary(checkpoint, batch, qs,
                                        selection["source_channel_interval_half_open"][0])
    result.update(completed_q_by_ON=done, completed_scan_tiles=checkpoint["completed_scan_tiles"],
                  checkpoint_all_tiles_present=all_tiles, status="PARTIAL_PINNED_CHECKPOINT")
    execution_path, failure_path = prefix+"EXECUTION_RECEIPT.json", prefix+"FAILURE_RECEIPT.json"
    execution = reader.load(execution_path) if reader.present(execution_path) else None
    failure = reader.load(failure_path) if reader.present(failure_path) else None
    if failure is not None:
        if failure["batch_id"] != batch or failure["fixed_batch_q"] != qs:
            raise ValueError("Failure receipt batch identity changed")
        result["failure_receipt"] = failure
        result["status"] = failure["status"]
    if execution is not None:
        if (execution["batch_id"] != batch or execution["fixed_batch_q"] != qs
                or execution["scope_sha256"] != reader.pins[SCOPE]
                or execution["metadata_selection_canonical_SHA256"] != SELECTION_SHA
                or execution["status"] != COMPLETE_STATUS):
            raise ValueError("Execution receipt differs from the common frozen scope")
        if (execution["one_historical_visit"] is not True
                or execution["OFF_veto_applied"] is not False
                or execution["qualified_sky_pilot"] is not False
                or execution["old_A_B_failure_statuses_changed"] is not False
                or execution["old_holdouts_reopened"] is not False
                or execution["calibrated_SNR_FAP_flux_EIRP_or_sensitivity"] is not False
                or execution["new_telescope_HTTP_requests_during_analysis"] != 0
                or execution["new_telescope_BODY_bytes_during_analysis"] != 0):
            raise ValueError("Scientific or acquisition contract changed")
        resources = {k: finite(execution[k], k) for k in
                     ("process_CPU_seconds_including_imports", "wall_seconds_including_imports", "peak_RSS_bytes")}
        if (resources["process_CPU_seconds_including_imports"] > 1200
                or resources["wall_seconds_including_imports"] > 1800
                or resources["peak_RSS_bytes"] > 4*1024**3
                or execution["search_summary"]["completed_scan_tiles"] != 321
                or execution["fixed_profile_summary"]["profile_count"] != 9 or not all_tiles):
            raise ValueError("COMPLETE receipt does not satisfy resource/completeness caps")
        result["execution_resources"] = resources
        result["execution_complete"] = failure is None
        result["status"] = execution["status"] if failure is None else failure["status"]
    top_path, profile_path = prefix+"DRIFT_TOP20.json", prefix+"FIXED_TOP3_PROFILES.json"
    if reader.present(profile_path):
        if not reader.present(top_path) or not all_tiles:
            raise ValueError("Saved profiles need their pinned top20 and complete search checkpoint")
        top20 = reader.load(top_path)
        expected = top20_check(top20, batch, qs, selection["source_channel_interval_half_open"][0])
        if execution is not None and execution["fixed_profile_summary"]["source_top20_sha256"] != reader.pins[top_path]:
            raise ValueError("Fixed-profile top20 provenance differs")
        result["profiles"] = profile_summaries(reader.load(profile_path), expected, batch, result["execution_complete"])
        result["profile_count"] = len(result["profiles"])
    if result["execution_complete"] and result["profile_count"] != 9:
        raise ValueError("Complete batch requires all nine pinned profiles")
    qa_path = prefix + "QA_RECEIPT.json"
    if reader.present(qa_path):
        qa = reader.load(qa_path)
        result["QA_status"] = qa.get("status", "STATUS_NOT_PRESENT")
        result["QA_receipt_sha256"] = reader.pins[qa_path]
    return result


def number(value, digits=6):
    if value is None:
        return "—"
    return f"{value:.{digits}f}".replace(".", ",")


def joint_source_QA(reader, scope, profiles):
    if not reader.present(SOURCE_CELL_QA):
        return {"status": "NOT_PROVIDED"}
    qa = reader.load(SOURCE_CELL_QA)
    if (qa["status"] != "PASS_18_FIXED_RAW_PATCHES_AUTHENTICATED_BITWISE_TO_SOURCE"
            or qa["public_scope_sha256"] != reader.pins[SCOPE]
            or qa["public_wrapper_sha256"] != scope["script_sha256"]
            or qa["freeze_commit"] != FROZEN_CODE_COMMIT):
        raise ValueError("Joint source-cell QA differs from frozen execution")
    expected_counts = {"compact_files": 6, "decoded_rows": 96, "patches": 18,
                       "scan_profiles": 108, "time_rows": 1728, "raw_cells_bitwise_checked": 222912}
    if qa["counts"] != expected_counts or len(profiles) != 18:
        raise ValueError("Joint source-cell QA count differs from all eighteen profiles")
    checks = {(c["batch_id"], c["track_id"]): c for c in qa["patch_checks"]}
    if len(checks) != 18 or set(checks) != {tuple(p["identity"]) for p in profiles}:
        raise ValueError("Joint source-cell QA identities differ from saved profiles")
    for profile in profiles:
        check = checks[tuple(profile["identity"])]
        prefix = f'{STAGE}/batch_{profile["batch_id"]:02d}/measurement/'
        if (check["bitwise_identical"] is not True or check["raw_cells"] != 12384
                or check["patch_sha256"] != profile["patch_provenance"]["sha256"]
                or check["raw_cell_bytes_SHA256"] != check["independent_source_cell_bytes_SHA256"]
                or check["source_execution_receipt_sha256"] != reader.pins[prefix+"EXECUTION_RECEIPT.json"]
                or check["source_profiles_JSON_sha256"] != reader.pins[prefix+"FIXED_TOP3_PROFILES.json"]):
            raise ValueError("Joint source-cell QA patch provenance differs")
    return {"status": qa["status"], "receipt_sha256": reader.pins[SOURCE_CELL_QA],
            "counts": qa["counts"], "audit_script_sha256": qa["audit_script_sha256"],
            "original_full_source_file_MD5_verified": False}


def render_report(summary):
    complete = summary["both_batch_executions_complete"]
    lead = ("Begge fastlåste kørsler er gennemført én gang." if complete else
            "Dette er en opgørelse af de gemte delresultater; begge kørsler er ikke dokumenteret komplette.")
    cov = summary["coverage"]
    lines = ["# SETI: driftsøgning i det sikre gemte frekvensudsnit", "",
             "**10. oktober 2026.** " + lead,
             f'Der er gemt **{summary["completed_scan_tiles"]} af 642 scanningsfelter** og '
             f'**{summary["profile_count"]} af 18 faste top-3-profiler**. '
             "Grupperne har hver deres ranglister; profilidentiteten er kombinationen af gruppe og track-ID.", "",
             "Alle seks scanninger stammer fra ét besøg den 17. marts 2016. Dette er eksplorativ analyse "
             "af allerede eksponerede data med 763 lineære drifthastigheder fra −4 til +4 Hz/s og bredde 1 og 3. "
             "A/B er fortsat FAIL_CLOSED, den kvalificerede himmelpilot er blokeret, og gamle holdouts er lukkede.", "",
             "## Dækning og kontrol", "",
             "| Gruppe | Gemte felter / 321 | Faste profiler / 9 | Kørselsstatus | Uafhængig QA |", "| --- | ---: | ---: | --- | --- |"]
    for batch in summary["batches"]:
        lines.append(f'| {batch["batch_id"]} | {batch["completed_scan_tiles"]} | {batch["profile_count"]} | '
                     f'{batch["status"]} | {batch["QA_status"]} |')
    source_QA = summary["joint_source_cell_QA"]
    if source_QA["status"].startswith("PASS"):
        lines += ["", "En særskilt kildecellekontrol matcher **alle 222.912 råceller i 18 profiludklip "
                  "byte for byte** mod de seks hashkontrollerede kompakte HDF5-kilder. Kontrollen "
                  "omfatter 96 afkodede kilderækker, 108 scanningsprofiler og 1.728 profilrækker. "
                  "Den bekræfter udklippenes råcelleidentitet og placering. De originale større "
                  "kilders fulde fil-MD5 er fortsat ikke verificeret."]
    lines += ["", "| ON | Tidligere + nye gemte referencekanaler | Andel af udsnittet |", "| --- | ---: | ---: |"]
    for scan in ONS:
        item = cov["by_ON"][scan]
        lines.append(f'| {SHORT[scan]} | {item["old_plus_completed_new_reference_channels"]:,}'.replace(",", ".")
                     + f' | {number(100*item["old_plus_completed_new_fraction"], 5)} % |')
    lines += ["",
              (f'De nye checkpoints indeholder **{summary["new_ON_carrier_origin_entries"]:,} '
               f'ON-kanal/origin-poster** og **{summary["new_hypothesis_entries"]:,} '
               "gyldige grid-/breddeposter ifølge feltkvitteringerne.").replace(",", "."),
              "Disse tællinger er beregningsdækning, ikke uafhængige statistiske forsøg.",
              "Ved to komplette kørsler er den samlede referencekanaldækning **254 af 256 felter, 99,21875 %**, "
              "inklusive de tidligere 40 felter. Kun dette grid og disse to bredder er omfattet. "
              "Randfelterne [0,4096) og [1044480,1048576) er usøgte; læse- og sporhaloer kan overlappe.",
              "Endelig integritetskontrol fremgår af QA-kvitteringerne; denne sammenfatning genkører ikke detektoren "
              "og åbner hverken rå HDF5 eller NPZ.", "", "## Hvad de højeste profiler viser", "",
              "De 18 profiler er udvalgte spor og udgør ikke 18 uafhængige fysiske signaler. "
              "Deres referencefrekvenser samler sig i to snævre områder:", "",
              "| Gruppe | Udvalgte spor | Native q | Referencefrekvensinterval, MHz |",
              "| --- | ---: | --- | ---: |"]
    for batch in summary["batches"]:
        selected = batch["profiles"]
        if selected:
            frequencies = [p["reference_frequency_hz"]/1e6 for p in selected]
            cores = ", ".join(str(q) for q in sorted({p["reference_core_q"] for p in selected}))
            lines.append(f'| {batch["batch_id"]} | {len(selected)} | {cores} | '
                         f'{number(min(frequencies))}–{number(max(frequencies))} |')
    if complete:
        first = summary["batches"][0]["profiles"]
        rank1 = [p for p in first if p["display_rank_within_batch_and_ON"] == 1]
        if (len(rank1) == 3 and all(p["drift_hz_s"] == 0 for p in rank1)
                and len({(p["source_reference_channel"], p["width_channels"]) for p in rank1}) == 1):
            means = [rank1[0]["all_six_fixed_scan_measures"][s]["mean_center_minus_flank"] for s in SCANS]
            lines += ["", f'Den højeste profil i alle tre ON-scanninger i gruppe 1 bruger samme '
                      f'stationære reference ved **{number(rank1[0]["reference_frequency_hz"]/1e6)} MHz**. '
                      f'Dens gemte middelresidualer er **{number(min(means))}–{number(max(means))}** '
                      "på tværs af alle seks scanninger. Den stærke stationære struktur er dermed "
                      "til stede i både alle ON- og alle OFF-scanninger. Det fastslår ikke dens oprindelse."]
        lines += ["", "Gruppe 2 indeholder også markant struktur på flere af de faste OFF-forløb; "
                  "de præcise middelværdier for hver profil står nedenfor. Nærliggende profiler og "
                  "gentagne udvælgelser af samme struktur er afhængige beskrivelser."]
    lines += ["", "## De gemte faste profiler", "",
              "Tallene nedenfor er gemt normaliseret centereffekt minus rækkens median af bevægelige "
              "flankkanaler med absolut offset større end tre inden for ±64. De er ikke kalibreret SNR. "
              "Alle OFF-værdier følger den oprindeligt valgte, uændrede driftmodel ved de faktiske scanningstider. "
              "ON2 og ON3 vises med både den forudgående og efterfølgende OFF; ON1 har kun den efterfølgende "
              "OFF i denne seks-scans sekvens. Alle seks scanningsforløb bevares i sammenfatningsfilen.", "",
              "| Gruppe | ON/rang | Frekvens, MHz | Drift, Hz/s | Bredde | ON-middel | OFF før | OFF efter |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for item in summary["profiles"]:
        origin = item["originating_scan"]
        before = item["adjacent_preceding_OFF"]
        after = item["adjacent_following_OFF"]
        lines.append(f'| {item["batch_id"]} | {SHORT[origin]}/{item["display_rank_within_batch_and_ON"]} | '
                     f'{number(item["reference_frequency_hz"]/1e6)} | {number(item["drift_hz_s"])} | '
                     f'{item["width_channels"]} | {number(item["origin_ON"]["mean_center_minus_flank"])} | '
                     f'{number(before["mean_center_minus_flank"] if before else None)} | '
                     f'{number(after["mean_center_minus_flank"])} |')
    if not summary["profiles"]:
        lines.append("| — | Ingen færdige, pinnede profiler | — | — | — | — | — | — |")
    lines += ["", "Profilerne er udvalgt efter ON-score inden for hver gruppe. De forbliver uafklarede. "
              "Positive rækker og halvdele er efter udvælgelse; en lille værdi ved et præcist OFF-spor "
              "fastslår ikke fravær af en nærliggende OFF-feature. Der er ingen optimeret OFF-forskydning eller "
              "kvalificeret OFF-veto og ingen oprindelsesklassifikation.", "", "## Målt kørsel", "",
              "| Gruppe | CPU, sekunder | Vægtid, sekunder | Maksimal RSS, bytes |",
              "| --- | ---: | ---: | ---: |"]
    for batch in summary["batches"]:
        r = batch.get("execution_resources", batch.get("failure_receipt", {}))
        lines.append(f'| {batch["batch_id"]} | {number(r.get("process_CPU_seconds_including_imports"), 3)} | '
                     f'{number(r.get("wall_seconds_including_imports"), 3)} | {r.get("peak_RSS_bytes", "—")} |')
    lines += ["", "Hver numerisk kørsel har højst 1.200 CPU-sekunder, 1.800 sekunders vægtid og 4 GiB RAM. "
              "Fasens 3.600 CPU-sekunder er arbejdsplanlægning, ikke en abonnementsbalance eller ny global "
              "stopgrænse. Historiske reservationer bevares uden tilbageførsel. Beløbet er 0 kr., og fasen "
              "har 0 nye teleskoprequests og 0 nye teleskopbytes. Arbejdsplads- og kumulative byteregnskaber "
              "føres særskilt af projektets ressourceledger.", "", "## Begrænsninger og reproduktion", "",
              "Kildeværdierne var allerede åbnet. Den prospektive fastlåsning vedrører de nye driftudfald; "
              "arbejdet er hverken blind validering eller en ny uafhængig besøgsobservation. Der er ikke "
              "beregnet kalibreret falskalarmrate, flux, EIRP eller følsomhed, og der påstås hverken generelt "
              "nulresultat eller uafhængighed mellem hypoteser. Ingen barycentrisk korrektion, ikke-lineære "
              "spor, andre bredder eller injektionskalibrering er tilføjet.",
              f'Kode og fælles kørselscope blev fastlåst offentligt i commit `{summary["public_code_freeze_commit"]}` '
              "og læst eksakt tilbage før nogen af de to kørsler. "
              f'Scope-SHA256 er `{summary["common_execution_scope_sha256"]}`. '
              "De kompakte inputfiler og 96 afkodede rækker er hashbundne; de originale større "
              "kilders fulde fil-MD5 er ikke verificeret. Det begrænser filproveniensen og ændrer ikke "
              "de deklarerede lokale checksums.",
              "Eksakte scopes, begge checkpoints, top-20-lister, profiler og kørsels-/QA-kvitteringer følger "
              "resultatpakken. Sammenfatningskvitteringen angiver hash og størrelse for hvert faktisk læst "
              "JSON-input. Publiceringscommit og pakkens endelige checksum tilføjes i projektstatus efter "
              "gemning og verificeret offentliggørelse.", ""]
    return "\n".join(lines)


def write_csv(path, profiles):
    columns = ["batch_id", "track_id", "originating_scan", "display_rank", "source_reference_channel",
               "reference_frequency_hz", "reference_seconds_from_anchor", "drift_hz_s", "width_channels",
               "saved_robust_score", *[s+"_mean_center_minus_flank" for s in SCANS],
               "origin_positive_rows", "origin_first_eight_mean", "origin_last_eight_mean",
               "batch_execution_complete", "classification"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for p in profiles:
            row = {key: p[key] for key in columns if key in p}
            row.update(display_rank=p["display_rank_within_batch_and_ON"],
                       origin_positive_rows=p["origin_ON"]["positive_rows"],
                       origin_first_eight_mean=p["origin_ON"]["first_eight_mean_center_minus_flank"],
                       origin_last_eight_mean=p["origin_ON"]["last_eight_mean_center_minus_flank"])
            row.update({s+"_mean_center_minus_flank": p["all_six_fixed_scan_measures"][s]["mean_center_minus_flank"] for s in SCANS})
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--pins", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report-path", default=str(ROOT/"RADIO_FULL_SAFE_REPORT_2026-10-10.md"))
    parser.add_argument("--mode", choices=("COMPLETE", "PARTIAL"), required=True)
    parser.add_argument("--root-authorized-summary-read", action="store_true")
    args = parser.parse_args()
    if not args.root_authorized_summary_read:
        raise SystemExit("Explicit root GO is required before opening any new numerical output")
    started = time.monotonic()
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    def timeout(signum, frame):
        raise TimeoutError("Saved summary CPU/wall deadline exceeded")
    signal.signal(signal.SIGALRM, timeout)
    signal.signal(signal.SIGXCPU, timeout)
    signal.alarm(WALL_CAP)
    root = Path(args.root).resolve()
    out, report = Path(args.output_dir).resolve(), Path(args.report_path).resolve()
    if not out.is_relative_to(root) or not report.is_relative_to(root):
        raise ValueError("Summary artifacts must remain inside this project")
    reader = PinnedJSON(root, Path(args.pins))
    activation, scope = reader.load(ACTIVATION), reader.load(SCOPE)
    selection, old = geometry(activation, scope)
    batches = [load_batch(reader, scope, i, selection) for i in (1, 2)]
    complete = all(b["execution_complete"] for b in batches)
    if args.mode == "COMPLETE" and not complete:
        raise ValueError("COMPLETE summary requires both full, resource-valid execution receipts")
    profiles = [p for b in batches for p in b["profiles"]]
    identities = [tuple(p["identity"]) for p in profiles]
    if len(set(identities)) != len(identities) or (complete and len(profiles) != 18):
        raise ValueError("Combined batch/profile identities or count differ")
    source_cell_QA = joint_source_QA(reader, scope, profiles)
    by_on = {}
    for scan in ONS:
        done = set().union(*(set(b["completed_q_by_ON"][scan]) for b in batches))
        by_on[scan] = {"completed_new_q": sorted(done), "completed_new_core_count": len(done),
                      "completed_new_reference_channels": len(done)*4096,
                      "old_plus_completed_new_core_count": len(old)+len(done),
                      "old_plus_completed_new_reference_channels": (len(old)+len(done))*4096,
                      "old_plus_completed_new_fraction": (len(old)+len(done))/256}
    entries = sum(b["completed_scan_tiles"] for b in batches)*4096
    summary = {"schema": "SETI_PINNED_TWO_BATCH_SAVED_SUMMARY_V1",
               "status": "COMPLETE_BOTH_BATCHES_SAVED_SUMMARY" if complete else "PARTIAL_BATCH_SAVED_SUMMARY",
               "both_batch_executions_complete": complete,
               "batch_rankings_separate_no_global_reranking": True,
               "profile_identity_fields": ["batch_id", "track_id"],
               "completed_scan_tiles": sum(b["completed_scan_tiles"] for b in batches),
               "expected_scan_tiles": 642, "profile_count": len(profiles), "expected_profile_count": 18,
               "new_ON_carrier_origin_entries": entries,
               "new_hypothesis_entries": entries*1526,
               "expected_new_ON_carrier_origin_entries_if_complete": 2629632,
               "expected_new_hypothesis_entries_if_complete": 4012818432,
               "coverage": {"by_ON": by_on, "previous_core_count_per_ON": 40,
                            "native_chunk_core_count": 256,
                            "full_safe_reference_core_count_if_complete": 254,
                            "full_safe_reference_fraction_if_complete": 0.9921875,
                            "unsearched_edge_intervals_relative_half_open": [[0,4096],[1044480,1048576]],
                            "partial_counts_from_checkpoints_not_independent_NPZ_QA": True},
               "batches": batches, "profiles": profiles,
               "joint_source_cell_QA": source_cell_QA,
               "one_historical_visit": True, "visit_date": "2016-03-17",
               "source_values_previously_exposed": True, "blind_validation": False,
               "A_B": "FAIL_CLOSED_UNCHANGED", "qualified_sky_pilot": False,
               "old_holdouts_reopened": False, "OFF_veto": False,
               "calibrated_SNR_FAP_flux_EIRP_or_sensitivity": False,
               "origin_classification": False, "general_null_result_claim": False,
               "independent_trials_claim": False,
               "new_telescope_HTTP_requests": 0, "new_telescope_BODY_bytes": 0,
               "metadata_selection_canonical_SHA256": SELECTION_SHA,
               "public_code_freeze_commit": FROZEN_CODE_COMMIT,
               "common_execution_scope_sha256": reader.pins[SCOPE],
               "detector_wrapper_sha256": scope["script_sha256"],
               "source_manifest_sha256": scope["source_manifest_sha256"],
               "acquisition_summary_sha256": scope["acquisition_summary_sha256"],
               "original_full_source_file_MD5_verified": False}
    if complete and (summary["completed_scan_tiles"] != 642
                     or entries != 2629632 or entries*1526 != 4012818432
                     or any(x["old_plus_completed_new_core_count"] != 254 for x in by_on.values())):
        raise ValueError("Complete aggregate counts differ from immutable metadata geometry")
    reader.unchanged()
    out.mkdir(parents=True, exist_ok=False)
    dump_json(out/"FULL_SAFE_SUMMARY.json", summary)
    write_csv(out/"PROFILE_SUMMARY.csv", profiles)
    report.write_text(render_report(summary))
    reader.unchanged()
    resources = {"process_CPU_seconds_including_imports": time.process_time(),
                 "wall_seconds_including_imports": time.monotonic()-started,
                 "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    if (resources["process_CPU_seconds_including_imports"] > CPU_CAP
            or resources["wall_seconds_including_imports"] > WALL_CAP
            or resources["peak_RSS_bytes"] > MEMORY_CAP):
        raise TimeoutError("Measured saved-summary resources exceed caps")
    receipt = {"status": "PASS_PINNED_JSON_SUMMARIZATION_NOT_DETECTOR_OR_RAW_QA",
               "mode": args.mode, "script_sha256": sha256(Path(__file__).read_bytes()),
               "input_pins_sha256": reader.pins_sha, "opened_inputs": reader.opened,
               "output_hashes": {str(p.relative_to(root)): sha256(p.read_bytes())
                                  for p in (out/"FULL_SAFE_SUMMARY.json", out/"PROFILE_SUMMARY.csv", report)},
               "HDF5_or_NPZ_opened": False, "detector_rerun": False, "global_reranking": False,
               "classification_or_OFF_optimization": False,
               "root_GO_required": True, **resources}
    dump_json(out/"SUMMARY_EXECUTION_RECEIPT.json", receipt)
    signal.alarm(0)
    print(json.dumps({"status": receipt["status"], "complete": complete,
                      "completed_tiles": summary["completed_scan_tiles"], "profiles": len(profiles),
                      "hypothesis_entries": entries*1526, **resources}, allow_nan=False))


if __name__ == "__main__":
    main()
