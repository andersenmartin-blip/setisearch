"""Discrete, descriptive figures for the closed 64-cell method study.

This module does not read source files, arrays, or scientific code. The caller
must establish closed-64 completeness and the audit gate before calling
``render_figures``. Only the supplied records are used. No rendering occurs at
module import, and all matplotlib imports are local to the render function.
"""


LEVELS = (10.0, 12.0, 16.0, 24.0)
DRIFTS = (-4.0, -1.25, 1.25, 4.0)
WIDTHS = (1, 3)
ACTIVITIES = ("single_third_ON", "all_three_ON")
ACTIVITY_LABELS = {
    "single_third_ON": "Third ON only (active index [4])",
    "all_three_ON": "All three ON (active indices [0, 2, 4])",
}
RESPONSES = (
    ("final_all_active_recovered", "All-active final recovery", "#245b83"),
    ("final_any_active_recovered", "Any-active final recovery", "#a55516"),
)


def _finite_number(value, label):
    """Return a finite numeric value without accepting booleans as numbers."""
    import math

    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite int or float")
    return float(value)


def _count(value, label):
    if type(value) is not int or not 0 <= value <= 4:
        raise ValueError(f"{label} must be an integer from 0 to 4")
    return value


def _validate_records(aggregates, cells):
    """Check plotting denominators and record agreement, without file access."""
    if type(aggregates) is not list or len(aggregates) != 32:
        raise ValueError("Expected exactly 32 aggregate records")
    if type(cells) is not list or len(cells) != 64:
        raise ValueError("Expected exactly 64 cell records")

    cell_index = {}
    case_ids = set()
    for cell in cells:
        if type(cell) is not dict:
            raise ValueError("Each cell must be a dictionary")
        case_id = cell.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in case_ids:
            raise ValueError("Cell case_id values must be unique nonempty strings")
        case_ids.add(case_id)
        level = _finite_number(cell.get("nominal_ideal_box_score"), "cell level")
        drift = _finite_number(cell.get("drift_hz_s"), "cell drift")
        width = cell.get("intrinsic_width_channels")
        activity = cell.get("activity")
        if level not in LEVELS or drift not in DRIFTS:
            raise ValueError("Cell factor value is outside the fixed study grid")
        if type(width) is not int or width not in WIDTHS or activity not in ACTIVITIES:
            raise ValueError("Cell width or activity is outside the fixed study grid")
        for response, _, _ in RESPONSES:
            if type(cell.get(response)) is not bool:
                raise ValueError(f"{response} must be a boolean in each cell")
        if cell["final_all_active_recovered"] and not cell["final_any_active_recovered"]:
            raise ValueError("All-active recovery cannot exceed any-active recovery")
        if activity == "single_third_ON" and (
            cell["final_all_active_recovered"] != cell["final_any_active_recovered"]
        ):
            raise ValueError("The single-active cell must have equal all/any responses")
        key = (activity, width, level, drift)
        if key in cell_index:
            raise ValueError("Duplicate grid cell")
        cell_index[key] = cell

    expected_cells = {
        (activity, width, level, drift)
        for activity in ACTIVITIES
        for width in WIDTHS
        for level in LEVELS
        for drift in DRIFTS
    }
    if set(cell_index) != expected_cells:
        raise ValueError("Cell records do not cover the exact 64-cell grid")

    aggregate_index = {}
    for aggregate in aggregates:
        if type(aggregate) is not dict:
            raise ValueError("Each aggregate must be a dictionary")
        dimension = aggregate.get("dimension")
        activity = aggregate.get("activity")
        width = aggregate.get("intrinsic_width_channels")
        factor = _finite_number(aggregate.get("factor_value"), "aggregate factor")
        if dimension not in ("strength", "drift") or activity not in ACTIVITIES:
            raise ValueError("Aggregate dimension or activity is outside the study grid")
        if type(width) is not int or width not in WIDTHS:
            raise ValueError("Aggregate width is outside the study grid")
        factors = LEVELS if dimension == "strength" else DRIFTS
        if factor not in factors:
            raise ValueError("Aggregate factor is outside the study grid")
        if type(aggregate.get("expected")) is not int or aggregate["expected"] != 4:
            raise ValueError("Every aggregate must have expected=4")
        if type(aggregate.get("valid")) is not int or aggregate["valid"] != 4:
            raise ValueError("Every aggregate must have valid=4")
        for name in (
            "final_all_active_recovered",
            "final_any_active_recovered",
            "pre_OFF_all_active_recovered",
            "pre_OFF_any_active_recovered",
        ):
            _count(aggregate.get(name), name)
        if aggregate["final_all_active_recovered"] > aggregate["final_any_active_recovered"]:
            raise ValueError("Aggregate all-active count exceeds any-active count")
        if aggregate["pre_OFF_all_active_recovered"] > aggregate["pre_OFF_any_active_recovered"]:
            raise ValueError("Aggregate pre-OFF all-active count exceeds any-active count")
        for mode in ("all", "any"):
            if aggregate[f"final_{mode}_active_recovered"] > aggregate[f"pre_OFF_{mode}_active_recovered"]:
                raise ValueError("Final recovery count exceeds its pre-OFF count")
        key = (dimension, activity, width, factor)
        if key in aggregate_index:
            raise ValueError("Duplicate aggregate record")
        selected_cells = [
            cell_index[(activity, width, factor, drift)]
            for drift in DRIFTS
        ] if dimension == "strength" else [
            cell_index[(activity, width, level, factor)]
            for level in LEVELS
        ]
        for response, _, _ in RESPONSES:
            if aggregate[response] != sum(cell[response] for cell in selected_cells):
                raise ValueError("Aggregate final recovery count disagrees with cell records")
        aggregate_index[key] = aggregate

    expected_aggregates = {
        (dimension, activity, width, factor)
        for dimension, factors in (("strength", LEVELS), ("drift", DRIFTS))
        for activity in ACTIVITIES
        for width in WIDTHS
        for factor in factors
    }
    if set(aggregate_index) != expected_aggregates:
        raise ValueError("Aggregate records do not cover the exact fixed grid")
    return aggregate_index, cell_index


