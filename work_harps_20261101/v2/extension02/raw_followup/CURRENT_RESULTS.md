# Aktuel råopfølgning på den nye HARPS prøve

**59 af de 336 nye V2-træf er rågennemgået:** 44 sandsynlige detektorartefakter, 8 forenelige med atmosfærisk O I, 6 uafklarede spektralstrukturer og 1 med utilstrækkelig billedkobling. De øvrige **277 mangler rågennemgang**. Alle vurderinger er foreløbige; der er ingen identificeret laser eller kvalificeret SETI-kandidat.

| Aktuel V2 status | Antal |
|---|---:|
| Sandsynlig detektorartefakt | 44 |
| Forenelig med atmosfærisk O I | 8 |
| Uafklaret spektralstruktur | 6 |
| Utilstrækkelig råbilledkobling | 1 |
| Endnu ikke rågennemgået | 277 |
| Hele det nye katalog | 336 |

Delprøven bruger 8 eksponeringer med alle 6 nye V1-træf, suppleret i den fastlagte observationsrækkefølge. Efter opfølgningen har V1-posterne 3 foreløbige artefakt- og 3 O I-vurderinger. Alle seks matcher et V2-træf i samme eksponering og tælles ikke som seks ekstra, uafhængige fysiske hændelser. Det V1-prioriterede udvalg er ikke en repræsentativ prøve til måling af en global falsk-alarm-rate.

Den første rågennemgang af 65 V1/V2-poster er bevaret i [baseline-rapporten](RESULTS.md). To separate analyseagenters vurderinger stemte for alle 65; hovedagentens 9 stikprøver stemte også. Efterfølgende gav den samme bredere referencekontrol som i det tidligere projekt støtte for 8 af de 9 mapping-begrænsede poster. To nye gennemgange stemte på 4 artefakter, 4 uafklarede spektrale/instrumentelle strukturer og 1 fortsat begrænsning. Hovedagenten gennemså alle tre neutrale billedsider og vedtog dette forsigtige statuslag. Det er ikke blindet forskervalidering eller uafhængigt menneskeligt review.

**V2E2-0225 forbliver begrænset.** Dens tidligere problematiske orden 33 består nu kontrollen, men orden 32 har kun en rå/native-korrelation på 0,6009. Den lille rumlige afvigelse på 0,0162 pixel tilsidesætter ikke korrelationskravet. Alle dækkende ordener blev kontrolleret, og kandidatkoordinaterne blev ikke flyttet. De oprindelige rå- og native-pixels er bevaret præcist.

Den numeriske kontrol reproducerede 35 baseline-udsnit fra tre fast valgte eksponeringer. Den udvidede kontrol reproducerede alle 16 større udsnit og alle 65 referencevinduer fra fire eksponeringer. Alle 16 endelige rå/TAR-produkters identiteter og hashes er verificeret. Tre efterladte delvise filer på i alt 4 MiB er bevaret som ubrugte diagnostiske præfikser; deres overlevelsesårsag og netværksproveniens er ukendt. De påvirker ikke de verificerede analyserede input og bruges ikke som ekstra observationer.

[Alle 336 aktuelle statusposter](CURRENT_V2_ALL336_DISPOSITIONS.csv) · [alle 65 udvalgte V1/V2-poster](CURRENT_SELECTED_EVENT_DISPOSITIONS.csv) · [aktuel opsummering](CURRENT_SUMMARY.json) · [statuskombinationskode](combine_current.py) · [bredere billedkobling](mapping_followup/README.md) · [gemte input](../checkpoints/SAVED_INPUTS.md).

Billedkoblingsreglerne varierer mellem historiske gennemgange. Originale produktionskataloger, baseline-tabeller og de friske kontrolforsøg er uændrede. Opfølgningen giver hverken en global følsomhedsmåling eller et kvalificeret fravær af lasersignaler.
