# Milestone 19 header-screen result

Status: **47 UMa d / HIP53721 CADENCE `--73992` SELECTED**.

GitHub Actions run `32584222734` completed the frozen header-only screen.
Artifact `9478611462` (`milestone-19-header-screen`) has digest
`sha256:295157e4bca3478b2f9a3e36a59fce9c8d2834f447593be4ba1bff2fd60290b9`.
Its internal manifest verifies `header_screen.json` at
`20ced66ce1b0200d18df3c1a473c57f4a594b5367db5a1448889999cfe02bec1`.
No HDF5 spectral dataset value was read.

## Screen outcome

| Frozen rank | Target | Qualifying L-band cadences | Outcome |
|---:|---|---:|---|
| 6 | HIP79755 / HD 147379 b | 0 | S-band only |
| 7 | HIP43587 / 55 Cnc d | 0 | One L-band cadence had an incomplete final scan; the other was S-band |
| 8 | HIP53721 / 47 UMa d | 1 | Selected |
| 9 | HIP32769 / HD 48948 d | 0 | S-band only |
| 10 | HIP78459 / rho CrB c | 1 | Qualifies but loses frozen rank order |

The L-band 55 Cnc sequence had five scans with 16 time integrations but only
7 in the sixth scan. It therefore failed the predeclared compatible-geometry
rule even though its frequency coverage was sufficient.

## Selected cadence

- archive target: `HIP53721`
- planet working template: 47 UMa d
- cadence: `http://seti.berkeley.edu/opendata/api/get-cadence/--73992`
- first scan: 2016-07-09 00:31:28 UTC, MJD 57578.02185185185
- sequence: Hip53721, Hip52647, Hip53721, Hip52881, Hip53721, Hip53076
- elapsed first-to-last scan start: 1,756.0 s
- common HDF5 shape: 16 x 1 x 322,961,408 float32 values
- integration time: 18.253611008 s
- channel width: 2.793967724 Hz
- header frequency coverage: 1023.925784-1926.269531 MHz
- conservative full-projection periastron drift bound at 1425 MHz:
  0.00031534 Hz/s

All six products responded without header errors, supported HTTP byte ranges,
had matching geometry, and covered the complete guarded search range.

## Next boundary

Selection does not authorize a spectral read. The official target record must
first be frozen, followed by a successful 630-case extraction-coverage proof
and a separate preregistration of the blind search.
