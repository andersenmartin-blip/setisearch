# LS4M: morphology of the measured B1 HTR control features

This is a retrospective, diagnostic-only continuation of LS4L. Its question is
where the actual HTR OFF-veto pulses occur in time, at which scales, and how
their positive native-channel excess is distributed. No threshold, veto,
candidate disposition or search significance is changed. The frequency bands
were selected by earlier digital injections, not by this morphology study.

## Selection frozen before the new read

Use the complete hash-pinned LS4L v2 ledger. Its 256 fragment evaluations
(64 selected fragments at four HTR amplitudes) reduce to 17 distinct detected
frequency-band/time-window selections. Retain all of their use mappings.
The 48 fixed-window controls reduce to four additional windows, separately
labelled. Extract the resulting ten unique frequency bands from the existing
B1 high-time-resolution scan only. Do not read A1 or reserved A3/C1/D1.

Reproduce the original six-width LS4E OFF pulse counts and OFF veto flags in
every one of the 256 selected and 48 fixed-window uses. No ON injection or
ON acceptance decision is rerun. The original Stage-1 rejections remain
attached to the LS4L records, and no sky candidate can be promoted here.

## Measurements

For each of the 21 distinct selections retain the unchanged residual metrics:
inside and reference-region pulse clusters, peak scores, cluster spans,
reference scale and block counts at all six widths. These are reused windows
of one observation, not independent observations or distinct physical pulses.

For every pulse peak, select the exact half-open native sample-center block
of its effective width. For each extracted native channel subtract the mean
over the full guarded reference region and clip negative excess to zero.
Retain the positive excess vector, largest-channel fraction, positive-channel
count and effective channel count `(sum excess)^2 / sum(excess^2)`. If there
is no positive excess, the fractional descriptors are null. This descriptive
channel baseline differs from the pulse detector's local detrending: it is
not a classifier of interference, broadband emission or physical origin.

Retain per-channel counts of byte values 0 and 255 across the scan; these do
not establish hardware saturation. For selected bands with exactly the same
window compare all inside and reference pulse times at equal scales using
the existing one-to-one matcher and one effective-width tolerance. Label
shared native channels explicitly. Coincidences are descriptive, not an
independence test or a calibrated probability.

## Resource and evidence contract

Download B1 only: 9,435,087,189 bytes, verified against the existing full-file
SHA256 and header before numerical use. Allow at most two charged attempts,
18,870,174,378 bytes total, with 4 GB extra free disk. One raw file resides in
a unique temporary directory outside the repository. Delete raw and partial
files on completion or failure. Publish derived evidence only, never a native
scan, extracted channel matrix or collapsed time series.

Save a derived checkpoint after each completed selection, before final replay
validation and before raw deletion. Abort on changed geometry, missing replay
uses or more than 50,000 pulse records; do not truncate and claim completion.
Preserve any abort and partial evidence. The output directory cannot be reused.

## Qualification and report

Before spectral access, test hand-computed narrow/broad channel descriptors,
native block boundaries at the actual sampling interval and all six scales,
reference guards, inside/reference pulse separation, deduplicated inventory,
replay tampering and coincidence overlap labels. Freeze and publish the plan,
configuration, implementation, tests and dependency identities before running.

Report exact unique-window denominators separately from reused evaluations,
inside/reference counts and score/time/concentration ranges by band and scale.
State the unchanged original decisions. If morphology is ambiguous, preserve
that ambiguity. LS4M does not measure ON/OFF simultaneity, astrophysical origin,
physical flux sensitivity, completeness or false-alarm probability.
