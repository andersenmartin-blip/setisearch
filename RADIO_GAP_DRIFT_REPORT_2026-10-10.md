# Otte nye driftkerner i SETI-søgningen — 10. oktober 2026

Der er nu søgt efter lineær frekvensdrift i **otte tidligere usøgte carrierkerner** i det allerede hentede frekvensudsnit. De ni faste top-3-profiler har alle et positivt ON-overskud i både første og sidste halvdel af deres oprindelige scanning, med **13–16 positive tidsrækker ud af 16**. Dette er udvalgte maksimumspor fra en stor søgefamilie; resultatet er beskrivende og giver **ingen bekræftet SETI-detektion eller kvalificeret kandidat**.

## Dækning og metode

De otte nye kerner indeholder hver 4096 referencecarriers. Der er beregnet 32768 nye carriers pr. ON-scanning og 24 scan/kerne-tiles i alt. Kernerne er valgt efter en på forhånd fastlagt regel i kanalindeks og overlapper hverken hinanden eller de 32 tidligere driftkerner. Samlet driftsøgt dækning er nu **163840 carriers pr. ON-scanning: 15,625 % af chunk151**, fordelt på 40 adskilte kerner. Resten af frekvensudsnittet er fortsat ikke driftundersøgt.

Den uændrede detektor undersøger 763 lineære driftrater fra −4 til +4 Hz/s og bredder på 1 og 3 native kanaler: 1526 gyldige hypoteser pr. carrier. Hver ON bruger sit eget første integrationsmidtpunkt som reference. Der er gemt alle carrier-maksima, vindende driftrater og bredder, gyldighedstællinger samt den fulde normalisering. Top-20 pr. ON vises med den tidligere afstandsregel på mere end tre kanaler. Der er ikke lavet en tilsvarende driftmaksimering på OFF-scanningerne.

Top-3 pr. ON er efterfølgende målt én gang i alle seks scanninger langs den valgte, faste frekvens/drift/bredde. Profilen bruger de tidligere gemte medianer af hele frekvensudsnittets 1048576 kanaler pr. tidsrække. Ingen frekvensforskydning, refit eller ny optimering er udført. Rækkerne indeholder middel af den valgte centralbredde minus medianen af flankekanalerne med absolut kanaloffset >3 inden for ±64 kanaler. Middel, median, positive rækker og begge halvdele er gemt sammen med rå og normaliserede profiler.

Kildedata var tidligere åbnet til stationær analyse. Afgrænsningen er prospektiv for **de nye driftudfald**, ikke blind for kildedata og ikke en uafhængig validering. Alle seks scanninger stammer fra samme historiske besøg 17. marts 2016 mod HIP98505/HD189733. Navnene epoch1/2/3 er scanningsetiketter, ikke separate besøg.

## De ni faste top-3-profiler

Frekvensen er ved det oprindelige ON-referencepunkt. Den robuste score og profiloverskuddet har forskellige definitioner. Scoren er ikke kalibreret SNR eller en sandsynlighed. Profilen er i enheder af rå effekt divideret med den gemte rækkemedian.

| Spor | Frekvens (MHz) | Drift (Hz/s) | Bredde | Robust score | ON-middel | ON-positive | ON mindste halvmiddel |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 ON/1 | 1427.439220833 | -2.708661417 | 3 | 5.742891 | 0.093457 | 15/16 | 0.080643 |
| 1 ON/2 | 1427.446902212 | 0.188976378 | 3 | 5.574992 | 0.092297 | 15/16 | 0.072800 |
| 1 ON/3 | 1425.960157033 | -1.459317585 | 3 | 5.555797 | 0.089249 | 14/16 | 0.074789 |
| 2 ON/1 | 1425.207098364 | 0.356955381 | 1 | 5.704613 | 0.097150 | 15/16 | 0.081093 |
| 2 ON/2 | 1425.209616292 | 0.587926509 | 1 | 5.609792 | 0.099217 | 13/16 | 0.070165 |
| 2 ON/3 | 1425.578761975 | -0.629921260 | 1 | 5.544223 | 0.144054 | 14/16 | 0.143767 |
| 3 ON/1 | 1427.067282179 | -1.238845144 | 1 | 5.982187 | 0.163525 | 15/16 | 0.148672 |
| 3 ON/2 | 1427.064185809 | 1.522309711 | 1 | 5.902228 | 0.169044 | 16/16 | 0.120759 |
| 3 ON/3 | 1425.207597413 | -0.430446194 | 1 | 5.639012 | 0.098456 | 14/16 | 0.081328 |

