# Retained codec fixture reconciliation — no regeneration

The sole fixture execution encoded all 48 chunks and preserved the exact
legacy source declaration, then stopped after 1.138451004 s in the comparison
oracle. Its reversed NumPy view violated the unchanged normalizer's C-order
input contract. The generator, its input pins, both HDF5 files and full error
remain unchanged. Do not rerun `radio_hd189733_codec_profile.py` or create a
replacement fixture.

This corrective implementation step copies only the oracle's block layout
to contiguous storage before applying the existing normalizer. Preserve the
same float32 element bits and order. Test that correction on a deterministic
strided array and reject invalid input types/nonfinite values. Then reconcile
the already retained compressed and decoded bytes for the originally fixed
48 chunks and 48 extraction rows. Persist receipts as each row finishes.
Repeated checks of the first role are recovery of incomplete evidence, not
new independent data or an additional statistical trial.

No scientific gate, spectrum, seed, fixture value, filter or numerical setting
changes. Use the unused part of the original 600 active seconds and the same
512 MiB RSS / 128 MiB file ceiling; no new fixture/exposure allocation. Publish
the original failure and separate corrective reconciliation. Source/receiver
receipt integration and telescope admission are still separate requirements.
