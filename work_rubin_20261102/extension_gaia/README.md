The separate extension selects **2 stellar associations from 104 metadata-prerequisite candidates**. It cannot provide 50 evaluable stars under the frozen rules. No extension science flux has been requested or read by this stage.

The one same-center Gaia DR3 query returned 13,202 sources inside 1.1 degrees in 3,121,898 bytes, succeeding on its first attempt. The candidate 104 came from the fixed one-degree Rubin cone and had already passed the original metadata temporal/quality prerequisites. Gaia association, motion propagation, stellar guards and ranking were unchanged.

Of 104 candidates, 56 had a unique positional association under the fixed 1 arcsec match/no second neighbor within 2 arcsec rule. Only 2 also met the astrometric stellar-evidence guard; 102 candidates were rejected. Association reasons overlap: 41 had no Gaia within 1 arcsec, 16 had unavailable nearest-source motion, and 73 failed the parallax/PM evidence guard. No threshold was relaxed.

| Selection | Exact Rubin DiaObjectID | Exact Gaia DR3 sourceID | Separation (arcsec) | Parallax S/N | Joint PM significance |
|---|---|---|---:|---:|---:|
| 1 | `170587117148176510` | `4992675146868443392` | 0.050939 | 1.898 | 11.161 |
| 2 | `313791827794198596` | `4992867015942886656` | 0.057474 | 2.415 | 191.749 |

Both selected associations pass through proper motion; neither has parallax S/N>=3, so no reliable parallax-distance ranking is assigned. They are ordered by exact numeric Rubin ID. This is an association selection, not a calibrated discovery significance or a flux-evaluability result.

The prior-cohort exclusion set contains 269 Gaia identities: the union of original 433 neighbors within 2 arcsec, original 188 selected counterparts, historical development annotations, and a fresh exclusion-only computation for prior 433 using the same catalog. No candidate needed additional prior-counterpart or duplicate exclusion. The original 188 selection is byte-identical and the extension plus original main totals 190 IDs, below the fixed 500 cap. `main_selected=False` in PRIOR433_RECOMPUTED_CONTEXT refers only to exclusion from this separate extension; it does not revise the original selection.

Independent review passed 77 transport/binding checks, 32 scientific-protocol checks, and 19,326 actual matching checks over 7,089,474 candidate/catalog pairs. The independent angular reconstruction agreed within 1.93e-8arcsec and reproduced both exact selected identities and the exclusion union.

The metadata temporal prerequisites are necessary only: finite flux/error, original baseline precision, source-quality/image review and all frozen science conditions remain unchecked here. All original metadata source withdrawal statuses were unknown. Rubin coordinate reference epochs and covariance are not fully documented; matching uses the original midpoint-time proxy. Annual observer parallax is not applied, missing RV uses zero, and missing distance uses angular-only propagation. Catalog completeness and the 360 arcsec motion margin are conditional, and unresolved or uncatalogued companions are not ruled out.

MAIN_SELECTION.csv SHA-256: `1f63da98d74fabba20297bb15e754d6a14cbe1afc50ba24474fed0888c4fa3e7`. Exact plans, request receipts, catalog bytes, all neighbor evidence, all 104 dispositions, rejects and SELECTION_FREEZE.json are retained. The parent workflow must publish the frozen extension selection and unchanged detector before any science acquisition release.
