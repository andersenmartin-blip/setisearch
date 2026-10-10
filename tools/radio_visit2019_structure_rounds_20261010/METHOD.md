# Pure typed metadata plans over a retained cache history

This separate source family preserves the already frozen initial V2 planner
and parser. `plan_once.py` uses the exact c677 shared cache-admission source
and the exact 5fb pure typed parser, with a prospective round scope carrying
the complete initial and optional typed-completion cache configuration.
The root owns every execution and every cache or HTTP operation.

The config accepted by `prepare_scope.py` is:

```json
{
  "schema": "SETI_VISIT2019_TYPED_STRUCTURE_ROUND_PLAN_CONFIG_V1",
  "round_id": "round_01",
  "cache_admission": "Exact SETI_VISIT2019_GENERIC_METADATA_CACHE_ADMISSION_V1 object, including closed completion history",
  "additional_dependency_pins": []
}
```

The configuration is a JSON file inside the repository. The root supplies its
exact SHA256 and `--root-go-source-only-scope`. The scope writer hashes only
UTF8 source and JSON metadata, and checks retained binary paths and lengths
by file stat. It never opens PREFIX.bin or FRAGMENT.bin and imports neither
the cache loader nor parser. The generated create-only scope is
`tools/radio_visit2019_structure_rounds_20261010/scopes/round_01.json`.
After source review and exact public scope freeze the root may run:

```text
PYTHONDONTWRITEBYTECODE=1 python plan_once.py --scope ABS_SCOPE --expected-scope-sha256 EXACT_SCOPE_SHA --public-freeze-commit EXACT_40_HEX_COMMIT --root-go-metadata-only
```

The runtime first installs 20 CPU seconds, 300 wall seconds and 512 MiB
address-space caps, then authenticates every source pin and closed transport
receipt through the shared loader. Each of the six sources receives one
MetadataCache built only from its retained exact spans and one pure
`plan_source` call. No HDF5 library, dataset value, chunk-index traversal,
network API, automatic cache miss acquisition or retry is used.

Each create-only `results/radio_visit2019_structure_rounds_20261010/round_01`
contains PLAN_RESULT.json, INPUT_PINS.json and EXECUTION_RECEIPT.json.
The result preserves the pure parser's exact six plans and worst structural
status. `COMPLETE_TYPED_STRUCTURE_PLAN_CAPTURE_NO_VALUES_ADMISSION` means a
closed plan capture, even when structure remains incomplete or unsupported.
The execution receipt binds the exact result SHA and scope, worker, parser
and public commit pins. Authenticated input pins are always carried by the
bounded `SETI_VISIT2019_TYPED_STRUCTURE_INPUT_PINS_V1` manifest, keeping the
terminal receipt below 64 KiB. All admitted inputs receive exact end readbacks.

Output is capped at 4 MiB within the 12 GiB shared workspace cap. A started
output directory cannot be reused. Root separately measures reaped child
process closure. No header or scientific eligibility is asserted here; the
later cache-only metadata worker requires all six structural plans complete,
with no missing, invalid or unsupported fragments.
