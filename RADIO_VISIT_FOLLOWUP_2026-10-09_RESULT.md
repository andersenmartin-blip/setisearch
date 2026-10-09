# SETI — nye observationsbesøg undersøgt, 9. oktober 2026

**Fem senere HIP98505-filers mål-, tids- og frekvensmetadata er verificeret.
Ingen af disse fem filer dækker det uafklarede spor ved 1424,079069888 MHz.**
Der er derfor ikke tilføjet en uafhængig signalmåling eller en ny kandidat.
De syv tidligere svage ON-profiler er fortsat **UNRESOLVED**; A/B er fortsat
**FAIL_CLOSED**, og den kvalificerede pilot er blokeret.

Denne afgrænsede arkivgennemgang følger de afsluttede native kontrolanalyser.
Deres 120 tidsprofiler, driftssøgninger, kontraster og gamle testbanker er ikke
genkørt. Det tidligere [signal-/kontrolresultat](RADIO_NATIVE_CONTROL_2026-10-09_RESULT.md)
bevares uændret.

## Hvad det aktuelle arkiv faktisk viser

En live forespørgsel på `target=HIP98505`, med grænse 500 og uden instrument-,
filtype- eller frekvensfilter, gav 21 katalogposter: det kendte L-båndsbesøg
17. marts 2016 og S-båndsbesøget 28. april 2017. De officielle
[2019-observationstabeller](https://seti.berkeley.edu/listen2019/listen2019_tables.pdf)
viser samme L- og S-båndsbesøg. S-båndsbesøget kan ikke kontrollere 1424 MHz.
Katalogets ældre poster er ikke et fuldstændigt register over filserveren.

Det officielle [pipelineindeks](https://bldata.berkeley.edu/pipeline/) nævner også
fem senere sessioner med HIP98505. Der blev udvalgt den første kronologiske
højopløsningsfil i hver af de fem undersøgte sessioner på grundlag af filnavne,
før frekvensmetadata blev læst. Ingen effektværdier styrede udvælgelsen.

| Session | Verificeret headerstart, UTC | Læst produkt | Kanalcentrenes interval, MHz | Dækker 1424,079070 MHz? |
|---|---|---|---|---|
| AGBT18B_999_18 | 2018-09-07 05:13:37 | Én spliced ON-fil, scan 0037 | 3563,964845–8438,964842 | Nej |
| AGBT18B_999_26 | 2018-09-23 02:31:20 | Én spliced ON-fil, scan 0094 | 3947,753909–8201,660156 | Nej |
| AGBT18B_999_29 | 2018-09-27 02:49:07 | Én spliced ON-fil, scan 0108 | 3947,753909–8201,660156 | Nej |
| AGBT19B_999_23 | 2019-09-14 06:21:03 | Én blc40 ON-fil, scan 0092 | 11063,964845–11251,464842 | Nej |
| AGBT19B_999_31 | 2019-09-29 22:00:49 | Én blc40 ON-fil, scan 0077 | 8251,464845–8438,964842 | Nej |

Alle fem har `source_name=HIP98505`, `telescope_id=6`, `CLASS=FILTERBANK`,
endelige frekvens-/tids-/positionsværdier og kanal-/feedtal, der stemmer med
datasættets form. Headerstart stemmer med filnavnets MJD og sekunder: afvigelse
0 s i alle fem. De deklarerede koordinater ligger 0,307–0,970 buesekund fra
den bevarede 2016-ON-header. Dette er konsistens mellem filheaders, ikke en
uafhængig bekræftelse af teleskopets faktiske retning.

Intervallerne er beregnet direkte som `fch1` og
`fch1 + (nchans - 1) * foff`; de angiver kanalcentre. Der er ingen omregning til
barycentrisk frekvens, fysisk flux, SNR eller sky-sandsynlighed.

**Konklusionen gælder de fem læste filer.** Én filheader dokumenterer ikke en
komplet ON/OFF-kadence. De to `blc40`-headers dokumenterer ikke alle øvrige
splitfiler eller hele 2019-sessionernes frekvensdækning. Gennemgangen beviser
ikke, at brugbare L-båndsdata mangler overalt i arkivet.

## Metadata blev læst uden signalåbning

Første offentlige frysning fastlagde fem præcise URLs, én HEAD og én
4096-byte prefix-GET pr. kilde. Alle fem prefix-parsninger stoppede, da HDF5
ville læse mere end de bevarede bytes. Disse faktiske fejlreceipts og prefixer
er bevaret; kilderne blev ikke erklæret ugyldige, og requests blev ikke gentaget.

De bevarede HDF5-headers peger på en global heap og en objekt-headerfortsættelse.
En særskilt offentlig frysning fastlagde ti præcise nye metadataområder ud fra
disse pointere: heapens manglende slutning og objekt-headerfortsættelsen for hver
fil. De oprindelige HEAD-pins og prefixer blev genbrugt. Serverens ETag, status
206, Content-Range, længde, URL og encoding blev kontrolleret før bodylæsning.
Ingen redirects, HTTP-retries eller fuldfildownloads blev udført.

Kun bevarede metadataområder blev eksponeret til HDF5. En manglende cache-range
ville stoppe læseren uden netværksopfølgning. Der er **0 datasæt-værdiadgange**,
**0 nye power-chunks** og **0 s ny signaleksponering**. Samtlige 15 binære
metadatafiler, tilsammen 36.824 bytes, er SHA256-kontrolleret og gemt i Git sammen
med kilde- og områdepins, kode og receipts. Ingen fuldfil-MD5 er verificeret.

Frysninger og præcise readbacks før hver kørsel:

- [Prefix-scope og læser](https://github.com/andersenmartin-blip/setisearch/commit/1302985b3300ebc90cebed47aa1f2da446f055ec).
- [Metadatafortsættelser med bevarede første fejl](https://github.com/andersenmartin-blip/setisearch/commit/66575c698404399e025e0acae6080e6529a17242).

En separat læsegennemgang kontrollerede fil-/besøgsgrænserne og metadata-only
adgangen uden nye requests, kørsel eller gateændringer. For 18B_999_26 og
18B_999_29 er de oprindeligt læste directory-bodies ikke bevaret; URL-observationer
og modtagne byteantal er registreret. De faktiske kildeheaders, serverpins og
metadatafortsættelser er bevaret og hashkontrolleret.

## Ressourcer og næste bevistrin

100 CPU-s er konservativt reserveret til hele aktiviteten, inklusive forberedelse,
fejl, review og publicering. De to headerprocesser brugte tilsammen
0,369753 målte process-CPU-s; dette er ikke en måling af hele aktivitetens CPU.
Disse komponenter debiteres ikke igen. Den interne afslutningsreserve er
prospektivt reduceret fra 1700 til 1600 CPU-s under brugerens fortsatte prioritet
til signalarbejde, inden for uændret godkendt 12-CPU-timers total.
Saldo: **1602,705145 CPU-s**, heraf **1600 beskyttet til 20. oktober**.
Gamle reservationer refunderes ikke.

Kendte nye application-body-bytes fra lokale arkivforespørgsler, directorylæsninger
og de fem headers er 388.598, heraf 36.824 teleskopheaderbytes; ingen nye
teleskop-signalbytes. Byteantallet omfatter ikke HTTP-headers/socketbuffering,
Git eller webværktøjets separate sidehentninger. Begge headerprocessers peak-RSS
var under 44 MB. Miljø: Python 3.12.14, h5py 3.15.1, HDF5 1.14.6; ingen
power-codec anvendt. Pris 0 DKK; ingen personkontakt, betaling eller booking.

Det uafklarede spor kræver stadig et andet observationsbesøg med verificeret
målidentitet, frekvensdækning omkring 1424 MHz og egnede kontroller. Frekvens-/
Dopplermodel og søgefamilie skal fastlægges før signalværdier åbnes. Et andet
muligt bevistrin er en særskilt kvalificeret kalibrering af hele den oprindelige
udvælgelsesfamilie. Denne metadataafklaring er hverken et kalibreringsforsøg,
en ny sky-pilot eller en generel nuldetektion. Der kører ingen ny baggrundsworker.

## Reproducerbar evidens

- [Samlet resultat og metadatahashes](results/radio_visit_followup_20261009/VISIT_FOLLOWUP_RESULT.json).
- [Ressourceledger](results/radio_visit_followup_20261009/RESOURCE_LEDGER.json).
- [Live katalogsvar](results/radio_visit_followup_20261009/hip98505_all_records.json).
- [Første prefix-job, inklusive fejl](results/radio_visit_followup_20261009/headers/HEADER_RESULT.json).
- [Færdige headers og range-receipts](results/radio_visit_followup_20261009/header_completion/COMPLETION_RESULT.json).
- [Første scope](tools/radio_visit_followup_20261009/header_scope.json) og
  [metadatafortsættelsernes scope](tools/radio_visit_followup_20261009/completion_scope.json).

De bevarede 2016-powerarkiver og deres tidligere Library-identiteter ændres
ikke af denne Git-baserede metadataopfølgning.
