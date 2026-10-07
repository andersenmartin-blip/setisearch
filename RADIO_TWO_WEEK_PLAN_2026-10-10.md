# SETI: ny 2-ugers plan, 10.-23. oktober 2026

Udarbejdet 7. oktober 2026 efter Martins udtrykkelige ønske om en ny plan.
Den gamle periode afsluttes 9. oktober. Denne plan er en ny undersøgelse;
gamle fejl, lukkede forsøg, reservationer og uåbnede testpaneler bevares.
Planen er udarbejdet, men nye analysejob er endnu ikke aktiveret.

## Mål og beslutning

Hovedmålet er mindst én gennemført søgning i en hidtil uanalyseret, offentlig
ON/OFF-sekvens med seks scanninger, ét på forhånd fastlagt frekvensbånd og en
fuldstændig liste over hits og deres efterfølgende vurdering. En dokumenteret
nul-liste tæller som et analyseresultat; manglende data eller en afbrudt kørsel
gør ikke. Et teknisk testprogram alene opfylder ikke hovedmålet.

Første rigtige referenceanalyse skal fungere senest 11. oktober. Hele pilotens
første teleskopanalyse skal være afsluttet senest 16. oktober, hvis de faglige
kontroller består. En varig blokering udløser straks et skift til en konkret
metodeundersøgelse; 16. oktober er seneste beslutningsfrist. Metodeundersøgelsen
skal give faktisk beregnede recovery-, RFI- og støjresultater, hvis et tilladt
køremiljø består den særskilte kapabilitetsprøve senest 11. oktober.
Vi fortsætter SETI-projektet ved
at ændre en blokeret tilgang, uden at forlænge den samme fejlfindingskampagne.

## Hvad der ændres

1. Kørsel bevises før mere infrastruktur bygges. Én kommando skal kunne hente
   eller læse en lille autentisk reference, analysere den og gemme resultatet.
2. Den nye undersøgelse bruger almindelig reproducerbarhed: kodeversion,
   låste pakker, datakilder, checksums, indstillinger, kommando og log.
   Den søger ikke at genskabe den historiske runtime fil for fil eller bevise
   hvert kernel-/loader-event. Det ændrer ikke den gamle kontrakts udfald.
3. Læser og en enkel lineær driftsøgning genbruges fra eksisterende kode eller
   etablerede værktøjer. Udgangspunktet er blimpy til .fil/.h5 og turboSETI
   som reference for smalbåndssøgning; valget låses før pilotværdier åbnes.
   Den gamle neighbor9-score er ikke automatisk kvalificeret.
4. Analyse og publicering er adskilte. Et gemt, kontrolleret resultat må ikke
   vente på, at GitHub-upload virker. Publiceringsfejl bliver en særskilt
   status, ikke en grund til at gentage selve analysen.
5. Fremskridt måles i data læst, frekvensbredde søgt, ON-eksponering,
   gennemførte kontrolforsøg og vurderede hits. Antal kode- eller
   dokumentpakker tæller ikke som nye teleskopresultater.

## Køremiljø og data

Første valg er et nyt, afgrænset job i det eksisterende offentlige GitHub-repo
med en almindelig Linux-runner. GitHubs officielle dokumentation beskriver
gratis standard-runnere til offentlige repositories. Det er en mulighed,
ikke bevis for at vores job kan startes eller hente de valgte arkivdata.
Adgang, udgående netværk, installation og resultatlagring skal demonstreres
med referencekørslen. En allerede tilgængelig Linux-maskine er alternativet;
adgang til Martins computer eller server antages ikke.

Vi vælger fra metadata ét pilotdatasæt og højst ét alternativ. HD189733/
HIP98505 cadence 85030 er første kandidat, fordi de valgte pilotværdier
fortsat er uåbnede. Det er ikke en allerede godkendt kildekontrakt.
Kildestørrelse, pointing, tidsstempler, frekvensopløsning, ON/OFF-par og
tidligere brug skal bestå nye, udtrykkelige kildekontroller. Hvis kandidaten
ikke kan bruges, vælges alternativet efter den frosne metadata-rækkefølge,
ikke efter synlige signaler. HD1461s pointing-hold bevares.

En separat, allerede offentlig reference/engineering-region anvendes til
første læseprøve og softwareudvikling. Den indgår ikke senere som frisk
pilot eller ueksponeret validering. Små færdige dataprodukter foretrækkes.
Et stort HDF5-arkiv må kun bruges, hvis målte delvise reads faktisk holder
downloadgrænsen; lille RAM-indlæsning betyder ikke automatisk lille download.
Ingen adgangsbegrænsning omgås.

## Kalender og leverancer

