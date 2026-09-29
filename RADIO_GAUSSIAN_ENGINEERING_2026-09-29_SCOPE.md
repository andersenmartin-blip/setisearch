# Prospective Gaussian/native engineering scope — 29 September 2026

Status at publication: **ENGINEERING ONLY; no values drawn**. This is the first
bounded numerical stage of the integrated Gaussian/compact-score/native physical/
recovery/RFI/null qualification requested at `f63861ad3054d655aa8d4ac7f9018a6499f5817b`.
The scientific 127/24 proposal remains **PROPOSED_NOT_ACTIVATED**.

## Why this stage is separate

The production whole-cadence threshold requires 127 real reference maxima from
the same declared noise/domain. A pair of Gaussian engineering cases cannot
provide that reference or establish false-alarm, recovery or RFI performance.
We must first measure real Gaussian score generation, compression, retained
arithmetic and resource use. This scope authorizes only that first stage, not a
fabricated reference distribution or a relabelled deterministic fixture.
Subsequent physical/gate work needs its own prospective reference/threshold
design and budget. No result here may tune the 127/24 evaluation or authorize
opening telescope spectra.

## Fixed data, identities and arithmetic

Use HD189733/HIP98505 cadence 85030 metadata only. The original preparation
contract remains unchanged and not ready. Exact source, geometry, receiver
bank and old identity files are pinned by `radio_receiver_adapter_common.PINS`.
The generated `results_radio_gaussian_engineering_2026-09-29/plans.json` is the
full machine-readable plan, including both complete frequency windows and
every stream call. Namespace: `radio-gaussian-native-engineering-20260929a`.

| Case | Metadata window, inclusive physical bounds in Hz | Digital input |
|---|---|---|
| 0 | calibration: 1402140020.024552–1402325844.7410803 | Gaussian-only null |
| 1 | validation: 1411059742.5220742–1411245567.2386024 | Gaussian plus ON signal, width 129 channels, rate label −2 Hz/s, digital power 500 per active row; all three ON epochs, no OFF injection |

These role names choose metadata windows only; both cases are **engineering**.
Six scans, sixteen integrations each, 65,536 channels, 96 row calls per case.
Use NumPy PCG64 with SeedSequence([case_seed,scan_index]), normal(100,1,65536),
float64 draws cast to float32, optional float64 pixel-integrated injection,
then float32 native storage and the existing native normalization/score chain.
The separate engineering noise-law hash must never become a scientific law.
Seeds are the first eight big-endian bytes of SHA256(namespace/name/seed-v1).
Case identities include context/source/bank/law and the complete fixed recipe.
Compare both seeds and identities against all 151 reserved proposal cases and
the recorded historical JSON configuration inventory. This verifies distinct
labels, not statistical independence or exclusion of unknown external uses.

Use the unchanged receiver bank: 81 rates from −4 through +4 Hz/s in 0.1
steps, widths 1,3,5,9,17,33,65,129, 81 central bins and 99 support bins.
Preserve all 1,296 score vectors (384,912 values per case), all 48 cache
ancestries and all 96 row receipts. Reduce the complete family to its recorded
maximum; preserve its mask/selection provenance. Primary remains neighbor9.
There is **no statistical threshold, detection decision, physical veto or
recovery/RFI/null pass claim** in this stage.

## Publication, one-shot consumption and no resume

Before execution, publish this scope, all new code/tests, plans, allocation,
identity comparison and transitive runtime freeze. Fetch the immutable commit
and verify every pinned code/input/runtime byte. Then publish a separate
`consumption_intent.json` referencing that freeze and allocation. Publication
irreversibly reserves **both** cases for the one supervised invocation, even
if it fails before RNG. Freshly fetch and verify that intent before invoking
the runner. This intent is consumed, not permission for a future replacement
worker; it must never be reused after lost scratch, process loss or ambiguity.

Within that invocation, a durable engineering DirectoryStore journals each
case consumption and writes a registered RNG-start artifact **before** the
first PRNG constructor. It retains every ledger revision. Duplicate, partial,
uncertain or incomplete cases cannot restart; an incomplete first case blocks
the second. No refund, seed substitution, threshold change or automatic retry.
Publish all retained artifacts and revisions, including failed/partial states.
The local journal and public whole-run reservation do **not** qualify the
separate scientific per-artifact remote publication adapter.

## Prospective ceilings and outcomes

- Exactly two engineering cases and 192 row calls; at most 12,582,912 new
  Gaussian values. The 127/24 scientific allocation and older closed ledgers
  are charged zero new cases and must remain unchanged.
- Reserve 180 seconds and 8 MiB artifact capacity per case. Both reservations
  remain charged on interruption. Each case has an alarm plus lease checks;
  whole-run active cap is 420 seconds including at most 60 seconds overhead.
- RSS ceiling 512 MiB; modelled arrays 256 MiB. Total new scope evidence cap
  20 MiB: 16 MiB case reservations, 2 MiB ledger and 2 MiB setup/summary reserve.
  Count retained ledger revisions in physical evidence totals.
- Publication after this freeze starts has a separate ceiling of 96 GitHub
  connector calls, 32 MiB uploaded payload and 64 MiB returned content, with
  1,800 seconds cumulative connector latency. Charge calls before dispatch;
  report setup and publication separately from numerical case time. These
  ceilings are not the scientific 40/80-second quotas.
- Engineering PASS requires complete exact score inventory, matching source/
  context/plan/noise-law hashes, complete row receipts, finite native values,
  byte-for-byte archive verification, compact re-reduction equal to the native
  maximum and all engineering resource caps. Preserve all output regardless.
  A pass cannot certify detector sensitivity or scientific publication timing.

Compact archives retain score bytes, source/cache identities and row hashes.
They omit raw and normalized source arrays and cannot reconstruct them without
regenerating values. Regeneration is not authorized by this scope. No claim of
raw-array recovery, Gaussian tail calibration or independent observation.

## Preserved boundaries and exact next work

HD1461/71139 remains HOLD_POINTING_PROVENANCE_UNRESOLVED; GJ724 is untouched.
M43AI stays failed and closed; original M43AF 112+128 holdouts stay unopened.
M15 GJ581 and M33 HD3651 remain unresolved. LS pauses at LS8BD–LS8BE with
LS8BF untouched; CHEOPS remains UNSENT. No external messages or telescope
spectral values, no coordinate edits, no additional target selection, no
extension past the 9 October consolidation.

After this one invocation, close both engineering cases permanently, publish
measured sizes/timings and failures, and assess the concrete remaining gap:
an actual same-law reference set or a separately justified engineering-only
threshold interface for the native physical/recovery/RFI/null chain, followed
by genuinely integrated remote publication within its own frozen ceilings.
Do not rerun these cases or declare the scientific proposal ready.
