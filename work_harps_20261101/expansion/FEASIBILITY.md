# Mulig udvidelse af HARPS-piloten

Opgørelsen bruger kun det eksisterende udsnit på 5.000 metadata-rækker og samme kvalitetskrav som piloten. Ingen nye spektre er hentet eller analyseret.

| Datagruppe | Ekstra eksponeringer | Mål med ekstra data | Mål med ≥5 ekstra eksponeringer og ≥3 nætter |
|---|---:|---:|---:|
| De oprindelige 20 hovedmål | 504 | 19 | 16 |
| Andre HD-mål, uden udviklingsstjerner | 455 | 55 | 15 |
| Udviklingsstjerner, holdt særskilt | 39 | 1 | 1 |

Et konkret forslag er 100 ekstra eksponeringer fordelt så jævnt som muligt på de 19 oprindelige mål med ekstra data: 2–6 pr. mål. Estimeret overførsel er 0.539 GB, med en foreslået hård grænse på 2,0 GB inklusive gentagne forsøg. Datoer er spredt over de tilgængelige nætter; forslaget dækker 90 nye mål/nat-par i forhold til de oprindelige 105 eksponeringer.

Præcis fem ekstra til hvert af de 20 mål er ikke muligt i dette udsnit: HD114082 har 2, HD115031 4, HD119130 2 og HD13445 ingen. Et loft på fem pr. mål giver kun 88 ekstra eksponeringer.

De 504 + 455 = 959 ekstra metadata-kandidater er endnu ikke endeligt verificerede eksponeringer. Forslaget er ikke en frosset eller udført ny analyse. Alle 105 tidligere valgte eksponeringer er udelukket både på ADP-ID og på normaliseret målnavn + t_min, så alternative reprocesseringer med samme mål og starttid ikke tælles som nye. Kendte upstream-ADP-referencer er også udelukket. Rå-ID-kontrol er PENDING og afventer eventuelle senere downloads. Tidligere søgninger i de resterende data er ukendte; fravær i referencelisten beviser ikke nyhed.

Reproduktion fra projektroden: `python expansion/inventory_metadata.py --output expansion_repeat`. CSV-filerne gemmer måloversigt, alle resterende metadata samt det foreslåede batch på 100 eksponeringer.
