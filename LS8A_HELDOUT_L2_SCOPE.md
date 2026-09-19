# LS8A — held-out CHEOPS L2 transfer preflight

Specified 19 September 2026 after the LS7X/LS7Y/LS7Z branches were closed.
This is a prospective transfer test of the **unchanged LS7X L2 screening
method** on an unused public 55 Cnc visit.

## Selection fixed before any new L2 row is read

The already published LS7R archive visit inventory contains the retained March
2020 pilot plus later public 55 Cnc visits. Select the **chronologically earliest
public 55 Cnc visit after the March 2020 pilot**. No score, light curve,
aperture behavior or image value enters this choice.

That deterministic rule selects:

- archive visit id: `100006000301`
- observation request: `1000060003`
- OBSID: `1300462`
- target: `55 Cnc`
- observation start: `2020-12-01T14:06:00`
- observation stop: `2020-12-02T17:27:00`
- expected latest revision: 3
- expected file key: `CH_PR100006_TG000301_V0300`

If that exact file key or DEFAULT L2 product is unavailable, stop and report
the metadata obstruction. Do not substitute the next visit.

## Frozen transfer method

If metadata preflight succeeds, reuse the LS7X primary rule unchanged:

- official DRP DEFAULT-aperture `SCI_COR_Lightcurve` only;
- durations: 1, 2, 3 consecutive rows;
- 12 sideband rows before and 12 after;
- two-row guard on each side;
- STATUS==0 and finite FLUX/FLUXERR eligibility with FLUXERR>0;
- same cadence-gap rule relative to the visit's declared `TEXPTIME`;
- same unweighted straight-line sideband baseline;
- same MAD/FLUXERR screening scale;
- positive threshold +8.5 and negative control -8.5;
- same overlap/one-row clustering rule;
- no aperture, threshold, duration, sideband or guard retuning.

The implementation must reuse the already audited LS7X scoring module or an
exactly verified generalization. Any cadence-dependent arithmetic uses the new
visit's declared `TEXPTIME`; this is an input value, not a tuned parameter.

## Metadata-only first stage

Before any table row is opened, acquire only FITS headers under the same strict
range discipline as LS7X. Record file identity, ETag, size, product/schema
versions, table row count/row width/columns, DEFAULT aperture, NEXP, EXPTIME and
TEXPTIME.

No L2 table data bytes are permitted in this preflight. A separate freeze/run
is required before evaluating the held-out rows.

## Interpretation

LS8A is a **method-transfer/control study**, not a new SETI candidate search
with tuned parameters. A positive screen is an L2 excursion requiring the same
instrumental follow-up discipline used for LS7X. A null or positive result does
not by itself qualify the detector or establish a false-alarm probability.