**ON/OFF-midler ved præcis den samme valgte driftbane:** alle seks scanninger er vist. De parrede OFF-kontroller er 1 ON → 1 OFF; 2 ON → 1 OFF og 2 OFF; 3 ON → 2 OFF og 3 OFF. Dette er faste forudsigelser med de faktiske tider, ikke en søgning efter maksimum i hver kontrolscanning.

| Spor | 1 ON | 1 OFF | 2 ON | 2 OFF | 3 ON | 3 OFF |
|---|---:|---:|---:|---:|---:|---:|
| 1 ON/1 | 0.093457 | -0.028865 | -0.007246 | -0.005109 | 0.009818 | -0.014687 |
| 1 ON/2 | 0.092297 | 0.008997 | -0.007663 | 0.003677 | 0.002248 | 0.023551 |
| 1 ON/3 | 0.089249 | 0.021380 | 0.025111 | 0.020014 | 0.029472 | 0.004381 |
| 2 ON/1 | -0.025228 | -0.015373 | 0.097150 | -0.008263 | -0.008547 | -0.005554 |
| 2 ON/2 | -0.005973 | 0.011304 | 0.099217 | -0.007976 | 0.043073 | 0.022122 |
| 2 ON/3 | 0.016186 | -0.019177 | 0.144054 | -0.011833 | 0.029924 | 0.001979 |
| 3 ON/1 | -0.035604 | -0.005478 | -0.021397 | -0.024037 | 0.163525 | 0.046200 |
| 3 ON/2 | -0.013977 | 0.000422 | -0.011070 | 0.024133 | 0.169044 | 0.010559 |
| 3 ON/3 | 0.019843 | 0.011410 | -0.017765 | -0.007467 | 0.098456 | -0.003191 |

De største robuste scorer er 5,742891 i 1 ON, 5,704613 i 2 ON og 5,982187 i 3 ON. Den største score blandt samtlige nye carriers er dermed 5,982187. Vedholdenheden i de ni udvalgte origin-scanninger er et observeret profiltræk efter udvælgelsen; der er ingen kalibreret falsk-alarmrate, og resultatet kan ikke udlægges som ni uafhængige signalfund.

3 ON/2 ved 1427,064185809 MHz har 16 positive origin-rækker ud af 16 og mindste halvmiddel 0,120759. 3 ON/1 har den største robuste score; dens faste 3 OFF-profil har middel 0,046200 og mindste halvmiddel 0,042326. 1 ON/3 har et mindre positivt middel i flere andre scanninger, herunder 1 OFF (0,021380), 2 ON (0,025111), 2 OFF (0,020014) og 3 ON (0,029472). Disse tal er bevaret som kontrolkontekst, uden ny klassifikation.

Et lavt eller negativt OFF-middel ved en ikke-nul driftbane viser kun udfaldet ved de forudsagte kanaler. Banen kan i en senere OFF-scanning passere væk fra en nærliggende næsten stationær linje. **Nabofrekvensers OFF-indhold er ikke undersøgt af denne faste profiltest.** Der er derfor hverken dokumenteret fravær af nærliggende OFF-emission, kvalificeret ON/OFF-udvekslelighed eller himmeloprindelse.

## Alle seks scanningsprofiler

Tabellen fastholder de 54 profil/scanningstilfælde. Halvmiddel er middel af de første eller sidste otte af de 16 gemte tidsrækker. Alle 864 rækkeudfald samt kanalcentrene kan læses i CSV og de oprindelige profilfiler.

