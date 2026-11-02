# Independent audit of the bounded Rubin extension

The two-object extension passed **48 pre-acquisition checks** and **2,972 independent result comparisons**, including 472 numerical comparisons with **zero numerical difference**. The original 188-object main selection and all original science outputs remain unchanged. The shared independent scalar helper also remains byte-identical to the development, recovery and first-main audits.

## Pre-acquisition review

The transfer code is identical to the original acquisition implementation. The analysis wrapper changes only its output directory and a summary accounting-key label; the cutout wrapper changes only its input/output directories. All request fields, quality flags, transfer limits and frozen scientific rules are unchanged.

Both exact selected identities satisfy the earlier metadata-only prerequisite. Neither identity or Gaia counterpart duplicates the original main sample, and both lie beyond 2 arcsec of every original 433 metadata position; the smallest separation is 639.56 arcsec. Combined selection is 190 objects, below the original 500-object cap. These checks establish the declared sample accounting, not photometric evaluability or a detection.

`PREFLIGHT.json` records the state before extension acquisition. Its historical “not started” checks are expected to fail if the entire preflight is rerun in an already completed working directory; preserve the receipt and run the result auditor to verify current evidence.

## Independent results

The result auditor uses the unchanged scalar `../independent_main_audit/independent_science.py`, importing no production detector functions. It reproduces normalized records, every October score and reason, raw-file lineage, all 2×2 eligibility rows, summaries, empty trigger lists and exact cutout associations. It verifies frozen extension code and method hashes and rechecks every original main output after extension execution.

| Separate extension stream | Returned objects | Measurements | October measurements | Numerically evaluable objects | Evaluable measurements | Triggers |
|---|---:|---:|---:|---:|---:|---:|
| Source-position science photometry |2|54|6|0|0|0|
| Object-position forced photometry |2|53|10|1|2|0|

All 54 source identities match the earlier metadata-only history snapshot exactly, with no missing or additional identities. The six source-position October records split into three with insufficient prior visits/dates and three that fail the unchanged positive/stable/precise baseline criterion. Metadata eligibility therefore did not guarantee usable photometry.

The two evaluable forced measurements have about 107.7-day reference gaps, unknown withdrawal status and unavailable measurement-quality flags. They do not establish a fully vetted event search or local quiescence. The minimum 50 evaluable main objects remains unmet. No scientific threshold was changed to increase this count, and zero triggers is not a qualified null result.

Reproduce the numerical audit in a separate copy:

```bash
python3 audit_extension.py
```

The audit writes `AUDIT.json`; original science outputs are only read. No network request or acquisition is performed.
