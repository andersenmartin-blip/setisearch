# Adjacent S2017 native170/172 delivery plan

This is preparation, not acquisition, search, QA, archive-completion or save evidence.
The previous phase and its archives remain unchanged. The corrected V2 manifest
is `source_manifest_v2.json`, SHA256
`2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909`.
V1 metadata remains preserved as preparation history; its per-source byte totals
were corrected before new values or public activation.

| Step | Required actual evidence | Storage action |
|---|---|---|
| Acquire |192 first-attempt ranges,597792529 BODY bytes,12 complete H5|Retain192 fsynced compressed sidecars and12 H5|
| Source QA |Actual12-file/192-compressed/192-decoded-row PASS|Retain all source bytes|
| RAW package |Root GO, pinned acquisition/source QA,192 H5 raw chunks reverified|Create-only ZIP with12 H5; omit redundant sidecars; CRC/every-member SHA|
| Durable RAW save |Root-confirmed archive identity and actual durable-save receipt|Builder performs no remote save or deletion|
| Retention |Root alone confirms save plus192 compressed H5 identities|Root may remove only192 newly redundant sidecars, retaining all old files|
| Science |Six interior jobs and two boundary jobs with public scope/code admission|No rerun of native171 interiors; record all successes/failures|
| Final QA/results |All8 complete receipts and actual saved-output/source QA|New RESULTS ZIP includes new outputs/code/scopes/receipts/plots; references prior171 H5 identities and runtime|

The unique allocated baseline was6156554240 bytes, with2433380352 bytes remaining
under the8GiB cap. The new raw bodies total597792529 bytes; H5 stores those same
compressed chunks plus small headers. Keeping sidecars,H5 and a new RAW ZIP
temporarily adds approximately three copies of the new compressed payload.
After confirmed durable RAW save, root-only removal frees597792529 logical bytes
before the approximately381MB new science outputs and approximately180MB RESULTS
ZIP. These estimates are planning, not measured artifact sizes.

Every builder instead measures current allocated blocks once per inode, checks
physical free space, admits a conservative payload-sized ZIP upper bound plus
manifest/ZIP overhead, and refuses work above8589934592 bytes. It retains kernel
flocks and has180CPU-s/1800wall-s/2GiB AS caps. Actual resource values and ZIP sizes
are written only after completion. Partial archives and failures remain preserved;
no builder retries, resumes, overwrites or deletes source payloads.

RAW preserves relative paths and all referenced retained metadata/code. It does
not copy native171 H5. `delivery/reconstruct_raw_sidecars.py` restores the exact
192 compressed sidecars from complete H5 after full-file/raw-chunk SHA checks,
without HTTP or dataset decoding. Its `--verify-only` option creates no sidecars.
The acquisition SHA must come from the archive's embedded payload manifest and
the archive itself must match its externally recorded ZIP checksum.

RESULTS excludes H5,raw bodies,wheel binaries,old ZIPs and the external
`DATA_PACKAGES.json`. It includes the prior171 acquisition receipt/H5 identity
references and exact dependency-restoration receipt, with base Python/NumPy/
SciPy/Matplotlib requirements and separately delivered original RAW/runtime
artifacts. It is not a hermetic source/input/runtime archive.

Root GO is required for either builder. RAW also requires the prospective
`RAW_DELIVERY_SCOPE.json` SHA and actual acquisition/source-QA SHA arguments.
RESULTS requires a separately pinned actual-completion admission JSON binding
all8 receipt SHAs, actual empirical QA, the root retention receipt, final builder
hashes and external-reference pins. No numeric values, HTTP or package builder
have been opened/run during this preparation.

After root verifies the prospective builder scope/code and the actual source
receipts, the RAW invocation is:

```sh
python3 analysis/s2017_next_native/delivery/build_raw_package.py \
  --root "$PWD" \
  --expected-scope-sha256 <actual-RAW_DELIVERY_SCOPE-SHA256> \
  --acquisition-sha256 <actual-COMPLETE-acquisition-SHA256> \
  --source-qa-sha256 <actual-source-QA-PASS-SHA256> \
  --freeze-commit <actual-public40hex-builder-freeze> \
  --root-go-after-source-qa
```

The builder writes `delivery/RAW_PACKAGE_RECEIPT.json` and a
`SIDECAR_RETENTION_CANDIDATES.json` after success. Candidates grant no deletion
authority. Root's confirmed save and removal record is a separate actual
receipt, using the interface in `RESULTS_ADMISSION_INTERFACE.md`.
