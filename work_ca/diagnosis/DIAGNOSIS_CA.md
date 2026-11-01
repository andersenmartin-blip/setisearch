# CA: hvor mistes de mellemstærke testsignaler?

Denne efteranalyse forklarer udvalgte scores fra den afsluttede BZ-test.
Der er ingen ny blind søgning, ingen nye observationer og ingen ændring af
detektoren eller dens tærskler.

For hvert af de 24 A=8 ON-only-tilfælde vælges blandt de allerede gemte BZ-spor
det spor, der har den største mindste score i de tre ON-scanninger. 20 tilfælde
har sådanne kildespor. De resterende fire har ingen gemt kildetop over tærsklen;
de får ikke efterfølgende konstrueret et erstatningsspor.

De 60 udvalgte ON-scores er genberegnet med direkte skalarsummer og stemmer
præcist med de gemte scores. Med den allerede gemte median og MAD fastholdt
opdeles hver score i:

\[
\mathrm{ESS}=\frac{\text{baggrundssum}-\text{gemt median}}{\text{gemt MAD}}
+\frac{\text{tilført overskud efter float32-afrunding}}{\text{gemt MAD}}.
\]

| Driftrategruppe | Tilfælde med kildespor / 8 | Tre ON bestået / 8 | Median af baggrundsled* | Median af tilført signalled* |
|---|---:|---:|---:|---:|
| Cirka −1 Hz/s | 4 | 0 | −0,671 | 10,268 |
| Cirka 0 Hz/s | 8 | 8 | −0,108 | 18,885 |
| Cirka +1 Hz/s | 8 | 7 | +0,596 | 10,201 |

\* På de valgte spor gennem de tre ON-scanninger: henholdsvis 12, 24 og 24
korrelerede spor. Medianerne er beskrivende; de er ikke følsomhedsmålinger.

Ved omtrent ±1 Hz/s bevæger signalet sig gennem cirka 6,55 frekvenskanaler i
hver 18,25-sekunders integration. De valgte spor bruger derfor bredde 9. Deres
tilførte signalled ligger tæt på tærsklen 10. I den negative gruppe ligger
otte af de 12 udvalgte ON-scores under tærsklen. I syv af disse otte ville
signalleddet alene nå 10, men baggrundsleddet trækker summen under tærsklen.
I den positive gruppe er alle 24 valgte baggrundsled positive; ét af de 24
spor ligger samlet under tærsklen.

Det er en algebraisk forklaring på disse gemte spor, ikke et forslag om at
fjerne baggrunden i den praktiske detektor. Median og MAD er fastholdt fra de
oprindelige injicerede data. Signalled og baggrundsled er derfor ikke
kalibrerede selvstændige detektionsstatistikker.

De fire negative tilfælde uden kildespor deler alle den første carrierposition
(offset 1536). De øvrige fire negative tilfælde deler den anden (offset 2560)
og tabes i senere ON-scanninger. De otte geometrier pr. rategruppe er således
variationer af kun to nært beslægtede frekvensforløb; de må ikke fortolkes som
otte uafhængige forsøg.

En separat frekvensspejling med modsat driftrate sammenligner 120 sparse
template/scanningspar, i alt 1.920 tidsrækker. Kanalvægtene stemmer til maksimalt
3,664 × 10⁻¹⁵. Alle 60 heltalsspor giver præcis samme direkte sum på den
spejlede baggrund med modsat heltalsforskydning. Det afgrænsede tjek finder
ingen fortegnsasymmetri i denne template- og sporalgebra. Det afprøver ikke
alle grene i kildeudvælgelsen eller projektionskoden og betyder ikke, at den
uspejlede virkelige baggrund har samme følsomhed for begge fortegn.

En senere afprøvning bør bruge på forhånd fastlagte nye carrierpositioner og
parrede positive/negative rater, hvis fortegnsafhængigheden skal undersøges
ud over disse eksponerede forløb. Nye skabelonbredder eller matchning til
eksponeringens form kræver et særskilt forsøg og sammenlignelig
falsk-alarm-belastning.

Kilde: [diagnostikkode](decompose_bz.py) og
[komplet decomposition og inputhashes](SCORE_DECOMPOSITION_CA.json).
Uafhængig numerisk gennemgang rapporteres særskilt.
