2017: beskrivende ON/OFF-struktur i gemte profiler

Denne opfølgning bruger allerede målte og autentificerede profiler fra samme 2017-observation. De nye beskrivende mål og gemte output har bestået QA. Der er ingen ny teleskopanskaffelse, detektorsøgning eller profiludmåling i denne fase.

Alle 1.905 oprindelige ON-medlemsstier fra 635 cross-ON-tripler indgår med deres seks gemte scans. Kun det præcise oprindelige rang1-tripel var udeladt i profilfasen; beslægtede profiler kan stadig berøre samme lokale struktur. Stier og tripler er korrelerede og tælles ikke som uafhængige signaler.

Middel-forskellen er det allerede gemte min(ON1, ON2, ON3)-max(OFF1, OFF2, OFF3) for de normaliserede, bredde-valgte residualmidler. Halv-forskellen anvender de gemte første/sidste halvdele. Det særskilte nabomål sammenholder ON-midlet med den største gemte lokale OFF-boksrespons i det afgrænsede profilvindue. Disse efterfølgende mål er beskrivende; de har ingen kalibreret falskalarmrate eller detektionstærskel.

Af alle 1.905 stier har 341 positiv gemt middel-forskel, 30 positiv gemt halv-forskel og 0 positiv gemt lokal naboforskel. 0 stier har positivt residual i alle 16 rækker i samtlige tre ON-scans. Tallene er overtaget direkte fra kildens deskriptive optælling; de er ikke uafhængige forsøgs- eller detektionstal.

Den største gemte lokale naboforskel er -0.00074347117405743068 (oprindeligt medlemsindeks 92, direkte fra kildens fulde nabomålsrangliste). Det lokale mål er særskilt fra middel-forskellen og fastslår ingen fysisk oprindelse.

Den viste sti er kildens forudeksporterede største middel-forskel: original tripelrang 308, sti fra ON3. Gemt middel-forskel: +0.0755704849; halv-forskel: +0.0187451493; lokal naboforskel: -0.0499544493. Valget følger de observerede værdier. En stor middel-forskel er ikke i sig selv et bestået lokalt OFF-kriterium eller en uafhængig bekræftelse.

Figur 1, hele den bevarede familie: presentation/SIGNED_WORST_ON_OFF_GAP_VS_DRIFT.png

Figur 2, den eftervalgte stis fulde lokale vindue: presentation/PRESELECTED_MAX_MEAN_GAP_LOCAL_PROFILES.png

Alle 129 gemte kanaloffsets vises; der er ingen dynamisk peakfit, frekvensflytning, driftændring eller maskering. Vinduet følger den oprindelige faste sti med dens egen ON-reference. Det er lokal struktur og underbygger ingen påstand om fravær på hele OFF-sporet.

Kildens første ti middel-rangposter (beskrivende, efterfølgende rangering):

1. Original tripelrang 308 / ON3; drift -3.89795918 Hz/s; bredde 1; middel-forskel +0.0755704849; halv-forskel +0.0187451493; naboforskel -0.0499544493.
2. Original tripelrang 55 / ON3; drift +1.10204082 Hz/s; bredde 1; middel-forskel +0.0489305181; halv-forskel +0.0127536559; naboforskel -0.0267774129.
3. Original tripelrang 528 / ON3; drift -0.43877551 Hz/s; bredde 1; middel-forskel +0.0468743778; halv-forskel +0.0199681132; naboforskel -0.0455005059.
4. Original tripelrang 310 / ON1; drift -2.25510204 Hz/s; bredde 1; middel-forskel +0.0456215154; halv-forskel +0.0137388896; naboforskel -0.0297536821.
5. Original tripelrang 515 / ON1; drift -2.44897959 Hz/s; bredde 1; middel-forskel +0.0448359911; halv-forskel +0.00551847285; naboforskel -0.0217324193.
6. Original tripelrang 529 / ON3; drift +1.34693878 Hz/s; bredde 1; middel-forskel +0.0446783817; halv-forskel -0.0101483833; naboforskel -0.0340394887.
7. Original tripelrang 512 / ON1; drift -2.83673469 Hz/s; bredde 1; middel-forskel +0.044267876; halv-forskel -0.00196970052; naboforskel -0.0376386654.
8. Original tripelrang 193 / ON2; drift +3.41836735 Hz/s; bredde 1; middel-forskel +0.0442158939; halv-forskel -0.00761997864; naboforskel -0.0288593747.
9. Original tripelrang 376 / ON1; drift -0.183673469 Hz/s; bredde 1; middel-forskel +0.0425513133; halv-forskel -0.0153146462; naboforskel -0.0144975343.
10. Original tripelrang 19 / ON2; drift -3.19387755 Hz/s; bredde 1; middel-forskel +0.0419365052; halv-forskel +0.0177861191; naboforskel -0.012607314.

Resultatet ændrer ikke projektets oprindelige A/B-status FAIL_CLOSED eller independent_validation BLOCKED. Der er ingen sky-falskalarmkalibrering, blind gentagelse, fysisk oprindelsesklassifikation eller detektionspåstand. Figurerne læser alene nye, gemte JSON-scalarer og den allerede gemte lokale middelprofil; de gentager ingen måling eller rangering.

Alle gemte mål og prædefinerede ranglister: measurement/SAVED_PROFILE_AGGREGATE.json
Original execution: measurement/EXECUTION_RECEIPT.json
