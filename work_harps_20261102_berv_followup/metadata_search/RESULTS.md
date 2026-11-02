The bounded metadata search **stopped on an ESO query-syntax error**. It did not produce an inventory of additional observations, and the empty `CANDIDATES.json` is not evidence that suitable epochs do not exist.

| Target | Actual outcome |
| --- | --- |
| HD122640 | One POST on 2026-11-02, 10:23:13.938719–10:23:21.545264 UTC; HTTP 400; 370 response bytes; no redirects; no usable metadata rows |
| HD135204 | Not requested: the first-request failure activated the frozen stop rule |

The original response is preserved as `responses/HD122640.vot`. Its VOTable `QUERY_STATUS` is `ERROR`; the server reports an unexpected period and expects the end of a sort expression, a comma, semicolon, `ASC` or `DESC`. This is consistent with a parser rejection of qualified column names in the query's `ORDER BY` clause (`o.t_min`, `o.dp_id`, `p.source_file`), but that explanation has not been tested against the live service. The failed query and its frozen code remain unchanged.

The prospective freeze was published at commit `234562d3619ea894bfd4c8a9b58e7dd002f6f2e8` before the request, with exact remote-byte verification recorded in `ROOT_RELEASE.json` and `PUBLICATION_RECEIPT.json`. `responses/HD122640.REQUEST.json`, `.headers`, `.curl.json` and `.stderr` preserve the request and transport outcome. Curl reported 7.587964 seconds and exit code 0; the executor correctly treated HTTP 400 as failure. The exclusive run/attempt records prevent an accidental repeat.

**Executed totals: one target request, zero usable products, zero header requests, zero science payload bytes and zero label changes.** Both stars' recorded BERV coverage remains unchanged: 2.237910 km/s for HD122640 and 1.714121 km/s for HD135204. All 185 U and 35 M labels are preserved. No widened baseline or origin conclusion follows from this failed request.

This frozen run is closed. A further attempt would require a new, explicit bounded plan and independent syntax/contract review before publication and execution; it must preserve this failed attempt and its consumed request. Do not edit/restart the original executor, silently send HD135204, or begin header acquisition from the empty candidate file.
