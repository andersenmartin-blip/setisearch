# Portable fixed-context replay

This replay requires Python 3 and NumPy. It reads no HDF5 files and imports no
detector. Keep the archive's relative paths when unpacking it.

The previous 54 logical profiles retain their original numerical values and
provenance. Their 48 normalization crops are authenticated as opaque stored
bytes, including all 768 row hashes. Earlier normalization and profile scores
are never recomputed by this driver. Only genuinely new fixed physical
templates would trigger independent normalization and score calculations.

The actual final selector chose the same nine prior logical tuples: this
replay therefore calculates zero running medians, normalizations, or new
physical profile scores. It verifies the 54 selected source links and nine
original per-carrier map scalar checks without decoding source-power floats.

From the unpacked package root, use a fresh output path because archived
receipts must remain unchanged:

```bash
python carrier_followup/reproduction/reproduce_from_saved_crops.py --run --root . --scope carrier_followup/reproduction/SCOPE.json --go carrier_followup/reproduction/ROOT_GO.json --out /tmp/carrier_context_replay_fresh.json
```

The GO file must authorize the exact code and scope hashes. `--check-only`
prints the prepared interface without reading arrays or running the replay.

The original baseline replay source, scope, and frozen inputs are retained
separately for an optional user-invoked reconstruction of the earlier 48
normalizations; that historical replay is never started automatically.
The optional full selector check uses the unchanged authenticated QA module
through a wrapper that writes to a new directory inside the unpacked root:

```bash
python carrier_followup/reproduction/reproduce_selection.py --root . --out-dir carrier_followup/reproduction/selection_replay_fresh
```

Choose an output directory that does not already exist. The wrapper preserves
the archived receipts and changes only the destination of newly produced QA
files. This selector check is never started automatically by the context
replay.

This is numerical provenance verification. It does not reproduce original
search maximization, calibrate false alarms, or establish an independent sky
confirmation.
