The released header batch stopped at its first canary. Exactly **one request** was made: HTTP 200, 2,639 bytes of HTML, with no FITS primary header or recorded BERV. The January 2018 response contains the error `Invalid format for dp_id ADP.2018-01-21T01%3A01%3A37.761`. The May 2017 job was consequently not requested, as prescribed by the frozen stop rule.

This is a request-serialization failure, not evidence that the exposure or its header is absent. The endpoint echoed the percent-encoded colons literally. The official demo’s URL-only response had used literal colons. The published plan and code used standard URL encoding; that representation is not accepted by this particular endpoint. No retry, redirect, alternative header, catalogue lookup, or whole-spectrum download followed the failure.

The unchanged frozen selector ran once after the batch reached final status and produced **zero payload proposals**. Both targets have zero newly verified BERV measurements. Existing coverage therefore remains:

| Target | Existing exposures | Existing/combined BERV span (km/s) | Span divided by c/R | Payload readiness |
| --- | ---: | ---: | ---: | --- |
| HD122640 | 14 | 2.2379098704629 | 0.8584593382373666 | Not met |
| HD135204 | 15 | 1.714121120020998 | 0.6575346495288243 | Not met |

The fixed readiness threshold is combined span strictly greater than 2.6068909391304347 km/s. These are descriptive planning scales, not origin classifications or detection-power estimates. The second target had no eligible metadata candidate in the bounded query; neither its wider archive coverage nor the existence of other epochs is ruled out.

`HEADER_RESULTS.json`, the exact response bytes, and the individual request receipt preserve the failure. `EXTREME_SELECTION.json` records the empty proposal and both unchanged benchmark spans. Frozen code and PLAN hashes were rechecked and remain unchanged. Any correction preserving literal colons must be made in a separate prospective plan/release; none is executed or authorized by this result file.

This follow-up is outside the earlier 300-spectrum survey. No new spectral arrays were requested or interpreted, and previous scientific dispositions remain unchanged. Cost remains 0 DKK.
