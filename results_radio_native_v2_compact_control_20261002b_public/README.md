These chunks retain bytes from the failed 2026-10-02 b engineering control.
They do not complete that control or authorize another invocation. The original
scope and its durable spent claim remain closed.

From a checkout containing this directory, verify all chunk and whole-file
SHA256/Git blob hashes without writing:

```sh
python3 -I -S -B results_radio_native_v2_compact_control_20261002b_public/reassemble_retained_data.py --verify-only
```

To copy the already retained bytes, use `--output-dir /absolute/new-directory`.
The directory must not exist; its parent must exist. The only outputs are
`deterministic-source.bin` and `request-part.bin`. Original scope, ledger and
retention-input destinations are refused. A failed copy may leave partial files
in the newly created directory; the script never overwrites or retries them.

The script pins the exact chunk manifest and verifies chunk order, offsets,
sizes and hashes before creating an output directory. Copying rechecks those
bindings. Neither mode regenerates sources, starts a control or reads the live
ledger. Public retention must be checked at the exact published commit.
