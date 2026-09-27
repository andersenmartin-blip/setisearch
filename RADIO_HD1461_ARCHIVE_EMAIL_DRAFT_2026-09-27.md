# HD1461 original metadata request — unsent draft

**Status: UNSENT.** No email, helpdesk ticket or other external message has
been sent. The owner's current instructions prohibit external messages.

**To:** bsrc@berkeley.edu

**CC:** none

**Subject:** Original pointing metadata for AGBT16A_999_189, HIP1499 scans 0015/0017/0019

This institutional address is published on the official
[Berkeley SETI collaboration page](https://seti.berkeley.edu/jobs.html),
checked 27 September 2026. It is a general routing contact, not a confirmed
archive helpdesk or named custodian. The message asks for routing explicitly.

---

Hello Berkeley SETI team,

Could you please route this metadata question to the person responsible for
Breakthrough Listen's GBT data archive?

For the SETIsearch project, I am checking the pointing provenance of the public
HIP1499 / HD1461 observations in session AGBT16A_999_189 on 14 May 2016.
The three ON files in the holding directory are:

| Scan | HDF5 header start, UTC rounded to second | Filename |
|---|---|---|
| 0015 | 2016-05-14 16:36:09 | `spliced_blc0001020304050607_guppi_57522_59769_HIP1499_0015.gpuspec.0000.h5` |
| 0017 | 2016-05-14 16:47:23 | `spliced_blc0001020304050607_guppi_57522_60443_HIP1499_0017.gpuspec.0000.h5` |
| 0019 | 2016-05-14 16:58:37 | `spliced_blc0001020304050607_guppi_57522_61117_HIP1499_0019.gpuspec.0000.h5` |

The retained HDF5 declinations are approximately −8.62416 degrees, about
34.23 arcminutes from the retained catalogue direction, −8.0536206 degrees.
RA is approximately 0.31175 hours. This is a provenance discrepancy, not a
claim that the telescope was physically mispointed or that a signal was found.

Would you be able to provide, or point us to, original RAW/FIL headers or
telescope GO/observing records for these three scans? A metadata-only extract
would suffice if it identifies the original file/session/scan and preserves
the original coordinate bytes, units, frame/equinox/epoch and timestamp
convention. Please distinguish commanded from measured pointing where present.
A filename/checksum or other verifiable link to the original record would help.

Alternatively, a documented conversion actually used for these exact files,
including its version/command and original coordinate inputs, could resolve
the discrepancy. Generic converter source alone cannot identify what happened
to these files.

The public GBT progress sheet lists HIP1499 at −8.053611 degrees with an L-band
date of `2016-05-14 16:58:31`. Does that row originate from a target catalogue,
a commanded position, or a telescope record? Its scan and time convention are
not stated in the returned row, so we have not used it to correct the HDF5 values.

We need only provenance metadata at this stage. If the original records are
unavailable, information on their retention or the appropriate custodian would
also help.

The [technical specification](https://github.com/andersenmartin-blip/setisearch/blob/b2ad32adf074b3ac85be92838f8b1a4348f6ab51/RADIO_HD1461_PROVENANCE_REQUEST_2026-09-26.md)
and [pinned file identities and retained attributes](https://github.com/andersenmartin-blip/setisearch/blob/b2ad32adf074b3ac85be92838f8b1a4348f6ab51/config/radio_hd1461_source_preparation_20260926.json)
contain the exact URLs and values.

Thank you,
Martin Andersen

---

The official [GBO help page](https://greenbankobservatory.org/portal/help/)
also links [GBO/NRAO Helpdesk](https://help.nrao.edu/). This is a separate
possible routing path, not an additional recipient or an opened ticket.
No login or helpdesk submission was attempted.
