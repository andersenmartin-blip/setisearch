# LS7K input-inventory correction

14 September 2026. Original source commit:
315adb475dfe66e41546a709da8eb6673dc0e6c5.
[Initial run 34828116310](https://github.com/andersenmartin-blip/setisearch/actions/runs/34828116310).

Acquisition restored all 8,020 timing rows, all 50 PRFs and four engineering
product links. The independent audit stopped at the header-value equality
check; no input result was published as complete.

The serializer used str(value) for FITS values outside JSON's primitive
types. An undefined FITS header value can therefore contain a process-specific
object representation. Encode that missing value as JSON null, and compare
it to the actual Undefined type in the reopened FITS header.

The corrected execution must restore the first run's artifact and demonstrate
that every changed header value is exactly this undefined-value encoding,
all other header fields are identical, all fifty PRF hashes are unchanged,
and all timing arrays agree exactly. The resulting AUDIT.json records every
affected keyword. If those checks fail, this explanation is not accepted and
publication remains blocked.

This is a metadata-serialization correction. Acquisition scope, mission file identities,
selected cadence rows and scientific stopping rules are unchanged. There is
no detector evaluation or changed LS7J result. The original failure logs and
source commit remain public; the workflow artifact preserves the first input
packet.
