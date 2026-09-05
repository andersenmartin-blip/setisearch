# LS5 Kepler-160 archival S-band screen

The selected sequence is --813641, observed 2020-06-14: scans 0025–0030,
alternating ON/OFF as independently specified by Perez et al. (2020) and the
archive catalogue. Search 1.8–2.8 GHz using the unchanged LS1 detector:
4, 8, 16, 32, 64 second templates; native-channel aggregation 1024;
widths 1, 4, 16, 32, 64 aggregate bins; ON threshold 8, adjacent OFF threshold
6, frequency overlap 0.5, and retention cap 2048 per scan. Scores are screening
statistics. Any truncation invalidates disposition. There is no threshold tuning.

The exact URLs, sizes, sampling, source headers and implementation hashes are
in config/ls5_kepler160_s_light_sail.json. Expected medium download is
3,510,634,236 bytes across six files, processed sequentially with derived
checkpoints and deletion of each raw file. No HTR samples may be read until a
survivor and a separate follow-up freeze. Header source names are identical
across scans; metadata role mapping is frozen independently of spectral values.

This sequence is qualified with unresolved pointing: its final designated ON
header is 0.248 degrees from the published target coordinates. No stellar
attribution or sensitivity follows from the labels alone. The nominal b/c
projected separation is 31.912 stellar radii; this is not a close conjunction.
Known transit-timing variations and unknown mutual node are not represented by
the approximate linear model. Preserve the earlier failed source-name preflight.

Perez et al. already searched these observations for narrowband and short
artificially dispersed pulse signals. This run tests longer broadband envelopes
within this project. It makes no priority, detection, calibrated sensitivity,
or population-rate claim. See LS5_POINTING_AMENDMENT.md for source links.

The configuration and implementation are committed and publicly published before
spectral contact. Completed LS1–LS4 records remain unchanged.
