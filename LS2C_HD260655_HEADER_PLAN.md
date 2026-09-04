# LS2C plan: HD 260655 header preflight

## Trigger and scope

The published LS2B result selected HD 260655 cadence `--64524` and also retained
a second GBT cadence, `--78205`. Both contain six medium-resolution products;
the first lists all six HTR products and the second lists five. LS2C freezes a
header-only comparison of both opportunities before any spectral dataset value
is read.

HD 260655 is about 10.01 pc away and has two transiting planets. The NASA
default solutions used by LS2 give periods of 2.76953 and 5.70588 days,
semimajor axes of 0.02933 and 0.04749 au, and a stellar radius of 0.439 solar
radii.

## Permitted access

For the exact URLs inherited through the hash-pinned LS2B result, LS2C may read:

- HTTP status, size, range and entity metadata;
- HDF5 root and dataset attributes; and
- dataset shape, type, chunk and compression metadata.

The HDF5 `data` dataset must never be indexed or sliced. No spectral value may
be read or published.

## Header gate

A medium-resolution cadence qualifies only if:

- exactly six `.gpuspec.0002.h5` headers are readable;
- the source pattern is A-B-A-C-A-D with `HIP31635` in all three ON positions;
- channel count, time sampling and channel spacing agree across all six scans;
- sampling lies between 0.5 and 2.0 seconds;
- absolute channel spacing lies between 1 and 5 kHz; and
- each scan spans at least 700 MHz.

Full follow-up capability additionally requires six readable HTR headers with
sampling between 0.1 and 1.0 ms. Missing HTR coverage does not retroactively
invalidate a medium-resolution cadence, but it is disfavoured at selection.

## Conjunction metric and uncertainty diagnostic

For every medium-qualified cadence, compute the LS1 circular, edge-on,
common-node projected b--c separation at the midpoint of the first ON scan.
MJD is treated as BJD for this archive-ranking approximation.

The observation predates the NASA transit reference epochs by several hundred
orbits. LS2C therefore also evaluates all 81 combinations formed by -1, 0 and
+1 published-sigma perturbations of both orbital periods and both transit
epochs. The resulting minimum and maximum separation are a deterministic
input-sensitivity envelope, not a confidence interval. Per-planet propagated
timing uncertainties are reported explicitly.

## Selection and next boundary

Among medium-qualified cadences, prefer full HTR coverage, then the smallest
nominal projected separation, followed by observation time and cadence URL.
Selection authorizes only preparation of a separately frozen LS2 broadband
search preregistration. Spectral access remains forbidden until that later
configuration, templates, vetoes, retention limits and synthetic validations
are committed.

LS2C cannot support a signal, technosignature, null, sensitivity, false-alarm
or occurrence-rate claim.
