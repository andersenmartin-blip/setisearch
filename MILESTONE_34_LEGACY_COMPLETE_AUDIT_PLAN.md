# Milestone 34 legacy complete-disposition audit

Status: **FROZEN BEFORE EITHER LEGACY PRIMARY CADENCE IS RE-EXTRACTED OR
RERUN**.

Milestone 34 closes a reporting-boundary debt before the survey is extended
to new targets. The primary Milestone 17 and Milestone 21 searches both used
the then-frozen 50-cluster per-window output limit. In each search, a capped
1400 MHz list ended while its 50th retained cluster was still above the global
threshold:

| Search | Target | Window | Clusters formed | Published | Published #50 S/N | Global threshold | Omitted clusters requiring audit |
|---:|---|---|---:|---:|---:|---:|---:|
| 17 | GJ 849 | `m17_1400p5` | 64 | 50 | 45.1478875 | 8.9124193 | 14 |
| 21 | HD 154345 | `m21_1400p5` | 53 | 50 | 49.1037247 | 9.5556164 | 3 |

The lists are sorted by S/N, but case 51 could in principle fall directly
below threshold. The original searches established that every *published*
over-threshold case was physically vetoed or resolved in a separately frozen
review; they did not preserve the measurements needed to count and classify
the 17 omitted cases. This audit fills only that gap. It is retrospective and
cannot increase either primary search's significance.

## Frozen inputs

| Search | Primary config SHA-256 | Primary search-summary SHA-256 | Primary data-manifest SHA-256 |
|---:|---|---|---|
| 17 | `87372243bc6f8eec0b9cdf4f80d3a3c37fbffdd13bddd6efeafdfd5f383b2e76` | `321b00be48ba9ebbc033427f11c7a811e87b41c1055399671f55081df70f5061` | `8e1ae1559e7c56e3e0a662020c49a7de9025a8bb200fc2923eb5f29e37c65e12` |
| 21 | `441597c69c1b3227648ee7aaf4bd6c8b0a09241c807755e03b355baa194b21e7` | `e098ed1cf2d73a785aa73ece68fc5a490aff80d35758917703b00ef23483dbf0` | `6ce30183d3f9153ce95fffce5305934ae1bcac2b777b90e40aa7bd3323324d69` |

The two known Milestone 21 arithmetic-family review cases were already
resolved as `RFI_OR_INSTRUMENTAL` under a protocol frozen before their
cutouts were opened. The machine-readable review SHA-256 is
`83bc8f58b11fb8d1c599f7e1a712b0474e20b2f9fbcfeb228ed3d32ff9750335`.
Those two fixed resolutions may be carried into the complete accounting; no
new case may inherit them by similarity.

## Sole configuration change

For each search, the audit configuration is generated deterministically from
the published primary JSON by changing only:

`search.candidate_reporting.max_report_clusters`: **50 -> 500**.

The generated audit-config SHA-256 values must be:

- Milestone 17: `4f9e5b643dd98626d3502643136120c47da100fa6b13a87c9b55d45a02b72d6f`;
- Milestone 21: `f9724e05a0c2bbdcdc4b5a5a95471151ef20944300c294c11949a3975fce988a`.

The cap of 500 exceeds the already recorded largest pre-limit window counts
of 337 and 189. Telescope identities, scan times, extraction ranges, orbital
templates, activity subsets, four spectral widths, S/N rules, random seeds,
256 scrambles, completeness injections, clustering, and detector-v0.5 veto
rules remain byte-for-byte unchanged.

The runtime is also frozen to the common environment recorded by both primary
searches: Python 3.12.14, NumPy 2.5.2, Astropy 8.0.1,
astropy-iers-data 0.2026.8.18.14.22.31, pyerfa 2.0.1.5, Matplotlib 3.11.1,
h5py 3.16.0, fsspec 2026.7.0, and hdf5plugin 6.0.0.

Detector v0.5.0 computes receiver-frame aliases and arithmetic-frequency
families *after* applying the report cap. Expanding the retained list can
therefore add alias or family evidence to an already published cluster even
though its score, hypothesis, OFF diagnostics, and receiver-frame signature
are unchanged. The audit treats that as an explicit legacy implementation
property: cap-independent quantities must reproduce exactly, and old and new
flags/dispositions are both preserved. Receiver-alias evidence is monotonic
because the old retained set is a prefix of the new set. Arithmetic-family
membership may be added or removed because the family finder selects nearest
members from the whole retained list; it remains non-physical context. No
earlier physical veto may disappear.

## Fixed audit procedure

For each target independently and in parallel:

1. Verify every frozen source hash, require the installed detector source and
   package definition and tests to match detector commit
   `32720a0b5e097403f864e2b84d53a071d65d7c46`, run the complete unit-test
   and detector-validation suites, and generate the one-field audit config.
2. Re-extract only the six scans already opened in the original primary
   cadence. No reserved or independent cadence may be accessed.
3. Require all 30 extracted-slice SHA-256 values to match the corresponding
   primary data manifest by window and scan label.
4. Rerun detector v0.5.0 with the original seeds and generated config.
5. Require exact reproduction of the global result; every window maximum,
   null calibration, RFI-mask summary, diagnostic, known-answer result, and
   completeness result; every hypothesis and pre-limit cluster count; and all
   originally published cap-independent cluster measurements, top members,
   and veto diagnostics.
6. Require every audit window's published count to equal its pre-limit count.
7. Preserve and count every cluster at or above the unchanged primary global
   threshold, including those previously hidden by the cap.

For already published clusters, below-threshold and physical-veto
dispositions must be unchanged. An arithmetic-family-only case may remain so,
gain a receiver-frame alias, or lose only the non-physical family flag. All
cap-independent flags must remain identical, and an old receiver-alias flag
may not disappear.

The two complete records are combined only after both independent audit jobs
pass. Extracted telescope slices are not published.

## Classification and stopping rule

The unchanged automatic physical dispositions are
`rfi_veto_off_source`, `rfi_veto_single_adjacent_off`,
`rfi_veto_local_off_source`, and `rfi_veto_receiver_frame_alias`.

- If every newly exposed over-threshold case has one of those dispositions,
  the legacy cap debt closes.
- A Milestone 21 case matching one of the two exact, already reviewed
  frequencies may retain its published post-hoc `RFI_OR_INSTRUMENTAL`
  resolution.
- Any other `follow_up_required`, arithmetic-family-only, or otherwise
  non-physical disposition is a new open case. Its exact hypothesis must be
  published, then a candidate-local protocol must be committed before any
  targeted morphology is inspected.

This audit cannot turn a prior result into a detection. It can reveal an
omitted follow-up obligation, or prove that the old reporting caps hid only
additional physically vetoed interference.

## Next boundary

Ranks 36--40 remain spectrally and header-wise untouched. A separate frozen
header-only extension is permitted only after this audit is reported. That
future extension must prospectively widen the smearing bank and raise its
report cap before any new telescope product is opened.
