# HD189733: prospective synthetic calibration and fixed evaluation panel

This freeze completes the synthetic control protocol following the six closed
development cases. It does not authorize a telescope request or rewrite either
source preparation contract. Primary remains neighbor9. All source, bank,
window and identity pins remain those in the published receiver reservation.

## Exact inputs and measurement domain

Use the three calibration identities and 24 evaluation identities in
`results_radio_hd189733_receiver_2026-09-28/control_identity_reservation.json`,
in index order. Six spent development identities cannot be reused. Calibration
uses its own 65,536-channel extraction geometry; evaluations use validation
geometry. The original fixed native intervals, 81 scored carriers, 99 support
carriers, 81 drift labels, eight detector widths, six scans and 96 integrations
remain unchanged. All exact frequencies and identities are transitively pinned
through `scripts/radio_receiver_adapter_common.py` and the machine config.

For each scan initialize PCG64(SeedSequence([reserved seed, scan index])). Generate
each complete native row in ascending frequency, Gaussian digital power with
mean 100 and sigma 1, cast float32. No comb or other artificial calibration
support is added. The law is a synthetic digital fixture, not a telescope-noise
or instrumental-channelizer model. All three calibration realizations are
noise only. Their namespaces/seeds are disjoint from evaluation and development.

The reserved evaluation recipes are unchanged: two nulls, ten ON-only signals,
ten matched ON/OFF controls and two single-adjacent-OFF controls. Every signal's
intrinsic rectangle has its reserved width 1/5/33/65/129 native channels and
total power 100 or 500 per integration; every designated scan is active for its
full 16 integrations. Use the analytic exposure convolution already qualified
in development, evaluated separately at each exact header midpoint/duration.
The received track is q(1+r*t/C), q=C at the role's carrier centre, with the
reserved rate-label cycle. Matched OFF uses this same received track at OFF
times; single-adjacent has ON epochs 0,2 and OFF epoch 0. Nulls have no additions.
Truth enters only post-decision recovery accounting, never detection or vetoes.

## Null construction, transfer and immutable threshold rule

Each calibration has an explicit published table of 127 distinct triples
(0,a,b), a,b in integers 32 through 48 inclusive. Tables are selected without
replacement from the 289 possible ordered pairs with PCG64, seeded from the
first eight big-endian bytes of SHA-256(namespace + '/scrambles-v1'). The full
tables, not just seeds, are in the frozen config. Epoch zero remains fixed;
epoch vectors and their neighbor9 exclusion masks rotate together on the
81-cell scored axis. These are conditional resamplings of each of three
independent synthetic realizations, not 381 independent observations.

The published complete score-map equality permits an explicit **synthetic**
calibration-to-validation score translation: the relative raw-array noise law
is the same by construction, normalization/filter/gather indices match, and
the score-vector payloads do not change. Original calibration source/cache
receipts are retained as original receipts. A distinct translation receipt
binds the source and destination contexts and the externally pinned map proof.
No old certificate is relabelled and no destination telescope measurement is
claimed. New calibration accumulators and certificates are generated for the
validation context. Absolute-frequency vetoes are evaluated there on each
evaluation's own native arrays. No pilot shortcut or real-frequency noise/RFI
exchangeability is established.

All three calibrations must complete their entire hypothesis inventory with
finite observed and all 127 finite null maxima. An empty maximum is minus
infinity, serialized as null with an explicit meaning. It is a **failed
calibration prerequisite**, not a zero false-alarm rate. Preserve all empty
entries; do not add a comb, drop empty rows, substitute a floor, alter the
active-epoch rule, or retry. Complete the other preassigned calibration
realizations after such a scientific failure. An integrity/resource failure
stops the run immediately and retains inputs and the error.

The **preselected index-0 calibration** supplies the operational threshold:
max(10, higher empirical quantile at 1.0 of its 127 null maxima). The rank is
(1 + number of null maxima >= member score)/128, with ceiling 0.01. Calibration
indices 1 and 2 are retained diagnostic realizations; they cannot select,
pool, raise or lower that threshold. If any calibration lacks finite support,
none of the 24 evaluation values is generated and this attempt closes. There
is no replacement calibration budget.

## Detection, association and stopping gates

Use unchanged numerical neighbor9 mask, minimum active-epoch S/N 3, sum stack,
all four two-or-three-epoch subsets, full retention, matched OFF tolerance
20 Hz, single-adjacent OFF floor 5.5, receiver neighborhood ±100 Hz, local peak
floor 5.5, shared-epoch minimum 2 and ON-track alias tolerance 20 Hz. Preserve
every retained ON/OFF trigger, physical veto, rank outcome and full component.

A concrete pre-exposure defect was found: legacy retention/alias metadata
required orbital phase and projected scale. The new explicit receiver schema
stores rate label, rate-reference frequency and receiver-bank identity instead.
Legacy records keep their exact old fields. No orbital placeholders are made;
the numerical score/mask/rank/OFF/alias kernels are unchanged. The frozen code
and targeted interface tests make this extension reviewable before exposure.

Apply all numerical gates in the existing reservation. A final member passes
both physical vetoes and the inclusive rank cut. Association requires active
epochs to be a subset of injected ON epochs and every integration midpoint in
those epochs within two native channel spacings of the injected track. Require
one associated final member and component in every ON-signal case. Retain its
unassociated members explicitly; they do not change that recovery gate.
Noise, matched ON/OFF and adjacent-OFF controls require zero final members
and components; widths 65 and 129 separately require zero unassociated final
members/components in those controls. A mixed component contributes to both
associated/unassociated reports; each member belongs to exactly one component.
If a scientific recovery/control gate fails, finish the fixed remaining cases
without any tuning. Integrity or capacity failure stops immediately. No
truncation, replacement case, remedy, alternate detector selection or pilot.

## Publication, durable consumption and budgets

Publish and read back this protocol, executable code, config and reservation
before any reserved values are generated. Publication charges the three
calibration attempt slots and the one evaluation-attempt allocation. The 24
evaluation identities remain conditionally reserved and unexposed if calibration
fails; the same attempt cannot be restarted to use them. Missing scratch or
missing completion is never permission to reset/replay. The local attempt
directory is created exclusively and every case is charged before generation.

Limits for this connected execution: 3 calibrations; at most 24 evaluations in
one run; 0 remedies; 0 pilots; 0 network/source requests; 3600 active seconds;
512 MiB process RSS; 256 MiB modelled arrays; 256 MiB retained evidence; 10,000
retained records per scan-kind/case, with existing 128,000,000-byte stage limits.
The already spent six development cases, prior 80 source-metadata requests /
55,841 response bytes / 557.320353 active seconds, closed synthetic acquisition
ledger and inactive telescope genesis remain separately accounted, never reset.

Archive all score vectors in lossless NPZ before downstream execution, with
vector hashes and complete source/cache/row receipts. Raw random/native arrays
are not archived; deterministic generation and row hashes remain available.
Store full decisions and all outcomes without truncation. The runtime is pinned
to Python 3.12.14 and NumPy 2.3.5; exact files are pinned in the config.

After completion, publish the evidence, precise counters and next step. A failed
panel permits only the plan's one bounded diagnosis on retained evidence, not a
new tuning/evaluation cycle. A synthetic pass still requires source-specific
codec/runtime handoff and a verified integrated prospective acquisition/trial
protocol before any telescope spectra. All earlier dispositions, HD1461's hold,
untouched GJ724 reserve, M43AI failure, original M43AF holdouts, M15/M33,
LS pause and unsent CHEOPS persist. No external messages; no plan extension.
