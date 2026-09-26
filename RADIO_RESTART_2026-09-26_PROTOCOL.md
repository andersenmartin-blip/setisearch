# Radio restart: frozen metadata selection and source verification

Status: prospective metadata-only protocol, before new remote archive requests.
Owner instruction on 26 September: start the new two-week radio plan and work
as autonomously as possible. This is the first integrated package under that
plan. LS remains paused and its saved restart is unchanged.

## One deterministic pilot choice

Use the original M16 catalogue snapshot, SHA-256
`0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`,
and the already published M36 attribute-only screen. The first remaining
qualifying host after M37 is rank **38, HD 1461 / HIP1499**, cadence **71139**.
The pilot shortlist contains this single sequence. Do not skip it after an
access failure, inspect rank 41, or substitute an attractive old outcome.
Additional pilot sequences need their own fixed selection before any values.

The six exact URLs, all historical attributes, sizes and ETags are in
`config/radio_restart_metadata_20260926.json`. The sequence begins at MJD
57522.691770833335 (2016-05-14), in session `AGBT16A_999_189`. It alternates
HIP1499 / HIP462 / HIP1499 / HIP897 / HIP1499 / HIP947. M43's development
sequence begins at MJD 57470.581099537034 in session `AGBT16A_999_104`.
These are distinct observing dates and sessions, not translated carriers or
interleaved repeats of the development inputs. This does not assert statistical
independence of all telescope noise or interference.

The conservative prior-source register includes every radio HDF5/filterbank
URL in the 69 committed configurations containing such URLs: 236 distinct
URLs, including preflight and reserved inputs. It is a deny-list, not a claim
that every configured source was consumed. None of the six HD 1461 URLs, or
any HIP1499 source URL, occurs there. The earlier M37 selection explicitly
reserved HD 1461. Input file hashes and the full URL/configuration mapping
are retained in `results_radio_restart_2026-09-26/prior_source_inventory.json`.

## Current object verification

Read the current HTTPS cadence-71139 catalogue; its fine HDF5 URL set must
equal the six frozen products. For each product require the pinned size,
strong ETag, attributes, shape, dtype and chunk geometry to match exactly.
Use HEAD and bounded, conditional byte ranges to inspect HDF5 attributes.
The range status must be 206, with exact start/end/total, length and ETag.
Unexpected redirects, source changes, schema failures or ignored ranges stop
that source task. The historical header record is not a current-access receipt.

Eligibility requires a non-overlapping six-scan alternating ON/OFF sequence,
three ON scans on HIP1499, the same telescope/backend and spectral/time geometry,
a start-to-start span at most 0.04 day, and coverage of 1399.65–1425.85 MHz.
This coverage is a metadata compatibility check, **not a frozen search band**.
The new primary screen, extraction band, motion/width bank, calibration and
numerical recovery/control gates must still be frozen before any new spectrum.
No old score threshold or native cache is assumed to transfer to this target.

## Separate HD 3651 availability check

Snapshot the current archive target list. Query all exact normalized HIP3093
and HD3651 aliases for primary-target GBT fine-cadence listings, maximum 2000
rows per query. Hitting the cap is an incomplete check. Preserve all returned
rows. Compare cadence identities with the original M33 cadence 73274.

At most two newly listed cadences may receive header inspection in this package;
if more exist, publish the complete listing and freeze a separate header scope.
Each must have exactly six fine HDF5 products, no shared M33 scan, a distinct
MJD date and the same bounded ON/OFF eligibility. A catalogue absence applies
only to this query scope; it is not proof that no observation exists elsewhere.
No HD 3651 spectral values or candidate metrics may be read here. Any independent
candidate follow-up requires its own frozen hypothesis test.

## Budgets, evidence and stops

The shared remote budget is 32 MiB, 300 requests and 20 minutes; each JSON
response is capped at 4 MiB, each source's metadata reads at 512 KiB and each
request at 25 seconds. Maximum two attempts only for transient timeout/network
or 408/429/500/502/503/504 errors; no permission/identity retry. Independent
pilot and HD 3651 tasks are reported separately, so a technical obstruction in
one cannot be misrepresented as a negative astronomical result in the other.

Preserve requested URLs, UTC times, HTTP headers, byte ranges, returned byte
counts, SHA-256 and base64 bodies, plus parsed catalogue/header snapshots.
Transport metadata reads can include adjacent container bytes; no HDF5 data
element is indexed, decoded, scored or plotted. Whole 15 GB products are not
downloaded. No injections, null calibration or candidate search runs here.

The script requires a published freeze commit and verifies its exact code,
config, protocol and pinned input hashes before remote access. The result
cannot be overwritten. Run once with:

```sh
python scripts/radio_restart_metadata.py --freeze-commit <published-commit>
```

All original radio candidate dispositions remain authoritative. In particular,
M33 remains unresolved; M16's non-redetection is preserved alongside M35's
conservative possible-detection count. M14's partial-cadence non-redetections
are not relabelled physical vetoes. M37 is closed with no unresolved candidate;
M43AI is a closed failed method. The 112+128 reserved M43AF inputs stay unopened.

Publish this protocol, executable script, configuration and source inventory
before remote inspection, then publish the complete outcome and exact next
action under the owner's existing GitHub authorization. No unattended job or
external message is created by this package.
