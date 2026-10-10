# Data og reproduktion: S2017, native 170/171/172

Den nye science-fase er afsluttet med otte udførselskvitteringer og to faktiske gemte-output-/kildekontroller med PASS. Nye native 170/172-rådata er faktisk gemt som tre bytepræcise dele. Resultatpakkens byteidentitet og faktiske gemmestatus dokumenteres særskilt i `DATA_PACKAGES.json`, `RESULTS_PACKAGE_RECEIPT.json` og den sanitiserede gemmekvittering; denne tekst påstår ikke i sig selv en afsluttet gemning af RESULTS. Et arkivs egen SHA256 indlejres ikke i det samme arkiv.

## De tre RAW-dele

| Fil | Bytes | SHA256 |
|---|---:|---|
| `SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip.part01` | 209715200 | `ad4be599d3e7da809df1d473c8fa677e0c2581d251fb65d9cc01d90849dd8dbb` |
| `SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip.part02` | 209715200 | `2ad6609f4984c536fc4dbee2223975f756459d681b8c9e1f5c6b8731f149a97f` |
| `SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip.part03` | 184969381 | `d585965102de3ac3cbc9864a92249e0fb660ed6968540249c34e650b880b15ca` |

Alle tre har faktisk per-item-gemmestatus `succeeded`, dokumenteret i [RAW_PARTS_DURABILITY_RECEIPT.json](RAW_PARTS_DURABILITY_RECEIPT.json). Der påstås ingen vellykket gemning af det samlede RAW-arkiv som én fil. Ordnet sammenkædning giver præcis 604399781 bytes med SHA256 `b78521c9f51a47d698af1ea1f8949b5676c843656389655191042a0fbc06817f`. Før opdeling bestod arkivet ZIP-CRC og SHA256 for hvert medlem. Efter kapacitetsarbejdet blev de lokale tre deles bytes, checksums og filidentiteter samt den samlede checksum bekræftet i [RAW_PARTS_LOCAL_RESTORATION_AND_ASSEMBLY_RECEIPT.json](RAW_PARTS_LOCAL_RESTORATION_AND_ASSEMBLY_RECEIPT.json).

Hent de tre dele, [restore_raw_archive.py](restore_raw_archive.py) og [RAW_ARCHIVE_PARTS_PLAN.json](RAW_ARCHIVE_PARTS_PLAN.json). Kontroller de downloadede filers SHA256 mod tabellen, planen og det eksterne `DATA_PACKAGES.json`. Behold planen ved siden af scriptet, eller angiv dens sti med `--manifest`. Målet skal være en ny fil, og der skal være mindst 604399781 bytes +1 MiB fri plads:

```bash
python3 restore_raw_archive.py \
  --parts-dir /path/to/downloaded_parts \
  --output /path/to/fresh/SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip
```

Restoreren verificerer længde/SHA for hver del og det samlede arkiv samt uændret filidentitet under læsning. Den bruger ingen HTTP, HDF5-afkodning eller detektor. Den overskriver ikke et eksisterende mål, og en fejl bevarer dens egen delvise outputfil. POSIX-grænserne er CPU 180 s, RAM 2 GiB og wall 1800 s. Script-SHA er `75fc94179549e33817bb01c4ba47c8881a227cbcc147905f045372980d739fd9`; plan-SHA er `764b48cffa38f72d41b870de4640f5e744339093297c94296b492fa790131a15`. Den uafhængige gennemgang af scriptet er en statisk kodekontrol, ikke en påstand om at gennemgangen udførte samling eller reproducerede science.

## RAW-indhold og autentificeret kilde

RAW indeholder de 12 nye kompakte HDF5-filer, den fulde kilde-/intervalprovenance, de pinnede HDF5-metadata, kode og helpers. ZIP-medlemsstier bevarer de fulde lokale `analysis/...`-stier; `PACKAGE_MANIFEST.json` beskriver hvert medlems længde og SHA. De seks native 171-filer kopieres ikke ind i den nye RAW-pakke.