| Spor | Scanning | Middel | Median | Positive | Første 8 middel | Sidste 8 middel | Mindste halvmiddel |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 ON/1 | 1 ON | 0.093457 | 0.109595 | 15/16 | 0.080643 | 0.106270 | 0.080643 |
| 1 ON/1 | 1 OFF | -0.028865 | -0.033865 | 5/16 | -0.036505 | -0.021224 | -0.036505 |
| 1 ON/1 | 2 ON | -0.007246 | -0.034789 | 6/16 | -0.003599 | -0.010894 | -0.010894 |
| 1 ON/1 | 2 OFF | -0.005109 | -0.005613 | 6/16 | -0.015789 | 0.005571 | -0.015789 |
| 1 ON/1 | 3 ON | 0.009818 | 0.020195 | 11/16 | 0.006655 | 0.012981 | 0.006655 |
| 1 ON/1 | 3 OFF | -0.014687 | -0.014562 | 7/16 | 0.004315 | -0.033688 | -0.033688 |
| 1 ON/2 | 1 ON | 0.092297 | 0.109964 | 15/16 | 0.111793 | 0.072800 | 0.072800 |
| 1 ON/2 | 1 OFF | 0.008997 | 0.013654 | 10/16 | 0.002521 | 0.015473 | 0.002521 |
| 1 ON/2 | 2 ON | -0.007663 | -0.015871 | 6/16 | 0.018324 | -0.033651 | -0.033651 |
| 1 ON/2 | 2 OFF | 0.003677 | -0.012888 | 7/16 | -0.007340 | 0.014693 | -0.007340 |
| 1 ON/2 | 3 ON | 0.002248 | 0.000254 | 8/16 | 0.027734 | -0.023238 | -0.023238 |
| 1 ON/2 | 3 OFF | 0.023551 | 0.036916 | 12/16 | 0.008953 | 0.038149 | 0.008953 |
| 1 ON/3 | 1 ON | 0.089249 | 0.081171 | 14/16 | 0.103710 | 0.074789 | 0.074789 |
| 1 ON/3 | 1 OFF | 0.021380 | 0.013895 | 10/16 | 0.043263 | -0.000502 | -0.000502 |
| 1 ON/3 | 2 ON | 0.025111 | 0.020789 | 12/16 | 0.050500 | -0.000278 | -0.000278 |
| 1 ON/3 | 2 OFF | 0.020014 | 0.024299 | 9/16 | 0.009633 | 0.030396 | 0.009633 |
| 1 ON/3 | 3 ON | 0.029472 | 0.032968 | 12/16 | 0.025658 | 0.033287 | 0.025658 |
| 1 ON/3 | 3 OFF | 0.004381 | 0.008078 | 10/16 | -0.018239 | 0.027000 | -0.018239 |
| 2 ON/1 | 1 ON | -0.025228 | -0.027096 | 6/16 | -0.021406 | -0.029051 | -0.029051 |
| 2 ON/1 | 1 OFF | -0.015373 | -0.009808 | 7/16 | -0.005732 | -0.025013 | -0.025013 |
| 2 ON/1 | 2 ON | 0.097150 | 0.089313 | 15/16 | 0.113206 | 0.081093 | 0.081093 |
| 2 ON/1 | 2 OFF | -0.008263 | -0.010838 | 8/16 | -0.016358 | -0.000168 | -0.016358 |
| 2 ON/1 | 3 ON | -0.008547 | -0.001633 | 8/16 | -0.028766 | 0.011672 | -0.028766 |
| 2 ON/1 | 3 OFF | -0.005554 | -0.000611 | 8/16 | -0.021067 | 0.009960 | -0.021067 |
| 2 ON/2 | 1 ON | -0.005973 | -0.011953 | 7/16 | 0.000506 | -0.012451 | -0.012451 |
| 2 ON/2 | 1 OFF | 0.011304 | 0.004529 | 8/16 | 0.031366 | -0.008757 | -0.008757 |
| 2 ON/2 | 2 ON | 0.099217 | 0.106669 | 13/16 | 0.070165 | 0.128269 | 0.070165 |
| 2 ON/2 | 2 OFF | -0.007976 | -0.009263 | 7/16 | -0.030712 | 0.014760 | -0.030712 |
| 2 ON/2 | 3 ON | 0.043073 | 0.042386 | 11/16 | 0.073284 | 0.012862 | 0.012862 |
| 2 ON/2 | 3 OFF | 0.022122 | 0.015561 | 9/16 | -0.009586 | 0.053829 | -0.009586 |
| 2 ON/3 | 1 ON | 0.016186 | 0.004705 | 9/16 | 0.003665 | 0.028708 | 0.003665 |
| 2 ON/3 | 1 OFF | -0.019177 | -0.012342 | 5/16 | -0.033246 | -0.005107 | -0.033246 |
| 2 ON/3 | 2 ON | 0.144054 | 0.124339 | 14/16 | 0.144341 | 0.143767 | 0.143767 |
| 2 ON/3 | 2 OFF | -0.011833 | -0.008009 | 6/16 | -0.024516 | 0.000850 | -0.024516 |
| 2 ON/3 | 3 ON | 0.029924 | 0.026616 | 9/16 | 0.052456 | 0.007393 | 0.007393 |
| 2 ON/3 | 3 OFF | 0.001979 | -0.011598 | 8/16 | 0.005937 | -0.001979 | -0.001979 |
| 3 ON/1 | 1 ON | -0.035604 | -0.002828 | 8/16 | -0.053232 | -0.017975 | -0.053232 |
| 3 ON/1 | 1 OFF | -0.005478 | -0.013074 | 6/16 | 0.002375 | -0.013331 | -0.013331 |
| 3 ON/1 | 2 ON | -0.021397 | -0.005791 | 8/16 | -0.017868 | -0.024926 | -0.024926 |
| 3 ON/1 | 2 OFF | -0.024037 | -0.071202 | 5/16 | -0.026030 | -0.022044 | -0.026030 |
| 3 ON/1 | 3 ON | 0.163525 | 0.142710 | 15/16 | 0.178377 | 0.148672 | 0.148672 |
| 3 ON/1 | 3 OFF | 0.046200 | 0.095196 | 10/16 | 0.042326 | 0.050074 | 0.042326 |
| 3 ON/2 | 1 ON | -0.013977 | 0.002984 | 9/16 | -0.029339 | 0.001385 | -0.029339 |
| 3 ON/2 | 1 OFF | 0.000422 | -0.005489 | 8/16 | 0.032820 | -0.031975 | -0.031975 |
| 3 ON/2 | 2 ON | -0.011070 | 0.001499 | 9/16 | 0.013963 | -0.036103 | -0.036103 |
| 3 ON/2 | 2 OFF | 0.024133 | -0.030007 | 7/16 | 0.064696 | -0.016430 | -0.016430 |
| 3 ON/2 | 3 ON | 0.169044 | 0.157217 | 16/16 | 0.217329 | 0.120759 | 0.120759 |
| 3 ON/2 | 3 OFF | 0.010559 | 0.005532 | 10/16 | 0.023402 | -0.002283 | -0.002283 |
| 3 ON/3 | 1 ON | 0.019843 | 0.025807 | 9/16 | 0.013305 | 0.026381 | 0.013305 |
| 3 ON/3 | 1 OFF | 0.011410 | -0.005152 | 7/16 | 0.006009 | 0.016811 | 0.006009 |
| 3 ON/3 | 2 ON | -0.017765 | -0.024361 | 7/16 | -0.001149 | -0.034382 | -0.034382 |
| 3 ON/3 | 2 OFF | -0.007467 | -0.015886 | 6/16 | -0.027614 | 0.012681 | -0.027614 |
| 3 ON/3 | 3 ON | 0.098456 | 0.090048 | 14/16 | 0.081328 | 0.115585 | 0.081328 |
| 3 ON/3 | 3 OFF | -0.003191 | -0.005785 | 8/16 | -0.002933 | -0.003449 | -0.003449 |

