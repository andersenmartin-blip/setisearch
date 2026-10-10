# S2017: faste profiler for de 635 øvrige matches

Denne særskilte fase følger alle 635 matches fra den afsluttede cross-ON-kørsel, bortset fra præcis den kendte rang 1-kombination, hvis profiler allerede er målt. Der bruges 1905 uændrede ON-medlemsspor, hver på alle seks scans: 11430 logiske scanprofiler og 11369 forskellige udtræksgeometrier. De 61 geometriske gentagelser deler et enkelt udtræk og bevarer egne referencetider.

De gemte 96 fuldbåndsmedianer genbruges som nævnere. De lokale 122 flankekanaler får nye medianer i de nye profiler. Ingen detektor, hypotesesøgning, fælles sporfit, OFF-tærskel eller kildeforespørgsel gentages. Fasen er en efterfølgende beskrivende kontrol i samme observation; den kvalificerer ingen SETI-kandidat.

Metode, kode, faktisk adgangskontrol, udvælgelse og geometri fryses offentligt og læses tilbage før den ene numeriske kørsel. Grænserne er 180 CPU-sekunder, 1800 vægsekunder, 1 GiB RAM, 128 MiB output og 12 GiB for de to delte arbejdsområder. Fejl bevares uden automatisk genkørsel.

Efter faktisk afslutning kontrolleres nye output og deres rådatadigests særskilt, uden at genmåle profilmedianer eller gentage detektoren. Ingen ekstra betalte tjenester anvendes.

Den første syntetiske testrunner og den første metadataadgangskontrol fejlede før nogen numerisk profilkørsel. Begge fejlhistorikker og kildeversioner er bevaret. Den korrigerede test bestod alle ni prøver; den korrigerede metadataadgangskontrol og den ene scopegenerering er faktisk afsluttet. Stirettelsen har en særskilt uafhængig kildegennemgang.
