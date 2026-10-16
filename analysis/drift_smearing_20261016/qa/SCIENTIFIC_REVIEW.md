# Independent scientific review

This check reconstructs a frozen descriptive calculation from saved raw crops.
It does not admit a new candidate, select a new drift, change a threshold, fit a
response to the data, or estimate a false-alarm probability.

The response is an assumed unit-area intrinsic box of one native channel,
convolved with a uniform linear drift sweep over one full 18.253611008-second
integration. Its channel masses follow from integrating that convolution over
each native channel bin. The instrumental channel filter and an actual source's
intrinsic line shape have not been measured. In particular, this one-channel box
is an explicit idealization; it is not a literal monochromatic delta function.

The original carrier, drift, zero phase, and four source rows remain fixed.
Removing the nearest-even central bin from every row removes that bin's direct
weighted contribution. It does not erase the original selection of the tracks,
possible frequency/time noise correlations, or shared baseline and normalization
dependence. Each median501 baseline can depend on the central raw sample through
its order statistic, and the original saved normalization was fitted using the
original data. The central mask therefore provides a useful morphology check,
not statistical independence from the original search.

The unit-L2 denominator treats kernel coefficients algebraically. It does not
establish a unit-variance null distribution: channels can be correlated, local
median baselines overlap, saved robust normalization is estimated, controls
share these estimates, and origins were selected after the primary search.
These values must be named weighted standardized sums, not calibrated SNRs.
Control ranks, differences, and extrema cannot be read as p-values.

All nine tracks and all six original ON/OFF contexts come from one historical
2017-04-28 visit already exposed to previous analyses. They are not six
independent observing visits or new confirmations. Acquisition roles and sky
directions remain those of the source records. Frozen extrapolation into the
other contexts does not establish sky origin, and sensitivity can change if a
real source's drift is not constant over the gaps.

Positive energy in the modeled neighboring bins would support agreement with
this particular broad line morphology. It would not distinguish a celestial
transmitter from terrestrial interference or an instrumental feature. A low or
negative neighboring sum weakens agreement with this assumed sustained-line
model, while leaving other temporal or spectral source shapes untested.

The QA reconstruction verifies arithmetic, saved source identities, mask
placement, complete coverage, and sums. It cannot validate unobserved telescope
data, the astrophysical nature of the original peaks, or a discovery claim.
