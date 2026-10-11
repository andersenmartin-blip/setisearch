# SETI: nye signalanalyser, 11. oktober 2026

**1536 nye spektralkort er færdige.** Der er undersøgt 6.291.456 nye referencefrekvenser fordelt på tre historiske stjerneobservationer: HIP97319, HIP97461 og HIP97663. Hver har fået 5.859375 MHz ekstra frekvensdækning. De ni højest rangerede spor er kontrolleret ved uændrede frekvenser, drift og bredde i alle seks oprindelige observationer.

Der er stadig **intet kvalificeret SETI-fund**. Tallene nedenfor viser stærke og svage svar i denne søgemetode; de er ikke kalibrerede SNR-værdier eller sandsynligheder for et astronomisk signal.

| Stjerne | Rang | Frekvens ved første midtpunkt (MHz) | Drift (Hz/s) | Bredde (kanaler) | Primær score | Største tidsrækkes andel af positive bidrag |
|---|---:|---:|---:|---:|---:|---:|
| HIP97319 | 1 | 2297.460937500 | -0.000000 | 1 | 20540.2 | 6.6% |
| HIP97319 | 2 | 2303.320312500 | -0.000000 | 1 | 20213.1 | 6.4% |
| HIP97319 | 3 | 2297.460948676 | -0.051020 | 3 | 5976.94 | 12.9% |
| HIP97461 | 1 | 2297.460937500 | -0.000000 | 1 | 21440 | 6.5% |
| HIP97461 | 2 | 2303.320312500 | -0.000000 | 1 | 21153.8 | 6.4% |
| HIP97461 | 3 | 2297.460948676 | -0.051020 | 3 | 6233.21 | 13.1% |
| HIP97663 | 1 | 2297.460937500 | -0.000000 | 1 | 21687.1 | 6.5% |
| HIP97663 | 2 | 2303.320312500 | -0.000000 | 1 | 21427.9 | 6.6% |
| HIP97663 | 3 | 2297.460926324 | +0.051020 | 3 | 6309.52 | 12.9% |

Den største enkelte tidsrække leverer 6.4–13.1% af de positive bidrag i de primære spor med positive bidrag. Det er en direkte beskrivelse af, hvor svaret kommer fra; andelen er ikke et mål for falsk-alarm-sandsynlighed. Ved ingen positive bidrag er andelen ikke defineret. De øvrige observationers svar fremgår af figuren og CONTEXT54.csv.

Alle ni primærscorer er reproduceret med samme faste 4096-kanals normalisering, 501-kanals medianfilter og 4000-kanals margin. Der er gemt 54 rå profiler med 16×503 kildeceller samt hvert tidsbidrag. De oprindelige float32-rækker er verificeret i alle 18 frekvensdele.



Den fulde nye søgning omfatter 9.877.585.920 korrelerede kombinationer af frekvens, drift og bredde. Det er ikke så mange uafhængige forsøg. 6.153 rå scorekontroller er gemt fra de nye kort; en separat kontrol kan rekonstruere deres valgte scorer uden at gentage søgningen.

De tre primærstjerner har hver én historisk observation fra 28. april 2017. HIP98505-observationerne og de andre OFF-retninger giver sammenligningskontekst, men er ikke nye eller uafhængige genobservationer af primærstjernerne. Driftens trin er valgt til én 16-rækkers observation; den faste forlængelse gennem hele sekvensen er ikke en ny tilpasning.

![Faste spor i de seks observationer](SETI_CONTEXT54_2026-10-11.png)

![Scorernes tidsbidrag](SETI_ROW_CONTRIBUTIONS_2026-10-11.png)
