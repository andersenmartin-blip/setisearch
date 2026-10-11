# Data og reproduktion

Den komplette resultatpakke indeholder de 450 gemte kort, 540 diagnostiske
poster, 540 truth-audits, normaliseringsposter, begge eksekveringskvitteringer,
den uafhængige QA, all-group-sammenfatningen, den statiske figur samt den
offentligt fastlåste kode og scopes.

Pakkeidentitet og den bekræftede todelte gemning registreres i
`DATA_PACKAGE.json`. De to ordnede filer samles bytepræcist med:

```sh
cat SETI_S2017_INJECTION_2026-10-11.zip.part00 \
    SETI_S2017_INJECTION_2026-10-11.zip.part01 \
    > SETI_S2017_INJECTION_2026-10-11.zip
```

Det samlede arkiv skal have SHA256
`fb10a8b5371ade34faa09c9d4e927e0a6cce2b103fa9bd262d5a35cd811b8023`.
Den ordnede partstrøm er faktisk kontrolleret mod denne hash, og ZIP-testen
bestod for alle 1481 medlemmer. To forsøg på at gemme den enkelte 72.542.890-
byte fil fejlede ved overførsel; de skabte ikke et Library-element. De to
mindre dele blev derefter gemt med bekræftet succes.

De seks kompakte S2017-kildefiler er ikke duplikeret i resultatpakken. Deres
eksakte SHA256-identiteter står i QA-kvitteringen og svarer til det allerede
bevarede S2017-kildemateriale.

Frosne Git-punkter:

- benchmarkkode og scope: `aedf9a3e2bf33424f2d4e88875569eaa19ef4130`;
- uafhængig QA-, sammenfatnings- og figurkode: `3f6cc15bca1d7cbda7f870193db6deb9ea7cfa64`.

Den numeriske benchmark og QA må ikke genkøres som almindelig reproduktion.
Reproduktion består her af bytekontrol af den gemte pakke og saved-output-
gennemgang. Ingen fil i pakken etablerer kalibreret SNR, FAP, fysisk oprindelse
eller en bestået A/B-kvalifikation.

