# Gemte stationære ON/OFF-forskelle — 9. oktober 2026

Én ny eksplorativ prioritering over de seks allerede gemte fuldtidsspektre fra HIP98505. Der hentes ingen nye teleskopdata, afkodes ingen HDF5-stykker og genkøres ingen afsluttet driftsøgning. Den oprindelige A/B-kvalifikation forbliver FAIL_CLOSED.

For hver scanning og kanal beregnes det relative overskud `e = mean_power / running_median_baseline - 1`. Bredder 1 og 3 kanaler undersøges. Hver ON rangeres selvstændigt efter `D = e_ON - max(adjacent_OFF_e within ±32 channels)`, med samme bredde i ON og OFF. ON1 bruger OFF1; ON2 bruger OFF1/OFF2; ON3 bruger OFF2/OFF3. Alle fortegn og begge bredder bevares. En lav forskel er ikke et veto.

Det faste kanalinterval er `[283, 1048293)`, relativt til fysisk kildekanal 159383552. Marginen dækker den tidligere 501-kanals baseline, én breddekanal og 32 kanalers kontrolvindue. Top20 pr. ON vises med NMS32; top3 pr. ON får seks gemte spektralprofiler over ±128 kanaler. Signaler i kun én ON kræver ikke gentagelse i de øvrige ON-scanninger for at blive bevaret.

Script, kildeoplysninger, seks NPZ-indgange og omfang låses med hash før kørslen. NPZ-indgangene udtrækkes fra det bevarede resultatarkiv og kontrolleres mod dets indeks. En konservativ reservation på 60 CPU-s dækker denne analyse, forberedelse, gennemgang og publicering. Jobgrænser er 45 CPU-s, 120 s wall og 1,5 GiB hukommelse. Delresultater bevares ved fejl; der genkøres ikke automatisk.

Forskellen er en beskrivende størrelse i relative effektenheder, ikke SNR eller kalibreret signifikans. Baselineforskelle kan ligne ON-overskud; maksimum i OFF-vinduet kan inkludere anden emission. Frekvens- og breddeforsøg er korrelerede. Fuldtidsmidling kan udviske driftende eller korte signaler. Det er én historisk observation, og eksponering og frekvensdækning tælles ikke som nye uafhængige observationer.
