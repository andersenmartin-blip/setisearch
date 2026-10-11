This phase treats HIP97319, HIP97461 and HIP97663 as three distinct primary
targets. Their acquisition roles remain OFF. Each target contributes one
historical2017 scan, rather than repeated scans of the same star.

Metadata-only admission:

```bash
python analysis/s2017_control_targets_20261011/driver.py --job primary20170428_HIP97319 --check-only
python analysis/s2017_control_targets_20261011/driver.py --job primary20170428_HIP97461 --check-only
python analysis/s2017_control_targets_20261011/driver.py --job primary20170428_HIP97663 --check-only
```

Actual execution requires root-authored PUBLIC_FREEZE.json and ROOT_GO.json.
The former uses `{commit,status:"PASS_...",files:[{path,bytes,sha256,git_path,
exact_served_commit_bytes:true}]}`. Every listed text file must still match;
the list includes driver, preparer, scope, scientific proposal and independent
reviews. The ROOT_GO fields checked by the driver are:

```json
{
  "status": "GO_THREE_FROZEN_PRIMARY_TARGET_JOBS",
  "scope_sha256": "<closed scope SHA256>",
  "public_freeze_commit": "<40 hexadecimal commit>",
  "CPU_cap_s_per_job": 1000,
  "wall_cap_s_per_job": 1800,
  "memory_cap_bytes_per_job": 2147483648,
  "memory_cap_bytes_aggregate": 6442450944,
  "max_simultaneous_jobs": 3,
  "workspace_cap_bytes": 8589934592,
  "job_output_budget_bytes": 104857600,
  "other_science_jobs_running": 0
}
```

The root alone invokes the actual CLI, supplying exact current SHA256s:

```text
driver.py --root <workspace> --job <primary_id> --scope-sha256 <scopeSHA>
          --freeze-commit <commit> --public-freeze-sha256 <freezeJSON_SHA>
          --root-go-sha256 <GO_JSON_SHA>
```

Each job creates 251 maps, 251 normalization records, 1007 separate raw503
capsules and four inventories/rank JSON files; the terminal receipt is the
1514th file. It authenticates its own complete compact before and after and
checks its16 decoded rows before and after. Other five source values are not
opened. All251 map searches are single calls to the unchanged detector.
Final top3 raw capsules use previously cached row-box sums, not repeated
searches. The top3 identities are metadata for a separately frozen six-scan
context phase.

Each raw503 capsule contains float32 `raw_power[16,503]`, int64
`rounded_absolute_centers[16]` and float64 `standardized_row_box_sums[16]`.
Column offsets are -251 through251. The raw501 median supports for width1
and width3 are explicitly recorded in the scope. The four queries percore
and three global top queries remain separate logical queries even when
their winning tuples coincide.

Source provenance and sampled arithmetic QA do not calibrate SNR/FAP or
establish independent sky confirmation. Maps and drift-width hypotheses
are correlated. Original failures and prior protected holdouts remain
unchanged.
