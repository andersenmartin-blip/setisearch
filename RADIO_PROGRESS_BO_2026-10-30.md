# BO — fem deterministiske tekniske kontroltrin gennemført

Alle fem faste kontroltrin afsluttede med faktisk exit 0 på **42,218 sekunder**. Dette er kontrol af filadapter, normalisering, regning, koordinater og procesafslutning på konstruerede data. De astronomiske HIP45688-målinger er ikke åbnet, og ingen ny signalsøgning eller tilfældighedsgenerator er aktiveret i BO.

Kode og plan blev fastlagt før første testværdi. [Præregistreringen](https://github.com/andersenmartin-blip/setisearch/tree/a13cd82e917f5d4ebbfa4717dc171afc4e8e1d99/work_bo) indeholder alle 22 tekstfiler, som blev genlæst fra GitHub uden forskelle. Planens SHA256 er `cc04271a255bcf97c47450ccc267aa3d8df84e57c853315b8828227c77b2bfb5`; den binder 21 kilde- og dokumentationsfiler. Den uafhængige kildegennemgang godkendte kun denne tekniske fase.

| Trin | Faktisk resultat | Afgrænsning |
| --- | --- | --- |
| E01: gemt NPY | 68 af 68 fastlagte accept-/afvisningscases bestod, inklusive fulde 16 × 1.048.576-arrays i NPY v1/v2 | Byteidentitet, skrivebeskyttelse, metadata og transport; den rigtige DATA-manifest er fortsat uåbnet |
| E02: normalisering | To fulde deterministiske mønstre; 72 uafhængige ankre, 720 koefficienter og 288 normaliserede prøver havde nul målt afvigelse; seks fatale fejlcases afvist | Udvalgte uafhængige prøver og fuld ankergeometri, ingen signalfølsomhed |
| E03: summer | 1.260 aktuelle summer matchede `math.fsum` præcist; de tilsvarende float32-stadier blev gengivet præcist | Fastlåst absolut/relativ grænse; guard/fallback og tab i ubevogtet regning blev eksplicit testet |
| E04: kalibrering og tid | 800 komplette lokale og to komplette globale vektorer bestod sorteringsreferencer; 1.600 faktorielle diagnoser bevaret | Globalt M-interior inkluderer q128; lokale og globale metoder forventes ikke ens |
| E05: procesafslutning | Én gyldig case accepteret, alle syv fastlagte fejlcases afvist | Faktiske exits, EOF, resultatbinding, tidsstop, ændret pin og eksisterende output |

Den fælles E02–E04-fase brugte 39,682 CPU-sekunder inklusive capture-forælder og børn, 36,133 vægsekunder og 637.276.791 gemte bytes. Grænserne var 180 CPU-sekunder, 300 vægsekunder, 2 GiB RSS og 1 GiB gemte bytes. Alle individuelle grænser bestod også. Hver proces blev ventet på præcist; loggens observerede og gemte bytes samt afsluttende JSON/resultat-SHA blev sammenholdt. Den særlige forskel mellem procesnumre i Python og hostens procfs blev håndteret med validerede namespacebindinger; signaler bruger kun ejede procesgrupper.

De nye deterministiske float32-referenceprøver havde **217 overskridelser af den oprindelige absolutte 5e-5-grænse**, herunder de på forhånd krævede 60 cancellation-fejl. Tallet omfatter prøver på begge fastlagte normaliseringer og er ikke et nyt mål for den gamle astronomiske M-kørsel. Alle overskridelser står fortsat som `FAIL`; største afvigelse i den konstruerede cancellation-fixture var 231. En trofast gengivelse af float32-regningen giver ingen numerisk kvalifikation eller ændring af tidligere QA.

Den oprindelige HIP45688-M-kørsels **24 raw-sum-fejl og fuld-QA=false** samt alle M-familiens 142 fejl bevares. Originale launchere og kørselsidentiteter er ikke kørt. Beskyttet HIP98505/HD189733 fra 2016, beskyttede 2019-data og de lukkede B06/restoration-identiteter er ikke åbnet. Der er 0 nye observationer, 0 nye teleskoparkivforespørgsler og 0 ny dækningskredit. BA står fortsat på 486 unikke arkiv-ID'er og 268,50128173828125 tekniske MHz-besøg.

E04 kontrollerede hele bankens 839 × 16 interne offsets, tolv eksplicitte afvisninger af manglende support og forskellen mellem M's gemte nominelle +8dt og de faktiske row7.5-centrerede indekser. Historiske frekvens-/tidslabels er bevaret; den særskilte halve-dt-transformation er kun en ny koordinathypotese. Det er ikke dokumentation af headerens integrationskant/center-semantik eller af fuld seks-scan-association.

**Næste konkrete fase er implementering og præregistrering af de 24 parrede syntetiske seks-scan-kontroller.** Begge metoder skal få samme uforanderlige input og signaler, mens legacy-kalibreringen beholder sit fulde globale domæne. Den særskilte fulde 839-rate-kontrol, faktisk DATA-admission og en senere HIP45688-signalsøgning kræver derefter deres egne afsluttede forudsætninger og planer. BO kvalificerer ingen recovery-rate, FAP, SNR/sigma, flux/EIRP, astronomisk følsomhed eller himmeloprindelse.

Den uafhængige slutgennemgang afsluttede med faktisk exit 0 og `PASS_INDEPENDENT_CLOSED_EVIDENCE_REVIEW`. Den genhashte alle 124 bundne regulære evidensfiler to gange, kontrollerede to særlige afvisningsfixtures og genkontrollerede alle 21 frosne inputfiler. Slutmarkør, kildepins og evidenskort var uændrede. Reviewets SHA256 er `943b0679ee21557cbfafd741e4e033a3ed8013920b805f7efd20404acfdfa8a5`.

Fem ekstra, ikke-kanoniske delkopier med uafklaret oprindelse var allerede med i slutmarkørens hashbindinger. De bevares som hjælpeartefakter uden sciencekredit; kun de fastlagte kanoniske stier blev brugt som testinddata. Tidligere kvitteringers mappestørrelser er øjebliksbilleder og skal ikke fejlagtigt kræves identiske med senere inventarer. Det endelige hashbundne E02–E04-inventar ligger fortsat under den fastlagte 1 GiB-grænse. Ingen fil er slettet eller repareret for at få kontrollen til at bestå.

Resultatpakken består af binær evidens samt manifest og genoptagelseshenvisninger. Kode, tekstlogs og JSON-resultater bevares på GitHub. Alle ejede kontrolprocesser og underprocesser er afsluttet; ingen ny fase fortsætter automatisk.

Første pakning stoppede med faktisk exit 1, fordi en yderligere kopi af den samme auditor-exitkvittering blev skrevet, mens arkivet blev bygget. Pakkekontrollen afviste det ændrede filsæt. Der var præcis én tilføjet JSON-sti, ingen fjernede filer og ingen ændring af testenes slutmarkør eller resultater. Første forsøg og dets indlejrede manifest er bevaret uden leveringskredit; arkivets SHA256 er `0e7e95ab2d961f3ff988edfb9af75cc8f2a1498d7b2bf6c256cbcc3bbbc989a3`. Den endelige pakning bestod under en særskilt identitet efter afsluttet skrivning. Ingen teknisk gate eller scienceidentitet er genkørt.

Det endelige arkiv er **118.567.847 bytes med 104 medlemmer**, SHA256 `3351f0de644bb0c102f64f782680f43f73d9d2aed4e8dc306654009099e18f5a`. Alle CRC'er, medlems-SHA256 og oprindelige filidentiteter blev kontrolleret. De 64 binære filer, to særlige afvisningsfixtures og 36 mapper er bevaret sammen med manifest og genoptagelseshenvisninger. Tekst-/kodeindhold er ikke duplikeret i det binære arkiv.


[Binær resultatpakke](https://chatgpt.com/library?file_id=libfile_705b21d2a7508191854bd12fe44b8ce7&account_id=personal) · [Arkivmanifest](https://chatgpt.com/library?file_id=libfile_d7c90af0d3548191a888deb7ae202437&account_id=personal). De præcise identiteter og kvitteringer findes i `work_bo/DELIVERY_BO.json`.

