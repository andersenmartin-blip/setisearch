# Rubin access and development pilot — 2 November 2026

**Real Rubin alert photometry was retrieved for all 20 frozen development objects:** 259 distinct source detections, plus 326 distinct forced measurements for 14 of those objects. All 585 rows provide direct science flux and a positive formal flux error. The source history spans **26 June–31 October 2026 UTC**. This is an access/development sample, not the main stellar-dimming search, and it establishes no technosignature candidate or calibrated null result.

The official Fink/Rubin API returned LSST schema versions `lsst.v10_0`, `lsst.v11_0` and `lsst.v11_1`. The source observations are marked `ddf_elaiss1` or `pairs_ri_33.0`; all requested source injection flags are explicitly false. These are records from the public Rubin service, not a ZTF substitution or locally generated simulation. Original alert-packet bytes are not part of this download; API responses and representative original FITS cutouts are preserved.

## Selection and separation from the main sample

[METADATA_PLAN.json](METADATA_PLAN.json) specifies a metadata-only cone centered at the Fink documentation's example coordinates, RA 8.986275°, Dec −42.709834°, radius 1,800 arcseconds, with the approved October 2026 time window and `kind=across`. The query returned 433 distinct object IDs. The 20 smallest positive IDs in exact integer order were fixed in [DEVELOPMENT_FREEZE.json](DEVELOPMENT_FREEZE.json) and [DEVELOPMENT_SELECTION.csv](DEVELOPMENT_SELECTION.csv) before any development flux retrieval. Selection did not depend on flux, anomalous behavior or Gaia distance.

Two API limitations are explicit. A request with `n=1000`, suggested by the Swagger default, returned HTTP 400 and a maximum-100 message. The otherwise unchanged metadata query with `n=100` succeeded but returned 433 distinct objects. Both responses are retained; no completeness or effective pagination guarantee is inferred. The October statistics query returned rows for 30 and 31 October; that response is not evidence that only two October nights exist globally.

The other 413 objects remain a **metadata-only, Gaia-unverified candidate inventory**. Five saved source-history metadata queries return 3,596 rows covering all 413 identities, with no flux or anomaly-score fields. Their identities, positions, times, bands and catalog annotations may inform a separately frozen main selection. The 20 development identities and associated Gaia/nearby counterparts must be excluded from that sample. Gaia annotations such as `Fail` and `nan` are retained as missing; an annotation alone is not an independently verified unambiguous stellar match.

## What is usable now

| Retrieved product | Objects | Distinct rows / products | Scope |
|---|---:|---:|---|
| `sources` history | 20 | 259 detections | Direct science, template and signed difference flux, errors, times, filters, detector/visit and source flags |
| Object-position forced history | 14 | 326 measurements | Direct science and signed difference flux, errors, times, filters and detector/visit; no returned quality flags |
| Science/template/difference FITS cutouts | 2 | 6 products | Frozen latest metadata source ID for the first two development objects; all six readable |

The six cutouts contain a 30×30 primary image, `UNCERT` with `UTYPE=VarianceUncertainty`, a 30×30 `MASKPLANE`, and a PSF image. Primary headers declare `BUNIT=nJy`. Availability has only been checked for these six products; this is neither full image review nor proof that cutouts exist for every source.

[DEVELOPMENT_OBJECT_INVENTORY.csv](DEVELOPMENT_OBJECT_INVENTORY.csv) and [DEVELOPMENT_BAND_COVERAGE.csv](DEVELOPMENT_BAND_COVERAGE.csv) retain per-object and per-band coverage. Ten development objects have at least one source-photometry band with three positive pre-October measurements; thirteen have such a forced-photometry band. These are sampling descriptors, not adopted baseline-quality criteria or claims that those objects are evaluable stars.

## Photometry and quality rules for downstream work

Direct `scienceFlux/scienceFluxErr` are available in both streams and expressed in nJy. Source-position science photometry and object-position forced photometry stay separate. Signed `psfFlux` measures difference-image flux; adding it to template flux is not an exact reconstruction of science flux. No magnitude or dimming decision is computed here.

Original times remain `midpointMjdTai`; UTC inventory dates use Astropy's explicit `Time(..., format='mjd', scale='tai').utc` conversion. IDs are parsed using Python `json.loads(..., parse_int=str)` and preserved as decimal strings. Source, forced-source, visit and object identities never pass through floating point or JavaScript numbers. Each stream has zero duplicate measurement IDs in this response; overlap between source and forced observations is expected and is not new telescope exposure.

Most requested critical source flags are explicitly false in this small sample, while `isDipole` is true for 21 source rows. The supplemental metadata request confirms global `pixelFlags` and central interpolation flags false for all 259 source rows. `timeWithdrawnMjdTai` was requested but absent in every source and forced row; absence is retained as unknown, not interpreted as nonwithdrawn. Forced measurements have no returned quality flags. Reliability scores are retained for documentation but do not validate a detection.

## Provenance, limits and reproduction

An [independent audit](independent_audit/AUDIT.json) passed 9,650 checks of exact selection/identities, byte hashes, all coverage inventories, the metadata-only remainder and FITS planes. It does not independently validate physical origins or Gaia associations.

Every network payload has a separate request/response receipt with exact request parameters, status, elapsed time, byte count and SHA-256. The initial Swagger request has its own receipt. [DEVELOPMENT_VALIDATION.json](DEVELOPMENT_VALIDATION.json) records exact stream counts, schema versions, flag availability and input hashes. [CUTOUT_VALIDATION.json](CUTOUT_VALIDATION.json) describes the six FITS structures. No account, paid service, alternate Rubin provider or ZTF data was used. Local setup errors before network access are recorded separately; the sole unsuccessful data-API request was the preserved HTTP 400 limit error.

Run `python3 validate_development.py` to recreate the tabular inventory from the retained raw JSON with Astropy installed. It performs no network request or dimming search. `access.py` is the bounded, logged transfer utility; reproducing acquisition may return a newer service state, so the saved raw responses define this checkpoint. Downstream science methods, injection tests and main-data selection require a separate freeze.

## Primary documentation

- [Fink/Rubin API and Swagger schema](https://api.lsst.fink-portal.org/), downloaded as `docs/swagger.json`.
- [Object/source API and 64-bit identities](https://doc.lsst.fink-broker.org/services/api/diaobjectid/).
- [Cone search and time-boundary behavior](https://doc.lsst.fink-broker.org/services/api/conesearch/).
- [Photometry definitions](https://doc.lsst.fink-broker.org/data/photometry/).
- [Forced-photometry API](https://doc.lsst.fink-broker.org/services/api/forced_photometry/).
- [Cutout data and FITS access](https://doc.lsst.fink-broker.org/services/api/imagesearch/).
- [Field provenance and schema API](https://doc.lsst.fink-broker.org/services/api/definitions/).
- [Known association, history and field limitations](https://doc.lsst.fink-broker.org/data/issues/).
- [Quality and reliability caveats](https://doc.lsst.fink-broker.org/data/quality/).

The official documentation distinguishes source-position and object-position photometry, warns about split nearby object identities and incomplete fields, and advises against trusting the reliability score by itself. None of those limitations is resolved by obtaining a successful HTTP response.
