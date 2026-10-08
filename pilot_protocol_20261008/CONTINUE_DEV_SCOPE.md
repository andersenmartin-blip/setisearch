# Untouched DEV continuation, 8 October 2026

The first full-family case completed: case wall64.324964s, process
wall64.671677s/CPU66.326375s/peakRSS73,912,320B. Its one declared active ON
was localized before and after OFF; this is development evidence only.

The already admitted remaining23 distinct DEV recipes will each run once with
the unchanged scientific code and settings pinned at
`cbc27ebfb10fc09f58a8ab4a1f00adad47ab1960`. The operational coordinator starts
at most four independent jobs, using unique outputs and exclusive CPU
partitions:1500CPU-s per job, total34,500CPU-s, below the37,933.673625CPU-s
remaining DEV allowance. Every child's full receipt is charged, including
failures/startup/output, with parent overhead measured separately. The unused
allocation is returned after completion. No allowance is shared twice.

```sh
python pilot_engine_20261008/continue_dev.py
```

This continuation changes execution scheduling only. It never regenerates the
first recipe, runs validation, opens telescope values, or changes scientific
definitions. All 24 DEV outcomes, including misses and interference survivors,
will be reported. A scientific miss does not abort the other prespecified
development cases; a job error remains a failure, never a zero count or pass.
