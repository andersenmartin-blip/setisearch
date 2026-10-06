# Independent source review

Disposition: **PASS_SOURCE_ONLY**.

The review begins from science commit
`505b2adc210c11701a3762383d2bfb8eb8986ec1` and does not infer state from an
older checkpoint.  The 14 input paths are ordinary files, total below the 4 MiB
source-read ceiling, and each raw body is bound by SHA-256 and Git blob SHA-1.
The four original metadata bodies retain their previously published independent
pins.  The closed G receipt and actual review state one of twelve handoffs,
engineering-only, with no codec certificate.

The admission source is inspected, not imported.  Its exact generated six-label
order and literal 22-law tuple match the preparation.  The generated plan has
exactly 12 handoffs in calibration-six then validation-six order, indices 0–11,
chunk indices 159×6 then 156×6, and the published role-specific context, bank and
window identities.  All handoffs use 16 rows and the exact source shape, chunking,
dtype and filter signature.

The metadata-law control authenticates and compiles only the 1,651-byte pure
guard, whose AST contains a docstring and functions only.  Its refusing fake
dataset records no indexing attempt.  All four positive laws accept and all 18
negative laws reject in the exact admission order.  There is no native import,
HDF5 file or telescope value access.

The deterministic future formula adds `256*handoff_index` to the integer
numerator before exact power-of-two division.  The 12 handoff bases are distinct,
there is no PRNG, and the plan labels the values controlled engineering data,
not a telescope/noise model.  The resource arithmetic closes: 24 × 16 MiB =
384 MiB HDF5 ceiling; 400 MiB leaf + 48 MiB outer = 448 MiB artifact ceiling;
1 GiB address space is no smaller than the 768 MiB RSS ceiling.  These are
proposals only and do not mutate cumulative spent reservations.

Nine source-only tests pass.  The plan and review explicitly refuse dispatch,
activation, allocation, spectra, holdouts and certificate issuance.  The next
allowed transition is a distinct immutable executable freeze with complete
public readback and independent review; it must not silently treat this source
checkpoint as an activated control.
