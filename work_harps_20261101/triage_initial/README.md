# Første bølgelængdekontrol — 1. november 2026

Dette er et afgrænset supplement til den eksisterende prøve. Der er ikke analyseret nye eksponeringer. Alle ti hændelser beholder deres oprindelige status `UNREVIEWED`.

Ved den foreløbige omregning fra barycentriske til topocentriske luftbølgelængder, `lambda_top = lambda_bary / (1 + BERV/c)`, findes tre tætte sammenfald med O I-linjer:

| Mål og observationsdato | Beregnet topocentrisk bølgelængde, Å | O I-reference, Å | Afvigelse, Å |
|---|---:|---:|---:|
| HD114082, 2024-04-18 | 5577,338595 | 5577,339 | −0,000405 |
| HD120411, 2022-04-12 | 5577,340144 | 5577,339 | +0,001144 |
| HD120411, 2022-05-21 | 6300,306609 | 6300,304 | +0,002609 |

Referencelinjerne er tabuleret som luftbølgelængder i [NBS' O I-tabeller](https://www.govinfo.gov/content/pkg/GOVPUB-C13-8e601b629710db9963b4d618c9a1192a/pdf/GOVPUB-C13-8e601b629710db9963b4d618c9a1192a.pdf), PDF-sider 26 og 22. [ESO's DRS-manual](https://www.eso.org/sci/facilities/lasilla/instruments/harps/doc/DRS.pdf), afsnit 4.2.7, beskriver S1D som resamplet til barycentrisk referenceframe med 0,01 Å-trin. BERV-formlen og fortegnet følger den generelle beskrivelse i [Bertaux m.fl. 2014](https://doi.org/10.1051/0004-6361/201322383), ligning 1.

Den præcise HARPS_3.8-implementering er endnu ikke verificeret, og der er ingen rå 2D-kontrol her. Afvigelserne er mindre end en halv bølgelængdebin, men antallet af decimaler er regnepræcision, ikke dokumenteret målenøjagtighed. Sammenfaldene giver konkrete hypoteser at kontrollere; de er ikke en endelig ophavsbestemmelse eller en grund til at slette hits. De øvrige syv er heller ikke klassificeret ved denne begrænsede sammenligning med to referencelinjer.

[Alle ti beregninger](TEN_HIT_HEADER_OFFSETS.csv) · [Forudsætninger og usikkerheder](INITIAL_TRIAGE.json) · [Kilder](SOURCES.json). Reproduktion: `python triage_initial/calculate_header_offsets.py`.
