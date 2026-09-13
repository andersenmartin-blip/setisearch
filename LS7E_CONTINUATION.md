# LS7E continuation

12 September 2026. LS7E completed the frozen 3,180-case **closed sector 32**
development comparison. Read [the result](results_ls7e_joint/REPORT.md), including
the failed weak-signal and extended-control requirements, before designing a
successor. Do not rerun LS7C or reinterpret LS7E as independent qualification.

The main prototype raises nominal recovery from 3/40, 12/40, 27/40 to
18/40, 37/40, 40/40 and rejects all 120 original 2×2 controls. It also accepts
4/40 and 8/40 new 3×3 controls at strengths 8.5 and 12. The sparse option helps
stellar events containing an additional aperture residual, but weak-source
separation remains inadequate. No model is adopted.

The next integrated development step is a noise-weighted comparison of stellar
and broader nuisance morphology, using these saved vectors and explicit
signal-loss accounting. Determine whether that separation supports a useful
method before spending another observing sector. Use already closed sector 29
for a separately fixed transfer comparison if warranted; sector 28 is also
closed but had the earlier continuity/eligibility failure.

## Provenance and reproduction

- Scientific local freeze: `70e9ee5cb81dbfebee4a0b4b5cf0de4ba77f18e3`.
- Public source base: `343a9d52b81f3f2724e251ca2a8f119157c1efc6`.
- [Exact freeze bundle](publication_records/2026-09-12/ls7e_source.bundle) requires
  that source base. The public release includes the same frozen file hashes.
- Raw sector 32 FITS are public MAST products, identified by original hashes in
  [source_manifest.json](results_ls7e_joint/source_manifest.json). They can be
  redownloaded; do not treat missing local caches as missing published results.
- Original LS7C/LS7D and both historical LS7C identities remain separate and
  unchanged. The [September release record](PUBLICATION_2026-09-12.md) preserves
  their publication accounting. M43AI remains complete and unadopted.

```sh
sha256sum -c LS7E_FREEZE.sha256
cd results_ls7e_joint && sha256sum -c SHA256SUMS
# From repository root:
OPENBLAS_NUM_THREADS=1 python scripts/ls7e_review.py
```

The extractor refuses an existing result directory. Any necessary reproduction
uses an explicit separate output directory and the original source hashes.
Normal continuation starts from the current public science branch and its
PROJECT_STATUS.md, not a historical worktree with pending-publication notes.
