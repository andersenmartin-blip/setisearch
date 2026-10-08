# Den ene kørselsrettelse er afprøvet med nye udviklingsfrø

To nye DEV_RUNTIME-forsøg er afsluttet 8. oktober 2026 med uændret detektor,
generator, søgebånd, driftsøgning, tærskler og OFF-regel. De anvender de to
tunge transientgeometrier, som afbrød A, men har nye, adskilte identiteter og
SHA256-frø. De er udviklingsprøver; de erstatter ikke de fejlede A-forsøg og
tæller ikke som uafhængig videnskabelig validering.

| Ny udviklingsprøve | CPU-s i resultatkvittering | Bevarede ON-hits | Fulde søgekort |
|---|---:|---:|---:|
| DEV_RUNTIME000 | 295,309 | 1.816 | 6 |
| DEV_RUNTIME001 | 296,615 | 1.814 | 6 |

Begge afsluttede alle OFF-sammenligninger og gemte deres fulde resultater
og kontrolsummanifester. Antallet er rå nabokanaler, ikke uafhængige kilder.
Alle disse hits overlever i de syntetiske kortvarige udbrud; den tidligere
påviste begrænsning ved tidslig vedholdenhed bevares.

Den samlede belastning er 592,053813 CPU-s inklusive hele de afsluttede
børneprocesser og styringsprocessen. Samlet vægtid var 296,678 sekunder;
største målte RAM var 87.801.856 bytes. Begge holdt sig inden for de uændrede
1.800-sekunders jobgrænser og 4 GiB. Rettelsen er løbende reservation af
eksklusiv køretid, ikke en højere samlet grænse eller ny søgemetode.

A forbliver FAIL_CLOSED, og ingen A-identitet gentages. Teleskopværdier og
det eksisterende 142-forsøgs B-panel er stadig uåbnede ved denne afslutning.
B får efter gennemgang og separat fastlåsning en samlet allokering på
19.500 CPU-s med højst otte samtidige 1.800 CPU-sekunders reservationer.
Alle oprindelige fælles krav skal bestå på samtlige 142 B-forsøg.

Efter faktisk A- og udviklingsbelastning, 3,942393 CPU-s til A-arkivpakning,
0,107116 CPU-s til udviklingsarkiverne og en særskilt konservativ
forberedelsesreservation på 1.200 CPU-s er
23.695,968678 CPU-s disponible. Den fulde B-allokering efterlader
4.195,968678 CPU-s, nok til to yderligere fulde 1.800-sekunders jobpartitioner
til en eventuel datalæsning og pilot. Ukendte historiske målinger bliver
ikke gjort til målte totaler.

Den nye udviklingskode og de fulde A-arkiver blev offentliggjort og
kontrolleret før første nye frø ved
`2579f700479b9083331f32fd57e675d3891b635e`.
Fuld udviklingskvittering: `pilot_runtime_correction_20261008/runtime_development_proof.json`.
Ressourcer og kommende allokering: `pilot_runtime_correction_20261008/post_development_ledger.json`.
