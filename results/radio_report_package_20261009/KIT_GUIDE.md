# SETI-radio: rapport- og reproduktionskit, 9. oktober 2026

Start med [den aktuelle rapport](../../RADIO_REPORT_PACKAGE_2026-10-09.md). [Den gamle periode](../../RADIO_PERIOD_2026-09-26_TO_2026-10-09_FINAL.md) er formelt lukket. De nye beregninger og gemte fejlanalyser er afsluttet; rapport- og pakningsleverancen er fremrykket til 9. oktober. Periodens afsluttende checkpoint står til 20. oktober. Download og udpakning starter ingen analyse.

## Inkluderet

- De 21 originale, hashbundne adgangskrav til METHOD-verifikationen: frosne kode-/kontrakt-/protokoltekster, case-definitioner og allerede observerede A/B-metadata.
- METHOD-admission, afslutningsmetadata og tabeller fra alle 64 afsluttede forsøg; den originale rapport og seks originale vektor-PDF-figurer. Originale PNG-embeds i METHOD-rapporten ligger eksternt; PDF-links kan bruges offline.
- Original verifierkode samt den faktisk gennemførte 8.-oktober-invocation, resultatkvittering, restaurering, transportrettelse, review og ressourcer. Denne pakning er ingen ekstra verifier-invocation.
- Den gamle formelle slutlukning, aktuelle rapport og bevarede reference-/valideringsrapporter. Voyager-spektrumpayload og reference-scorekort er eksterne og ikke inkluderet.
- Eksterne A/B/METHOD-arkivindeks, et eksplicit eksternt indeks og et manifest med byteantal, SHA256 og Git-blob-hashes for alle inkluderede payloadfiler.

Pakken bevarer repository-stier. De eksisterende originale bytes kopieres; de videnskabelige programmer importeres eller udføres ikke. Hashing og ZIP-pakning er dokumenthåndtering, ikke nye genfund eller dataanalyser.

## Kontroller de inkluderede bytes

Fra den udpakkede pakkes rod kan filerne kontrolleres med:

```bash
sha256sum -c SHA256SUMS
```

Dette læser kun pakkens filer og kontrollerer transportintegritet. Det kører ikke generator, detektor eller verifier. KIT_MANIFEST.json angiver de inkluderede payloadfiler; manifest og SHA256SUMS medtages som kontrolfiler uden selvrefererende hashes. ZIP'ens egen hash og faktiske pakkekontrol findes i PACKAGING_RECEIPT.json ved siden af ZIP-filen.

## Originale figurer

| Visning | Original PDF |
|---|---|
| ALL versus idealniveau | [Styrke, ALL](../radio_pilot_method_report_20261008/method_strength_final_all_active_recovered.pdf) |
| ANY versus idealniveau | [Styrke, ANY](../radio_pilot_method_report_20261008/method_strength_final_any_active_recovered.pdf) |
| ALL versus drift | [Drift, ALL](../radio_pilot_method_report_20261008/method_drift_final_all_active_recovered.pdf) |
| ANY versus drift | [Drift, ANY](../radio_pilot_method_report_20261008/method_drift_final_any_active_recovered.pdf) |
| De 64 binære ALL-celler | [Celler, ALL](../radio_pilot_method_report_20261008/method_cells_final_all_active_recovered.pdf) |
| De 64 binære ANY-celler | [Celler, ANY](../radio_pilot_method_report_20261008/method_cells_final_any_active_recovered.pdf) |

Figurerne er kopieret fra den eksisterende publikation uden genrendering. ALL/ANY er beskrivende genfund efter OFF i alle/mindst ét aktivt ON; idealniveau er ingen målt SNR eller flux. Der er én realisering pr. præcis celle, ikke en estimeret genfindingskurve.

## Reproduktionsgrænser

Scorekort og casearkiver ligger **eksternt** i allerede publicerede, immutable Git-versioner. De er identificeret i EXTERNAL_BINDINGS.json og de originale arkivindeks. Pakken indeholder derfor ikke alle cases til offline verifierkørsel. Den udtrækker ingen casearkiver og genlæser ingen numeriske scorekort.

Den afsluttede verifikation omfatter gemte kort → hits/veto/genfund. Rå syntetisk power, preprocessing og scores blev ikke genskabt. Pakket historisk kode kan inspiceres; dens tilstedeværelse dokumenterer ikke en ny end-to-end-kørsel, et uafhængigt miljø eller nye realiseringer. Der udføres ikke en ekstra kørsel i den nuværende kampagne.

Gamle pending-felter og saldi i originale inputs bevares som historik. Den faktiske 8.-oktober-verifikationskvittering supersederer pending/19.-oktober-felter. Dagens aktuelle rapportledger ligger eksternt ved pakken; historiske ledgers i ZIP'en ændres ikke og må ikke summeres som separate nye debiteringer.

A og B forbliver FAIL_CLOSED; HD189733-payload, gamle 112+128 holdouts og øvrige uåbnede paneler er fortsat uåbnede. Der er ingen ny kvalificeret himmelsøgning eller sky-nuldetektion. Dette kit aktiverer ingen ny metode, kvalifikation eller kampagne.

## Kildesnapshot

Originale filer er bundet til repository `andersenmartin-blip/setisearch`, immutable commit `76405d84b096f1dea4ce9aded0e9aeb792bef220`. Dagens rapport, gamle slutlukning, guide og pakkemanifester er særskilt markeret som skabt 9. oktober. De efterfølgende udgivelses-/ressourcekvitteringer er placeret ved siden af pakken for at undgå cirkulære pakkehashes.