def render_figures(aggregates, cells, output_directory):
    """Render six figure pairs from admitted in-memory descriptive records.

    ``aggregates`` contains 32 records: dimension (strength/drift), activity,
    intrinsic_width_channels, factor_value, expected=4, valid=4, and the final
    and pre-OFF all/any recovery counts. ``cells`` contains the exact 64 grid
    cells, with case_id, nominal_ideal_box_score, drift_hz_s,
    intrinsic_width_channels, activity, and final all/any boolean responses.

    Each aggregate fixes activity and intrinsic width and pools four distinct
    cells at the four values of the opposite factor. It is an observed count,
    not a repeated-realization estimate. Each heatmap cell is one realization.
    Files are new PDF and 300 dpi PNG outputs; existing destinations are refused.
    Returned metadata records their paths, byte sizes, hashes, and denominators.
    This function does not determine admission or read an audit artifact.
    """
    from hashlib import sha256
    from pathlib import Path

    aggregate_index, cell_index = _validate_records(aggregates, cells)
    destination = Path(output_directory)
    if not destination.is_absolute():
        raise ValueError("output_directory must be an absolute path")
    destination.mkdir(parents=True, exist_ok=True)
    stems = [
        f"method_{dimension}_{response}"
        for response, _, _ in RESPONSES
        for dimension in ("strength", "drift")
    ] + [f"method_cells_{response}" for response, _, _ in RESPONSES]
    for stem in stems:
        for extension in ("pdf", "png"):
            if (destination / f"{stem}.{extension}").exists():
                raise FileExistsError(f"Figure destination already exists: {stem}.{extension}")

    # These imports and all drawing occur only after record validation.
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Patch

    note = (
        "Observed descriptive counts; no probability, confidence interval, or false-alarm estimate.\n"
        "Nominal ideal input score is neither measured SNR nor flux. Activity groups use independent draws.\n"
        "With three ON observations, all-active requires all three; any-active requires at least one."
    )
    style = {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    }
    figures = []

    def save_pair(figure, stem, details):
        try:
            files = []
            for extension in ("pdf", "png"):
                path = destination / f"{stem}.{extension}"
                figure.savefig(path, format=extension, dpi=300, bbox_inches="tight")
                files.append({
                    "format": extension,
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path.read_bytes()).hexdigest(),
                    "dpi": 300 if extension == "png" else None,
                })
            figures.append({"figure_id": stem, **details, "files": files})
        finally:
            plt.close(figure)

    with plt.rc_context(style):
        for response, response_label, color in RESPONSES:
            for dimension, factors in (("strength", LEVELS), ("drift", DRIFTS)):
                figure, axes = plt.subplots(2, 2, figsize=(8.3, 6.8), sharey=True)
                figure.suptitle(response_label, fontsize=13, fontweight="bold", y=0.99)
                pooling = "four drift values" if dimension == "strength" else "four nominal input levels"
                figure.text(
                    0.5, 0.935,
                    f"Each marker pools {pooling}; fixed activity and intrinsic width; n = 4 distinct cells",
                    ha="center", va="top", fontsize=9,
                )
                for row, activity in enumerate(ACTIVITIES):
                    for column, width in enumerate(WIDTHS):
                        axis = axes[row, column]
                        counts = [
                            aggregate_index[(dimension, activity, width, factor)][response]
                            for factor in factors
                        ]
                        positions = list(factors)
                        axis.scatter(positions, counts, color=color, s=52, marker="o", zorder=3)
                        for position, count in zip(positions, counts):
                            axis.annotate(
                                f"{count}/4", (position, count), xytext=(0, 8),
                                textcoords="offset points", ha="center", fontsize=9,
                                fontweight="bold", color=color,
                            )
                        axis.set_title(f"{ACTIVITY_LABELS[activity]}\nIntrinsic width: {width} channel{'s' if width != 1 else ''}")
                        axis.set_xticks(positions, [f"{factor:g}" for factor in factors])
                        axis.set_yticks(range(5))
                        axis.set_ylim(-0.25, 4.65)
                        margin = (max(factors) - min(factors)) * 0.08
                        axis.set_xlim(min(factors) - margin, max(factors) + margin)
                        axis.grid(axis="y", color="#d5d9de", linewidth=0.6, zorder=0)
                        axis.spines["top"].set_visible(False)
                        axis.spines["right"].set_visible(False)
                        axis.set_xlabel(
                            "Nominal ideal input score\n(neither measured SNR nor flux)"
                            if dimension == "strength" else "Injected drift (Hz s⁻¹)"
                        )
                        if column == 0:
                            axis.set_ylabel("Recovery count (out of 4 distinct cells)")
                figure.text(0.5, 0.012, note, ha="center", va="bottom", fontsize=8, linespacing=1.5)
                figure.subplots_adjust(left=0.09, right=0.98, bottom=0.24, top=0.85, hspace=0.7, wspace=0.18)
                save_pair(figure, f"method_{dimension}_{response}", {
                    "kind": "discrete_aggregate_counts",
                    "response": response,
                    "dimension": dimension,
                    "n_per_marker": 4,
                    "marker_count": 16,
                    "opposite_factor_pool": list(DRIFTS if dimension == "strength" else LEVELS),
                    "fixed_panel_factors": ["activity", "intrinsic_width_channels"],
                    "connecting_lines": False,
                    "uncertainty_or_probability": False,
                })

            figure, axes = plt.subplots(2, 2, figsize=(8.3, 6.8))
            figure.suptitle(f"{response_label}: exact 64-cell responses", fontsize=13, fontweight="bold", y=0.99)
            figure.text(0.5, 0.935, "One independent realization per cell (n = 1); binary observed response", ha="center", va="top", fontsize=9)
            cmap = ListedColormap(["#edf0f3", color])
            norm = BoundaryNorm([-0.5, 0.5, 1.5], cmap.N)
            for row, activity in enumerate(ACTIVITIES):
                for column, width in enumerate(WIDTHS):
                    axis = axes[row, column]
                    values = [
                        [int(cell_index[(activity, width, level, drift)][response]) for level in LEVELS]
                        for drift in DRIFTS
                    ]
                    axis.imshow(values, cmap=cmap, norm=norm, origin="lower", interpolation="none", aspect="auto")
                    for drift_index, value_row in enumerate(values):
                        for level_index, value in enumerate(value_row):
                            axis.text(level_index, drift_index, str(value), ha="center", va="center", fontweight="bold", color="white" if value else "#29323a")
                    axis.set_title(f"{ACTIVITY_LABELS[activity]}\nIntrinsic width: {width} channel{'s' if width != 1 else ''}")
                    axis.set_xticks(range(4), [f"{level:g}" for level in LEVELS])
                    axis.set_yticks(range(4), [f"{drift:g}" for drift in DRIFTS])
                    axis.set_xticks([0.5, 1.5, 2.5], minor=True)
                    axis.set_yticks([0.5, 1.5, 2.5], minor=True)
                    axis.grid(which="minor", color="white", linewidth=1.5)
                    axis.tick_params(which="minor", bottom=False, left=False)
                    axis.set_xlabel("Nominal ideal input score\n(neither measured SNR nor flux)")
                    axis.set_ylabel("Injected drift (Hz s⁻¹)")
            figure.legend(
                handles=[Patch(facecolor="#edf0f3", edgecolor="#bac1c8", label="0: not recovered"), Patch(facecolor=color, label="1: recovered")],
                loc="lower center", bbox_to_anchor=(0.5, 0.142), ncol=2, frameon=False, fontsize=9,
            )
            figure.text(0.5, 0.012, note, ha="center", va="bottom", fontsize=8, linespacing=1.5)
            figure.subplots_adjust(left=0.09, right=0.98, bottom=0.29, top=0.85, hspace=0.75, wspace=0.3)
            save_pair(figure, f"method_cells_{response}", {
                "kind": "exact_binary_cell_responses",
                "response": response,
                "n_per_cell": 1,
                "cell_count": 64,
                "interpolation": "none",
                "uncertainty_or_probability": False,
            })

    return {
        "schema": "pilot-method-figures-v1",
        "closed_cell_count": 64,
        "aggregate_record_count": 32,
        "figure_count": 6,
        "file_count": 12,
        "figure_source": "validated_in_memory_aggregates_and_cells",
        "nominal_input_label": "Nominal ideal input score; neither measured SNR nor flux",
        "activity_comparison": "Independent draws, not paired realizations",
        "three_ON_response_relationship": "All-active requires all three ON; any-active requires at least one ON",
        "inference_scope": "Observed descriptive counts only; no probabilities, confidence intervals, or false-alarm estimates",
        "figures": figures,
    }
