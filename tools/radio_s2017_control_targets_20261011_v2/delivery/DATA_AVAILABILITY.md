# Kilder og efterprøvning af de nye kontrolretninger

Den nye resultatpakke indeholder alle 753 gemte søgekort, 3.021 rå503-scorevinduer med normaliseringsdata, 54 faste kontekster med deres råvinduer, begge uafhængige QA-receipts, kode, scope, fejlproveniens, rapport, figur og tabeller. De seks fulde kilde-H5-filer ligger i den tidligere RAW-pakke og duplikeres ikke.

RAW-afhængighed: `SETI_S2017_NATIVE171_RAW_2026-10-10.zip`, 466.351.822 bytes, SHA256 `6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786`. De allerede gendannede filbytes blev autentificeret før denne fase; `continuation_20261011/recovery/NATIVE171_OPAQUE_RESTORATION_RECEIPT.json` har SHA256 `1b8392ea4eeccfce9bd5e4727ca2258ed4028998e67226fe388007e3dd6a11a2`. Den nye kontekst-QA autentificerede igen alle seks H5-filer og 96 afkodede rækker. Ingen nye teleskopdata blev hentet.

| Relativ kildefil | Bytes | SHA256 |
|---|---:|---|
| `analysis/new_visit_recovery/results/acquire/epoch1_off.compact.h5` | 50432235 | `7808fdf482af7d6eeead61f4aee17e185ffa55e5767d74debe3bfa1362eb91e3` |
| `analysis/new_visit_recovery/results/acquire/epoch1_on.compact.h5` | 49818880 | `8dd5d3461772a5b670ee322903ac59113a724be3ea38c6c65a9dc9c6e9c50a82` |
| `analysis/new_visit_recovery/results/acquire/epoch2_off.compact.h5` | 49736169 | `2ae845df0df0cf6e0d3665c61930b63f61539b7eecd9c2987b1709ef8609e0a4` |
| `analysis/new_visit_recovery/results/acquire/epoch2_on.compact.h5` | 49384759 | `b6c96c859938dabe4501d56ac3f7ec09cb009df1c6884fd7c3b342bddfc24df1` |
| `analysis/new_visit_recovery/results/acquire/epoch3_off.compact.h5` | 49597930 | `ffa798638d16e3db51ce106af46aa8b921d3b94fb5dc4f5951fc62e18935643c` |
| `analysis/new_visit_recovery/results/acquire/epoch3_on.compact.h5` | 49336615 | `431afe1b7bd5a3c2f2444945dcbfcf5ea7c5fd35558186ad6edf3c9a5bb6d0fc` |

Bevar pakkens workspace-relative stier. `MANIFEST.json` giver eksakt medlemskab, filstørrelser og SHA256. De tre primærreceipts erklærer alle outputs; QA-receipts binder de faktiske inputbytes. Rå503-vinduerne gør lokale 501-medianer og de gemte rækkebokssummer kontrollerbare. Kernens gemte MAD/lokation er hashbundet, men kræver de fulde H5-filer og preprocessing for en separat fuld refiltrering. Alle 4096 carrier-maksima pr. kort er gemt; QA er ikke en uafhængig genkørsel af hele drift/bredde-gridet.

Den faktiske kode/scope-frysning før nye værdier er commit `867005e7da7aed50ea98220a0c4643d601cf6416`; `PUBLIC_FREEZE.json` indeholder den eksakte served-byte-kontrol. Runtime: Python med NumPy 2.3.5, SciPy 1.17.0, h5py 3.15.1, hdf5plugin 7.1.0, HDF5 1.14.6; rapportfigur Matplotlib 3.10.8. `CLI.md`, de fire faseprogrammer og scopes dokumenterer de faktisk anvendte argumenter og grænser. Programmerne er create-only og kræver lukkede inputpins og særskilt adgang til en ny outputfase ved genkørsel. De historiske GO-filer er kørselsproveniens.

Søgning på de oprindelige OFF-stjerner er særskilt fra ON-søgningen og den tidligere indsprøjtningstest. Hver stjerne har én primærscanning fra samme besøg. Resultaterne fastslår ingen kalibreret S/N, FAP, fluxfølsomhed, besøgsreplikation eller fysisk oprindelse. Den forberedte mulighed for 1536 yderligere kort er kun en metadataplan og er ikke kørt.
