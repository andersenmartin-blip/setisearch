# BX — nye data kontrolleret; ingen ny SETI-søgning

31. oktober 2026, Europe/Copenhagen. Fortsættelse af BW med prioritet på nye, selvstændige data. **To originale ATA-testfiler er hentet og kontrolleret. Alle 51.968 komplekse visibilitetsværdier falder uden for den på forhånd fastlagte gyldighedsregel. Filerne kan derfor ikke bruges til den planlagte signalsøgning.** Der er ikke fundet eller afvist nye astronomiske kandidater i BX.

## Hvad der faktisk blev analyseret

Kilden er [rasg-datasets ved den fastlåste kildecommit](https://github.com/RadioAstronomySoftwareGroup/rasg-datasets/tree/55bd68b28fabe0936011bd9540cbaef9e20809db/visibility_data/ATA): to nedskalerede, autonormaliserede UVH5-testeksporter fra samme ATA-observation af 3c286. De er nyindlæste i dette projekt; observationen er fra 2024. De er ikke to uafhængige observationer eller en komplet ON/OFF-sekvens. Begge filer er verificeret mod kildens byteantal og Git-blob-hash samt en lokal SHA-256.

| Egenskab | C0352 | C0544 |
|---|---:|---:|
| Filstørrelse, bytes | 279.504 | 279.504 |
| Kanalcentre, MHz | 1.252,0–1.259,5 | 1.260,0–1.267,5 |
| Kanalbredde | 500 kHz | 500 kHz |
| Lagrede integrationer | 1 | 1 |
| Integrationstid | 30,015488 s | 30,015488 s |
| Form: baselines × kanaler × polarisationer | 406 × 16 × 4 | 406 × 16 × 4 |
| Komplekse værdier | 25.984 | 25.984 |
| Gyldige værdier efter den fastlagte maske | 0 | 0 |

Begge filer har 28 antenner. Headerens tidspunkt er **2024-12-03 17:30:10,023268 UTC**, mens vedligeholderens README angiver 2024-12-12. Denne provenienskonflikt er bevaret som uafklaret. Værdiernes enhed er `uncalib`; der er ingen selvstændig fluxkalibrering.

Masken kræver uflagget, endelig kompleks visibilitet og et endeligt, positivt `nsamples`. Alle værdier er uflaggede og endelige, men **samtlige afkodede `nsamples` er negative: −1.229.139.083.264**. Dette blev efter kørslens afslutning præciseret fra den allerede registrerede kategori “ikke-positive”. Masken er ikke ændret, og vægte er ikke erstattet. Fundet vedrører de offentliggjorte testeksporter; det fastslår ikke en fejl i den oprindelige teleskopobservation. Én integration og 500 kHz kanaler udelukker desuden den aktuelle smalbåndede drift- og ON/OFF-analyse.

## Kontrol og afgrænsning

[Plan og kildekode blev offentliggjort før numerisk analyse](https://github.com/andersenmartin-blip/setisearch/commit/f7a02cdc80e1f05e8f4c03f8bc823c6d59f0a7ae). Produktionskørsel og separat audit afsluttede naturligt med exitkode 0, uden timeout eller genkørsel. Begge afsluttede bevisarkiver er kontrolleret med CRC, medlemstørrelser og SHA-256 før og efter eksport. Inddata og de fastlåste afhængigheder var uændrede.

Den uafhængige skalarkontrol gennemgik alle **51.968 celler og 3.248 baseline/polarisationsgrupper**, inklusive maskering og profilernes NaN-status; maksimal profilafvigelse var 0. Den deler h5py-dekoderen og NumPy-lagringen med produktionen. Kontrollen er derfor uafhængig i beregninger og reduktioner, men er ikke en uafhængig dekodning af HDF5-bytes. Temporal kohærens er udefineret, og ingen kandidat- eller driftstærskel er anvendt.

Fire syntetiske QA-kontroller bestod før fastlåsningen. Den separate sikre TOP8-indlæser bestod fem syntetiske kontroller. En senere sammenfatningsrutine antog fejlagtigt nulvægte og stoppede på en assertion, før den skrev et resultat. Rutinen er rettet til negative vægte; denne fejl og rettelsen er bevaret i `work_bx/AGGREGATION_CORRECTION_BX.json`. Produktion og audit er uændrede.

## Det tidligere publicerede TOP8-datasæt

Forfatterens [ML_GBT_SETI-data](https://github.com/PetchMa/ML_GBT_SETI/tree/5f9c006a2960683969d9face28119af4d5b410b5/data_archive) blev identificeret som en mulig retrospektiv kontrol af otte allerede udvalgte signaler. De er ikke blinde, nye surveydata. Den 12.613.542-byte store pickle kunne ikke hentes gennem de tilgængelige normale connector-metoder: binærdekodningsfejl, tomt base64-indhold og afvisning af binær GitData-respons. Alle tre forsøg er dokumenteret. **Ingen pickle eller signalarrays er modtaget eller analyseret.** Der foretages ikke yderligere transportforsøg i BX.

Et relevant publiceret resultat er, at [Margot et al. (2023), afsnit IV.3](https://arxiv.org/html/2308.02712v4), klassificerede MLc3, 4, 5, 7 og 8 som radiointerferens. MLc1, 2 og 6 blev ikke undersøgt i den analyse. Dette er litteraturkontekst, ikke vores egen bekræftelse; detaljer og begrænsninger står i `work_bx/provenance/PUBLISHED_TOP8_ASSESSMENT.md`.

## Projektstatus og næste arbejde

- BX tilføjer **0 SETI-søgninger, 0 arkiv-ID'er til den oprindelige surveyoptælling og 0 tekniske MHz-besøg**. ATA-filerne registreres særskilt som testdata.
- Den tidligere autoritet er uændret: **486 unikke arkiv-ID'er**, **268,50128173828125 tekniske MHz-besøg** og **0 kvalificeret astronomisk følsomhed**. BU+BV+BW omfatter q1–254, 2,90679931640625 MHz, i fem komplette HIP44295-scanninger.
- Den fulde sekvens har fortsat status `NOT_EVALUABLE_MISSING_OFF5`. Der mangler rækker 8–15 samt fuld kontrolgenlæsning af række 7 i HIP43223/65143. Køen er ikke rykket frem; ingen beregningsjob kører i baggrunden.
- Første prioritet er normal adgang til den manglende OFF-scanning med de eksisterende BB/BC/BE-kontroller eller et selvstændigt, egnet ON/OFF-datasæt. Uændret adgang giver ingen grund til at gentage afsluttede søgninger. En særskilt, på forhånd fastlagt injection/recovery-undersøgelse på bevarede data er næste nyttige lokale metodearbejde; simulerede signaler skal markeres tydeligt, og resultatet giver ikke ny observationsdækning.

Maskinlæsbar status: `work_bx/SUMMARY_BX.json`. Bevisoversigt og permanente artefaktreferencer: `work_bx/DELIVERY_BX.json`. BX fortsætter fra BW-indekset `libfile_be9824abb8cc8191bd02b787c6222203`.
