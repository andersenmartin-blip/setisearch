# SETI BD — offlinekontrol og forberedelse til genoptagelse

29. oktober 2026. **HIP44295 / 65133 er fortsat delvist hentet: 88 af 96 rækker.** BD tilfører en reproducerbar kontrol af checkpointets bytes og en præcis plan for de otte manglende rækker. BD har ikke hentet nye teleskopdata eller kørt en detektor.

## Udført og kontrolleret

BC-pakken er hentet fra det eksisterende checkpoint og kontrolleret mod dens offentliggjorte SHA-256. Alle **136 inventarposter, i alt 75.156.741 bytes**, svarer til de fastholdte længder og hashes. En ny Python-kontrol bruger kun standardbiblioteket og læser NPY-lagerformatets header direkte. Den kontrollerer hver af de otte gyldige rækker i scan 5 mod de tidligere fastholdte rækkehashes: **33.554.432 bytes**, med samlet SHA-256 `cc31b6008bf9722fbe27ddbc8a00d1ae17b95a1cba5683a633dc3b1aeda240f8`.

De allokerede rækker 8–15 indgår i filens integritetshash, men fortolkes ikke som målinger og indgår ikke i rækkekontrollen. Der er ingen ny flydende talberegning, codec-dekodning eller signalanalyse. BD kontrollerer de gemte bytes mod arvet dokumentation; det er ikke en uafhængig validering af den oprindelige HDF-/bitshuffle-model.

Række 7's afledte komprimerede fil er bevaret. Dens første 3.103.298 bytes matcher BC's modtagne prefix; de resterende 13.580 bytes har bevaret BB-tail-datalinje. BB's oprindelige tail-kvittering er ikke genindlæst og valideret uafhængigt i BD. Filen beskrives fortsat som en afledt union, ikke som en ny HTTP-206-kvittering for hele chunken.

## Fund i genoptagelseskoden

Et separat kildekodereview viser, at BC's recovery-runner stadig forventer **87 tidligere + 9 nye rækker**, sammenligner kun de syv gamle partial-rækker og tæller række 7 som ny. De forberedte native-, inputbindings- og faseadaptere fastholder samme gamle tælling. De kan derfor ikke genbruges uændret efter BC's faktisk gennemførte tilføjelse af række 7.

Den nye offlineplan fastlægger i stedet **BB87 + BC1 + senere8 = 96** og **5 tidligere + 1 senere gentagelseskontrol**. Den tillader ingen netværksanmodning eller produktionskørsel. Ny acquisition og de tilhørende adaptere skal implementeres og gennemgås særskilt, med nye outputstier og bevarelse af begge gamle partial-filer og alle fejlede kørslers dokumentation. Det numeriske søgeprogram og de oprindelige søgeregler er uændrede.

## Aktuel blokering og næste trin

Det aktuelle miljø begrænser netværksdestinationer; Berkeley-arkivet er ikke på den tilladte liste. **BD har foretaget nul arkivanmodninger**, ingen gentagelse og ingen alternativ rute. BC's tidligere tunnel-403 bevares som historisk fejl; BD hævder ikke at have målt en ny fejl eller diagnosticeret teleskopserveren.

Første kendte manglende interval er fortsat **9241886720–9241903103**, 16.384 bytes i arkiv-ID 65143. Det er et TREE-metadatainterval, mens række 8 lokaliseres. Række 8's komprimerede payload-interval er endnu ukendt og må ikke gættes.

Fortsættelsen kræver normal adgang til arkivet og en særskilt gennemgået missing-only-implementering. Genopret de fem komplette BB-arrays og den fulde kvitterings-/TREE-cache fra deres præcise forælderreferencer. Bevar og sammenlign alle otte nuværende scan-5-rækker. Hent kun de manglende rækker 8–15 samt den ene reelle gentagelseskontrol for scan 5, række 7. Efter fuld acquisition kræves native-kontrol, uændret detektor og ON/OFF-triage, numerisk review og afsluttende artefaktkontrol før ny dækning kan bogføres.

De fem komplette BB-arrays er bevaret gennem deres tidligere checkpointreferencer. **De er ikke fysisk genindlæst eller genhashet i BD.** Den fulde BB-cache er heller ikke genindlæst. Offlinekontrollen af BC-pakken er derfor ikke en fuld native-kontrol af hele cadencen.

## Videnskabelig status

Den senest afsluttede autoritet er fortsat **BA: 486 unikke arkiv-ID'er og 268,50128173828125 tekniske MHz-besøg**. BD tilføjer 0 ID'er, 0 tekniske MHz-besøg, 0 nye observationsepoker og 0 kandidatvurderinger. HIP44295 bliver ved køens hoved. Teknisk bogføring er ikke kalibreret astronomisk følsomhed. Ingen baggrundssøgning fortsætter efter denne aflevering.

## Reproduktion og dokumentation

- [Offlinekontrollens resultat](results/radio_bd_offline_2026-10-29/PREFLIGHT_RESULT_BD.json)
- [Separat review af recovery-koden og begrænsninger](results/radio_bd_offline_2026-10-29/INDEPENDENT_RECOVERY_READINESS_REVIEW_BD.json)
- [Standardbibliotekets preflight-program](tools/radio_bd/preflight_bd.py)
- [Adversarielle regressionskontroller](tools/radio_bd/test_preflight_bd.py)
- [Testresultat](results/radio_bd_offline_2026-10-29/TEST_RESULT_BD.json)
- [SHA-256-kontrolsummer](results/radio_bd_offline_2026-10-29/SHA256SUMS.txt)
- [Uændret BC-checkpoint](https://github.com/andersenmartin-blip/setisearch/blob/b9648f3881714c650f765d0381430349ee62c7b2/RADIO_PROGRESS_BC_PARTIAL_2026-10-29.md)

Udpak BC's eksisterende pakke uden at ændre filerne. Kør `python3 tools/radio_bd/preflight_bd.py --root PATH_TO_EXTRACTED_BC --out NEW_RESULT.json`. Programmet foretager ingen netværksoperationer; exit 0 betyder alene, at de specificerede offlinekontroller består. Resultatets status angiver fortsat, at den fulde recovery er blokeret. Testene køres med `SETI_BC_ROOT=PATH_TO_EXTRACTED_BC python3 tools/radio_bd/test_preflight_bd.py`.
