# D002: særskilt HARPS-søgning på friske stjerner

## Offentlig metode før nye signalværdier

Denne fase følger [D001-leverancekontrollen](../work_seti_20261105_d001_delivery/README.md). Den bruger det allerede fastlagte udvalg på **50 hovedeksponeringer af ti andre stjernenavne** samt **fire kontrolspektre fra to yderligere stjerner**. Udvalget og alle mangler fastholdes; der indsættes ingen erstatningsobservationer efter at signalværdier er åbnet. Dette dokument beskriver den prospektive metode, ikke et allerede gennemført resultat.

De tre aktuelle, gemte ESO-metadataforespørgsler giver 54 hovedproduktposter, 108 produkt-/ancillaryposter og 54 entydige råforløbere. Alle 54 passer til de fastlagte metadata; ingen ADP- eller rå-ID'er overlapper de oprindelige 309 input eller den kendte publicerede referenceliste. Det beviser ikke, at ingen tidligere har søgt i data. Kataloget er fortsat den afgrænsede, alfabetiske 5.000-rækkers prøve. Se [metadata og alle 54 checks](metadata/VERIFICATION.json) og [den faste liste](metadata/VERIFIED_COHORT54.csv). Der er endnu ikke hentet science-FITS eller åbnet nye signalværdier ved metodefrysningen.

## Data, headerkrav og bevaring

Hent kun de 54 kontrollerede URL'er. Brug tre samtidige hentninger, højst to forsøg med 20/40 sekunders timeout, otte MB pr. fil og højst 700 MB konservativ afregning. Hvert forsøg afregnes med hele otte MB, også når en læsning fejler; komplette returnerede kroppe måles også særskilt. Nye forsøg må ikke starte efter ti minutter. HTTP 401/403/404 genprøves ikke. Fejl og de valgte observationer bevares uden udskiftning.

En komplet, polstret FITS-fil skal have passende Content-Length. Inspektionen læser kun de to headers og bekræfter mål, koordinater, eksponeringstid, tidspunkt, råforløber, enkelt-eksponering, luftbølgelængde, barycentrisk frame, ADU-enhed, nominelt 0,01 Å-grid, opløsning 115.000 og endelig BERV. Spektralværdier må først åbnes efter godkendte headers og verificerede SHA256-hashes. Målidentitet betyder her katalog-/header-/pegningskonsistens, ikke en ny uafhængig Gaia-identifikation.

Alle præcise nye FITS-input skal arkiveres med filhashes, før en komplet leverance hævdes. Rå science-filer er udelukket fra Git; source-indekserede kontroludsnit og træfvinduer medtages som NPZ. Delvise filer bruges aldrig som input. De gamle science-filer og kataloger ændres ikke.

## Uændret detektor og nye kontroller

V2-koden og konfigurationen er præcis de tidligere publicerede versioner: 3800–6900 Å, sidebåndsbaseret lineær baggrund og MAD, amplitude/MAD mindst seks, profilcosinus mindst 0,8, fast Gaussian-bredde bølgelængde/115.000 samt den eksisterende forhåndsscreening, maskering og dubletregel. Der køres ikke en ny V1-analyse i denne fase. Scorer er ikke kalibreret statistisk signifikans.

Kontrolstjernerne er HD142022 og HD142415, to observationer af hver. De seks på forhånd valgte positioner er **3807,13; 3861,29; 4233,17; 4932,47; 5779,53 og 6617,31 Å**. Hver krydses med pixelplaceringerne 0, 0,25 og 0,5 samt styrkerne 4, 8, 16 og 32 gange den oprindelige lokale populationsspredning. Der er 288 faste forsøg, 24 unikke 1.001-punktsudsnit og 72 parrede geometrier; forsøgene er afhængige.

