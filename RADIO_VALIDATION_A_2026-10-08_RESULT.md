# Frisk validering A: hovedprøver består, samlet adgangskrav fejler

Alle 142 fastlagte identiteter blev forsøgt én gang 8. oktober 2026.
140 forsøg blev afsluttet; to nødvendige transientdiagnostikker blev afbrudt
af deres 250 CPU-sekunders kørselsgrænse. Den frosne fælles gate er derfor
**FAIL_CLOSED**: 8 af 9 krav består, men fuldstændighed og data-integritet fejler.
Pilotens teleskopværdier er fortsat uåbnede.

| Gruppe | Faktisk udfald |
|---|---|
| Stærke signaler | 14/14 genfundet i alle aktive ON-scans efter OFF-reglen |
| Signaler på arbejdsniveau | 46/48 fulde genfund; alle aktivitets-, drift- og breddekrav består |
| Matchet ON+OFF-interferens | 24/24 først genfundet i alle ON-scans, derefter alle afvist |
| Frisk syntetisk støj | 32/32 uden overlevende kandidat |
| Kortvarige udbrud i én række | 10 afsluttede forsøg, alle med overlevende hits; 2 kørselsfejl |
| Nær-spors OFF-forurening | 12/12 signaler først genfundet, derefter afvist af OFF-reglen |

Tabene ved arbejdsniveau er operating014, som ikke gav et genfund, og
operating040, hvor én af to aktive ON-scans manglede et lokaliseret genfund.
Rå nabokanaler tælles ikke som uafhængige kilder. En afbrudt diagnostik er
ikke et målt nulresultat eller et videnskabeligt signal-tab.

De afbrudte forsøg er single_row_transient010 og 011 (kørselsindeks 128 og
129). De brugte henholdsvis 250,485232 og 250,985458 CPU-s, med bevarede
TimeoutError-spor. De blev afbrudt under den fulde OFF-sammenligning; deres
manglende kort er registreret, ikke rekonstrueret. Alle originale fejl,
claims, logs, arrays-checksums, afsluttede kort og hits bevares i arkiverne.
Ingen A-identitet må køres igen eller omklassificeres til bestået.

Kørslen belastes med 11.143,686462 CPU-s: den største af summen af de fulde
proceskvitteringer og forælderens målte børne-CPU plus forælderens egen CPU.
Den tidligere reservation frigives først efter afslutningen. Der er
25.492,071999981 CPU-s tilbage før yderligere arbejde og særskilt konservativ
reservation til hidtil umålt forberedelse. Den samlede 12 CPU-timers grænse
og gamle ukendte målinger ændres ikke.

De afsluttede transientforsøg viser en væsentlig begrænsning: denne
driftsøgning kræver ikke vedvarende signalstyrke inden for en scan. Nær-spors
OFF-forurening kan samtidig afvise et ægte indsprøjtet ON-signal. De små,
syntetiske paneler giver ikke en kalibreret fejlrate på himlen.

## Den ene tilladte udviklingsrettelse

Den godkendte plan tillader højst én udviklingsrettelse og derefter helt
frisk validering. Rettelsen her vedrører udelukkende kørselsallokeringen:
250 CPU-s pr. case erstattes af løbende, eksklusive reservationer på højst
1.800 CPU-s inden for samme samlede budget og samme 30-minutters jobgrænse.
Detektor, generator, støjlov, geometri, tærskler, OFF-regel og fælles
videnskabelige krav bevares byte for byte.

To nye, adskilte DEV_RUNTIME-identiteter prøver de samme to tunge
transientgeometrier med nye SHA256-frø. Deres fulde kørsel skal afsluttes og
gennemgås før det stadig ubrugte B-panel åbnes. B skal derefter bestå alle
142 forsøg og alle oprindelige krav. En ny fejl giver metodeundersøgelse;
ingen yderligere rettelse eller ekstra valideringspanel introduceres.

Fuld opgørelse: `pilot_protocol_20261008/validation_a_complete_summary.json`.
Ressourcer: `pilot_protocol_20261008/validation_a_complete_resource_receipt.json`.
Kode/love blev fastlagt før DEV ved `cbc27ebfb10fc09f58a8ab4a1f00adad47ab1960`;
A-kørslen blev fastlagt før første frø ved
`d7f08e5caa80efbf029a728c7288d29b2e1166ba`.
