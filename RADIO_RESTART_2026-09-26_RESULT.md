# Radio restart result — 26 September 2026

**First integrated metadata package complete. Selected HD 1461 pilot on hold:
pointing provenance is unresolved. No new spectrum, calibration or search has
been evaluated.** The ordinary radio track remains active; LS stays paused.

The owner asked to start the new two-week plan and work autonomously. This
package carries out its restart/source-selection phase: reconciles earlier
inputs and candidate decisions, verifies a new observing sequence, checks
HD 3651 availability and follows up a concrete source-metadata inconsistency.
It is one work package, not several new detector-qualification milestones.

## What is established

| Item | Result |
|---|---|
| Deterministic selection | Original catalogue rank 38: HD 1461 / HIP1499, cadence 71139; one-sequence shortlist |
| Previous-source inventory | 69 committed configurations; 236 distinct HDF5/filterbank URLs, including preflight/reserved inputs; no selected-source overlap |
| Independent observing session | 2016-05-14, `AGBT16A_999_189`; distinct from M43's 2016-03-23 session |
| Current catalogue | 18 HDF5 product rows for six scans at three resolutions; six fine products exactly match the frozen selection |
| Current source verification | All six sizes, ETags, attributes, shapes, dtypes and chunks match the historical pins |
| Cadence | Three ON and three paired OFF scans; common timing/frequency geometry, no temporal overlap; 1682 s start-to-start span |
| Official selected record | One complete NASA Exoplanet Archive HD 1461 b composite record; all 18 requested fields present |
| Cross-source pointing check | All three ON headers differ from the official position by approximately 34.23 arcminutes; unresolved |
| HD 3651 availability | Current bounded query lists only original cadence 73274; no new independent cadence found in that scope |
| Candidate continuity | All 24 dedicated historical investigation cases indexed, with five published independent follow-ups joined without changing their hypotheses |
| Verification | Six offline HDF5-header replays, receipt hashes, official record and ledger joins pass; three changed-transport tests pass |

The configuration register is a conservative deny-list: a configured URL does
not prove it was consumed. The earlier M37 selection explicitly reserved HD
1461, and its selected six URLs occur in none of that register. The new sequence
is a different date/session, but this does not assert that all instrumental
noise and interference are statistically independent.

## Source identity and geometry

The six fine products start at MJD 57522.691770833335, or
**2016-05-14 16:36:09 UTC**, and follow:
HIP1499 → HIP462 → HIP1499 → HIP897 → HIP1499 → HIP947.
Each has shape `[16, 1, 318230528]`, float32 values, 17.986224128 s integrations,
2.835503418452676 Hz channels and coverage 1023.9257840855033–1926.26953125 MHz.
These are 96 integrations within one cadence, not 96 independent observations.
No new search band, motion bank or calibration follows from this header coverage.

Full URLs, HTTP receipts, metadata bytes, sizes, ETags, catalogue IDs and the
archive's listed MD5 fields are retained. **The complete approximately 15 GB
products were not downloaded or checksum-validated.** The receipts establish
the identity and exact bytes of the metadata read; later spectral extracts
still require their own content receipts and direct-native arithmetic checks.

## Why the pilot is on hold

The current official record identifies HD 1461 = HIP 1499 at RA 4.6762645 degrees,
Dec −8.0536206 degrees. The three ON-source attributes instead contain:

| Fine product ID | Start MJD | Header RA (hours) | Header Dec (degrees) | Angular separation (arcmin) |
|---:|---:|---:|---:|---:|
| 71139 | 57522.691770833335 | 0.31174999999999997 | −8.624161388888888 | 34.232447344 |
| 71145 | 57522.69957175926 | 0.3117497222222222 | −8.624173333333335 | 34.233164018 |
| 71151 | 57522.70737268519 | 0.3117497222222222 | −8.62416111111111 | 34.232430685 |

A separate spherical calculation agrees with Astropy within 1e-8 arcminute.
This is a literal comparison of the retained fields; no catalogue reference
epoch or undocumented coordinate correction is assumed. The archive catalogue
also repeats the discrepant declination, so it is not an independent resolution.

