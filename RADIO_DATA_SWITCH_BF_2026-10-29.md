# SETI BF — gemte 2017-data prioriteres før blokeret arkivhentning

29. oktober 2026. Brugeren har bedt om at gå videre til andre data, så signalsøgningen kan genoptages. **HIP44295 / 65133 sættes derfor på pause. Første prioritet er nu den allerede gemte S2017/native171-rådatapakke fra HIP98505 / HD189733.** HIP58684 / 65193 og HIP59280 / 65205 beholdes som reserve for nye arkivdata.

## Et konkret alternativ er fundet

`SETI_S2017_NATIVE171_RAW_2026-10-10.zip` er fundet i Library med størrelse **466.351.822 bytes**. Den historiske [råpakkekvittering](https://github.com/andersenmartin-blip/setisearch/blob/d44afffa8f462b3e9c559cedc2ad2eb88baf7dfa/results/radio_s2017_verified_review_20261010/receipts/RAW_PACKAGE_RECEIPT.json) dokumenterer kontrol af ZIP-CRC og alle 593 medlemmers SHA-256. Arkivets fastholdte SHA-256 er `6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786`.

Den nye kontrol har løst filens aktuelle identitet og kontrolleret metadataenes størrelse mod den historiske kvittering. **Selve filens bytes er ikke hentet eller genhashet i BF.** Det skal ske, før den bruges igen.

Data stammer fra 28. april 2017 og omfatter det tidligere undersøgte besøg med tre ON- og tre OFF-scanninger. Profiler og cross-ON-sammenligninger er tidligere gennemført. Det er derfor et grundlag for en udvidet, eksplicit beskrivende genanalyse eller opfølgning; det er ikke nye observationer eller et dokumenteret aldrig undersøgt datasæt. Den nye søgefamilie og tidligere dækning skal fastlægges og gennemgås, før nye metrikker beregnes. Beskyttede holdouts genåbnes ikke.

Fordelen er konkret: rådatapakken findes allerede som en gemt fil og kræver ikke en ny hentning fra Berkeley-arkivet.

## Aktuel blokering

**Beregningsmiljøet er nu utilgængeligt.** En faktisk kontrol returnerede: “No usable execution environment is available.” Det forhindrer både indlæsning/bytekontrol af den gemte pakke og en ny detektorkørsel her. Der er derfor endnu ikke startet en signalsøgning på alternativet.

Der er ikke foretaget nye arkivanmodninger, udløst alternative CI-kørsler eller oprettet baggrundsjob. Netværkskonfigurationen er uændret. Ingen historiske resultater er omklassificeret som nye.

## Fortsættelsespunkt

1. Når beregningsmiljøet er tilgængeligt, hentes den præcist identificerede gemte S2017-pakke og kontrolleres mod dens arkivhash, CRC og medlemsinventar.
2. De seks råkilder, tidligere søgebånd og søgefamilier dokumenteres. En udvidet genanalyse fastlægges og gennemgås med eksplicit tidligere eksponering, uændrede oprindelige klassifikationer og sædvanlige native-/ON/OFF-/reviewkrav.
3. Først efter de faktiske inddata- og metodekontroller starter detektoren. Valget af datasæt eller en bestået simulering tæller ikke som en udført søgning.

HIP44295s **88 af 96 rækker**, begge partial-filer og alle fejloptegnelser bevares gennem [BE-checkpointet](https://github.com/andersenmartin-blip/setisearch/blob/d44afffa8f462b3e9c559cedc2ad2eb88baf7dfa/RADIO_PROGRESS_BE_OFFLINE_2026-10-29.md). Det er en operationel pause efter brugerens nye instruktion, ikke en videnskabelig afslutning.

BA er fortsat senest afsluttede autoritet: **486 unikke arkiv-ID'er og 268,50128173828125 tekniske MHz-besøg**. BF tilføjer ingen data, udførte signalsøgninger, kandidatvurderinger eller observationsdækning.

[Maskinlæsbart datasætskift, præcis filidentitet og fortsættelsespunkt](results/radio_bf_data_switch_2026-10-29/DATA_SOURCE_SELECTION_BF.json).