Den nye acquisition anvendte 192 præcise kilde-GETs: 597792529 modtagne BODY-bytes og 597792721 reserverede øvre BODY-bytes. Der var ingen gentagne GETs eller retries. Dens kvittering, [ACQUISITION_RESULT.json](../results/acquire/ACQUISITION_RESULT.json), har SHA256 `2dd9d1f6f99cb41dbf60d47e28f23771da6b27c6ab786f4945b5696d2449df3e`. Faktisk [kilde-QA](../results/source_review/QA_RECEIPT.json), SHA `21a8edaf91e9a60d3209d33e4620a5f93038aabfafd3910094bd25e0fd66318a`, kontrollerede 12 kompakte filer, 192 komprimerede chunks, 192 afkodede rækkehashes og hele intervalprovenancen.

De 192 komprimerede sidecars er udeladt for at undgå at lagre de samme payloads to gange. Root fjernede dem først efter de tre faktiske gemninger og en ny kontrol af samtlige 192 identiske HDF5-rawchunks under eksklusive kernel locks. De 12 HDF5-input blev ikke ændret; de oprindelige rå hashes er bevaret i acquisition og kilde-QA. [ROOT_RAW_RETENTION_RECEIPT.json](ROOT_RAW_RETENTION_RECEIPT.json) dokumenterer handlingen.

Efter udpakning i et særskilt arbejdsområde kan den medleverede helper kontrollere samtlige komprimerede chunks uden at afkode science-værdier:

```bash
python3 analysis/s2017_next_native/delivery/reconstruct_raw_sidecars.py \
  --root . \
  --acquisition-sha256 2dd9d1f6f99cb41dbf60d47e28f23771da6b27c6ab786f4945b5696d2449df3e \
  --verify-only
```

Udelades `--verify-only`, rekonstrueres alle 192 byteidentiske komprimerede sidecars på de deklarerede create-only-stier. Det kræver yderligere 597792529 bytes og den eksakte h5py/HDF5-runtime. Helperen bruger ingen kilde-GETs, power-afkodning eller detektorkørsel. Verifikation og rekonstruktion er reproduktionskommandoer, ikke påstande om endnu en udført science-kørsel.

## Tidligere native 171 og runtime

De sammenføjede grænser kræver også den særskilt leverede `SETI_S2017_NATIVE171_RAW_2026-10-10.zip`: 466351822 bytes, SHA256 `6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786`. Tidligere acquisition/kilde-QA og filidentiteter refereres i de nye scoper og kvitteringer; den nye RAW-pakke duplikerer ikke disse seks kilder.

De to eksakte h5py/hdf5plugin-wheels på tilsammen 51507696 bytes og deres restaurationsbevis ligger i den tidligere `SETI_FULL_POWER_RESULTS_2026-10-10.zip`: 143418523 bytes, SHA256 `0193d5fe7e822a850be38dacf540a9e77c71b26b3f415d6f5e6c5e8056a33a92`. De kopieres ikke ind i den nye resultatpakke. Den dokumenterede runtime er Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, Matplotlib 3.10.8, h5py 3.15.1/HDF5 1.14.6 og hdf5plugin 7.1.0. Python og de øvrige pakker/base-runtime skal tilvejebringes særskilt; leverancen er ikke et hermetisk miljø. `analysis/runtime/EXACT_DEPENDENCY_RESTORATION.json` (sti fra arkivets rod) og de uændrede science-dependencies bevarer versions-/byteidentiteterne.

## Gemte resultater og reproduktion

Resultatpakkens navn er `SETI_S2017_ADJACENT170_172_RESULTS_2026-10-10.zip`. Dens medlemsmanifest, verifikationskvittering og eksterne `DATA_PACKAGES.json` er de autoritative byteidentiteter. Den afgrænsede payload omfatter 1536 nye kort, 72 faste profiler, alle nye scoper/kode/kvitteringer, eksekveringskontrol, faktisk QA, CSV/JSON/PNG-fortolkninger og runtime-/tidligere 171-identiteter. HDF5, komprimerede raw-sidecars, gamle arkiver og wheels indgår ikke som duplikerede payloads. Git-publiceringen er et kurateret tekstudvalg; alle numeriske NPZ-output ligger i RESULTS. PDF-varianter er ikke medlemmer af denne afgrænsede RESULTS-pakke; rapporternes billedhenvisninger bruger PNG.

