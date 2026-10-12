# Gamma51-kontrol af den fulde burst4-søgning

Dette er en afgrænset syntetisk ingeniørkontrol. Otte fastlagte støjfamilier gennemløber samme geometri som de 96 referencefelter i burst4-søgningen: native udsnit 170, 171 og 172, q = 4 + 8k for k = 0–31. Hver syntetisk power-celle genereres uafhængigt fra Gamma(shape = 51, scale = 1/51). Hvert domæne bruger `Generator(PCG64(SeedSequence(20261012, spawn_key=(familieindeks, domæneindeks))))`, familieindeks 1–8 og domæneindeks 0–95 i kanonisk native/q-orden. Der foretages ét Gamma-kald med formen (16,12096) i float64 og derefter én little-endian float32-konvertering. Ingen redraw eller efterfølgende seed-valg er tilladt. RNG-identiteter, rækkefølge og versionskrav bindes af offentligt fastlåst scope og producentens kildekode før generation.

Forbehandlingen bruger alle 16 tidsrækker i den oprindelige 4096-kanals kerne med 4000 kanalers halo og medianfilter på 501 kanaler. Den uændrede søgefamilie har syv overlappende vinduer på fire rækker, første række 0, 2, 4, 6, 8, 10 eller 12, 159 drifthastigheder fra −4 til +4 Hz/s og bredde én eller tre kanaler. De tre højeste spor vælges inden for hver syntetisk familie. Derpå beregnes 24 identitetsinklusive tilordninger af de fire afrundede centerkanaler for hver af de 24 udvalgte syntetiske TOP3-tuples.

Den fastlagte beregningsdækning er 768 kombinerede kort, 3.145.728 carrier-maksimumforekomster, 7.002.390.528 korrelerede hypoteseforekomster, 3.096 score-auditforespørgsler, 24 syntetiske TOP3-rækkefølgeforespørgsler, 576 permutationsscore-forekomster og 384 rækkecenter-boxforekomster. Antallet af forskellige afrundede centervektorer kan være mindre end 24 pr. tuple. Identiske vektorer og eksakte score-ties må ikke tælles som uafhængige kontroller.

Otte syntetiske familier er de otte sammenligningsenheder. De 24 TOP3-tuples er udvalgte og indbyrdes afhængige inden for familierne. En empirisk sammenligning med de ni tidligere valgte virkelige OFF-spor er betinget af støjmodellen og det tidligere sporvalg. Den giver ingen kalibreret astronomisk falskalarmrate, SNR, følsomhed eller signaloprindelse. En god kronologisk rang beviser ikke tidsmæssig kohærens eller himmeloprindelse og afviser ikke radioforstyrrelser. Ingen ny teleskopobservation, real-data-frekvensdækning, maske, veto eller åbning af beskyttede holdouts følger af kontrollen.

## Bevarede inputs og evidensgrænser

Resultatarkivet indeholder alle nye syntetiske maksimumkort, normaliseringsfiler, score-auditkapsler, rækkefølgekapsler, bevarede rå vindercrops, kode, scope, reviews, kvitteringer og rapportfiler. Tidligere virkelige referencefiler medtages alene som hashbundne JSON-, CSV- og tekstfiler. Der kopieres ingen tidligere NPZ- eller HDF5-kilder til denne pakke.

Hvert syntetisk kort binder sit fulde genererede crops hash, alle 16 rækkehashes og præcise RNG-identitet. Fuld råcrop med formen (16,12096) bevares for hvert forskelligt TOP3-vindende domæne, én til tre pr. familie, højst 24 samlet. De øvrige rå crops kan regenereres fra seeds og hashes, men er ikke indeholdt i pakken. QA må regenerere de samme fastlagte bytes til hash- og rækkemedianverifikation; det er ingen ny realisering. Fuld median501, MAD og winsoriseret lokation rekonstrueres uafhængigt for vinderdomænerne. Andre lokale scoreaudits er betinget af gemte kernetermer. Dette efterprøver ikke selv alle maksimumværdier ved ny maksimering af hele søgefamilien. Den færdige QA-kvittering afgrænser de faktisk gennemførte kontroller.

For de tidligere virkelige referenceværdier er den lokale aritmetiske QA betinget af gemte fuldkerne-MAD/skaler og winsoriserede lokationer, som ikke er uafhængigt fuldt refiltreret. Denne begrænsning må ikke overføres stiltiende til syntetiske rå-vinderkontroller eller skjules i sammenligningen. Se den nye QA-kvittering for, hvilke syntetiske normaliseringsparametre der faktisk er uafhængigt rekonstrueret.

## Uafhængig senere reproduktion

Udpak i en separat ren projektrod, og bevar alle relative medlemsstier. Brug versionskravene i scope og de afsluttede producentkvitteringer. Arkivet indeholder ikke runtime-wheels. Kontrollér først den eksterne arkivkvitterings fulde ZIP-SHA256 og den indlejrede `RESULT_PACKAGE_MANIFEST.json`, inklusive alle medlemsstørrelser, SHA256-værdier og ZIP-CRC. Manifestets egen SHA256 står i den eksterne kvittering, så ingen hash er cirkulær.

En senere uafhængig regeneration må kun bruge de fastlagte seeds, RNG-versioner, native/q-geometri, normalisering, søgegrid, tie-regler og udvælgelsesrækkefølge. Brug særskilte nye outputmapper. En genkørsel af den fulde søgning er en ny numerisk reproduktion; den er ikke autoriseret af denne dokumentation i den aktive fase. Bevar de oprindelige afsluttede og eventuelle fejlede kvitteringer uændret.

Kildekontrollerne nedenfor er alene interfacekontrol og åbner ingen arrays eller gemte resultatmetadata:

```bash
python "$PROJECT_ROOT/analysis/burst_null_20261012/build_delivery.py" --check-only
```

Selve pakningen udføres kun af root efter offentligt fastlåst kode/scope, en konkret root-GO-kvittering, otte afsluttede numeriske familier, uafhængig bestået QA samt gennemgået rapport og figurer. Brug de faktiske hashes fra de afsluttede kvitteringer:

```bash
python "$PROJECT_ROOT/analysis/burst_null_20261012/build_delivery.py" \
  --root "$PROJECT_ROOT" --build \
  --scope-sha256 "$SCOPE_SHA256" \
  --script-sha256 "$PACKAGER_SHA256" \
  --root-go analysis/burst_null_20261012/ROOT_GO.json \
  --root-go-sha256 "$ROOT_GO_SHA256" \
  --qa-receipt-sha256 "$QA_RECEIPT_SHA256" \
  --report-receipt-sha256 "$REPORT_RECEIPT_SHA256"
```

Pakningen kopierer NPZ som ufortolkede bytes. ZIP, publikationsplan og ekstern arkivkvittering oprettes eksklusivt og overskrives aldrig. ZIP må højst være 200 MiB; alle medlemmer efterlæses med CRC, størrelse og SHA256. Fejlede delarkiver bevares og må ikke genkøres over samme destination. Pakningens egen grænse er 200 CPU-sekunder, 900 vægsekunder og 2 GiB RAM. Den prospektive faseallokering er 6.000 CPU-sekunder; primæroutputs højst 40 MiB pr. familie og 320 MiB samlet, med 8 GiB arbejdsplads. Disse grænser er beregnings- og evidenskontrakten og siger intet om abonnementsbalance.
