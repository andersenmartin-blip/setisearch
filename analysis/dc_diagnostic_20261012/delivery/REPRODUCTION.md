# Reproduktion af DC-diagnosen

Dette er et selvstændigt pakkelayout. Udpak ZIP til en ny mappe med `dc_study/` og `seti_previous/` som søskende. Publicerede kodekopier under GitHub `analysis/dc_diagnostic_20261012/` skal placeres i dette layout, ikke køres direkte med det relative bibliotekstræ fra repository.

Pakken indeholder de 108 oprindelige rå503-kapsler og normaliseringer, de to context-JSON-filer, seks TOP20/TOP3-ranglister og de 18 primære geometri-auditkapsler. Den indeholder kun disse afgrænsede eksisterende data og deres forudsætninger, ikke fulde telescope-HDF5-filer. Fuldkerne-normaliseringerne forbliver betingede gemte inputs.

Primærkoden kører én gang i et nyt outputtræ med de nøjagtige scope- og driverhashes:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 dc_study/primary/driver.py --run --scope-sha256 c01a4397bb52f536300c2e3f9692bed01f8c639868cd92ff1c01332e8e2a9b32 --driver-sha256 5c881284d499a2d26e6a97df21c7933365ea37c7a80fb8110f1b92615829529f
```

Det gemte originalresultat-træ må ikke overskrives. Brug en separat kopi med en ny primærresultatmappe ved en egentlig reproduktion. Scope-inputpins og ZIP MANIFEST.json skal verificeres først. De bevarede scripts fastlægger også ranking-GO og selvstændig QA. Python-/NumPy-versioner og ressourcekvitteringer er i hver udførelseskvittering. Der er ingen detektorrekørsel eller telekop-HTTP-kald. Report-rendereren bruger kun gemte afledte resultater.
