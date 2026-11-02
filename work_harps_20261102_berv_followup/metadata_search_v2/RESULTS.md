The corrected bounded search returned **18 additional single-exposure metadata candidates for HD122640**. It returned no HD135204 rows matching the frozen query. Both responses completed normally; no science spectra or BERV values were acquired in this stage.

| Target | Joined rows / distinct products | Metadata candidates | Observation dates | HTTP / response bytes |
| --- | ---: | ---: | --- | --- |
| HD122640 | 18 / 18 | 18 | 20–22 May 2017; 16 and 18–20 January 2018 | 200 / 35,157 |
| HD135204 | 0 / 0 | 0 | None returned under this contract | 200 / 21,438 |

HD122640 contributes 10 May observations and 8 January observations, spanning seven distinct observing dates and two month numbers. These dates come from observation-start MJD, not the dates embedded in ADP product IDs. All 18 products have distinct new raw progenitors, a recorded public release, `n_obs=1`, `multi_ob='S'`, the expected main science category, and matching canonical target names within the frozen coordinate guard. There are no duplicate raw exposures or excluded returned products. The identity checks remain internal metadata checks, not independent absolute astrometry or photon-origin certification.

The two responses were received on **2026-11-02 between 10:31:05.944784 and 10:31:29.196608 UTC**. Both contain `QUERY_STATUS=OK`, with fewer than 1,000 rows and no overflow, redirects or transfer-limit failures. Their combined size is 56,595 bytes. `responses/` preserves the original VOTables, HTTP headers, curl diagnostics, request receipts, parsed rows and product inventories. `CANDIDATES.json` retains the exact 18 candidate product/raw identifiers and metadata.

This amendment was published before execution at commit `4ee21b47d332ab467dbb4c3d452f07a71882dddb`. Its freeze SHA-256 is `156584f21aeba1039cc0d34e8ec228786061e476a113f42075f95a3bc6265fd0`; `ROOT_RELEASE.json` and `PUBLICATION_RECEIPT.json` record the exact remote-byte verification. The unchanged first attempt remains in `../metadata_search/`: one HTTP 400 response and zero usable rows. **Total continuation usage is three target requests: one original failure and two successful amended requests.** No further metadata attempts are authorized by either completed plan.

The new dates provide a concrete route for a **separately frozen header-only BERV and identity check**. Under the root's subsequent latest-observation-per-month-number rule, only January and May are represented, so the proposed next header selection contains two products: `ADP.2018-01-21T01:01:37.761` and `ADP.2017-05-23T01:01:52.459`. The header acquisition plan must independently reproduce and freeze that choice; these products are not scientifically admitted here.

BERV has not yet been measured for any of the 18 new products. The prior verified spans remain **2.237910 km/s for HD122640 and 1.714121 km/s for HD135204** until a subsequent header stage establishes otherwise. No claim about widened BERV coverage, astrophysical origin or laser significance follows from this metadata result alone. The HD135204 empty response applies only to the exact public, single-exposure, time, naming/coordinate and provenance query; it is not proof that the star has no other observations.

All **185 U / 35 M** labels and the 300-exposure scientific cohort remain unchanged. This stage adds zero science-payload bytes and performs no classifier or spectral-array analysis. `RESULT_HASHES.json` records the saved outputs and verifies that every frozen input and historical source file is unchanged.
