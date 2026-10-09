# Reproduktion af fast frekvensformdiagnostik

Dette er analyse af allerede udvalgte profiler fra ét besøg 2016-03-17. Det er ikke en ny signaludvælgelse, nulfordelingskalibrering eller kandidatklassifikation.

## Eksakte indgange

- SETI_ON_OFF_EXCESS_2026-10-09.zip: 77.022.050 bytes, SHA256 893e1c804436bd46b36b4569eaff361621e5570e8257c82d27ae2a03570ee88c.
- SETI_NATIVE_CONTROLS_2026-10-09.zip: 86.165.383 bytes, SHA256 07f840fcfb0453f62c96f6dfc084967a24e44d5f71e40ea5af8ea83c2a105e64.

Begge tidligere arkiver er bevaret som brugerens datafiler. Scriptet læser kun hashpinnede patchmedlemmer, ikke de store allerede færdige kontrast-arrays. Ingen HDF5-kilde åbnes og ingen teleskopdownload udføres. Offentlige resultater omfatter de sammenklappede profiler; de originale powerudsnit genbruges fra de tidligere arkiver.

Kør fra repositoryroden med Python3, numpy og matplotlib. De tre threadvariabler begrænser BLAS-parallelitet. Scopes håndhæver CPU, vægtid og hukommelse. Outputmapperne skal være nye:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 tools/radio_shape_20261009/frequency_shape.py --scope tools/radio_shape_20261009/scope.json --reference tools/radio_shape_20261009/original_reference.json --archive INPUTS/SETI_ON_OFF_EXCESS_2026-10-09.zip --output reproduction_seven
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 tools/radio_shape_20261009/family_shape.py --scope tools/radio_shape_20261009/family_scope.json --reference tools/radio_shape_20261009/family_reference.json --seven-profiles results/radio_shape_20261009/seven/FIXED_FREQUENCY_PROFILES.npz --archive INPUTS/SETI_NATIVE_CONTROLS_2026-10-09.zip --output reproduction_panel
```

Paneljobbet genbruger den publicerede eksakte syv-profils NPZ, der er hashpinnet i scope. En ny generering af en NPZ kan have identiske værdier, men forskellig ZIP-metadata/hash; derfor bruges det publicerede input ved eksakt reproduktion. CSV/JSON-måltal er læsbare uden genkørsel.

Job1 scope/kode blev frosset ved e470c95b2db4d8e05e9af2760e707d75afc9be1c. Paneljobbet blev frosset ved b79f4dcb747c5fa90f09c4746a12dfc6846ea5ac. Hver ny måling fandt sted efter nøjagtig Git-genlæsning. Resultaternes receipts opgiver målte processkomponenter, ikke hele sessionens CPU-forbrug. Den fulde konservative debit er 200 CPU-s uden refusion.

For 113 patches rekonstrueres baseline fra allerede gemt power over den oprindeligt valgte bredde minus den gemte residual. Der beregnes ingen ny flankmedian. Alle 120 gamle bredde-1/3-midler kontrolleres først ved deres oprindelige bredde; nye måltal bruger faste vinduer på 1/3/5/9/17 kanaler.

ARCHIVE_ALIAS_EVIDENCE.zip indeholder de nøjagtigt bevarede metadata-bodies, receipts, matches og resultater fra otte nye GETs. Det arkiv er en statisk kildekopi, ikke en downloader. Den dokumenterede headerreceipt-kollision er bevaret i manifestet.

Tekniske navne med “complete selection family” og figurens “complete preselected family” refererer kun til det frosne 120-profils top20-panel. Ingen nulfordeling for millionkanalsøgningen eller uafhængighed er antaget.