| Dato | Arbejde | Krav før næste trin |
|---|---|---|
| 10.-11. okt. | Nyt køremiljø, separat reference og én komplet kommando. Gem waterfall, resultatfil, versioner, checksums og log. Prøv også at beregne og gemme en lille syntetisk metodekontrol. | Senest 11/10 skal et ægte teleskoparray være læst og analyseret. Ellers lukkes ruten og ét påvist tilgængeligt alternativ prøves. Metodealternativets køreevne skal også være demonstreret. |
| 12.-13. okt. | Fastlæg præcis kilde, bånd, drift, tærskel, ON/OFF-regel, masker og nye udviklings-/valideringsidentiteter. | Protokollen og konfigurationen skal være gemt og kontrolleret før pilotens søgeværdier eller nye valideringsudfald åbnes. |
| 14.-15. okt. | Nye adskilte signal-, interferens- og støjkontroller. Gem alle udfald og tab. | Recovery-, RFI-, støj- og data-integritetskrav skal bestå. Højst én udviklingsrettelse; derefter helt frisk validering. |
| Senest 16. okt. | Kør første seks-scans pilot i det låste bånd. Søg alle erklærede bærefrekvenser og gem samtlige hits. | Færdig resultatliste, seks ON/OFF-paneler, målt dækning og afsluttet log. Ved fortsat blokering skiftes samme dag til metodeundersøgelsen. |
| 17.-18. okt. | Følg hvert overlevende hit i de parrede OFF-scans og øvrige ON-scans. | Hvert hit får forklaring eller status: afvist efter fast regel, uafklaret eller kræver uafhængig observation. |
| 19.-21. okt. | Ved bestået pilot: én ekstra uafhængig sekvens valgt på forhånd. Ellers afslut metodeundersøgelsen. | Højst to pilotsekvenser i perioden. Ingen udvidelse efter attraktive amplituder. |
| 22. okt. | Gentag én repræsentativ analyse fra den gemte pakke i en frisk proces; helst også et uafhængigt tilgængeligt miljø. | Kilder, indstillinger og centrale outputs skal stemme. Det er reproduktion, ikke nye observationer. |
| 23. okt. | Samlet rapport og reproduktionspakke med alle faktisk opnåede data, logs, plots og kontrol-/hit-resultater. | Tydelig konklusion: teleskopsøgning, metodeundersøgelse eller dokumenteret kørselsblokering. Ingen automatisk forlængelse. |

## Faglige minimumskrav

Protokollen på 12.-13. oktober skal udfylde følgende før validering og sky-pilot:

- Korrekt måling: fuldstændige efterspurgte rækker, kanalretning, enheder,
  absolutte frekvenser, tidspunkt og ON/OFF-identitet. En manglende række
  er en fejl, aldrig et tomt videnskabeligt resultat.
- Afgrænset søgning: start med 4.096 sammenhængende native kanaler pr. scan.
  Dette er båndet af søgte frekvenser ved et fast referencetidspunkt, ikke
  nødvendigvis hele det udlæste bånd. Interval, bredde i Hz og referencetid
  låses fra metadata før værdier ses. Udlæsningen skal desuden rumme en
  særskilt budgetteret rand til maksimal drift gange tidsafstand fra
  referencetiden, linjebredde og matchtolerancer. Opgør faktisk dækkede
  bærefrekvenser efter kanttab og masker. Første driftområde foreslås +/-4 Hz/s;
  faktisk grid vælges fra kanalbredde og tidsbaseline, ikke det gamle
  0,1-Hz/s-grid. For påstået smalsporsdækning må halv-grid-mismatch højst
  være en halv kanal over den tidsbaseline, som modellen faktisk bruger.
  Hvis dette ikke passer inden for ressourcerne, begrænses området før freeze.
- Udvikling, frisk validering og sky-pilot har forskellige data/seed-identiteter.
  De gamle 112+128 holdouts og den uaktiverede 127/24-allokering genbruges ikke.
  Allerede gennemført matematik for empty-aware ranks kan genbruges som
  dokumenteret metodeviden, ikke som ny empirisk validering.
- Valideringsmål: et nyt fast panel med mindst 12 stærke signalforløb
  skal alle genfindes. Mindst 48 forløb på et på forhånd fastlagt arbejdsniveau
  skal give mindst 44 genfund. Et genfund er korrekt lokaliseret inden for
  frosne frekvens-/drifttolerancer og overlever hele analysen, inklusive
  OFF-reglen. Foreløbige ON-genfund og endelige genfund rapporteres separat;
  tab opgøres efter drift, aktivitetsmønster, kanter og masker.
  Test både en enkelt aktiv ON-scan og gentagen aktivitet. Mønsterspecifikke
  systematiske fejl stopper den berørte dækning, selv hvis totalen består.
- Mindst 24 styrkematchede ON+OFF-interferensforløb skal afvises efter
  den låste OFF-regel; ingen må overleve som pilotkandidat i dette panel.
  Separat rapporteres single-scan-transienter, nær-spors OFF-forurening og
  mindst 32 uafhængige, friske støjforløb. I dette panel må højst ét forløb
  give en endelig kandidat efter hele den låste kæde. Denne støjgate og
  tærsklen fryses før udfaldene ses. Disse små paneler er foreløbig
  metodeafprøvning, ikke bevis for en universel lav fejlrate.
