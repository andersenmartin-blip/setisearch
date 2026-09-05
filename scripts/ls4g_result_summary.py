#!/usr/bin/env python3
"""Validate and present the completed LS4G ledger without rerunning detection."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ls4g_synthetic_recovery import encoded, verify_manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_ls4g_synthetic_recovery"
FLAGS = ("passed", "supported", "recovered", "off_veto", "reference_veto")


def verify_results():
    verify_manifest(ROOT / "LS4G_FREEZE.sha256")
    verify_manifest(ROOT / "LS4E_FREEZE.sha256")
    config = json.loads((ROOT / "config/ls4g_synthetic_recovery.json").read_text())
    summary = json.loads((OUT / "summary.json").read_text())
    identity = summary.pop("result_sha256")
    assert hashlib.sha256(encoded(summary)).hexdigest() == identity, "summary digest"
    summary["result_sha256"] = identity
    assert summary["freeze_sha256"] == hashlib.sha256((ROOT / "LS4G_FREEZE.sha256").read_bytes()).hexdigest()
    raw, archive = OUT / "trials.jsonl", OUT / "trials.jsonl.gz"
    payload = raw.read_bytes() if raw.exists() else gzip.decompress(archive.read_bytes())
    assert hashlib.sha256(payload).hexdigest() == summary["ledger_sha256"], "ledger digest"
    rows = [json.loads(line) for line in payload.splitlines()]
    assert summary["status"] == "completed"
    assert len(rows) == summary["total_trials"] == config["expected_trials"]
    seen = set()
    totals = [{key: 0 for key in (*FLAGS, "trials")} for _ in summary["cells"]]
    for row in rows:
        key = (row["cell"], row["seed"])
        assert key not in seen, "duplicate trial"
        seen.add(key)
        assert row["seed"] in config["seeds"] and 0 <= row["cell"] < len(totals)
        assert all(isinstance(row[k], bool) for k in FLAGS)
        assert row["passed"] == (row["supported"] and not row["off_veto"] and not row["reference_veto"])
        assert row["recovered"] == (row["passed"] and row["matched_truth_pulses"] >= 3)
        assert row["matched_truth_pulses"] <= len(row["injected_on"])
        assert all(len(row[k]) == 6 for k in ("inside_counts", "reference_counts", "off_counts"))
        if summary["cells"][row["cell"]]["kind"] == "null":
            assert not row["injected_on"] and not row["injected_control"]
        totals[row["cell"]]["trials"] += 1
        for flag in FLAGS:
            totals[row["cell"]][flag] += row[flag]
    for expected, calculated in zip(summary["cells"], totals):
        assert expected["trials"] == len(config["seeds"])
        assert all(expected[k] == v for k, v in calculated.items()), "aggregate mismatch"
    compressed = gzip.compress(payload, compresslevel=9, mtime=0)
    if archive.exists():
        assert gzip.decompress(archive.read_bytes()) == payload
    else:
        archive.write_bytes(compressed)
    return config, summary


def matrix(cells, widths, amplitudes, **filters):
    return np.array([[next(c["recovered"] for c in cells if
                          all(c.get(k) == v for k, v in filters.items()) and
                          c["width_s"] == w and c["amplitude_sigma"] == a)
                      for a in amplitudes] for w in widths])


def figure(config, summary):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.hashsalt": "ls4g-v1"})
    fig, axes = plt.subplots(2, 3, figsize=(13, 8.7), gridspec_kw={"height_ratios": [1.45, 1]})
    fig.subplots_adjust(left=.075, right=.97, bottom=.105, top=.84, wspace=.36, hspace=.52)
    fig.suptitle("LS4G · synthetic pulse recovery", x=.075, y=.97, ha="left", fontsize=22, fontweight="bold")
    fig.text(.075, .92, "Truth-associated recoveries / 12 seeds per cell · unchanged LS4E detector", fontsize=12)
    fig.text(.075, .885, "Amplitude is added per-sample level / baseline noise SD; it is not integrated S/N.", color="#4b5563")
    labels = ["Independent Gaussian noise", "Correlated Gaussian noise · ρ = 0.8", "ON interval · noise variance ×4"]

    def draw(ax, values, widths, amplitudes, title):
        ax.imshow(values, cmap="Blues", vmin=0, vmax=12, aspect="auto")
        ax.set_xticks(range(len(amplitudes)), [f"{a:g}" for a in amplitudes])
        ax.set_yticks(range(len(widths)), [f"{1000*w:g}" for w in widths])
        ax.set_xlabel("Added amplitude / baseline SD")
        ax.set_ylabel("Pulse width (ms)")
        ax.set_title(title, fontsize=11, pad=12, loc="left")
        for (i, j), value in np.ndenumerate(values):
            ax.text(j, i, str(value), ha="center", va="center", color="white" if value >= 7 else "#172554", fontsize=11)
        for spine in ax.spines.values():
            spine.set_visible(False)

    for ax, bg, label in zip(axes[0], config["backgrounds"], labels):
        draw(ax, matrix(summary["cells"], config["widths_s"], config["amplitudes_sigma"], kind="recovery", background=bg),
             config["widths_s"], config["amplitudes_sigma"], label)
    control = config["control"]
    for ax, location, label in zip(axes[1, :2], ["off", "on_reference"], ["One extra OFF pulse", "One extra ON-reference pulse"]):
        draw(ax, matrix(summary["cells"], control["widths_s"], control["amplitudes_sigma"], kind="control", location=location),
             control["widths_s"], control["amplitudes_sigma"], label)
        ax.set_ylabel("Control pulse width (ms)")
    axes[1, 2].axis("off")
    axes[1, 2].text(0, .98, "Control experiment", fontsize=13, weight="bold", va="top")
    axes[1, 2].text(0, .80, "ON train fixed at 12 ms, amplitude 10.\n\nA single 100 ms control pulse at\namplitude 2 vetoed recovery in\nall 12 seeds at either location.\n\nControls can reject an injected signal.", fontsize=11, va="top", linespacing=1.5)
    fig.text(.075, .035, "Fixed 1 ms synthetic geometry; reused seeds across cells. No radio data, survey completeness or calibrated false-alarm rate.", fontsize=10, color="#4b5563")
    fig.savefig(OUT / "recovery_grid.svg", metadata={"Date": None})
    fig.savefig(OUT / "recovery_grid.png", dpi=160, metadata={"Software": "LS4G result summary"})
    plt.close(fig)


def report(config, summary):
    cells = summary["cells"]
    text = """# LS4G: conditional synthetic recovery result

