# Selvstændig numerisk reproduktion

Udpak resultat-ZIP til en ny mappe. Dens søskendemapper er `next_dc/` og `seti_previous/`. Publicerede kodekopier under repository `analysis/dc_free_followup_20261012/` er dokumentation; reproduktionskoden skal bruge pakkens eksplicitte layout.

Verificér først alle `MANIFEST.json` medlemshashes. Den NumPy-only reproduktion læser de 48 fulde rå12096-crops, deres manifest, de 54 rå503-kapsler og normaliseringer samt de hashbundne kanoniske resultater. Den genberegner full16-kernemedianer, median501-residualer, MAD/lokation og alle faste scorer. Den åbner ingen HDF5-fil og kører intet detektorgitter.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 next_dc/qa/context/reproduce_from_saved_crops.py --out replay_receipt.json
```

Eksisterende kvitteringer overskrives ikke. Inputscope og GO er bevaret, så en kopiering til ny rod bevarer de relative identiteter. Python3.12/NumPy2.3.5 var den udførte numeriske runtime; alle konkrete versioner og ressourcekvitteringer er bevaret.

Den fulde historiske rådataautentifikation er en ekstern forudsætning: de 18 HDF5-kompakter og deres oprindelige arkiv-/fil-/rækkehashes. Arkiverne er identificeret i `next_dc/feasibility/RAW_RESTORATION_RECEIPT.json`; selve fuld-HDF5-filerne er ikke kopieret ind i denne ZIP. Crops er afledte bit-identiske udsnit og bevarer den udførte numeriske beregning, men kan ikke alene autentificere enhver celle i de fulde kildefiler.

Udvælgelsens 2.289 oprindelige kernemaksima kan reproduceres fra de bevarede gamle auditindeks, CSV-tabeller og core_max-rå503-kapsler. `select_cached_coremax.py` er bevaret med sit offentligt fastlåste scope; brug en separat kopi med tomt outputtræ ved en sådan genkørsel. Ingen model-falskalarmrate eller ny kvalificeringsgate følger af reproduktionen.
