# SETI: verificeret fortsættelse, 10. oktober 2026

To yderligere grænsepar, **154+155 og 157+158**, er afsluttet og har fælles gemt output-/kilde-QA. De tilføjer **75.005.952 korrelerede drift-/breddehypotesekombinationer** på den allerede undersøgte observation fra 17. marts 2016. De samme beregninger er ikke gentaget i denne gennemgang.

| Afsluttet par | Numerisk process-CPU | Største udvalgte rangscore |
|---|---:|---:|
| 154+155 | 16,071806403 s | 5,841219633 |
| 157+158 | 15,139869252 s | 5,635329945 |

Scorerne er maksimummer fra et fast grid, **ikke kalibreret SNR eller statistisk signifikans**. De stærkeste faste profiler har primært overskud i den ON-scanning, hvor de blev udvalgt. Det dokumenterer ikke en gentaget kilde på himlen. Ingen kvalificeret SETI-detektion er dokumenteret; svag respons på den præcise OFF-bane udelukker ikke struktur ved nærliggende frekvenser.

Resultaterne omfatter 12 kort, 120 top20-poster og 18 faste profiler, hver med alle seks ON/OFF-scanninger. Den eksisterende QA-kvittering dokumenterer 24 autentificerede kompakte kildefiler, 384 dekodede rækkehashes og **222.912 råcelleforekomster, der matcher kilden bit for bit**. Vores uafhængige gennemgang bekræfter alle 54 gemte målefilers SHA256/størrelser samt bindingen mellem kode, offentlige scopes og kvitteringer. Den kører ikke detektoren igen. Den fulde normaliserende kildemedian genmåles ikke uafhængigt, og hele de oprindelige teleskopfiler har fortsat ikke verificeret MD5.

De seks native udsnit 151, 153, 154, 155, 157 og 158 har tidligere givet 27.827.208.192 nye evaluerede kombinationer. Sammen med de tre historisk afsluttede grænsepar er det **27.939.717.120 forskellige evaluerede kombinationer**, eksklusive den tidligere første 40-core-søgning i 151. Kombinationerne er afhængige og er ikke et antal uafhængige forsøg. Tre af de 12 oprindelige native programmer endte med CPU-fejl; deres senere accepterede og kildekontrollerede gemte outputs ændrer ikke fejlstatus.

Den samlede grænsehistorik er fem programstarter, tre afsluttede numeriske passager og to fejl før datalæsning. De tre forskellige grænsepar omfatter 112.508.928 kombinationer uden gentagen videnskabelig søgning. Det oprindelige 153+154 beholder COMPLETE-/QA-historikken, men dets fulde videnskabelige output er fortsat tabt. Den planlagte nye rekonstruktionsfamilie blev derfor holdt ueksekveret, da nyere, overlappende arbejde blev opdaget. Dens projekterede gentagelsesregnskab er ikke faktisk forbrug eller nye fund.

## Den nye observation fra 2017

Den særskilte S-båndsobservation fra 28. april 2017 har verificerede headere og 96 fastlagte blokbeskrivelser. Første indhentning modtog 27 blokke, **83.845.205 BODY-byte**, og stoppede med en HDF5-skrivefejl. Fejlkvittering og alle seks fysiske partialfiler bevares uden at kalde indhentningen komplet. 26 dekodede rækker var allerede verificeret; den 27. modtagne blok findes også blandt bevarede fysiske bytes og er autentificeret i den særskilte recovery-gennemgang.

Den separat fastlåste recovery-indhentning er nu **COMPLETE**: 27 blokke blev genbrugt lokalt, og kun de 69 endnu ikke forsøgte HTTP-blokke blev hentet. Alle 96 komprimerede blokke er autentificeret; seks komplette kompakte filer og 96 dekodede rækkehashes er gemt. Samlet payload er 298.238.620 BODY-byte, uden gentagne GET-forespørgsler. Den oprindelige fejlstatus bevares. Indhentningen giver yderligere **100.663.296 rå float32-celler** fra en ny historisk observation; en afsluttet driftsøgning og efterfølgende måle-QA er endnu ikke dokumenteret i denne status. 2017-observationen dækker et andet frekvensbånd og kan ikke bekræfte tidligere 1424 MHz-spor ved samme frekvens.

## Bevarede resultater og kildebeviser

- `SETI_VERIFIED_BOUNDARY_CONTINUATION_2026-10-10.zip`: de to eksisterende komplette målefamilier, kode/scopes, gemt QA, figurer, resumé og uafhængige gennemgange. Rå native kildefiler hentes særskilt fra de allerede bevarede RAW-pakker.
- `SETI_S2017_FAILED_PARTIAL_SOURCE_2026-10-10.zip`: den oprindeligt fejlede indhentnings seks fysiske partialfiler, kode/scope/manifest og uændrede fejl-/inputkvitteringer. Alle arkivmedlemmers SHA256, størrelser og CRC er kontrolleret. Pakken gør ikke partialfilerne til komplette målinger.

Oprindelige holdouts og A/B-fejl forbliver lukkede. Ingen betalte ressourcer, personbeskeder eller nye observationsbestillinger er anvendt. Marginalomkostning: **0 DKK**.