**Completed: 1,692 frozen synthetic trials; no detector retuning or radio-data access.**

The unchanged LS4E diagnostic has a width- and noise-dependent operating range.
Correlated noise reduces recovery, particularly for the shortest pulses. A
single unrelated pulse in a control region can reject an otherwise recovered
ON train. These findings qualify interpretation of LS4F's 0/7 result; they do
not change those seven dispositions or identify the origin of any feature.

![Recovery counts for every injected grid cell](results_ls4g_synthetic_recovery/recovery_grid.svg)

## Selected comparisons

All fractions below are truth-associated recoveries from 12 seeds per cell.
Amplitude is added per-sample level divided by baseline marginal noise SD,
not integrated S/N or flux. Each train contains six separated rectangular
pulses with seed-specific time jitter. This is a conditional synthetic study,
not an astronomical sensitivity measurement.

| ON pulse width | Amplitude | Independent noise | AR(1), rho 0.8 | ON variance ×4 |
|---|---:|---:|---:|---:|
"""
    for width, amplitude in [(0.001,16.),(.003,8.),(.012,4.),(.03,4.),(.1,2.),(.3,1.)]:
        counts = [next(c["recovered"] for c in cells if c["kind"] == "recovery" and
                       c["background"] == bg and c["width_s"] == width and c["amplitude_sigma"] == amplitude)
                  for bg in config["backgrounds"]]
        text += f"| {width*1000:g} ms | {amplitude:g} | " + " | ".join(f"{n}/12" for n in counts) + " |\n"
    text += """