- EMPTY bevares som et gyldigt nuludfald. Hvis en rank-metode benyttes,
  ligger EMPTY under endelige scores, ties tælles konservativt inklusive,
  og et helt tomt observeret/reference-eksperiment får p=1. Rank-referencer
  er nye og adskilt fra de 32 friske støjvalideringer. Referenceantal M og
  beslutningstærskel fryses; mindste p=1/(M+1) skal kunne nå tærsklen.
  Støjmodel og eventuel tærskelberegning låses før validering. Et Gaussian-rank
  resultat gælder kun den erklærede syntetiske lov, ikke teleskopets RFI.
- Alle ON-hits bevares. En enkelt ON-forekomst slettes ikke alene, fordi
  den ikke gentages; intermittens er et muligt udfald. Tilbagekomst kan
  prioritere opfølgning, men er ikke alene bevis for kunstig oprindelse.

Et bestået kontrolpanel tillader kun den beskrevne eksplorative pilot. Vi
påstår ikke en kalibreret sky-false-alarm-rate, flux/EIRP-grænse, planetarisk
eller kurvet-spors-komplethed eller et populationsresultat. De seks scanninger
i én session kaldes ikke tre uafhængige observationsbesøg.

## Stopgrænser og alternativt resultat

Infrastruktur får højst to konkrete ruter og højst 90 minutters aktiv
fejlfinding pr. rute. Ingen proces-tracing-/runtime-redningskampagne overtager
resten af perioden. En deterministisk adgangsfejl eller manglende fil lukker
ruten; en dokumenteret ny årsag kan senere begrunde en særskilt tilgang.
For en reelt midlertidig overførsels-/publiceringsfejl tillades højst ét
ekstra forsøg. Et tvetydigt forsøg kontrolleres før nogen gentagelse.

Planens nye, foreløbige ressourcegrænser er 0 kr., højst 4 GiB RAM,
2 GiB modtagne kildebytes pr. pilotsekvens, 256 MiB til engineering-reference,
højst 4,25 GiB modtagne kildebytes samlet og 8 GiB lokal arbejdsplads,
30 minutters vægtid pr. analysejob og 12 CPU-timer samlet til nye beregninger.
Alle kørslers tid/bytes og outputstørrelser logges; også fejl tælles.
Grænserne verificeres og låses senest 13. oktober. Kan første mål ikke passe,
vælges et mindre bånd/dataprodukt før freeze; grænserne hæves ikke lydløst.
Gamle reservationssubtotaler er ikke et nyt brugsmål eller et nulstillet budget.

Hvis pilotgaten ikke kan passere, skiftes straks og senest 16. oktober til en
afgrænset, faktisk kørt metodeundersøgelse: recovery som funktion af styrke
og drift, aktivitetsafhængige tab, ON/OFF-interferens, empty/null-opførsel,
runtime og en kommandobaseret reproduktionspakke. Den mærkes tydeligt
"metodeundersøgelse; ingen gennemført ny sky-søgning". Det er ikke en
invitation til at skrive flere generiske runtime-komponenter.

Metodealternativet kræver også et fungerende miljø. Hvis ingen tilladt rute
kan beregne og gemme kontrolresultater senest 11. oktober, dokumenteres den
konkrete kapabilitetsfejl og en tydeligt mærket, endnu ukørt jobpakke.
Der loves da hverken beregnede metodeudfald eller en gennemført sky-søgning.

Nye betalinger, betalte maskiner, teleskopbooking og beskeder til andre er
ikke en del af planen. Uafklarede historiske kandidater og LS/CHEOPS-status
bevares. Kalenderen er arbejdsmilepæle; den lover ikke, at chatten kører
vedvarende i baggrunden. Automatisk kørsel tæller først, når et rigtigt
worker-/CI-job og dets første fulde kørsel er verificeret.

## Grundlag og kilder

- Projektstatus ved da3b97b1a804a99189ff28d7e226be5490cf925c:
  https://github.com/andersenmartin-blip/setisearch/blob/da3b97b1a804a99189ff28d7e226be5490cf925c/PROJECT_STATUS.md
- Oprindelig kalibrering og uåbnede evalueringer:
  https://github.com/andersenmartin-blip/setisearch/blob/da3b97b1a804a99189ff28d7e226be5490cf925c/RADIO_HD189733_PANEL_2026-09-28_RESULT.md
- Periodens blokeringer og ressourcebegrænsninger:
  https://github.com/andersenmartin-blip/setisearch/blob/da3b97b1a804a99189ff28d7e226be5490cf925c/RADIO_CLOSURE_2026-10-07_PREPARATION.md
- blimpy: https://github.com/UCBerkeleySETI/blimpy
- turboSETI: https://github.com/UCBerkeleySETI/turbo_seti
- GitHub-standardrunnere:
  https://docs.github.com/en/actions/reference/runners/github-hosted-runners

Eksterne værktøjsmuligheder er kontrolleret mod deres officielle dokumentation
7. oktober. Software-/runner-adgang og det nye forsøgs resultat er endnu ikke
afprøvet. Planens tal er fremadrettede mål og budgetter, ikke nye observationer.
