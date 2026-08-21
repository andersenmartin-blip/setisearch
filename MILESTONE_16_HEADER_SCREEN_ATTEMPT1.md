# Milestone 16 header screen attempt 1

Status: **TECHNICAL NO-RESULT — FILTER-DECORATED CADENCE URLS RETURNED ZERO
RECORDS**.

GitHub Actions run `32506931230` completed successfully as software, but every
one of the ten discovery-supplied cadence URLs returned an empty catalogue
record list. Artifact `9455606396` has digest
`sha256:e7eba37dd35bbe31040d6a99234e3d77413ae901a21e618490c455586d71d6d9`.

The discovery API encoded its active query filter in URLs such as
`-grades:fine;-76697`. The cadence endpoint returned HTTP 200 and an empty
result for that decorated route. Consequently the attempt found no HDF5 URLs,
opened no telescope product, read no HDF5 header, and inspected no spectral
value.

This is not evidence that the shortlisted cadences are absent or ineligible.
The correction retains the same ten terminal cadence IDs and the same frozen
ranking, but canonicalizes each route to the archive's unfiltered `--<id>`
form before repeating the header-only screen.
