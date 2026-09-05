# M43D: nested coefficient-disk bank coverage

Freeze this plan, configuration, executable and tests publicly before evaluating
any bank against the historical or new truth inventory. The original 93-template
bank and the M43B endpoint remain the baseline. M43C motivates this study:
330 unsupported historical truths lack a suitable track shape at 20 Hz.
This study addresses geometry only, on the same HD 156668 b cadence and the
m37_1412p5 proxy-carrier grid. No new telescope samples, injections or scores.

## Fixed banks and endpoint

Preserve the original 93 records as the exact prefix. Append all Cartesian
coefficient pairs (i/n,j/n) inside i²+j² <= n² for n=8,16,32, in ascending i,
then j order. Skip already present exact coordinate pairs. Each larger bank
contains every previous record. This produces 93, 289, 889 and 3,301 templates.
The physical circular-orbit coefficient domain remains x²+y² <= 1; neither
the known injected truths nor their best-fit values define these banks.
There is no data-selected rotation, tolerance change or carrier-grid refinement.

For each truth use all integration midpoints of its active ON epochs, one
fixed template and one common carrier. A match requires the literal binary64
maximum absolute frequency discrepancy to be <=20 Hz. An interval prefilter
uses a fixed 0.00001 Hz outward guard and four carrier bins of padding; final
acceptance uses exactly 20 Hz. Restrict factors to [0.5,1.5], grid magnitudes
to <=2e9 Hz and truth tracks to <=3e9 Hz. Abort outside that numeric domain or
above 8,000,000 materialized distance cells per association. No truncation.
This numerical implementation is checked against exhaustive small oracles,
radio-frequency boundary cases, and the historical planner; it is not a
formal real-arithmetic proof or an operational detector replacement.

## Historical comparison and prospective geometric check

1. Reconstruct the exact M43B basis/table prefix. Replay every historical
   per-truth plan hash and compare every baseline (template,carrier-index)
   pair with the new calculator on all 512 historical truths. Abort on any
   mismatch. Report all four bank counts with the original denominator.
2. Nominate the first bank in ascending size that supports >=95% of those
   512 known truths, or none. Seal the nomination before evaluating new tracks.
   This is development selection, not independent confirmation.
3. Generate 512 new deterministic, previously untested geometric tracks from
   16 equal-area radial strata and 32 angular strata. SHA-256-derived jitter
   uses the exact label and top-53-bit conversion in the pinned executable.
   Sample a continuous carrier between score_hz[256] and score_hz[-257]. This
   is the historical allowed proxy-carrier interval, not a rest-frequency
   selection or a claim to all five physical windows. New carriers are off
   the tested lattice; historical carriers were on it. Consequently historical
   and new rates must not be presented as identical-distribution estimates.
4. Evaluate each new track under all four activity subsets: (0,1), (0,2),
   (1,2), and (0,1,2). There are 512 unique new tracks and 2,048 associations;
   the four rates are paired, not 2,048 independent astronomical trials.
   No spectral width or S/N enters geometric support. Reject exact overlaps
   with historical coefficient pairs or any template point.
5. Confirm the nominated bank's geometric gate only if >=95% of the 512 new
   tracks are supported in EACH activity subset. Publish all banks, even if
   no bank qualifies. Do not switch nomination after seeing the new results.
   The same cadence basis is used: these are new parameter draws, not an
   independent sky observation, cadence or global coverage proof.

The 95% gate is an engineering screen chosen before this run. It neither
represents measured recovery nor guarantees the remaining 5% or domain edges.
No automatic production adoption follows. Report monotone candidate-cell
counts, per-bank pair hashes and a directly verified witness, aggregate
activity counts, and checksummed restart rows.

## Computational cost and later gates

Report exact score-cell counts (templates × 747665 carriers × 8 widths ×
4 activity subsets), a five-window arithmetic extrapolation, relative cost
versus 93 templates, table bytes and observed elapsed geometry time. Cell
ratios are not measured detector runtimes; geometry timing excludes spectra,
filtering, cache construction, masks and false-positive calibration. No
threshold or null result transfers to a larger bank without requalification.

Next: source/cache extraction coverage for a nominated bank, score and
false-association validation, deterministic exhaustive real-data anchors,
and only then renewed calibration. If no bank qualifies, preserve the failure
and diagnose geometry before any further bank tuning. Historical M37/M41/LS
results, their denominators and scientific interpretations stay unchanged.
