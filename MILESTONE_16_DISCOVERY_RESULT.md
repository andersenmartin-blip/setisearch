# Milestone 16 metadata-only discovery result

Status: **FIVE UNIQUE HOSTS ADVANCE TO HEADER-ONLY SCREEN**.

GitHub Actions run `32506360670` queried catalogue tables only. Artifact
`9455425040` (`milestone-16-target-discovery`) has digest
`sha256:a5e11baab62e32d33da9aaf3b27855d2103a0ed0168a0abcecd389de820dbfc7`.
No telescope product was opened and no spectral value was inspected.

## Discovery counts

- GBT fine L-band primary-target cadence rows: 1,329
- official composite planet rows with complete orbit and host astrometry: 803
- matched non-excluded planet/target pairs: 68
- pairs below the fixed 1 Hz/s acceleration-smearing bound: 42

## Frozen top five unique hosts

| Rank | Archive target | Planet template | Distance (pc) | Period (days) | Conservative drift upper bound at 1425 MHz (Hz/s) | Cadence records |
|---:|---|---|---:|---:|---:|---:|
| 1 | GJ876 | GJ 876 e | 4.675 | 124.26 | 0.0912 | 1 |
| 2 | HIP114622 | HD 219134 h | 6.531 | 2247.0 | 0.00262 | 5 |
| 3 | HIP65859 | GJ 514 b | 7.618 | 140.43 | 0.2660 | 1 |
| 4 | HIP109388 | GJ 849 b | 8.801 | 1925.31 | 0.00250 | 2 |
| 5 | HIP83043 | GJ 649 b | 10.380 | 600.1 | 0.0138 | 1 |

The acceleration bound is a conservative periastron proxy, not a measured
drift. For comparison, the same calculation gives about 5.58 Hz/s for GJ 581
b and 0.61 Hz/s for the earlier GJ 687 b model. The new ranking therefore
directly addresses Milestone 15's loss of completeness at high acceleration.

## Next boundary

Only these five unique hosts may enter the next header-only screen. That screen
will open the catalogue-listed HDF5 products only to read attributes, geometry,
object identity, range support, timing, and frequency coverage. The nearest
host with at least one complete compatible six-scan cadence covering every
established band will advance. No spectral dataset value may be read before a
separate target-specific preregistration.
