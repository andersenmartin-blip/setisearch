# Portable ON fixed-context replay

This replay requires Python 3 and NumPy. It reads no HDF5 files and imports no
detector. Keep the archive's relative paths when unpacking it.

The earlier 54 logical profiles retain their original values, capsule
references, and normalization pins. Their 48 normalization crops are
authenticated as opaque stored bytes, including all 768 row hashes. Earlier
profile scores are never recalculated by this driver.

Only genuinely new physical templates trigger independent full16/core4096
normalization and fixed original-width score reconstruction from saved
raw12096 crops. The replay also checks original ON normalization-domain and
checkpoint provenance, exact origin row-time vectors, transported rounded
centers, nine selected own map scalars, and the selected six-scan source links.

The original ON row times are transported as
`(context_tstart - origin_tstart) * 86400 + original_origin_row_times`.
The own-scan vector is retained exactly; it is never obtained by subtracting
rounded MJDs. Other ON scans are same-target scans within one visit and do not
establish an independent observing visit.

The original context QA in `on_cached/qa/context/` independently checked the
new profiles against authenticated restored source files. This separate
portable replay uses saved raw crops and NumPy only, so it requires none of
those HDF5 files. Its own receipt is
`on_cached/reproduction/REPRODUCTION_RECEIPT.json`.

After an exact code/scope ROOT_GO has been published, run from the unpacked
package root and choose a fresh output path:

```bash
python on_cached/reproduction/reproduce_from_saved_crops.py --run --root . --scope on_cached/reproduction/SCOPE.json --go on_cached/reproduction/ROOT_GO.json --out /tmp/on_context_replay_fresh.json
```

`--check-only` prints the prospective interface without reading arrays.
The original baseline normalization replay and full ON selector checks are
separate optional analyses; they are never started by this context replay.

To optionally rerun the full ON selector QA through its unchanged
authenticated checker, choose a new output directory inside the unpacked
root:

```bash
python on_cached/reproduction/reproduce_selection.py --root . --out-dir on_cached/reproduction/selection_replay_fresh
```

The output directory must not already exist. This wrapper preserves archived
receipts and changes only the destination for new QA products. It is not
invoked by the context replay.

This verifies numerical reproducibility and provenance. It does not repeat
detector maximization, calibrate false alarms, or establish astrophysical
origin.
