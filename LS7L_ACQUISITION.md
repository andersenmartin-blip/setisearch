# LS7L bounded engineering and coordinate inspection

Specified 14 September 2026 after LS7K, before reading engineering samples.
The four exact URLs are inherited from results_ls7k_inputs/inventory.json.
HEAD reports 284,840,640 / 417,271,680 bytes for sector-29 engineering /
quaternions, and 292,800,960 / 415,068,480 bytes for sector 32.

Inspect FITS headers by HTTP byte ranges, retaining original header blocks,
byte offsets, response validators and hashes. Require status 206 and exact
Content-Range. Cap header reads at 16 MB per file and 128 HDUs, and individual
headers at 256 KB. Do not download the four complete files.

After the schema is known, select only camera-4 quaternion/engineering rows
covering the twenty already saved contexts, with at most 60 seconds padding
on each side. The row-selection implementation and relevant field names must
be recorded before extracting those samples. Cap additional data reads at
64 MB per file, individual requests at 8 MB, and request timeouts at 30 seconds.
Missing or ambiguous time/reference/quality metadata remains a documented
limitation. Do not infer target exclusion or camera geometry from a column name.

Coordinate inspection may read the existing calibration arrays, their exporter,
and primary mission documentation. No native residual comparison or outcome-
dependent gain, sign, lag, coordinate or PRF selection occurs at this stage.
The physical response comparison receives its own fixed specification and
source freeze before evaluation. All old experiments and unused sectors remain
closed. Publication is covered by the standing project authorization.

## Acquisition amendment before response specification

The first byte-range walk produced only twelve short headers in several
minutes; engineering telemetry is split into many small HDUs. No pixel-response
outcome has been evaluated. Replace this transport strategy with bounded full
downloads of the same four identified files: at most 500 MB per file and
1,500 MB total, with exact HEAD sizes, 30-second request/read timeouts and four
parallel downloads. The known total is 1,409,981,760 bytes. This permits complete
FITS/header validation and original-file SHA-256 identities. Retain the first
range-read evidence and report the transport change. Only selected closed-
context rows enter derived inputs; whole source files are a reproducible cache.
The earlier range-only restriction is superseded by this explicit amendment.

## Recovered execution, 14 September 2026

The local execution environment was unavailable in the continuation session.
The exact original acquisition code is retained and run through the dedicated
GitHub Actions workflow. First restore the four complete products and audit
their full SHA-256 identities and physical FITS header chains. Publish only
the source inventory, complete header cards, compact schemas, checksums and
logs. No table sample extraction is part of this first stage.

The earlier byte-range attempt's blocks were not present in the recovered
Git tree. Their preservation cannot be verified here; no replacement range
evidence is invented. This does not change the four frozen source URLs.

The second stage must record the exact table and field selection and explicit
time conversion before extracting rows. It may reuse the same original cache,
with hashes checked against the published schema-stage manifest. No native
response comparison begins merely because engineering inputs are available.
