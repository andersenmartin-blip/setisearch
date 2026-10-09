# Ny kontrolanalyse: omvendte mål-/kontrolroller, 9. oktober 2026

Fastlagt før nye udfald beregnes. Dette er en afgrænset fortsættelse af den
eksplorative inspektion af den allerede åbnede HIP98505-sekvens. Ingen ny
observation, kvalifikationsbank, driftanalyse eller ændring af gamle udfald.

De tre oprindelige OFF-scanninger søges som pseudo-mål mod deres tilstødende
oprindelige ON-scanninger. Alle 1.048.010 erklærede bærefrekvenser og begge
bredder 1/3 medregnes. Frekvensvindue, normalisering, rand og ±32-kanalers
kontrolvindue følger den tidligere stationære analyse. De gemte oprindelige
ON-kontrastarrays læses uden genberegning. Randscanningernes ene kontrol og
indre scanningers to kontroller rapporteres særskilt.

De 20 højest rangerede kontrolcentre pr. OFF bevares med den gamle afstandsregel.
De første tre pr. OFF får en ny, fast tidskontrol i alle seks scanninger: alle
16 integrationer, centrum efter valgt bredde og faste flanker ±4…±64 kanaler.
Ingen stærk eller kendt linje fjernes fra det frosne kontrolpanel. De syv gamle
ON-profiler er kun gemt sammenligningsgrundlag; deres tidskontrol gentages ikke.

Dette undersøger, om tilsvarende dataudvalgte overskud også forekommer i
kontrolretningerne, når hele frekvensfamilien undersøges. Kontrolscanningerne
antages hverken udvekslelige eller certificeret støjfri. Derfor beregnes ingen
p-værdi eller kalibreret falskalarmrate. Fund ved en anden kontrolfrekvens
afviser ikke et bestemt ON-spor eller bestemmer dets fysiske oprindelse.

Den seneste instruktion om fortsættelse og førsteprioritet til hurtig
signalanalyse følges ved en **prospektiv omfordeling af 200 CPU-s** fra en intern
2.000-CPU-s-rapportreserve. **1.800 CPU-s beskyttes fortsat til afslutningen.**
Den godkendte samlede grænse på 12 CPU-timer øges ikke; ingen historisk reservation
refunderes eller nulstilles. Den nye aktivitet reserverer 200 CPU-s inklusive
forberedelse, fejl, gennemgang, gemning og publicering. Analysejobbet har egne
grænser: 150 CPU-s, 300 s vægtid og 1,5 GiB adresselager. Pris: 0 kr.

Kode, 19 inputidentiteter og hele sammenligningsreglen er låst i
`tools/radio_native_controls_20261009/scope.json`. Den nye ledger i
`results/radio_native_controls_20261009/RESOURCE_LEDGER.json` har forrang for denne
allokering; tidligere ledgers og alle A/B FAIL_CLOSED-statusser bevares.
