# Provenance and scope clarification

The acquired file is the author-deposited `data/voyager.hits` in Kevin Lacker's seticore repository, Git blob `d1eb0703218be2287ec7a61a83e27e700b72271c`. All 38,176 bytes are preserved in `voyager.hits` and SHA256-verified. The deposition's introduction commit is `bdba3b70c058304f948b133f361a7e17a74b1de8` (2022-06-03); the inspected repository revision is `2e6781827ca78d9c1f3238fb101f956882df0c46`.

The historical README calls the object Voyager data; its example notebook reads this exact file and displays the same five frequency/rate/SNR reference entries decoded here. The historical writer copies selected input power slices and observation metadata into the file. These are selected telescope-derived time-frequency powers, not raw voltage or an unselected original full observation. The original full filterbank was not downloaded and no end-to-end byte comparison with that original is claimed.

All five headers identify Voyager1, the same MJD 57650.78209490741 (2016-09-19 18:46:13 UTC), and telescope ID 6. The original blimpy observatory table maps ID 6 to the Green Bank Telescope. All source text and notebook bytes are preserved and Git-blob verified in `PROVENANCE_SOURCE_HASHES.json`.

The frozen scope/result contains the phrase “related carrier/sideband structures.” This was a preliminary interpretation based on a Voyager-labelled record and its frequency pattern. The inspected author documentation does **not** label the physical role of every individual stamp. The supported final description is **five selected signal structures from the same Voyager-labelled observation**. No independent astrophysical identification of all five structures is asserted. This clarification preserves the closed scope and result identities; it does not change the data, method, tolerance or 4/5 reference-consistency outcome.

There were two production executions. The first completed numerically, and the second used the same powers/method after correcting appended newlines in copied provenance files. An intermediate concurrent review encountered an incomplete NPZ during rewriting and is recorded as failed. Final review took place after stable closure and passed exact checks of all 9,344 sample values and 391,044 supported sums. The execution history and review-attempt record preserve this distinction.

