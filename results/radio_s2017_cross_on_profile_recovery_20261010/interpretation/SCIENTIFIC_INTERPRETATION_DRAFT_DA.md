# Deskriptiv læsning af de faste S2017-profiler

De 635 eksisterende sammenkædninger har alle tre positive middelværdier i de medlemsbaners oprindelige ON-scans: 1.905 af 1.905. Det er betinget af den tidligere udvælgelse i ON og er ikke ny validering. Kun 838 af de 1.905 uændrede medlemsbaner har positiv middelværdi i alle tre ON-scans. Sammenkædningen tillader nærliggende frekvenser og nabodrifttrin; den fastlægger ikke én fælles tilpasset bane.

OFF-profilerne er positive mindst én gang for 1.741 af 1.905 medlemsbaner og i alle tre OFF-scans for 341. Kun 8 medlemsbaner har en OFF-middelværdi mindst lige så stor som deres egen oprindelige ON-middelværdi; dette gælder ét medlem i hver af 8 sammenkædninger, mens 627 har nul. De faste tilstødende OFF-kontroller når mindst den oprindelige ON-middelværdi for 3 medlemsbaner. Disse optællinger er beskrivende; den udvalgte ON-værdi er ikke en udvekslelig støjkontrol, og tallene er hverken et OFF-veto eller en fejlalarmssandsynlighed.

1.899 af de 1.905 oprindelige ON-profiler har positiv middelværdi i både første og sidste halvdel. Positivitet af halve middelværdier siger ikke, at alle tidsrækker er positive, eller at resterne er statistisk signifikante.

Alle optællinger følger de private, fastlagte regler før læsningen: middelværdi > 0 uden tolerance, OFF >= samme medlems oprindelige ON, samt allerede gemt minimum af halv-middelværdier > 0. Ingen nye ranglister eller tilpassede tærskler er indført. 11.430 logiske profiler deler 11.369 geometrier og fælles kontroller; optællingerne tæller korrelerede forekomster.

| Oprindeligt medlem | Positive oprindelige ON | Positiv i alle tre ON | Mindst én positiv OFF | Alle tre OFF positive | Mindst én OFF >= egen ON |
|---|---:|---:|---:|---:|---:|
| epoch1_on | 635/635 | 285 | 583 | 124 | 2 |
| epoch2_on | 635/635 | 260 | 582 | 115 | 3 |
| epoch3_on | 635/635 | 293 | 576 | 102 | 3 |

## Eksisterende rang 2, uden ny udvælgelse

Alle tre medlemmer har bredde 1. ON1 og ON2 bevarer drift −1,5510204081632657 Hz/s; ON3 bevarer nabotrinnet −1,5612244897959187 Hz/s. Deres referencefrekvenser gælder forskellige oprindelige ON-tidspunkter og må ikke læses som samtidige statiske frekvenser.

| Frossen medlemsbane | ON1 | OFF1 | ON2 | OFF2 | ON3 | OFF3 |
|---|---:|---:|---:|---:|---:|---:|
| epoch1_on | 0.113029 | 0.016673 | -0.015297 | 0.008474 | 0.010985 | 0.050981 |
| epoch2_on | 0.032540 | -0.019298 | 0.108860 | 0.037169 | -0.003554 | 0.014919 |
| epoch3_on | 0.038529 | -0.010648 | -0.006559 | 0.008179 | 0.105651 | 0.031038 |

Egen ON-middelværdi er positiv for alle tre medlemmer i rang 2. Den faste ON1-bane giver samtidig −0,015297 i ON2, ON2-banen −0,003554 i ON3, og ON3-banen −0,006559 i ON2. Der er også små positive OFF-rester. Det viser betydningen af medlemsbanens nøjagtige kanal-, drift- og referencevalg; det etablerer hverken en fælles sammenhængende linje eller en bestemt fysisk oprindelse. De fulde 18 gemte metrikobjekter er kopieret i analyse-JSON, inklusive median, positive rækker og begge halv-middelværdier.

## Gyldighed og begrænsninger

ON og OFF er målt med den samme nye profilformel, de samme 96 lagrede fuldbåndsnormaliseringer og den uændrede individuelle medlemsbane. Profilmiddelværdier er dimensionsløse restmål efter lokale flankmedianer; de sammenlignes ikke med de oprindelige robuste detektorscorer.

OFF-scans kan indeholde modtager-, baggrunds- eller anden frekvensstruktur. En svag eller negativ rest langs en transporteret driftbane udelukker ikke en nærliggende stationær OFF-linje. Fortegn alene skelner ikke mellem støj, instrument, interferens eller himmelkilde. Resultatet er posthoc fra ét besøg og giver ingen kalibreret SNR/FAP, følsomhed, flux, kandidatgodkendelse eller uafhængig bekræftelse. Den kendte rang 1 er udeladt alene ved den tidligere fastlåste eksakte triple-identitet.

Kildekontrollen har autentificeret alle 96 fulde dekodede rækker og 181.904 rå række-hashes, svarende til 23.465.616 udvalgte celleforekomster. Den kontrollerer gemte profilresuméer internt, men genberegner ikke normalisering, flankmedian eller profilkernel uafhængigt. Hele de oprindelige kildefilers MD5 er fortsat ikke verificeret.

Profilberegningen tilføjer ingen ny detektor-gridscoring eller nye matchhypoteser. Denne læsning åbner kun de accepterede JSON-resuméer, ikke HDF5/NPZ, og genkører ingen profil-, median-, detektor- eller matchberegning. Det første JSON-formatforsøg fejlede på navnet af et QA-ressourcefelt; original kilde, markør og fejloptegnelse er bevaret, og en særskilt V2 læsning rettede QA-feltopslaget samt kontrol/proveniens- og CPU-bogføring. Ingen optællingsregel blev ændret efter værdilæsningen.

Profil- og QA-frysning: afa74530e81fad064bf97d60bbc501696377009a. Analyse-JSON SHA256: 4507ccf9d2235f6f0558d1467bc6abede8bb13e56fd2ceb5b8b8224216e72684. Private kildepins og fulde metrikværdier er inkluderet dér. Offentlige leverings- og arkivoplysninger skal tilføjes af root efter faktisk gemning.
