#!/usr/bin/env python3
"""Descriptive exports of two QA-passed boundary families; no source or search reads."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import signal
import time

QA_SHA = "48153e180358319feb3906fc719eabc9f224200933aa69eccbe0e20cdb8f1b36"
SOURCE_QA_SHA = "21a8edaf91e9a60d3209d33e4620a5f93038aabfafd3910094bd25e0fd66318a"
BASE = "analysis/s2017_next_native/boundaries"
PAIRS = ("pair170_171", "pair171_172")
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
COUNT, FCH1, DF, TSAMP = 1048576, 2802832031.25, -2.7939677238464355, 18.253611008


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(items):
    d = {}
    for k, v in items:
        if k in d:
            raise ValueError("Duplicate JSON key: " + k)
        d[k] = v
    return d


def jload(raw):
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def write_json(path, value):
    with path.open("x") as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")


def write_csv(path, records):
    with path.open("x", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("wall cap")))
    signal.alarm(180)
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[key] = "1"
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    self_path = Path(__file__).resolve()
    self_sha = sha(self_path.read_bytes())
    pins = {}
    qa_path = BASE + "/results/review/QA_RECEIPT.json"
    qa_raw = (root / qa_path).read_bytes()
    assert sha(qa_raw) == QA_SHA
    qa = jload(qa_raw)
    assert qa["status"] == "PASS12_S2017_JOINED_MAPS18_FIXED_PROFILES192_JOINED_MEDIANS_AND222912_BITWISE_SOURCE_CELLS"
    assert qa["new_source_QA_receipt_sha256"] == SOURCE_QA_SHA
    assert not qa["qualified_SETI_detection"] and not qa["detector_or_score_rerun"]
    pins[qa_path] = {"sha256": QA_SHA, "bytes": len(qa_raw)}

    def read(rel):
        # Deliberately admit only metadata and completed boundary saved outputs.
        assert rel in qa["all_input_byte_pins"] and Path(rel).suffix in (".json", ".npz")
        assert "results/search/" not in rel and "results/acquire/" not in rel
        raw = (root / rel).read_bytes()
        expected = qa["all_input_byte_pins"][rel]
        assert {"sha256": sha(raw), "bytes": len(raw)} == expected
        pins[rel] = expected
        return raw

    def read_json(rel):
        return jload(read(rel))

    def read_npz(rel):
        raw = read(rel)
        with np.load(io.BytesIO(raw), allow_pickle=False) as h:
            assert len(h.files) == len(set(h.files))
            return {k: h[k].copy() for k in h.files}

    source_qa_path = "analysis/s2017_next_native/results/source_review/QA_RECEIPT.json"
    source_qa = read_json(source_qa_path)
    assert pins[source_qa_path]["sha256"] == SOURCE_QA_SHA
    out = root / BASE / "results/interpretation"
    out.mkdir()  # Create only; preserve any failed attempt rather than overwriting it.
    tracks, measures, rows, tops, maps, families = [], [], [], [], [], []
    plot_maps = {}

    def dist_summary(values):
        a = np.asarray(values)
        return {"count": int(a.size), "minimum": float(a.min()), "median": float(np.median(a)),
                "p90": float(np.quantile(a, .9)), "p95": float(np.quantile(a, .95)),
                "p99": float(np.quantile(a, .99)), "maximum": float(a.max())}

    for pair in PAIRS:
        left, right = map(int, pair[4:].split("_"))
        join = right * COUNT
        lo, hi = join - 4096, join + 4096
        folder = BASE + "/results/" + pair + "/measurement/"
        scope = read_json(BASE + "/scopes/" + pair + ".json")
        receipt = read_json(folder + "EXECUTION_RECEIPT.json")
        assert pins[folder + "EXECUTION_RECEIPT.json"]["sha256"] == qa["pair_execution_receipt_SHA256s"][pair]
        assert pins[BASE + "/scopes/" + pair + ".json"]["sha256"] == qa["scope_SHA256s"][pair]
        checkpoint = read_json(folder + "DRIFT_CHECKPOINT.json")
        top20 = read_json(folder + "DRIFT_TOP20.json")
        profiles = read_json(folder + "FIXED_TOP3_PROFILES.json")
        assert len(profiles) == 9 and set(top20) == set(ONS)
        family = {"pair_id": pair, "native_chunks": [left, right], "native_join_channel": join,
                  "native_join_frequency_hz": FCH1 + DF * join,
                  "reference_channel_interval_half_open": [lo, hi],
                  "reference_frequency_at_low_channel_hz": FCH1 + DF * lo,
                  "reference_frequency_at_last_channel_hz": FCH1 + DF * (hi - 1),
                  "covered_reference_bandwidth_hz": abs(DF) * 8192,
                  "reference_times_seconds_from_MJD_anchor": {s: top20[s][0]["reference_seconds_from_anchor"] for s in ONS},
                  "MJD_anchor": receipt["MJD_anchor"], "origin_groups": []}
        for entry in checkpoint["receipts"]:
            a = read_npz(folder + entry["path"])
            assert set(a) == {"frequency_hz_at_tref", "maximum_robust_box_track_score", "winning_drift_hz_s", "winning_width_channels", "valid_hypothesis_count", "source_reference_channels", "drift_grid_hz_s"}
            assert a["source_reference_channels"].size == 4096
            assert np.array_equal(a["frequency_hz_at_tref"], FCH1 + DF * a["source_reference_channels"])
            assert np.all(a["valid_hypothesis_count"] == 1570)
            c, score = a["source_reference_channels"], a["maximum_robust_box_track_score"]
            assert np.isfinite(score).all()
            maps.append({"pair_id": pair, "scan_id": entry["scan_id"], "tile_index": entry["tile_index"],
                         "reference_channel_interval_half_open": entry["reference_channel_interval_half_open"],
                         "score_distribution": dist_summary(score),
                         "winning_width1_count": int(np.count_nonzero(a["winning_width_channels"] == 1)),
                         "winning_width3_count": int(np.count_nonzero(a["winning_width_channels"] == 3)),
                         "winning_drift_at_grid_endpoint_count": int(np.count_nonzero(np.abs(a["winning_drift_hz_s"]) == 4))})
            plot_maps.setdefault((pair, entry["scan_id"]), []).append((c, score))
        for on in ONS:
            entries = top20[on]
            assert len(entries) == 20
            channels = np.sort([t["source_reference_channel"] for t in entries])
            gaps = np.diff(channels)
            clusters = []
            for c in channels:
                if not clusters or int(c) - clusters[-1][-1] > 64:
                    clusters.append([int(c)])
                else:
                    clusters[-1].append(int(c))
            histogram = np.histogram(channels, bins=np.arange(lo, hi + 1, 512))[0].tolist()
            family["origin_groups"].append({"originating_scan": on,
                "saved_top20_score_range": [entries[-1]["maximum_robust_box_track_score"], entries[0]["maximum_robust_box_track_score"]],
                "reference_channel_histogram_16_equal_512_channel_bins": histogram,
                "nearest_sorted_reference_gap_channels_min_median_max": [int(gaps.min()), float(np.median(gaps)), int(gaps.max())],
                "descriptive_64_channel_single_linkage_groups": clusters,
                "top20_count_by_tile": [sum(t["reference_core_tile"] == i for t in entries) for i in (0, 1)],
                "top20_reference_within_native_join_channels": {str(d): sum(abs(t["source_reference_channel"] - join) <= d for t in entries) for d in (64, 256, 512, 1024)},
                "top20_reference_within_250_channels_of_either_core_endpoint": sum(min(t["source_reference_channel"] - (lo if t["reference_core_tile"] == 0 else join), (join - 1 if t["reference_core_tile"] == 0 else hi - 1) - t["source_reference_channel"]) < 250 for t in entries)})
            for t in entries:
                tops.append({**t, "reference_offset_from_native_join_channels": t["source_reference_channel"] - join,
                             "reference_distance_to_native_join_channels": abs(t["source_reference_channel"] - join),
                             "reference_distance_to_outer_window_edge_channels": min(t["source_reference_channel"] - lo, hi - 1 - t["source_reference_channel"])})
        for item in profiles:
            t = item["selected_track"]
            assert t == top20[t["originating_scan"]][t["display_rank"] - 1]
            a = read_npz(folder + item["patch"]["path"])
            assert a["raw_power"].shape == (6, 16, 129) and tuple(a["scans"].tolist()) == SCANS
            assert float(a["df_hz"]) == DF and int(a["fixed_source_channel_shift"]) == 0
            assert float(a["reference_frequency_hz"]) == t["reference_frequency_hz"]
            assert float(a["drift_hz_s"]) == t["drift_hz_s"] and int(a["width_channels"]) == t["width_channels"]
            means = [s["mean_center_minus_flank"] for s in item["scan_profiles"]]
            origin_index = SCANS.index(t["originating_scan"])
            offs = means[1::2]
            other_ons = [means[i] for i in (0, 2, 4) if i != origin_index]
            centers = a["frozen_source_channel_centers"]
            tr = {**t, "reference_offset_from_native_join_channels": t["source_reference_channel"] - join,
                  "all_scan_frozen_center_channel_range": [int(centers.min()), int(centers.max())],
                  "minimum_frozen_center_distance_to_native_join_channels": int(np.abs(centers - join).min()),
                  "frozen_centers_on_both_sides_of_native_join": bool(centers.min() < join <= centers.max()),
                  "patch_rows_touching_native_join": int(np.count_nonzero((centers - 64 < join) & (centers + 64 >= join))),
                  "origin_mean_center_minus_flank": means[origin_index],
                  "largest_fixed_OFF_mean_center_minus_flank": max(offs),
                  "largest_other_ON_mean_center_minus_flank": max(other_ons),
                  "origin_minus_largest_fixed_OFF_mean": means[origin_index] - max(offs),
                  "origin_largest_of_six_fixed_means": means[origin_index] == max(means),
                  "classification": item["classification"], "qualified_claim": False,
                  "scan_profiles": []}
            for i, s in enumerate(item["scan_profiles"]):
                assert s["scan_id"] == SCANS[i]
                residual = a["center_minus_flank_each_row"][i]
                assert np.array_equal(residual, np.asarray(s["all_16_center_minus_flank_rows"]))
                assert float(residual.mean()) == s["mean_center_minus_flank"]
                record = {"pair_id": pair, "track_id": t["track_id"], "originating_scan": t["originating_scan"],
                          "display_rank": t["display_rank"], "reference_frequency_hz": t["reference_frequency_hz"],
                          "drift_hz_s": t["drift_hz_s"], "width_channels": t["width_channels"],
                          "scan_id": SCANS[i], "scan_role": SCANS[i].split("_")[1].upper(),
                          "is_selection_scan": i == origin_index,
                          **{k: s[k] for k in ("mean_center_minus_flank", "median_center_minus_flank", "positive_rows", "first_eight_mean_center_minus_flank", "last_eight_mean_center_minus_flank")},
                          "minimum_frozen_center_channel": int(centers[i].min()),
                          "maximum_frozen_center_channel": int(centers[i].max()),
                          "first_midpoint_seconds_from_anchor": float(a["times_seconds_from_reference"][i, 0] + t["reference_seconds_from_anchor"]),
                          "last_midpoint_seconds_from_anchor": float(a["times_seconds_from_reference"][i, -1] + t["reference_seconds_from_anchor"])}
                measures.append(record)
                tr["scan_profiles"].append({**s, "times_seconds_from_reference": a["times_seconds_from_reference"][i].tolist(),
                    "frozen_center_frequency_hz": (FCH1 + DF * centers[i]).tolist(),
                    "center_row_normalized_power": a["center_row_normalized_power"][i].tolist(),
                    "fixed_flank_median_row_normalized_power": a["fixed_flank_median_row_normalized_power"][i].tolist()})
                for j in range(16):
                    rows.append({"pair_id": pair, "track_id": t["track_id"], "scan_id": SCANS[i], "time_row": j,
                        "time_seconds_from_reference": float(a["times_seconds_from_reference"][i, j]),
                        "frozen_source_channel_center": int(centers[i, j]),
                        "frozen_center_frequency_hz": float(FCH1 + DF * centers[i, j]),
                        "center_minus_flank": float(residual[j]),
                        "center_row_normalized_power": float(a["center_row_normalized_power"][i, j]),
                        "fixed_flank_median_row_normalized_power": float(a["fixed_flank_median_row_normalized_power"][i, j]),
                        "saved_raw_width_mean_power": s["all_16_raw_width_mean_power"][j]})
            tracks.append(tr)
        families.append(family)

    assert (len(maps), len(tops), len(tracks), len(measures), len(rows)) == (12, 120, 18, 108, 1728)
    origin_measures = [m for m in measures if m["is_selection_scan"]]
    context_measures = [m for m in measures if not m["is_selection_scan"]]
    summary = {"selected_score_distribution": dist_summary([t["maximum_robust_box_track_score"] for t in tracks]),
               "origin_fixed_mean_distribution": dist_summary([m["mean_center_minus_flank"] for m in origin_measures]),
               "unselected_context_fixed_mean_distribution": dist_summary([m["mean_center_minus_flank"] for m in context_measures]),
               "origin_largest_of_six_fixed_means_count": sum(t["origin_largest_of_six_fixed_means"] for t in tracks),
               "origin_both_eight_row_halves_positive_count": sum(m["first_eight_mean_center_minus_flank"] > 0 and m["last_eight_mean_center_minus_flank"] > 0 for m in origin_measures),
               "origin_positive_rows_min_max": [min(m["positive_rows"] for m in origin_measures), max(m["positive_rows"] for m in origin_measures)],
               "frozen_tracks_with_centers_on_both_native_join_sides": sum(t["frozen_centers_on_both_sides_of_native_join"] for t in tracks),
               "frozen_patch_row_occurrences_touching_native_join": sum(t["patch_rows_touching_native_join"] for t in tracks)}
    limitations = [
        "All ranks and fixed top3 profiles were selected after searching the same 2017-04-28 visit; profiles are not blind or independent confirmation.",
        "The row-MAD standardized box-track ranking statistic is not calibrated SNR, a p-value, FAP, flux or EIRP.",
        "49152 saved maxima summarize77168640 correlated drift/width combinations; neither is a count of independent tests.",
        "ON/OFF values follow exactly the same frozen frequency/drift/width at actual scan times. OFF scores, nearby OFF maxima and vetoes were not calculated.",
        "Small values on these exact fixed OFF tracks do not establish absence of nearby OFF structure, origin, sensitivity or sky qualification.",
        "Fixed-profile normalization uses each full2097152-channel joined rawfloat32 row median; detector normalization/MAD uses each4096-channel core. The two quantities are different metrics.",
        "Spatial bins and64-channel linkage groups are descriptive choices; no clustering significance or instrumental-origin classification is inferred.",
        "ON reference frequencies refer to different first-integration midpoints; proximity between different ON reference channels is not evidence of one persistent physical track.",
        "The native join and q255/q256 split coincide but are administrative reference/normalization partitions, not discarded/missing channels. Median filtering uses halo data; these are not the crop edges.",
        "Native171 was already examined before adjacent native170/172 were chosen. Protected2016 holdouts and original failed states remain unchanged."
    ]
    report = {"schema": "SETI_S2017_TWO_JOINED_BOUNDARIES_DESCRIPTIVE_SAVED_OUTPUT_INTERPRETATION_V1",
              "status": "COMPLETE_DESCRIPTIVE_ONLY_QUALIFIED_CLAIM_FALSE",
              "qualified_claim": False, "qualified_SETI_detection": False,
              "independent_or_blind_confirmation": False, "source_H5_opened": False,
              "detector_or_score_rerun": False, "fits_or_fixed_track_optimization": False,
              "OFF_veto_or_calibrated_SNR_FAP": False, "new_HTTP_requests": 0,
              "interior_saved_values_read": False, "interpretation_script_sha256": self_sha,
              "empirical_boundary_QA": {"path": qa_path, "sha256": QA_SHA, "counts": qa["counts"]},
              "source_QA": {"path": source_qa_path, "sha256": SOURCE_QA_SHA},
              "acquisition_receipt_sha256": qa["new_acquisition_receipt_sha256"],
              "prior171_source_QA_receipt_sha256": qa["prior171_source_QA_receipt_sha256"],
              "execution_receipt_SHA256s": qa["pair_execution_receipt_SHA256s"],
              "scope_SHA256s": qa["scope_SHA256s"], "search_public_freeze_commit": qa["search_public_freeze_commit"],
              "QA_public_freeze_commit": qa["qa_public_freeze_commit"],
              "geometry": {"fch1_hz": FCH1, "df_hz": DF, "tsamp_s": TSAMP,
                  "drift_grid_hz_s": {"min": -4, "max": 4, "count": 785, "step": 8/784},
                  "widths_channels": [1, 3], "widths_hz": [abs(DF), 3*abs(DF)],
                  "profiles_rows_per_scan": 16, "flank_offsets": "abs(channel_offset)>3 within[-64,64]",
                  "fixed_channel_shift": 0},
              "summary": summary, "families": families, "map_summaries": maps,
              "top20_tracks": tops, "fixed_tracks": tracks, "limitations": limitations,
              "authenticated_read_input_byte_pins": pins}
    write_json(out / "BOUNDARY_INTERPRETATION.json", report)
    write_csv(out / "FIXED_SCAN_MEASURES.csv", measures)
    write_csv(out / "FIXED_TIME_ROWS.csv", rows)
    write_csv(out / "TOP20_REFERENCE_TRACKS.csv", tops)

    matrix = np.asarray([[s["mean_center_minus_flank"] for s in t["scan_profiles"]] for t in tracks])
    fig, ax = plt.subplots(figsize=(10.5, 8))
    v = float(np.abs(matrix).max())
    im = ax.imshow(matrix, cmap="RdBu_r", vmin=-v, vmax=v, aspect="auto")
    ax.set_xticks(range(6), SCANS, rotation=25, ha="right")
    ax.set_yticks(range(18), [t["pair_id"] + " " + t["originating_scan"] + " #" + str(t["display_rank"]) for t in tracks], fontsize=8)
    for i, t in enumerate(tracks):
        for j in range(6):
            ax.text(j, i, f"{matrix[i,j]:.3f}", ha="center", va="center", fontsize=7,
                    color="white" if abs(matrix[i,j]) > .7*v else "black")
        ax.add_patch(Rectangle((SCANS.index(t["originating_scan"])-.5, i-.5), 1, 1, fill=False, edgecolor="black", lw=1.5))
    ax.axhline(8.5, color="black", lw=1)
    ax.set_title("18 fixed tracks: six-scan mean center − fixed flank\nOutlined cells selected the track; same-visit postsearch context")
    fig.colorbar(im, ax=ax, label="Dimensionless joined-row-normalized residual")
    fig.tight_layout()
    fig.savefig(out / "FIXED_SIX_SCAN_CONTEXT.png", dpi=180)
    fig.savefig(out / "FIXED_SIX_SCAN_CONTEXT.pdf")
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(12, 7), sharey=True)
    for i, pair in enumerate(PAIRS):
        join = int(pair.split("_")[-1]) * COUNT
        for j, on in enumerate(ONS):
            ax = axes[i, j]
            for k, (c, score) in enumerate(plot_maps[(pair, on)]):
                ax.scatter(DF*(c-join)/1000, score, s=1, alpha=.35, color=("#497da4", "#a5a5a5")[k], rasterized=True)
            selected = [t for t in tops if t["pair_id"] == pair and t["originating_scan"] == on]
            ax.scatter([DF*(t["source_reference_channel"]-join)/1000 for t in selected],
                       [t["maximum_robust_box_track_score"] for t in selected], s=16, facecolors="none", edgecolors="#b43131", linewidths=.7, label="saved top20")
            ax.axvline(0, color="black", lw=.8)
            ax.set_title(pair + " / " + on)
            ax.set_xlabel("Reference frequency − native join (kHz)")
            ax.set_xlim(-11.5, 11.5)
            if j == 0:
                ax.set_ylabel("Saved maximum robust box-track score")
    axes[0, 0].legend(fontsize=8, loc="lower right")
    fig.suptitle("Saved boundary maxima at each ON's own reference midpoint; correlated ranking statistic")
    fig.tight_layout()
    fig.savefig(out / "SAVED_MAXIMA_REFERENCE_FREQUENCY.png", dpi=180)
    fig.savefig(out / "SAVED_MAXIMA_REFERENCE_FREQUENCY.pdf")
    plt.close(fig)

    Danish = ["# Beskrivende gennemgang af S2017-kanalgrænser", "",
        "Ingen kvalificeret SETI-detektion er etableret (`qualified_claim=false`). De to færdige grænsefamilier omfatter 12 gemte ON-kort, 120 top20-rækker og 18 faste profiler med 108 scanningmålinger. Alt kommer fra samme besøg den 28. april 2017; profilerne blev valgt efter søgningen på de samme ON-data.", "",
        f"De 18 valgte rangscores spænder fra {summary['selected_score_distribution']['minimum']:.6f} til {summary['selected_score_distribution']['maximum']:.6f}. Scoren er en robust, række-MAD-standardiseret sum langs en boksbane, divideret med kvadratroden af antal rækker gange kanalbredde. Den er ikke kalibreret SNR eller falskalarm-sandsynlighed. De 49.152 gemte carrier-maksima kommer fra 77.168.640 korrelerede drift/bredde-kombinationer.", "",
        f"Den faste middelværdi (centrum minus medianen af de faste flanker efter normalisering) er størst i udvælgelses-ON for {summary['origin_largest_of_six_fixed_means_count']}/18 profiler. Udvælgelses-ON har positive middelværdier i begge halvdele for {summary['origin_both_eight_row_halves_positive_count']}/18 profiler og {summary['origin_positive_rows_min_max'][0]}–{summary['origin_positive_rows_min_max'][1]} positive rækker ud af 16. Det er beskrivende egenskaber ved efterudvalgte spor, ikke uafhængig bekræftelse.", "",
        f"Udvælgelses-ON-middelværdierne er {summary['origin_fixed_mean_distribution']['minimum']:.6f}–{summary['origin_fixed_mean_distribution']['maximum']:.6f}; de øvrige 90 faste scanningmålinger er {summary['unselected_context_fixed_mean_distribution']['minimum']:.6f}–{summary['unselected_context_fixed_mean_distribution']['maximum']:.6f}. ON og OFF følger uændret referencefrekvens, drift og bredde ved de faktiske scanningtider. Små værdier på disse præcise OFF-baner kan ikke udelukke nærliggende OFF-struktur. Der er ikke beregnet OFF-veto eller OFF-søgescores.", "",
        "| Grænse | Frekvens ved native-skel (MHz) | Referencedækning (MHz, kanalcentre) | ON1/ON2/ON3 top20 på venstre/højre kerne |", "|---|---:|---:|---|" ]
    for f in families:
        counts = "; ".join(f"{g['top20_count_by_tile'][0]}/{g['top20_count_by_tile'][1]}" for g in f["origin_groups"])
        Danish.append(f"| {f['pair_id']} | {f['native_join_frequency_hz']/1e6:.9f} | {f['reference_frequency_at_last_channel_hz']/1e6:.9f}–{f['reference_frequency_at_low_channel_hz']/1e6:.9f} | {counts} |")
    Danish += ["", "Hver grænse dækker 8.192 referencekanaler (22.888,183594 Hz) fordelt på to 4.096-kanals normaliseringskerner. De gemte top20-rækker beskrives med 16 faste frekvensbins og nabogab samt 64-kanals grupper i JSON. Grupperne er deskriptive; der er ingen test af klyngebetydning eller klassifikation af instrumental oprindelse. ON-scanningernes referencefrekvenser gælder forskellige første integrationsmidtpunkter.", "",
        f"{summary['frozen_tracks_with_centers_on_both_native_join_sides']}/18 faste baner har gemte kanalcentre på begge sider af native-skellet gennem de seks scanninger; {summary['frozen_patch_row_occurrences_touching_native_join']} af 1.728 patch-rækker berører skellet med deres ±64-kanals vindue. Skellet er også grænsen mellem de to reference-/normaliseringskerner. Det er ikke kanten af det indlæste halo-udsnit eller et hul i data. Afstandene er geometri, ikke evidens for årsag.", "",
        "Profilværdier og rangscores har forskellige normaliseringer: profiler bruger hele den sammenføjede float32-rækkes median over 2.097.152 kanaler, mens detektoren bruger den enkelte 4.096-kanals kerne og række-MAD. Profilresidualerne har ingen fluxenhed. Driftgitteret er −4 til +4 Hz/s i 785 trin; bredder er 1 og 3 kanaler (2,793968 og 8,381903 Hz). Der er ikke udført fit, frekvensforskydning eller ny optimering.", "",
        "Alle præcise sporidentiteter, værdier, tidsrækker og input-byte-pins findes i JSON og CSV. Figuren `FIXED_SIX_SCAN_CONTEXT.png` viser alle 108 middelværdier; rammerne markerer den scanning, der udvalgte hvert spor. `SAVED_MAXIMA_REFERENCE_FREQUENCY.png` viser alle gemte carrier-maksima og de allerede gemte top20-punkter.", "",
        f"Provenance: faktisk grænse-QA SHA256 `{QA_SHA}`; kilde-QA `{SOURCE_QA_SHA}`; faktisk ny acquisition `{qa['new_acquisition_receipt_sha256']}`. Søgefreeze `{qa['search_public_freeze_commit']}`; QA-freeze `{qa['qa_public_freeze_commit']}`. QA autentificerede 222.912 patch-celler bitvist; denne rapport åbner kun gemte grænseresultater og metadata, ingen kilde-H5 eller ufærdige interiører.", "",
        "Native171 var undersøgt, før de tilstødende native170/172 blev valgt. Beskyttede 2016-holdouts og oprindelige fejltilstande er uændrede. Der foreligger ingen blind bekræftelse, kalibreret falskalarmrate eller astronomisk oprindelsesbestemmelse.", ""]
    with (out / "RAPPORT_DA.md").open("x") as f:
        f.write("\n".join(Danish))
    for rel, expected in pins.items():
        b = (root / rel).read_bytes()
        assert {"sha256": sha(b), "bytes": len(b)} == expected
    assert sha(self_path.read_bytes()) == self_sha
    outputs = {p.name: {"sha256": sha(p.read_bytes()), "bytes": p.stat().st_size} for p in sorted(out.iterdir())}
    write_json(out / "INTERPRETATION_RECEIPT.json", {"schema": "SETI_S2017_BOUNDARY_SAVED_ONLY_DESCRIPTIVE_EXPORT_RECEIPT_V1",
        "status": "COMPLETE_DESCRIPTIVE_ONLY_QUALIFIED_CLAIM_FALSE", "qualified_claim": False,
        "empirical_boundary_QA_sha256": QA_SHA, "source_QA_sha256": SOURCE_QA_SHA,
        "interpretation_script_sha256": self_sha, "input_pins": pins, "output_pins": outputs,
        "counts": {"maps": 12, "saved_top20_entries": 120, "fixed_tracks": 18, "fixed_scan_measures": 108, "fixed_time_rows": 1728},
        "source_H5_opened": False, "detector_or_score_rerun": False, "interior_values_read": False,
        "process_CPU_seconds": time.process_time(), "wall_seconds": time.monotonic()-started,
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024})
    print(json.dumps({"status": "COMPLETE", "summary": summary, "interpretation_receipt_sha256": sha((out / "INTERPRETATION_RECEIPT.json").read_bytes())}, indent=2))


if __name__ == "__main__":
    main()
