# S2017: særskilt genopretning af profilkontrollen

Den tidligere fastlåste profilfase blev forsøgt én gang og stoppede før NumPy/HDF5-import, rådataudtræk og nogen ny profilmåling. Fejlen var en proceskontrol, som blandede PID fra systemkald og fra procfs. Den gamle fase, dens kode, forsøg, outputfri fejl og offentlige freeze bevares uden genkørsel.

Denne nye fase bruger procfs egen procesidentitet ved gennemgang af procfs og kontrollerer fortsat alle øvrige relevante processer. Metode og udvalg er uændret: de 635 øvrige cross-ON-matches, 1905 uændrede ON-medlemsspor, 11430 logiske profiler i alle seks scans og 11369 forskellige geometrier. De 61 aliases deler udtræk, men bevarer egne tidspunkter.

De samme 96 gemte fuldbåndsmedianer genbruges; nye lokale flankemedianer måles kun for de nye profiler. Ingen detektor, ny rangliste, fælles sporfit, OFF-tærskel, kildeforespørgsel eller uafhængig SETI-bekræftelse indgår.

Ny adgangskontrol, én scopegenerering, kildegennemgang, proceskontroltest og offentlig bytekontrol kommer før den ene numeriske kørsel. Grænserne er 180 CPU-sekunder, 1800 vægsekunder, 1 GiB RAM, 128 MiB output og 12 GiB for de delte arbejdsområder. Uafhængig rådatadigestkontrol følger kun efter faktisk afslutning.
