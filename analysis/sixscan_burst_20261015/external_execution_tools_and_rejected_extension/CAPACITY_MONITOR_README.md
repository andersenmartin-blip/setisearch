# External sampled capacity evidence

This helper adds passive file-size evidence after its launch. It does not alter the frozen study, its coordinator, its source pins or its scientific summary. The supervising root launches it once; an existing `MONITOR_STATE.json` blocks a second launch, including after an interrupted launch.

```bash
python external_sixscan_20261015/capacity_monitor.py \
  --stage sixscan_burst_20261015 \
  --workspace . \
  --scheduler-state checkpoints_sixscan_20261015/SCHEDULER_STATE.json \
  --out capacity_trace_sixscan_20261015
```

The production monitor has not been launched as part of preparing this helper. The separate fast fixture check is:

```bash
python external_sixscan_20261015/capacity_monitor.py --selftest
```

Every five seconds, the monitor traverses the workspace and stage `results` directory. It records logical `st_size` bytes of regular files, skips symlinks, and tolerates file-not-found races during atomic renames. Other stat errors remain explicit. It includes its own trace, state and summary files in workspace counts. Counts occur during traversal before the next trace/summary writes; those newly written bytes appear in a subsequent sample.

It also reads only the small scope, coordinator state and scheduler state JSON files. Each sample contains successful closed-child counts, phase statuses, live/unsubmitted counts, declared hard caps and the coordinator's 512 MiB prelaunch margins. It does not read scientific output values or decode array payloads.

`CAPACITY_SAMPLES.jsonl` is appended and fsynced per sample. `PEAK_SUMMARY.json` and `MONITOR_STATE.json` are atomically replaced and synced. Paths identify the stage, scheduler and output relative to the measured workspace. The monitor stops when the scheduler reports `ALL_FROZEN_PHASES_CLOSED` or `STOPPED_RETAINED_NO_RETRY` **and** all coordinator `running` lists are readable or absent and contain no live entries. An unreadable phase state prevents a claimed terminal closure.

Any sampled `results` count above its 3 GiB hard cap or workspace count above its 8 GiB hard cap, as loaded from frozen SCOPE, permanently flags `OBSERVED_PROTOCOL_RESOURCE_FAILURE` in the external evidence. It does not stop workers, change caps, clean files, upload files or edit the frozen `SUMMARY.json`. Crossing a prelaunch margin is recorded separately and is not silently reclassified as a hard-cap breach.

The target start-to-start interval is 5 seconds; the declared gap limit is 7 seconds. Traversal/write delays and larger gaps are measured explicitly. Each sleep is bounded to 5 seconds. This trace proves only sampled traversal observations after launch. It is neither an atomic simultaneous census nor continuous hard-cap proof. It establishes no peak for the earlier unmonitored period, and historical root snapshots are not automatically merged or promoted into such a guarantee. No observed breach means only `NO_BREACH_OBSERVED_AT_SAMPLED_TRAVERSALS`.
