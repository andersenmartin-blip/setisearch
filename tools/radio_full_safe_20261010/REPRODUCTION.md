# Reproduktion og bevarede data

De to originale søgekørsler er én gangs kørsler i forskellige mapper. En eksisterende målemappe må ikke slettes for at køre dem igen. En uafhængig reproduktion foretages i en separat kopi af projektet og mærkes som en reproduktion.

Den offentlige fastlåsning før begge kørsler er commit `73168f5f1b2d9d154b10eb381c17b8185c18a880`. Fælles `scope.json` har SHA256 `1e77f78f5c957082da3eebdb1c70641b6ba7687ce2996578ccb5a9caf0287d22`; søgekoden har SHA256 `8758f48de05e139431196c958c9e20b4bd6c24200fc57906245cc91ac4cfe56f`. Begge grupper blev fastlåst før første nye numeriske udfald.

Brug Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, Matplotlib 3.10.8, h5py 3.15.1 med HDF5 1.14.6 og hdf5plugin 7.1.0. De to præcise codec-wheels og deres SHA256 står i `ENVIRONMENT_RESTORATION.json`. Ingen pakker opgraderes ved reproduktion.

De allerede gemte input er:

| Arkiv | Bytes | SHA256 |
| --- | ---: | --- |
| `SETI_GAP_STATIC_CONTEXT_2026-10-10.zip` | 6.206.173 | `c00195d119596d1cf2a42653754a70bfd39e60262b406e59408c4e1759517146` |
| `SETI_FRESH_BAND151_RAW_2026-10-09.zip` | 305.428.707 | `6696fe54086e019ce966816dc818969ca5f1682e3ff9211326f1a68d2323ef1d` |
| `SETI_SIGNAL_FOLLOWUP_2026-10-10.zip` | 6.418.319 | `8cde42def9d1d46dfabc12da56fc7778fd796d260e5e9a985e359cfbe6a4eb70` |

Placér de tre arkiver i `seti_fullpower_work/recovered` ved siden af projektmappen. `recover_saved_inputs.py` er en kopi tilpasset sin offentlige placering; `recovery_executed_layout.py` bevarer den præcise oprindeligt udførte kode, hvis oprindelige placering var `seti_fullpower_work/recover_saved_inputs.py`. Der foretages ingen ny gendannelseskørsel i den oprindelige analyse. `RECOVERY_RECEIPT.json` beskriver de faktisk gendannede 188 medlemshændelser og deres byteidentiteter.

Kør fra projektets rod i den separate reproduktionskopi. Tilføj de fastlåste codecs til `PYTHONPATH`, hvis de ikke er installeret i det aktive miljø:

```bash
python tools/radio_full_safe_20261010/full_safe_search.py \
  --batch 1 \
  --scope tools/radio_full_safe_20261010/scope.json \
  --expected-scope-sha256 1e77f78f5c957082da3eebdb1c70641b6ba7687ce2996578ccb5a9caf0287d22 \
  --compact-dir results/radio_fresh_band_20261009/arrays \
  --acquisition-summary results/radio_fresh_band_20261009/arrays/ACQUISITION_RESULT.json \
  --outdir results/radio_full_safe_20261010/batch_01/measurement
```

Gruppe 2 bruger `--batch 2` og `batch_02/measurement`. Alle andre argumenter er identiske. Hver kørsel kontrollerer de seks kompakte filer og samtlige 96 afkodede rækker. Det verificerer de bevarede udsnit; det er ikke en verificering af de oprindelige hele teleskopfiler mod deres katalog-MD5.

Hvert afsluttet scanningsfelt bevarer alle 4.096 kanalmaxima, vindende drift og bredde, gyldige hypoteseantal og en fuld normaliseringskvittering. Checkpointet henviser til de præcise filer med størrelse og SHA256. Ranglister og profiler fortolkes inden for hver gruppe; profilidentiteten er `(batch_id, track_id)`. Resultatkontrollen genopbygger ranglister fra gemte maxima uden at gentage detektorsøgningen.

Eventuelle ufuldstændige kørsler forbliver ufuldstændige og bevarer deres checkpoints. En figur, en rangliste eller en stærk selekteret score er ikke en kalibreret test af signalets oprindelse. Alle data her er fra samme historiske besøg; A/B og den kvalificerede pilotstatus ændres ikke.
