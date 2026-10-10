# Session31/BLC77: første opaque prefixtransport

Familien fastholder de seks observerede fine0000-URL'er fra den uforanderlige cadence-JSON. Rå HTML er ikke længere bevaret; dens tidligere bodyhash og observationslinje er metadataevidens. Dette er ikke en global certificering af urørt arkiv, kvalificerede OFF-kontroller eller beskyttede rammer.

Efter offentlig kildefrysning, source-only peer og rodens sene admission må én kørsel foretage højst seks HEAD og seks præcis `bytes=0-8191` GET. HEAD skal være200 med stærk quoted ETag, identisk URL og længde mindst8192. GET skal være206, identisk ETag/URL, `If-Match`, korrekt Content-Range/Content-Length og identity encoding. Ingen redirect, retry, adaptiv metadataopfølgning, index eller signalpayload må hentes. Alle49.152 reserverede BODY-bytes forbliver konservativt debiteret også ved fejl; gamle tabte BLC66-bytes genhentes aldrig.

Prefixbytes behandles kun som opaque bytes. Ingen HDF5/NumPy/parser importeres, og form, attributter, filter, kanalgrid og midpoint forbliver unset. En senere særskilt frosset cachefase skal validere faktiske metadata og kendte beskyttelsesrammer, før enhver signaladgang.

Hvert faktisk returneret stykke registreres i BODY-tælleren og hukommelsen, derefter udskrives det som flushed JSON med source_id, offset, længde, SHA256 og base64 (højst1024 rå bytes/stykke), før den lokale filskrivning. HEAD/GET-observationer og afsluttende kvitteringer udskrives også med eksakt JSON-serialiseringspin. Launcheren relæer stdout til det overordnede værktøj før lokal logskrivning og måler den faktiske child med wait4 gennem interpreter-close. Roden skal tilbageholde hele streamen i V8, verificere kontinuerlige offsets/stykker/helhash og straks checkpoint'e seks prefixer samt HEAD/GET-bevis, før cacheparseren starter. Udsendt serialisering er ikke i sig selv en påstand om vellykket lokal lagring.

Kaps:60 CPU-sekunder samlet launcher+child;600 vægsekunder;512MiB pr.proces;32MiB output;12GiB delt workspace. Stdout fra child er særskilt begrænset til786.432B, stderr65.536B. Launcherens resourcePASS er adskilt fra faktisk child-exit og prefixtransportstatus.

Roden udfylder ROOT_ADMISSION efter sourcefrysning. Exactlate JSON-binding: schema SETI_VISIT2019_S31_BLC77_ROOT_INITIAL_PREFIX_ADMISSION_V1; status PASS_FINITE_PREFIX_ONLY_NO_REPLAY_ROOT_ADMISSION; initial_prefix_only_authorized=true; scope_sha256/wrapper_sha256/source_public_freeze_commit; peerpath results/radio_visit2019_s31_blc77_headers_20261010/proofs/INITIAL_PREFIX_SOURCE_ONLY_REVIEW.json med source-onlyPASS og code/scope/launcherpins; historical_request_eligibility_sha256; fresh_ownership_and_request_check_pin{path,bytes,sha256}. Den friske JSON skal indeholde stage_id, exact_source_URLs (de seks i fast rækkefølge), known_exact_source_URL_hits=[], finite_scope_only_not_global_registry_certification=true. Alle eksisterende protection/owner/no-refund/workspace/budgetfelter skal ligeledes passe.

Første actualkørsel (alle placeholderpins skal erstattes af rodens offentliggjorte eksakte pins; absolutte stier):

```sh
/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python /workspace/scratch/a8d1e29996d0/setisearch_fullpower/tools/radio_visit2019_s31_blc77_headers_20261010/launch_once.py --expected-launcher-sha256 LAUNCHER_SHA --expected-wrapper-sha256 WORKER_SHA --expected-scope-sha256 SCOPE_SHA --public-freeze-commit SOURCE_COMMIT --launcher-public-freeze-commit SOURCE_COMMIT --expected-root-admission-sha256 ADMISSION_SHA --root-go-header-metadata-only
```

Launcher og worker er inerte ved import. Genstart/resume efter eksisterende initial/command_attempt er forbudt. Fuld frisk source-only gennemgang og offentlige readbacks skal være afsluttet før netværk. Workerkoden kan fortsætte de øvrige endnu ikke kaldte faste kilder efter en almindelig per-source HTTP-fejl, men lokal bevarings-/resourcefejl stopper nye requests. Ingen faktisk kørsel er foretaget under kildeforberedelsen.
