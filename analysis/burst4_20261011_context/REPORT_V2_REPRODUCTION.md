# Presentation revision and reproduction

The first frozen report builder failed before creating a delivery directory because it compared a list of selected tracks with the primary QA's dictionary of per-primary TOP3 lists. Its source and failure receipt are preserved. All scientific production and both numerical QA phases were already complete and unchanged.

The separately published renderer `make_report_v2.py` flattens that dictionary in the exact selected scope's primary-directory order, verifies its own explicit SHA256 and the original frozen renderer's scope pin, and uses the displayed colormap's luminance for annotation contrast. It adds the maximum saved score with an explicit no-sigma interpretation. This presentation revision was made after saved values were exposed and is not a prospective scientific method change.

V2 source SHA256: `9d62ef125295ee03245694839aea2db04f9037856010c1e4a790baf5979a08e1`.

Its public source/readback freeze is `c417c46365ee0c0a5f46621f02aa6c5abc4b8a57`. Use the v2 parser with `--report-sha256` above, the actual context-scope, primary-QA and context-QA hashes, and their normal argument paths. Reproduce in a separate fresh directory with absent report output destination. Do not execute the known-failing original renderer as another scientific experiment or overwrite completed outputs. The completed report receipt records both original and revised code identities.
