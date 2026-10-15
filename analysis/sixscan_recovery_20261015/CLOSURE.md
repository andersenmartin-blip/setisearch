# SETI: afslutning af den ikke genfundne seks-scan-kørsel

Den 14. oktober-kørsel lukkes med **`UNKNOWN_UNRECOVERED`**. De oprindelige
205 syntetiske identiteter og ni allerede eksponerede bånddiagnostikker pensioneres
og køres ikke igen. Der foreligger ingen genfundne måleresultater, som kan bruges
til at godkende metoden eller beregne en succesrate.

Efter gendannelse af arbejdsmiljøet manglede de numeriske output, claim-filer,
faseafslutninger, børneprocessernes ressourcebilag og den uafhængige numeriske QA.
En lokal gennemgang er bevaret i `LOCAL_RECOVERY_AUDIT.json`. Root-agentens
fjernkontrol fandt forskningsgrenen ved det publicerede GO og fandt ikke et nyt
resultatarkiv ved en præcis titelsøgning. Disse afgrænsede søgninger beviser ikke,
at ingen ukendt kopi kan eksistere andre steder.

Kildekoden kan derimod genfindes: de 20 publicerede filer er gendannet separat fra
det ufuldstændige lokale stadium. Alle 17 SHA-256-pins i den publicerede `SCOPE.json`
stemmer byte for byte. Det dokumenterer den fastlåste metode, ikke dens udfald.

| Registrering | Status |
|---|---|
| Præregistrering | `bc3a42f7d99dfa19af3070b11e8eb7cafa11984f` |
| GO | `101138540dee6c01b40703b6789c5b3c283c613d` |
| SCOPE SHA-256 | `8bb84b8cd8f0a6756523139bff8b8869e1a4ad478a07d84004d1c199cf53e077` |
| Syntetiske slutpunkter | 205 primær- og 205 QA-slutpunkter `UNKNOWN_UNRECOVERED` |
| Eksponerede slutpunkter | 9 primær- og 9 QA-slutpunkter `UNKNOWN_UNRECOVERED` |
| Metodens integritets- og fælles resultatkrav | Ikke etableret |

Den seneste rapporterede fremdrift i samtalen var cirka 14. oktober kl. 18:43 UTC:
16 støjreferencer var meldt afsluttet med exitkode 0, fire var i gang, og 43 var
endnu ikke indsendt i dette øjeblik. Den afrundede rapporterede CPU-tid var
2.592,180 sekunder. Dette er et tidligere øjebliksbillede. Det fortæller ikke,
hvor langt processen eller den ventende hjælper senere nåede, og er ikke en
genfundet slutafslutning eller et numerisk kontrolresultat.

`CASE_STATUS.csv` indeholder alle 205 syntetiske identiteter og deres oprindelige
seed-hash. `EXPOSED_STATUS.csv` indeholder de ni historiske bånd. Alle målte felter
står tomme. Manglende dokumentation tælles hverken som en målt nulobservation,
en fejlmåling eller `NOT_RUN`.

| Syntetisk familie | Fastlagt antal | Genfundet slutresultat |
|---|---:|---|
| Støjkalibrering | 63 | Ukendt |
| Stærke signaler | 14 | Ukendt |
| Driftspunkter | 48 | Ukendt |
| Matchet interferens | 24 | Ukendt |
| Uafhængige nulforløb | 32 | Ukendt |
| Enkelt-række-transienter | 12 | Ukendt |
| Nærliggende OFF-forurening | 12 | Ukendt |

Hele det gamle loft på **90.000 CPU-sekunder** bevares som en konservativ,
uafstemt historisk debitering. Det er en regnskabsmæssig reservation; det er ikke
en påstand om 90.000 målte CPU-sekunder. De 1.000 sekunder til metadata og levering
er allerede indeholdt i beløbet. Ingen gammel kapacitet frigives, refunderes
eller tildeles igen. Den tidligere rapports afrundede delsum kan ikke bruges
til at beregne en restkapacitet.

Fortsættelsen forberedes som en særskilt bank, `SETI_SIXSCAN_BURST_20261015_RECOVERY_V1`, med
samme erklærede geometri og videnskabelige regler, nye identiteter og seeds,
ny præregistrering og en særskilt begrænset ressourcetildeling. Denne afslutning
indeholder ingen resultater fra den nye bank. Den nye bank er ikke en gentagelse
af gamle identiteter, og dens resultater må ikke lægges sammen med ukendte gamle
resultater. Der er ikke ændret på de videnskabelige regler ud fra gamle udfald.
Den tekniske parallelitet hæves fra fire til otte samtidige arbejdere; det nye,
særskilte samlede loft er fortsat 90.000 CPU-sekunder.

Der er fortsat **ingen kvalificeret SETI-detektion**. Den oprindelige A/B-status
er `FAIL_CLOSED`. De beskyttede 2016-data og den utilgængelige 2019-rute forbliver
lukkede. Det formelle kontrolpunkt er 20. oktober 2026. De ni gamle bånd kommer
fra et allerede eksponeret og efterudvalgt besøg i 2017; eventuelle Gamma16-rangtal
er en modeldiagnostik og kan ikke fortolkes som himlens falsk-alarm-sandsynlighed.
Der er ingen nye teleskopforespørgsler eller teleskopbytes og ingen udgift i DKK.

Reproduktionspakken indeholder de præcise publicerede input, audit og afslutning,
status for alle identiteter samt det uændrede oprindelige kildearkiv
`SETI_NATIVE_SPOR_2026-10-14.zip`. Pakningen kontrollerer ZIP-CRC og SHA-256 for
hver leveret fil, alle 17 kildepins og det indlejrede kildearkiv. Den indeholder
ingen genskabte eller opdigtede numeriske resultater.
