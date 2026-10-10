# Første headere for2019-09-14/session23/blc66

Dette er et separat metadataforløb for seks præcise primærarkiv-URLer. Koden er
ikke kørt i sourceforberedelsen. Den hentede metadatahistorik og de tidligere
blc40-fejl bevares; ingen tidligere prefix- eller continuationrange genhentes.

Før start skal root fastlåse og læse alle kildefiler tilbage fra den offentlige
commit. Derefter skriver root en særskilt `results/radio_visit2019_blc66_headers_20261010/ROOT_ADMISSION.json`
med den præcise scope/code/commitbinding, frisk request- og ejerskabskontrol,
faktisk global BODY-reservation uden refundering samt faktisk plads under12GiB.
`ROOT_ADMISSION_TEMPLATE.json` er ikke en gyldig admission og kan ikke bruges.

```bash
python /workspace/scratch/a8d1e29996d0/setisearch_fullpower/tools/radio_visit2019_blc66_headers_20261010/header_probe_v1.py \
  --scope /workspace/scratch/a8d1e29996d0/setisearch_fullpower/tools/radio_visit2019_blc66_headers_20261010/initial_scope.json \
  --expected-scope-sha256 EXACT_SCOPE_SHA256 \
  --expected-wrapper-sha256 EXACT_WRAPPER_SHA256 \
  --public-freeze-commit EXACT_PUBLIC_SOURCE_COMMIT \
  --root-admission /workspace/scratch/a8d1e29996d0/setisearch_fullpower/results/radio_visit2019_blc66_headers_20261010/ROOT_ADMISSION.json \
  --expected-root-admission-sha256 EXACT_ROOT_ADMISSION_SHA256 \
  --root-go-header-metadata-only
```

Højst seks HEAD og seks GET af bytes0–4095 er mulige:24.576 konservativt
reserverede BODY-byte,60 CPU-sekunder inklusive imports,600 vægsekunder,
512MiB RAM og32MiB output. Der er ingen redirects, retries, automatisk
completion, chunkindex eller datasetværdier. Alle partielle bytes og alle
request-/metadatafejl bevares i en create-only `initial`-mappe; en afsluttet eller
fejlet mappe kan ikke genbruges af helperen.

Runtime åbner kun ti allerede eksisterende ejer-guards read-only og holder
kernelLOCK_EX gennem forsøget. Den opretter eller skriver ingen ejer-guard og
certificerer ikke global ejerinaktivitet. Rootadmissionen binder præcist det
afgænsede historiske requestregister og den supplerende kontrol af de to
arbejdsrødder. Runtime genkontrollerer disse fastlåste metadatafiler og foretager
ingen yderligere bred directoryscan. Root skal klassificere eventuelle nye
omtaler som plan, egen spejling eller separat ejet datafase før admission.

H5py får kun retained-prefix-cache og må læse attrs/shape/dtype/chunks samt
creation-filtermetadata. Et cachemiss gemmes med offset/længde og stopper uden
en HTTP-callback. `HEADER_RESULT.json` og `EXECUTION_RECEIPT.json` skelner
ufuldstændige headere fra et metadata-PASS. Per-source-metadata er ikke en
kvalificeret fælles geometri: top-level `geometry` og `midpoint` forbliver unset.

Et efterfølgende pointerbaseret completion- eller indeksforløb kræver et nyt
scope fra de faktisk retainedblc66-prefixer. Geometri fra de gamle blc40-headere
eller2017-filer må ikke kopieres. Protected-registeret er eksplicit ufuldstændigt;
kildedata, OFF-kvalifikation og uafhængig signalvalidering er fortsat blokeret.
Procesressourcer i helperreceipt omfatter sidste HEADER_RESULT-serialisering;
den ydre kommandoreceipt bør måle hele processen inklusive sidste receipt/close.