## Ressourcer og sporbarhed

Den ene numeriske kørsel afsluttede alle 24 tiles og ni profiler: **73.861582975 CPU-sekunder**, 73.896858674 s vægtid og maksimal RSS 491298816 bytes. Den frosne jobgrænse var 90 CPU-sekunder, 1800 s vægtid og 4 GiB RAM. Ingen numerisk gentagelse er tilladt. Aktiviteten reserverede 160 CPU-sekunder i alt, heraf 70 til klargøring, QA, pakning og offentliggørelse; uudnyttet reservation refunderes ikke.

**Ingen nye teleskop-HTTP-anmodninger eller kilde-bodybytes. 0 kr.** De allerede bevarede seks kompaktfiler og samtlige 96 dekodede tidsrækker blev hashkontrolleret i kørselens indlæsning.

- Scope SHA-256: `c226ad41a87f344f71a642e0e7129657f00e44684db74d50124f075fd35d7a44`
- Script SHA-256: `b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58`
- Uændret detektor SHA-256: `1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45`
- Kildemanifest SHA-256: `d2e6c76b0d5fe50b26d45830e4b67e4780da97f33cfe8fcdf80c761f47aa3a4c`
- Acquisition-receipt SHA-256: `da165fe31ac4a70167b06f83b8f667fbb8604b595c642d3610fec68788bebf37`

Data: `results/radio_gap_drift_20261010/measurement/` indeholder 24 komplette carrier-NPZ'er, `DRIFT_CHECKPOINT.json`, alle 60 rangeringer, ni rå/normaliserede profil-NPZ'er og de fulde seks-scansprofiler. `FINDINGS.json`, `DRIFT_TOP20.csv` og `FIXED_PROFILE_SCAN_METRICS.csv` gengiver de gemte resultater. `SUMMARY_RECEIPT.json` måler denne tekst-/CSV-sammenfatning; den åbner ingen H5/NPZ og gentager ingen detektion eller profilberegning.

A/B forbliver **FAIL_CLOSED**, den kvalificerede pilot er fortsat blokeret, og de gamle holdouts er ikke åbnet. Alle nye profiltilfælde er uafklarede, eksplorative. Der er ingen kalibreret sky-SNR/FAP, flux, EIRP, følsomhed, oprindelsesklassifikation eller generel nulkonklusion.
