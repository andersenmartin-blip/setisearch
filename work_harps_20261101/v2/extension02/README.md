# HARPS extension02: 100 yderligere eksponeringer

Dette er en prospektivt fastlagt udvidelse. Ved frysningen er ingen af de 100 nye spektralfiler hentet eller åbnet. Udvalget, hentningsreglerne og kørekoden skal udgives og verificeres i et Git-commit før hentning. De oprindelige V1/V2-algoritmer, konfigurationer og kataloger ændres ikke.

Udvalget indeholder 100 nye eksponeringer fordelt på 16 af de oprindelige 20 mål: 86.849,578 sekunder (24,125 timer), heraf 74 mål/nat-kombinationer uden tidligere projektdata. De fire mål HD114082, HD115031, HD119130 og HD13445 har ingen ubrugte, kvalificerede eksponeringer i den fastholdte metadataudtrækning. Vi bevarer udvælgelsesreglen og benytter derfor de øvrige 16 mål. Udtrækningen indeholder 404 kvalificerede, ubrugte eksponeringer inden de 100 vælges.

`MAIN100.csv` indeholder udvalgte ADP-ID'er, rå progenitor-ID'er, metadata, kildelinks, rækkefølge og rollen `extension02_unopened`. Alle 100 er verificeret mod ESOs aktuelle metadata og provenance-tabel. `PRIOR209.json` udelukker alle 200 tidligere hovedeksponeringer samt ni udviklings-/valideringseksponeringer på ADP-ID, rå ID og mål/starttid. Ingen af de 100 matcher det fastlåste litteraturprojekts ADP- eller rå-ID-inventar ved commit `195bb3e3e4d067b153895fd2723f839f00e8f82a`.

Fravær i dette inventar dokumenterer **ikke**, at ingen tidligere har undersøgt dataene. Metadataudtrækningen er de oprindelige 5.000 alfabetisk afgrænsede rækker; den er ikke en fuldstændig eller repræsentativ optælling af HARPS-arkivet. De oprindelige metadataforespørgsler, udvalgsregler, fravalg og kontrolresultater ligger i `../next_sample/` og er omfattet af kildehashene.

## Fastlagt hentning og analyse

- Højst 700.000.000 response-body-bytes samlet, inklusive mislykkede forsøg, og højst 10.000.000 bytes per fil. Metadataestimatet er 538.889.216 bytes; faktisk størrelse registreres ved hentning.
- Tre samtidige arbejdere, højst to forsøg per fil med 20 og 60 sekunders timeout. Ingen nye forsøg startes efter 900 sekunder. Fejlede læsninger debiteres konservativt deres fulde reservation; HTTP/TLS-overhead er ikke målt.
- Kun de udvalgte 1D-produkter hentes. Ancillary-TAR- og råfiler hentes ikke. Ingen automatisk udskiftning af fejlede observationer eller genoptagelse af en afbrudt hentning.
- Før analyse kontrolleres SHA256, FITS-format, instrument, ADP-ID, præcist rå-ID fra metadataforespørgslen, objektnavn, tidspunkt, eksponeringstid, katalogposition, tilsigtede koordinater, observation/proposal, bølgelængdeenheder, luftbølgelængde, barycentrisk reference og endelig BERV-værdi.
- Fejlede eller afviste inputs beholdes i udvalget og rapporteres eksplicit. Kun filer med alle metadatakontroller bestået analyseres; der sker ingen erstatning.
- Den uændrede V1 og V2 kører separat under `production/`. Godkendte profiltræf får ID'er `V2E2-0001` osv.; V1-træf `V1E2-0001` osv. Rækkefølgen følger det frosne udvalg og algoritmernes uændrede eventrækkefølge. De gamle 333 V2-events sammenflettes ikke med dette katalog.
- Hvert nyt træf starter som `UNREVIEWED`. Profiltræf er ikke påviste lasere. De tidligere 192 injektionsforsøg er betingede valideringsresultater og må ikke omfortolkes som målt følsomhed for denne udvidelse.

## Kørsel

Kommandoer køres fra `work_harps_20261101` med projektets eksisterende Python-miljø. En preflight læser kun kode og metadata:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/scratch/9ddca116b0b1/python_deps python v2/extension02/acquire.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/scratch/9ddca116b0b1/python_deps python v2/extension02/verify_guards.py
```

Root skal først publicere og verificere `FREEZE.json`, alle nye kildefiler angivet deri og metadatafilerne fra `next_sample/`. Herefter indsættes det observerede fulde Git-commit og SHA256 af den publicerede `FREEZE.json` i følgende kommando. Argumenterne er en registreret attestering fra root; scriptet foretager ikke selv GitHub-verifikation:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/scratch/9ddca116b0b1/python_deps python v2/extension02/acquire.py --download --freeze-commit COMMIT_SHA40 --published-freeze-sha256 FREEZE_SHA256
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/scratch/9ddca116b0b1/python_deps python v2/extension02/run_main.py
```

`acquisition/PUBLICATION.json` gemmer commitattesteringen. `ACQUISITION_SCOPE.json`, individuelle receipts, manifest og resultat gemmer alle forsøg og kontroller. Analyseprodukterne gemmer hashes, inputstatus, alle screenede events, de accepterede træf og en særskilt dispositionstabel. Eksisterende outputmapper må ikke overskrives. Afbrudte kørsler kræver dokumenteret håndtering før en ny kørsel; scriptet genstarter ikke skjult.

`freeze_scope.py` blev kun brugt til den lokale frysning før hentning. Scriptet afviser refrysning, hvis en data-, acquisition- eller production-mappe eksisterer. Efter publicering er den publicerede `FREEZE.json` autoritativ og må ikke erstattes under samme prospektive protokol.