These selected comparisons illustrate the full frozen grid shown above; no
interpolated recovery threshold or confidence bound is inferred. Increasing
ON-only noise can occasionally raise detections because normalization uses
the unaffected reference. For example, at 30 ms and amplitude 2 the ON-variance
case recovered 2/12, versus 0/12 in independent unit noise. This is not evidence
that noisier observations improve intrinsic sensitivity.

## Control veto cost

The control experiment uses independent Gaussian noise and a fixed 12 ms ON
train at amplitude 10. With zero added control amplitude it recovers 12/12 in
every repeated baseline cell. Every control-grid trial retains cross-scale
ON support before vetoes. At 100 ms control width and amplitude 2, recovery
falls to 0/12 for both OFF and ON-reference locations. A single control pulse
can therefore reject a successfully detected injected ON train.

At 12 ms control width and amplitude 4, OFF vetoes occur in 6/12 trials and
ON-reference vetoes in 9/12. These locations have different times and noise
realizations, so this difference does not isolate a pure location effect.
OFF and ON scans are separate: no simultaneous sky coincidence is simulated.

## Nulls, completeness and evidence

The 36 no-injection cases produced zero passes: 0/12 in each background.
Seeds and innovations are reused across background families, so 36 is a
count of tested cases, not independent population trials. Across the entire
grid, every passing trial also satisfied the frozen truth-association rule.
Neither statement calibrates a false-alarm probability.

There are 1,296 recovery trials, 36 no-injection cases and 360 control trials.
All 141 cells contain exactly the 12 predeclared seeds. The ledger's SHA256,
unique trial identities, boolean decision logic and every aggregate were
checked independently of the simulation loop. All 39 relevant unit tests
passed before the first grid execution. The LS4E and LS4G freezes verify.
The plan was committed locally in `5605bec` before execution; it was not
publicly preregistered. Thresholds and grid were not changed after inspection.

## Scope and next boundary

The 1 ms sample geometry differs from LS4F's native 0.349525 ms geometry.
Fixed envelopes bypass Stage-1 selection. No frequency-channel extraction,
quantization, clipping, instrumental response, real-noise distribution or
physical diffraction template is modeled. Fractions are specific to this
small synthetic grid and cannot be transported to survey completeness, a
flux limit, an occurrence rate or a general light-sail exclusion.

A useful next experiment would separately freeze injections into measured,
candidate-independent background data and include the upstream selection
procedure. Its input identities, held-out windows and resource limits must
be defined before reading spectra. No such new data access occurs in LS4G.
The present detector and the published LS4F dispositions remain unchanged.

## Reproduction

```bash
sha256sum -c LS4G_FREEZE.sha256
sha256sum -c RESULTS_MANIFEST_LS4G.sha256
PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_ls4*.py'
PYTHONPATH=src:scripts python scripts/ls4g_result_summary.py
```

The summary script verifies and presents the existing ledger, and can read
its lossless `trials.jsonl.gz` archive directly. The uncompressed ledger SHA256
is bound in `summary.json`; no scan arrays are included. To rerun the frozen
simulation, first preserve and move aside the existing result directory,
then run `PYTHONPATH=src:scripts python scripts/ls4g_synthetic_recovery.py`.
The runtime refuses to overwrite a prior run. Scientific rows are deterministic
for the recorded runtime; elapsed time makes the full summary identity run-specific.
"""
    text += f"\nRuntime: Python {summary['python_version']}, NumPy {summary['numpy_version']}.\n"
    text += f"\nResult identity: `{summary['result_sha256']}`.\n"
    (ROOT / "LS4G_SYNTHETIC_RECOVERY_RESULT.md").write_text(text)


def main():
    config, summary = verify_results()
    # Report assertions bind prose conclusions to the retained evidence.
    assert all(c["passed"] == c["recovered"] for c in summary["cells"])
    assert all(c["supported"] == 12 for c in summary["cells"] if c["kind"] == "control")
    assert all(c["passed"] == 0 for c in summary["cells"] if c["kind"] == "null")
    figure(config, summary)
    report(config, summary)
    print(f"Verified {summary['total_trials']} trials and {len(summary['cells'])} cells; report and figure written.")


if __name__ == "__main__":
    main()
