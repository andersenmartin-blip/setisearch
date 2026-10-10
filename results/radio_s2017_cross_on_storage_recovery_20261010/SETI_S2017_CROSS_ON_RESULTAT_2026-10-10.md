# S2017: matches mellem de tre ON-observationer

Den første faktiske matchberegning er COMPLETE. Den sammenholder 3.121.152 allerede beregnede kanalvindere fra 762 kontrollerede kort og finder **636 gensidige tre-ON-matches**. Alle 636 er bevaret og vist; visningsgrænsen på 1.000 skjuler ingen rækker. Resultatet er en beskrivende, efterfølgende sammenligning fra samme historiske besøg. Ingen kvalificeret SETI-detektion er etableret.

## Det vigtigste resultat

Det øverste match er kanal **179830784 ved 2300,390625 MHz** i alle tre ON-scans. Den gemte drift har indeks 392 og er numerisk −4,44×10⁻¹⁶ Hz/s, altså den oprindelige grids næsten-nulværdi. Alle tre vindere bruger bredde 1. Den mindste af deres tre gemte scores er 22.022,861549. Denne rangering genfinder den tidligere dokumenterede struktur, som også ses i de tre OFF-scans; matchningen må ikke bruges som ny uafhængig bekræftelse eller bestemmelse af strukturens oprindelse.

De øvrige 635 matches er fortsat uklassificerede. Det næste match har minimumscore 3,968019; dette tal er en visningsscore, ikke SNR, sandsynlighed eller en fast detektionsgrænse. En matchrække kan fremkomme fra støj eller fælles modtagerfrekvensstruktur.

| Kontrolpunkt | Faktisk resultat |
|---|---:|
| Kontrollerede eksisterende ON-kort | 762 |
| Gemte kanalvindere pr. ON-scan | 1.040.384 |
| Gemte kanalvindere i alt | 3.121.152 |
| Udførte rettede nabosammenligninger | 6 |
| Gensidige tre-ON-matches | 636 |
| Bevaret og vist | 636 |
| Nye detektorberegninger eller teleskoprequests i denne fase | 0 |
| Ekstra udgift | 0 DKK |

## Metode og praktisk begrænsning

Den fastlåste regel flytter hver original vinderfrekvens til et fælles tidsreferencepunkt med dens allerede gemte drift. Den vælger nærmeste nabo på tværs af ON-scans med frekvensforskel, driftindeksforskel og kanal som faste binderegler. Et tre-ON-match kræver, at alle seks rettede valg peger på samme triple, og at den samlede frekvensspredning er højst 15,438025621 Hz og driftindeksspændet højst 1. Originale bredder 1 eller 3 bevares og behøver ikke være ens.

Tolerancerne er associationsregler, ikke kalibrerede måleusikkerheder. Kun den vindende hypotese pr. kanal er tilgængelig; fravær af match udelukker derfor ikke en sammenhængende struktur. Der er ikke foretaget ny profilberegning, OFF-veto, barycentrisk korrektion eller genfit. Matchantal og scoreorden giver ingen falsk-alarm-sandsynlighed, følsomhedsgrænse, flux eller EIRP. De beskyttede holdouts og tidligere A/B FAIL_CLOSED er uændrede; de oprindelige hele teleskopfiler har fortsat ikke verificeret MD5.

## Udførelse og sporbarhed

Koden og alle inputs blev fastlåst i commit `ab3915ef936ce5ae7edb9caf226275b0bbfe21af`; 23 offentlige UTF-8-filer blev læst tilbage med eksakt byteidentitet før start. Den lukkede underproces afsluttede med exit 0 og brugte 4,923687 CPU-sekunder, 4,927582 sekunder vægtid og 165.691.392 B maksimal RSS. Grænserne var 120 CPU-sekunder, 1.800 sekunder vægtid, 1 GiB hukommelse og 64 MiB output.

Den tredje families prospektive fælles diskramme var 12 GiB, efter at parallel indhentning og pakning af native 170/172 havde øget pladsbehovet. Begge tidligere starter er bevaret: en fejl ved opsætning af CPU-grænser ved opstart og et stop ved den tidligere 8 GiB-diskkontrol. Begge skete før NumPy-import, arraylæsning og faktisk matchning; ingen tidligere matchberegning blev gentaget.

Den fulde relation ligger i `measurement/ALL_MUTUAL_TRIPLES.npy` med 636 × 3 little-endian int32-indekser. Alle medlemsdata, scorer og parvise forskelle ligger i `measurement/TOP1000.json`. Den oprindelige 171-søgning omfattede 4.900.208.640 korrelerede kombinationer; matchningen genbruger dens vindere og tæller ikke disse hypoteser en gang til.

| Fil | SHA256 |
|---|---|
| Fastlåst scope | `8b43cb85e15cde702dc02afa0b021083432ce58963897271ed8ba0c59d7cf72f` |
| Fuld relation | `6e4f9a4c13b04788d86cc71cc4ce296784cb48f1aeb45adbc7b3b660fabfe07f` |
| Alle 636 viste matches | `f225f42ef99f71e8c6b51f268d1c9e8dd7cb8ec0903f0b5853cea73b1eb02439` |

Rapportens outputkontrol dokumenteres særskilt i den endelige kontrolkvittering. Søgningerne i native 170/172 tilhører en separat familie; deres planlagte hypotesetal indgår ikke i denne rapports udførte tælling.