The [Blimpy HDF5 reader](https://github.com/UCBerkeleySETI/blimpy/blob/3ebf04342227a95405aa32e5bc75832d1dd17f28/blimpy/io/hdf_reader.py)
uses hours for `src_raj` and degrees for `src_dej`. The inspected
[historical SIGPROC converter](https://github.com/UCBerkeleySETI/blimpy/blob/90a010f8ad756bc86dc1e16fea72993b0235fcf9/blimpy/sigproc.py)
does not establish that these HDF5 numbers should be decoded again or corrected.
The exact upstream identities and interpretation are saved in
`coordinate_format_sources.json`.

The separately frozen, target-only GBT catalogue diagnostic returned **18
rows**, below its 2000-row cap. Nine rows match the three ON start times at
three HDF5 resolutions. **No matching `.fil` or `.raw` original is listed.**
This is limited to the queried public catalogue, not a claim that an original
or observing log cannot exist elsewhere. No additional telescope product was
opened by the diagnostic.

The header labels and object identities are internally consistent, but the
target's pointing provenance is not resolved. The discrepancy does **not**
prove that the telescope actually pointed away from HD 1461. It also cannot be
silently repaired by replacing the header value with the catalogue coordinate.
The source-identity status `METADATA_ELIGIBLE_SPECTRA_UNOPENED` from attempt 2
therefore remains a true result of its narrower frozen checks; overall spectral
readiness is **`HOLD_POINTING_PROVENANCE_UNRESOLVED`**.

## Candidate continuity and HD 3651

The historical index retains both original investigation classifications and
subsequent independent-follow-up classifications. It is a navigation index,
not a new scientific adjudication or a replacement for full trigger ledgers.

| Latest recorded classification | Cases |
|---|---:|
| RFI or instrumental | 17 |
| Not redetected in partial independent cadence, M14 | 3 |
| Not redetected in complete independent cadence, M16 | 2 |
| Unresolved, independent cadence required | 2 |
| Total | 24 |

The two unresolved cases are **M15 GJ 581 at 1406.118273185 MHz** and
**M33 HD 3651 at 1424.934238382 MHz**. M16 case 1 at 1412.485745177 MHz remains
a possible true detection in M35's conservative counting despite its
non-redetection. No non-redetection is relabelled a physical interference veto.
M37's separate complete 43,883-member retained ledger remains closed with no
unresolved scientific candidate. M43AI's failed result and the reserved M43AF
112+128 inputs remain unchanged.

The fresh HD 3651 check snapshots **12,087 archive target names**, resolves
HIP3093 and checks current primary-target GBT fine-cadence listings. It returns
only cadence **73274**, the original M33 observation. This neither tests the
candidate again nor establishes absence of data at other telescopes, in other
formats or outside that catalogue scope. No GJ 581 availability check was added
to this package; its prior unresolved disposition is preserved.

## Execution and reproducibility

The first HTTPS API attempt was stopped on two HTTPS→HTTP redirects. It read
zero response-body bytes and no HDF5 source. A separately published amendment
used the explicit canonical HTTP metadata API already present in historical
catalogue links; HDF5 object access stayed HTTPS and redirects remained refused.
Both attempts are retained. The cumulative archive source/availability work
used **83 requests, 263,066 response-body bytes and 625.845 s**, below the fixed
limits. Official metadata added one 441-byte response; the pointing catalogue
added one 10,897-byte response. No unattended computation or message was created.

| Published boundary | Commit |
|---|---|
| Initial selection, inventory and metadata protocol | `c0c1e07cc44162b4da8dbf07b39575bfdaefc1f8` |
| Preserved stop and canonical API amendment | `b2067f3e3e6809e903ed9a053807ef8ba2f5d2a4` |
| Candidate/interface register and official-metadata protocol | `f820fbc46c9425c93b2e63d7b5b06428c4187524` |
| Complete metadata publication and bounded pointing protocol | `79b601fae9afa6409e1377436ec5384154429f3a` |

The code is in `scripts/radio_restart_metadata.py`, `radio_hd1461_metadata.py`,
`radio_restart_inventory.py`, `radio_restart_pointing.py` and
`radio_restart_audit.py`. Results are in `results_radio_restart_2026-09-26/`.
The audit reconstructs all six headers offline from retained byte-range
responses and verifies hashes, official metadata and the complete candidate
join. Passing those checks is not scientific qualification of a detector.

## Exact continuation

The current obstruction is **pointing provenance**, not a detector failure or
a negative SETI search. The bounded metadata diagnosis is complete. Do not
repeat it as a new result or replace HD 1461 with another source automatically.

The next information required is an original same-scan header or observing-log
record for `AGBT16A_999_189`, scans 0015/0017/0019, establishing the pointing,
or a documented file-specific conversion explaining these retained coordinates.
Use the exact scan timestamps and catalogue IDs above. Existing publication
authorization is sufficient; no new owner approval is needed for routine work.
No external message is authorized or sent by this continuation.

Once that source binding is resolved, prepare one integrated executable primary
screen and control protocol. The interface inventory identifies the concrete
engineering boundary: the live `source_m43h.extract_remote` entry point and M43
orchestration still bind to HD 156668 and old receipts. Build a new source entry
point with explicit HD 1461 pins while reusing unchanged arithmetic; do not
retarget historical configs. Freeze its band, templates, widths, fresh
calibration, complete end-to-end signal/interference/null panel and numerical
gates before any spectral access. LS8BF and the reserved radio panels remain
unopened. The two-week plan stays active on radio.
