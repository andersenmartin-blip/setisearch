# Uafhængig numerisk kontrol af extension02

Kontrollen bestod. 100 af de 100 fastlagte eksponeringer er analyseret; 0 er eksplicit udeladt. Alle downloadede filhashes, de godkendte headers og 55 fastlåste kildefiler er kontrolleret. Ingen ADP-, rå-ID- eller mål/starttids-overlap med de tidligere 209 inputs blev fundet.

De gemte per-spektrumresultater genskaber samtlige katalogtabeller præcist: **6 foreløbige V1-træf og 336 foreløbige V2-profiltræf**. V2-træffene står fortsat som `UNREVIEWED`. De tilsammen gennemsøgte samples er 30650654 for V1 og 30618855 for V2.

Første, midterste og sidste godkendte eksponering i den fastlagte metadatarækkefølge blev kørt igen med begge uændrede algoritmer. Alle seks komplette resultater og inputmetadata stemmer præcist. De øvrige eksponeringers detektorberegning blev ikke genkørt i denne kontrol.

Ingen oprindelige eller nye produktionsfiler er ændret, og kontrollen hentede ingen nye data. Dette er reproduktion af de samme algoritmer og filidentiteter; den fastslår ikke signalernes ophav eller udvidelsens følsomhed.

[Maskinlæsbar kontrol](SUMMARY.json) · [headerkontrol](HEADER_RECHECKS.json) · [kontrolkode](run_audit.py) · [fastlagt plan](PLAN.json)
