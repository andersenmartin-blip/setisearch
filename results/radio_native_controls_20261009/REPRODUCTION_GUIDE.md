# Reproduktionsgrundlag for de nye native kontrolanalyser

Begge analysejob blev faktisk kørt 9. oktober 2026 efter separate offentlige
frysninger. Kode, inputs, settings og målte outputkvitteringer er bevaret. Denne
vejledning er en manuel reproduktionsmulighed, ikke en ekstra kørsel eller et
verificeret baggrundsjob. Reproduktion giver ingen nye observationer.

## Miljø og filplacering

Se `ENVIRONMENT.json` for det faktiske miljø: Python 3.12.14, NumPy 2.3.5,
SciPy 1.17.0, h5py 3.15.1, hdf5plugin 7.1.0 og Matplotlib 3.10.8. Programmerne
sætter fire numeriske trådvariable til 1 før imports. Det er en ny almindelig
runtimeidentitet; gamle låste runtime-/holdoutkrav ændres ikke.

Læg checkoutet i en mappe med navnet `setisearch_work`. Dets forælder er den
`--workspace`, som de frosne inputstier er relative til. Bevar de tre eksisterende
inputarkivers bytes og udpak dem i forælderens `seti_inputs` som nedenfor:

- `SETI_RADIO_CACHED_SIGNAL_CHUNKS_2026-10-09/arrays/`: seks originale kompakte HDF5-filer.
- `SETI_SIGNAL_RESULTS_2026-10-09/broad_inventory/`: seks eksisterende spektrale NPZ-filer.
- `SETI_ON_OFF_EXCESS_2026-10-09/`: tre eksisterende ON-kontrastarrays.

De oprindelige arkividentiteter ligger i de tidligere Git- og artefaktindeks.
Programmerne kontrollerer hver anvendt fil ved størrelse og SHA256 før de nye
beregninger. De tekstlige inputs fra det aktuelle checkout skal matche deres
frosne pins; ingen pin må ændres for at få et mismatch til at passere.

Det nye `SETI_NATIVE_CONTROLS_2026-10-09.zip` bevarer 15 binære arrays/figurer
med eget SHA256-payloadindeks. Det rummer de nye resultater, ikke alle de
oprindelige kildearkiver eller repoets kode-/JSON-tekster. Arkivets ejertilgang
gør det ikke anonymt offentligt tilgængeligt.

## Faktiske kommandolinjer

Fra forælderen til `setisearch_work`, erstat `<workspace>` med dens absolutte
sti. Outputmapper skal være nye og fraværende før start. De oprindelige mapper
må ikke overskrives. En lukket fejl må ikke genkøres som ny validering.

```bash
python3 setisearch_work/tools/radio_native_controls_20261009/native_controls.py \
  --scope setisearch_work/tools/radio_native_controls_20261009/scope.json \
  --workspace <workspace> \
  --spectra-dir seti_inputs/SETI_SIGNAL_RESULTS_2026-10-09/broad_inventory \
  --original-dir seti_inputs/SETI_ON_OFF_EXCESS_2026-10-09 \
  --cache-dir seti_inputs/SETI_RADIO_CACHED_SIGNAL_CHUNKS_2026-10-09/arrays \
  --outdir <ny-mappe-til-kontrolresultat>

python3 setisearch_work/tools/radio_native_controls_20261009/ranked_time_panel.py \
  --scope setisearch_work/tools/radio_native_controls_20261009/ranked_time_scope.json \
  --workspace <workspace> \
  --cache-dir seti_inputs/SETI_RADIO_CACHED_SIGNAL_CHUNKS_2026-10-09/arrays \
  --outdir <ny-mappe-til-tidspanel>
```

Det andet job bruger sine eksakte, allerede gemte rang-/tids-JSON-inputs. Det
gentager ikke første søgning eller de 16 eksisterende profiler. Sammenlign
videnskabelige arrays og tabelværdier med de bevarede originaler; nye receipts
vil naturligt have andre CPU-/vægtidsmål. Figur-/ZIP-byteidentitet i et andet
miljø er ikke blevet efterprøvet. Ingen yderligere reproduktionskørsel udførtes
ved udarbejdelsen af denne vejledning.

## Videnskabelig status

Alle 120 profiler er eksplorativt udvalgt fra det samme historiske besøg. Data
er korrelerede, OFF er ikke certificeret støjfri, og ingen udvekslelighed eller
binomial signifikans antages. A/B forbliver FAIL_CLOSED; de syv svage ON-spor er
uafklarede. Et nyt miljø-PASS eller samme tabel er ikke en kvalificeret pilot,
uafhængig himmelbekræftelse eller detektion.
