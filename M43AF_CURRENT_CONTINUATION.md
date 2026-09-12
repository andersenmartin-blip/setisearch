# M43AF completed continuation

The frozen no-model branch is complete: all 502 prescribed records and the
independent whole-study audit pass. No boundary qualifies and no new detector
is adopted. The 112 validation inputs and 128 held-out native nulls remain unopened.

Read [the complete report](MILESTONE_43AF_RESPONSE_STUDY_RESULT.md).

## Public scientific anchors

- Scientific freeze: `75b271b4b92819783692375687586d6df4f40c57`.
- Verified training/model publication: `bdab6b0af39d6bc6c81ce9d5f07ef24c103ca833`.
- Model-decision seal: `e1ef8cfc261a4b155695cc61d3cbda875ca35ff9aef7c8b0cff20b03c48bf7a3`.
- Complete result seal: `4fdab085bfceb08207eea63c3ce1386ae237320a054b443a6771069b86e64cd5`.
- Complete audit seal: `dfc2c4a7734dffe1c033a33567c8fbbecfe4aab76880f1bda5c52137e6239d30`.
- Complete archive SHA256: `b66e2a2dbe41d3dda4a63254c4528185e761aae7fdcf4745ef8e3764ca6c9443`.

The original 940 pinned files, earlier endpoints, failed gates and closed
training records remain unchanged. The earlier training-release manifest
describes its exact payload at the training-publication commit above; compare
that historical manifest at that commit rather than against later status documents.

## Restore completed evidence

Use Python 3.12.14 and zlib 1.3.2 with the
frozen dependencies. Restore the earlier dependency archives and then the
complete M43AF archive; do not rerun closed scientific evaluations.

```bash
PYTHONPATH=src:scripts python scripts/m43z_restore_ledger.py
PYTHONPATH=src:scripts python scripts/m43ab_archive.py restore
PYTHONPATH=src:scripts python scripts/m43ad_archive.py restore
PYTHONPATH=src:scripts python scripts/m43ae_archive.py restore
PYTHONPATH=src:scripts python scripts/m43af_archive.py restore --stage complete
PYTHONPATH=src:scripts python scripts/m43af_archive.py verify --stage complete
```

The complete archive restores 508 original files, including all 502 records,
the full training grid, immutable decision, publication receipt and audits.
The earlier 244-file training archive remains available independently.

Native source data are needed only for a new native computation or an explicit
reproduction of the independent native checks. All six original sources and
96 arrays were reconstructed and verified during completion. Exact source
archives can restore the raw/normalized rows; the bounded recovery helper can
regenerate anchors or recover missing original sources against their pinned
receipts. Inspect availability before relying on a previous runtime.

## Next scientific scope

M43AF remains a failed qualification on one observing sequence. Any revised
grid, feature representation or acceptance rule requires a newly named,
prospectively frozen study and fresh evaluation inputs. The now-measured
historical coordinates may inform that design; they are not independent validation.
General adoption also requires evidence from an independent observing sequence.
No unattended computation between sessions is assumed.
