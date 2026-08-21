# Milestone 15 independent-cadence availability

Status: **NO PUBLIC INDEPENDENT CADENCE WITH 1406 MHz COVERAGE FOUND**.

This is an archive-availability conclusion, not a non-recurrence result. It
uses the metadata-only GJ 581 screen from GitHub Actions run `32502205358`,
artifact `9453942416`, digest
`sha256:357c0a074e596bbdc714d512b12ecf7725547f0aeca77a4ec3f55b45468c2b91`.
No additional spectral values were inspected for this conclusion.

The public target catalogue exposed two GJ 581 / HIP 74995 cadence records:

| Cadence | Start UTC | Receiver coverage | Use for 1406 MHz recurrence |
|---|---|---|---|
| `--87092` | 2016-03-30 09:53:27 | 1126.465-1876.465 MHz | Already searched in Milestone 15 |
| `--80557` | 2016-12-31 17:10:02 | 1797.949-2802.832 MHz | Ineligible: does not cover 1406 MHz |

Cadence `--80557` is temporally independent and contains three HIP 74995 ON
scans interleaved with three other sky positions, but its S-band product begins
about 392 MHz above the required receiver frequency. It therefore cannot test
recurrence of the 1406.118273185 MHz case. Alternate `.0002` and `8.0001`
products belong to the same observation IDs and do not create another cadence.

Unless new public data appear or a new observation is obtained, the unresolved
case cannot be advanced or rejected by independent recurrence. It must remain
labelled `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE`.