Den faktiske indre [output-QA](../results/search/review/QA_RECEIPT.json), SHA `03bea3023fb1a08528a1a8acc0f2bbe40c3944e3a9f48a6e92803810c7b14bdc`, kontrollerede 1524 kort/54 profiler og 668736 rå patchcelleforekomster bitvist. Den faktiske sammenføjede [output-QA](../boundaries/results/review/QA_RECEIPT.json), SHA `48153e180358319feb3906fc719eabc9f224200933aa69eccbe0e20cdb8f1b36`, kontrollerede 12 kort/18 profiler og 222912 forekomster. I alt er 891648 forekomster kontrolleret; tallet angiver ikke unikke fysiske celler eller uafhængige tests. QA rekonstruerede gemte rangordninger/profilaritmetik og fysisk indeksgeometri uden at gentage detektorsøgningen eller åbne nye HTTP-kilder.

Reproduktion af hele source-/output-QA og science kræver begge RAW-leverancer og den dokumenterede runtime. Udførselsdriverne/scoperne låser grid 785, bredder 1/3, tids-/frekvensgeometri, normalisering og de faste efterudvalgte profiler. De bruger faste outputstier og create-only mapper: en genkørsel kræver en særskilt rod med identiske input-/scopepins og tomme målmapper. Overskriv ikke de leverede kvitteringer eller arrays; bevar oprindelige fejltilstande og provenance. De gemte rapporter/CSV/JSON kan gennemgås uden at genkøre science, men en sådan metadata-only gennemgang erstatter ikke empirisk output-QA.

Triplet 170/171/172 dækker 766 af 768 referencekerner: 99.7395833333% og 8.76617431640625 MHz af de erhvervede 8.7890625 MHz. De ydre kerner 170 q0 og 172 q255 er udeladt. Det er samme historiske besøg og et valgt frekvensområde; det er ikke en blind uafhængig replikation, samme-frekvens-bekræftelse eller hele teleskopets S-bånd.

## Bevarede tekniske hændelser

To forsøg på forberedelse af gemning af ét stort RAW-arkiv mislykkedes før finalisering; de tre ovenstående dele er den faktisk gemte repræsentation. Kapacitetskvitteringerne bevarer midlertidig frigivelse/genetablering af del 1/2 samt frigivelse af opaque-checksum-verificerede, rekonstruerbare urefererede præfikskopier. En 44826624-byte HDF5-præfikskopi dukkede igen op byteidentisk før den planlagte manuelle genetablering. Dens ophav er ukendt; manuel genetablering eller oprindelig inodebevaring påstås ikke. Urefererede ZIP-/delpræfikskopier blev tilsvarende kun frigivet efter byte-/præfiksbevis. Disse kopier er ikke videnskabelige input eller resultatpakkepayload.

Dokumentationen omfatter [quarantined auxiliary](../review/AUXILIARY_FILE_QUARANTINE_RECEIPT.json), [reconstructible prefix release](../review/RECONSTRUCTIBLE_AUXILIARY_PREFIX_RELEASE_RECEIPT.json), [reappeared archive prefix release](../review/REAPPEARED_ARCHIVE_PREFIX_RELEASE_RECEIPT.json) og [generated cache release](ROOT_RECONSTRUCTIBLE_ARCHIVE_CACHE_RELEASE_RECEIPT.json). Kilde-/sciencepins og tidligere arkiver er bevaret; der blev ikke udført science-reruns eller gentagne kilde-GETs som følge af kapacitetsarbejdet. [Den uafhængige kvitteringsgennemgang](../review/final_data_availability/INDEPENDENT_RECEIPT_ACCOUNTING_REVIEW.json) er en metadata-only kontrol af de tre gemninger, lokal checksum-/identitetsbevaring og tidligere 171-reference. Private gemme-ID'er indgår ikke i Git-rapporteringen.
