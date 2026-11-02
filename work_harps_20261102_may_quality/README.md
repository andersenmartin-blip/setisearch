# HARPS: afsluttet kvalitetsopfølgning med en tredje referenceepoke

**Ét yderligere HD122640-spektrum er hentet og analyseret i en særskilt, fastlagt kvalitetsopfølgning.** Alle seks hændelsesposter er sammenlignet i begge referenceframes: seks hændelse/epoke-par og tolv profiler, ingen blokerede. Alle ti poster i den bevarede kø forbliver U; de fire på HD135204 har fortsat ingen ny udvalgt epoke.

Majobservationen fra 20. maj 2017 har bedre lokal kontinuumkvalitet end den tidligere majreference. Ingen af de tolv profiler får den arvede lav-kontinuum-markering. For de ti blå profiler ligger kontinuum/støjproxy-forholdet på 4,04–6,38 mod cirka 0,66–0,73 i den tidligere majreference. Dette er beskrivende kvalitetsmål; fejlkolonnen har stadig ingen endelige positive ERR-værdier og giver ingen kalibreret signifikans.

## Hvad sammenligningen viser

| Poster | Korrelation i barycentrisk ramme | Korrelation i topocentrisk ramme |
| --- | ---: | ---: |
| Fem blå poster ved 3866–3881 Å | 0,955933 til 0,979149 | −0,312911 til 0,153460 |
| V2E2-0235 ved 5548,09 Å | 0,475244 | −0,298943 |

Den nye BERV er **−9,84628486624399 km/s**. Afstanden fra opdagelsesepokerne er 36,195–37,087 km/s, svarende til 13,884–14,227 nominelle opløsningselementer. Alle seks fastlagte forskydningskrav er opfyldt. Det samlede tilgængelige BERV-spænd er fortsat 40,363479 km/s; formålet var bedre referencekvalitet ved stor forskydning.

De fem blå profiler følger den barycentriske skala langt bedre end den topocentriske i denne sammenligning. Det styrker beskrivelsen af vedvarende spektralstruktur, men afgør ikke i sig selv naturligt, instrumentelt eller kunstigt ophav. De fem poster dækker tre nærliggende bølgelængdegrupper og er ikke fem uafhængige signaler. Barycentriske bølgelængder er ikke en stjernehvileramme; kalibrering, stjernens radialhastighed og instrumentelle forhold er ikke nytilpasset.

V2E2-0235 behandles særskilt. Den har kun moderat barycentrisk korrelation med den nye reference og havde svag korrelation med begge tidligere referencer, selv om dens lokale kontinuum ikke var lavt. Den skarpe centrale top fra opdagelsesepoken genfindes ikke med sammenlignelig amplitude i den nye reference; den moderate korrelation er ikke en genfinding af dette udsving. Den oprindelige råbilledtvetydighed består. Ingen tærskel eller klassifikation er ændret efter resultatet.

[Komplet rapport, målinger og alle figurer](comparison/results/README.md) · [Maskinlæsbar opsummering](comparison/results/SUMMARY.json) · [Uafhængig numerisk kontrol](comparison_audit/NUMERICAL_AUDIT.json) · [Videnskabelig gennemgang](scientific_review/ACTUAL_SCIENTIFIC_REVIEW.json)

## Fastlagt metode og bevaret evidens

Valget er udtrykkeligt **posthoc**: den afsluttede majreference var støjplaget, og den højest rangerede ubrugte majobservation blev derfor valgt ud fra allerede gemt gennemsnitlig metadata-SNR (77,8). Det er en separat undersøgelse. Den tidligere to-epokeanalyse med 24 profiler og begge tidligere referencekurver er bevaret uændret.

Metode, udvælgelse og stopregler blev publiceret i `d8e16e5586d0538b0733b41ae1d497b0fd0aaeef` før den nye headerforespørgsel. Headeren blev publiceret i `81e33f8cc97fac06565129e563bd7c8b0f97f264` før spektret blev hentet. De præcise inputbytes blev publiceret og læst tilbage i `318b4201273aad853899c52dfe2a3e025bb686e6`, inden nye spektralarrays blev fortolket. Begge dataforespørgsler lykkedes ved første forsøg; ingen redirects, genforsøg eller erstatningsobservationer.

Det præcise produkt er `ADP.2017-05-21T01:01:50.278`, råforløber `HARPS.2017-05-20T02:21:45.847`. Headerens DATE-OBS er 2017-05-20T02:21:45.846, eksponeringstiden 1199,9982 sekunder, reduktionen HARPS_3.8. Hele FITS-filen er 5.264.640 bytes med SHA-256 `03f551de48d9acc207612e6683ff0d0b07f3d0f2b04e16a24289073e4e51b7af`.

Den uafhængige numeriske kontrol består med **1.571 checks og 15.096 skalarsammenligninger**, herunder alle tolv profiler og korrelationer. Største korrelationsafvigelse er 3,33×10⁻¹⁶. Den separate headerkontrol består med 27 checks og FITS-repræsentationen med 44. [Acquisition-auditten](acquisition_audit/README.md) bevarer eksplicit, at den afsluttende præflight-rapport blev færdiggjort efter roots headerstart; den tidligere kodegennemgang, offentlig frysning og roots egen kontrol ligger før requesten. Ingen uafviklede tests tælles som beståede.

[Protokol](PROTOCOL.md) · [Offentlig metodefrysning](PREFLIGHT_FREEZE.json) · [Gennemført hentning](acquisition/ACQUISITION_MANIFEST.json) · [Prospektiv sammenligningsplan](comparison/PLAN.json)

## Gendan og fortsæt

Fra repository-roden:

```bash
python3 work_harps_20261102_may_quality/preservation/restore_archive.py SCIENCE_INPUTS_MANIFEST.json
python3 work_harps_20261102_may_quality/preservation/restore_reference_cache.py
python3 work_harps_20261102_may_quality/preservation/restore_archive.py PROFILE_EVIDENCE_MANIFEST.json
```

Alle arkivdele og medlemmer verificeres, og afvigende eksisterende filer overskrives ikke. Det nye FITS-input ligger i to dele af et 1.780.594-byte arkiv; de tolv nye profilarrays i et 103.565-byte arkiv. De tyve oprindelige discovery-referencer og de 24 tidligere sammenligningsprofiler gendannes fra det allerede bevarede arkiv. Ingen ny ESO-hentning er nødvendig. Reproduktion skal ske i en separat kopi, så publicerede outputs og engangsmarkeringer bevares.

[Aktuel fortsættelsestilstand](CONTINUATION_STATE.json) · [Næste konkrete trin](scientific_review/NEXT_STEP.md) · [Fælles fortsættelse](../CONTINUE_SETI.md)

Den oprindelige fulde spektralsøgning er uændret: 300 eksponeringer, 20 stjerner, 70,874650833 timer; 403 A / 46 O / 185 U / 35 M / 0 N. De tre ekstra arkivspektre i de to opfølgningsfaser er målrettede sammenligninger. Ingen kvalificeret laserkandidat, sikker ophavsbestemmelse eller kalibreret nulresultat er etableret. Rubin forbliver ved 190 hovedobjekter, 2 numerisk vurderbare i hovedsporet og separat 4 i forced-sporet, herunder de to hovedobjekter; minimum 50 er ikke opfyldt.

Baseret på offentlige data fra ESO Science Archive Facility. Der er ikke foretaget nye teleskopobservationer, brugt betalte tjenester eller oprettet baggrundskørsel.
