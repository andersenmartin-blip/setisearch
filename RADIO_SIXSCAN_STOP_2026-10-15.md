# Seks-scan-validering stoppet lukket — 15. oktober 2026

Den frosne kørsel `SETI_SIXSCAN_BURST_20261015_RECOVERY_V1` er afsluttet som **`STOPPED_RETAINED_NO_RETRY`**. Stopkriteriet var den på forhånd fastsatte kapacitetsmargin under scenens 3 GiB-outputloft. Loftet blev ikke hævet efter data.

De 63 primære Gamma16-referencer var allerede gennemført. I den efterfølgende valideringsfase afsluttede 97 af 142 childprocesser med exit 0 og komplette `wait4`-kvitteringer. Identiteterne 160–204, i alt 45, blev aldrig indsendt. De er umålte og tælles ikke som nulresultater. Der var ingen aktive processer tilbage ved lukningen.

Valideringsfasen brugte 20.041,363962 målte child-CPU-sekunder. Inklusive tidligere målt kalibrering og den bevarede 1.000-CPU-s metadata-/leveringsreservation er den sluttede, forpligtede saldo 31.911,988964 CPU-s inden for den særskilte 260.000-CPU-s ramme. Pris, nye teleskoprequests og nye teleskopbytes er fortsat nul.

Der er én særskilt ressourceafvigelse. Case 147 rapporterede 598,727962 CPU-s inde i workeren før slutfinalisering, men coordinatorens autoritative hele-child-`wait4` var 601,151447 CPU-s mod det erklærede 600-CPU-s-loft. Processen sluttede med exit 0, men overskridelsen bevares som en engineering-/integritetsfejl og omskrives ikke til pass.

Ingen syntetisk QA-fase og ingen eksponeret autentisk fase blev startet. Derfor findes der intet fælles recovery-/RFI-/null-resultat, ingen kalibreret falskalarmrate og ingen kvalificeret SETI-detektion fra denne bank. Original A/B forbliver **`FAIL_CLOSED`**.

Efter stoppet blev outputobjektet for case 147 læst for at afstemme worker- og `wait4`-kvitteringer. Det skete efter at ingen flere cases kunne indsendes, førte ikke til tuning eller ny beregning og er eksplicit bevaret som post-stop-eksponering. Banken må under alle omstændigheder ikke beskrives som blind eller komplet validering.

42 lokalt hashverificerede checkpoints er gemt holdbart, samlet 1.287.220.502 bytes. Det afsluttende checkpoint er `CHECKPOINT_0042_primary_validation_phase_closed.zip`, SHA256 `05c66f5f5cd2b3cc18aa1c2024e010a2239ecc0ef3d15bbd6100a166a98e705c`, Library-id `libfile_00bcc483776481918171c4614d4ded13`. Checkpointindekset er version 32, SHA256 `a35eeec2d07e24857001c992e5d4d4789c65fee86befa6bc5786ecb14d46b388`.

Banken genoptages eller genkøres ikke. Der oprettes ingen ny bank i dette trin. Den formelle næste handling er at bevare lukningen til checkpointet 20. oktober 2026; et eventuelt senere separat studie kræver et nyt prospektivt outputbudget og en gate på autoritativ hele-child-CPU før udførelse.

[Maskinlæsbar lukning](analysis/sixscan_burst_20261015/STOP_CLOSURE_20261015.json)