Gaussian-profiler samples punktvis på det originale grid. Ingen originalværdi klippes til positiv flux. Nærmeste gridpunkt vælges med en 10⁻⁹ Å-bindingsregel, hvor det laveste indeks vinder. Spredningen måles over de oprindelige 101 punkter omkring dette indeks med ddof=0. Genfinding kræver et accepteret V2-center inden for 0,02000001 Å. Eksisterende match i uændrede kontroludsnit registreres særskilt. Ikke-finite/zero-fill/ufuldstændige udsnit eller manglende positiv spredning beholder alle deres faste ikke-vurderbare slots. Styrke, bølgelængde, stjerne og manglende vurderbarhed rapporteres hver for sig. De fire komplette kontrolspektre søges separat, uden at deres træf tælles med i hovedprøven eller automatisk kaldes falske positiver.

Metoden tilpasses ikke efter kontrollen. Hovedsøgningen køres efter samme faste regler på alle headergodkendte hovedinput, og dens fortolkning begrænses af alle kontroludfald. Lav genfinding giver en følsomhedsbegrænsning, ikke en skjult ændring af tærsklen. Kontrollerne gælder reducerede 1D-data fra to stjerner, ikke hele instrumentkæden, alle stjerner eller en global falsk-alarm-rate.

## Hovedsøgning og faste checks

Gem alle 50 observationsslots med status, eksponeringstid og faktisk søgte punkter. Alle screenede hændelser, afvisninger, dubletter og accepterede træf bevares. Træf får `D002-0001` osv. i den fastlagte observationsrækkefølge og detektorens eksisterende seedrækkefølge. Deres første status er `UNREVIEWED_1D_TRIGGER`. Der laves ingen fysisk råklassifikation i denne første søgning. Manglende gentagelse afviser ikke en enkeltstående linje.

Den særskilte numeriske kontrol rekonstruerer støj, Gaussian-indsættelser og profilfit med Python-skalarmatematik. Alle vurderbare kontrolforsøg genafspilles, alle accepterede hovedtræfs fit og source-udsnit kontrolleres, og de faste hovedpositioner **1, 25 og 50** reproduceres komplet, hvis deres input er godkendte. Tolerancer er relativt 10⁻⁹ og absolut 10⁻⁸. Et sådant check er samme assistents efterregning, ikke en uafhængig agent- eller forskervurdering. Syntetisk præflight kontrollerer 18 Gaussian-tilfælde inklusive negative baggrunde og seks enkeltpixelafvisninger; ingen science-arrays indgår.

Alle accepterede hovedtræf vises i et atlas med 12 paneler pr. side i den originale rækkefølge og ±0,75 Å display omkring det gemte center. Originale signed fluxpunkter og det gemte fits model vises. Kontrolfiguren opdeles efter stjerne, bølgelængde og styrke; manglende nævnere skjules ikke. Figurerne er 1D-kontekst og afgør ikke råt ophav.

## Kørsel efter verificeret offentlig metode

`FREEZE.json` binder metadata, kode, originale detektorfiler og konfiguration. Hentning og science-kørsler kræver en `PUBLIC_METHOD_READBACK.json`, der dokumenterer nøjagtigt offentliggjorte filer og nul nye science-værdier ved readback. Alle outputmapper er engangskørsler; reproduktion skal ske i en separat kopi.

```bash
python3 work_harps_20261105_d002_fresh/acquire.py
python3 work_harps_20261105_d002_fresh/run_science.py controls
python3 work_harps_20261105_d002_fresh/run_science.py main
python3 work_harps_20261105_d002_fresh/numerical_audit.py observed
python3 work_harps_20261105_d002_fresh/plot_results.py
```

Budgettet er 0 DKK. Ingen betalt tjeneste, ny konto eller forskerkontakt indgår. Rubin genåbnes ikke, og de afsluttede gamle diagnoser gentages ikke. Den separate søgning kan give uafklarede træf eller begrænset genfinding; den giver ikke automatisk en kvalificeret laserkandidat eller et kalibreret nulresultat.

Kilde til den benyttede, dokumenterede programadgang: [ESO programmatisk arkivadgang](https://archive.eso.org/programmatic/). Eksakte forespørgsler, rå svar og HTTP-kvitteringer er gemt under `metadata/`.
