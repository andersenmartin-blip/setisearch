"""Explicit-source radio orchestration; no inherited target or calibration.

The reference detector, filters, gathers and physical vetoes are unchanged.
This module supplies their native inputs and binds every handoff. Synthetic
and telescope sources retain separate types. All outputs remain diagnostic.
"""
from collections import defaultdict
from dataclasses import asdict, dataclass
import json
import math
import platform
from types import MappingProxyType
import numpy as np
from . import search_v0p6 as core
from . import detector_m43u as detector
from . import mask_m43u as masks
from . import source_radio
from . import source_m43h as source_rows
from . import transfer_m43g as synthetic
from . import transfer_m43i as telescope
from .injection_m43r import ScoreStore
from .receiver_m43q import measure_signature as telescope_signature
from .receiver_v0p6 import _predicted_midpoint_hz

METHOD = {
    "schema": "radio-neighbor9-reference-v1", "primary": "neighbor9",
    "widths": list(core.M37_SPECTRAL_WIDTHS),
    "activity_subsets": [list(s) for s in core.M37_ACTIVITY_SUBSETS],
    "minimum_active_epoch_snr": 3., "stack_statistic": "sum",
    "isolation_seed_snr": 10., "support_snr": 3., "support_radius_bins": 9,
    "mask_dilation_bins": 9, "off_track_tolerance_hz": 20.,
    "single_adjacent_off_floor": 5.5, "receiver_half_width_hz": 100.,
    "receiver_peak_floor": 5.5, "receiver_minimum_shared_epochs": 2,
    "candidate_selection_authorized": False,
}
digest = detector.digest
_TELESCOPE_PERMIT = object()


def modelled_array_bytes(context, rows, channels):
    score_bytes = 2*len(context.bank)*len(core.M37_SPECTRAL_WIDTHS)*3*context.grid.support_bin_count*4
    return (6*rows*channels*4 + synthetic.memory_bound(rows, channels)
            + 3*score_bytes + len(context.bank)*context.grid.support_bin_count*64)


class Context:
    """A new six-scan, 16-integration context with explicit geometry and factors."""
    def __init__(self, *, scans, basis, parent_bank, grid, window,
                 maximum_records=10000, memory_limit_bytes=128*1024**2):
        self.scans = json.loads(core.canonical_json_bytes(scans))
        self.basis, self.grid, self.window = basis, grid, str(window)
        self.maximum_records = synthetic.integer(maximum_records, "retention cap")
        self.memory_limit_bytes = synthetic.integer(memory_limit_bytes, "memory cap")
        if not self.window or self.maximum_records > 10000 or self.memory_limit_bytes > 512*1024**2:
            raise ValueError("invalid bounded radio context")
        core.m37_scan_indices_for_kind(self.scans, "on")
        core.validate_factor_basis_scan_inventory(basis, self.scans)
        self.bank, self.table, self.bridge = detector.catalogue_bridge(
            parent_bank, list(range(len(parent_bank))), basis)
        self.identity = digest(self.record())
        self.validate()

    def record(self):
        return {"schema": "radio-context-v1", "window": self.window,
                "scans": self.scans, "basis_sha256": self.basis.basis_sha256,
                "labels_sha256": self.basis.labels_sha256,
                "bank_sha256": core.template_bank_sha256(self.bank),
                "factor_table_sha256": self.table.factor_table_sha256,
                "grid_sha256": core.proxy_carrier_grid_sha256(self.grid),
                "numeric_runtime": {"python": platform.python_version(), "numpy": np.__version__},
                "method": METHOD, "maximum_records": self.maximum_records,
                "memory_limit_bytes": self.memory_limit_bytes}

    def validate(self):
        core.validate_factor_basis(self.basis)
        core.validate_factor_basis_scan_inventory(self.basis, self.scans)
        core.validate_template_factor_table(self.table, self.basis, self.bank,
            expected_template_bank_sha256=core.template_bank_sha256(self.bank))
        if digest(self.record()) != self.identity:
            raise ValueError("radio context changed")

    def arguments(self):
        self.validate()
        return dict(mask_policy="neighbor9", window=self.window, grid=self.grid,
                    bank=self.bank, table=self.table, basis=self.basis, scans=self.scans)


def synthetic_signature(cache, template, score_index):
    """M43Q stationary-peak arithmetic, with explicitly synthetic provenance."""
    template = core._strict_int(template, "receiver template")
    score_index = core._strict_int(score_index, "receiver score index")
    if type(cache) is not synthetic.SyntheticCache:
        raise ValueError("synthetic cache required")
    if not 0 <= score_index < cache.grid.score_bin_count:
        raise ValueError("receiver carrier outside score grid")
    g = cache.grid.support_guard_bins
    synthetic.gather_bank_slice(cache, g, g+1, template_indices=[template], chunk_bins=1)
    geometry = cache.source.geometry
    half = cache.width//2
    predicted = _predicted_midpoint_hz(float(cache.grid.score_hz[score_index]), cache.factors[template])/1e6
    hz = predicted*1e6
    lo = math.floor((hz-100.-geometry.raw_zero_hz)/geometry.channel_width_hz)-2
    hi = math.ceil((hz+100.-geometry.raw_zero_hz)/geometry.channel_width_hz)+2
    raw = np.arange(lo, hi+1, dtype=np.int64)
    frequency = (geometry.raw_zero_hz+raw.astype("<f8")*geometry.channel_width_hz)/1e6
    use = np.abs((frequency-predicted)*1e6) <= 100.
    raw, frequency = raw[use], frequency[use]
    if not raw.size or raw.min() < half or raw.max() >= geometry.channel_count-half:
        raise core.V0P6CoverageError("complete receiver neighborhood absent")
    sums = np.zeros(len(raw), dtype="<f4")
    for row in range(cache.source.integration_count):
        sums += cache.values[row, raw-half]
    sums /= np.float32(math.sqrt(cache.source.integration_count))
    if not np.isfinite(sums).all():
        raise ValueError("nonfinite stationary receiver score")
    winner = int(np.argmax(sums))
    signature = {"predicted_mid_mhz": predicted, "peak_frequency_mhz": float(frequency[winner]),
                 "peak_snr": float(sums[winner]),
                 "offset_from_prediction_hz": float((frequency[winner]-predicted)*1e6)}
    receipt = {"adapter": "radio-synthetic-stationary-native-peak-v1",
               "cache_identity": cache.identity, "source_identity": cache.source.identity,
               "template_index": template, "score_index": score_index, "width": cache.width,
               "local_half_width_hz": 100., "raw_start": int(raw[0]), "raw_stop": int(raw[-1])+1,
               "native_channels": len(raw), "winning_raw_index": int(raw[winner]),
               "tie_break": "first ascending native-channel maximum", "mask_applied": False}
    return signature, receipt


@dataclass(frozen=True)
class Calibration:
    context_sha256: str
    accumulator: object
    threshold: object
    binding: dict
    receipt: dict
    receipt_sha256: str

    def validate(self, context):
        context.validate()
        if self.context_sha256 != context.identity or digest(self.receipt) != self.receipt_sha256:
            raise ValueError("calibration context or receipt changed")
        core.validate_threshold_certificate(self.threshold)
        masks.validate_binding(self.binding, "neighbor9", self.accumulator, self.threshold)
        if (self.receipt["threshold"] != self.threshold.as_record()
                or self.receipt["binding"] != self.binding
                or self.receipt["null_maxima"] != self.accumulator.null_maxima.tolist()):
            raise ValueError("calibration payload changed")


class NativeRun:
    """One explicit cadence, one native filter cache at a time, full score support."""
    def __init__(self, context, sources, *, domain, authority, _permit=None):
        context.validate()
        expected = {s["label"] for s in context.scans}
        if set(sources) != expected:
            raise ValueError("exact six-source inventory required")
        adapter = {"synthetic": synthetic, "telescope": telescope}.get(domain)
        if adapter is None:
            raise ValueError("unknown source domain")
        if domain == "telescope" and (_permit is not _TELESCOPE_PERMIT or authority.get("context_sha256") != context.identity):
            raise ValueError("telescope context is not authorized")
        for src in sources.values():
            adapter.validate_source(src)
            if src.integration_count != 16:
                raise ValueError("reference requires 16 integrations per scan")
        if len({tuple(asdict(s.geometry).values()) for s in sources.values()}) != 1:
            raise ValueError("native cadence geometry differs")
        self.context, self.domain, self.adapter = context, domain, adapter
        self.sources = MappingProxyType(dict(sources))
        self.source_ids = {k: v.identity for k, v in sorted(sources.items())}
        self.authority = json.loads(core.canonical_json_bytes(authority))
        self._cached_key, self._cached = None, None
        first = next(iter(sources.values()))
        self.modelled_bytes = modelled_array_bytes(context, first.integration_count, first.geometry.channel_count)
        if self.modelled_bytes > context.memory_limit_bytes:
            raise core.V0P6CapacityError("radio source/score modelled buffers exceed cap")

    @classmethod
    def from_synthetic(cls, context, sources):
        return cls(context, sources, domain="synthetic", authority={"kind": "local-engineering-only"})

    @classmethod
    def from_telescope(cls, context, *, root, contract_path, contract_sha256, receipts):
        """Local rehydration only; refuse incomplete gates before opening row files.

        A future live contract must explicitly pin this context and module as
        well as the source reader. No acquisition or old receipt lookup occurs.
        """
        cfg, readiness = source_radio.load_contract(root, contract_path, contract_sha256)
        if readiness["blockers"]:
            raise ValueError("source contract blocked: " + "; ".join(readiness["blockers"]))
        module = "src/seti_repeater/pipeline_radio.py"
        if (cfg.get("analysis_context_sha256") != context.identity
                or cfg["pinned_files"].get(module) != source_rows.file_hash(__file__)
                or cfg["hdf5_runtime"] != source_radio.runtime()):
            raise ValueError("radio integration/context/runtime not frozen")
        scans = [{**s, "kind": s["role"], "epoch": i//2+1} for i, s in enumerate(cfg["scans"])]
        if scans != context.scans or set(receipts) != {s["label"] for s in scans}:
            raise ValueError("source contract and context inventory differ")
        window = next((w for w in cfg["windows"] if w["name"] == context.window), None)
        if window is None:
            raise ValueError("analysis window not frozen")
        channels = window["archive_interval"][1]-window["archive_interval"][0]
        if modelled_array_bytes(context, 16, channels) > context.memory_limit_bytes:
            raise core.V0P6CapacityError("radio source/score modelled buffers exceed cap before row loading")
        loaded = {}
        for definition in cfg["scans"]:
            label = definition["label"]
            entry = receipts[label]
            src = telescope.load_telescope_source(entry["directory"], trusted_receipt_sha256=entry["sha256"])
            expected = source_rows.make_scope(definition, window["name"], window["archive_interval"],
                                             contract_sha256, "telescope-remote")
            if json.loads(src.receipt_json)["scope"] != expected:
                raise ValueError("source receipt belongs to a different contract/window")
            loaded[label] = src
        return cls(context, loaded, domain="telescope", authority={"context_sha256": context.identity,
                   "source_contract_sha256": contract_sha256, "readiness": readiness}, _permit=_TELESCOPE_PERMIT)

    def cache(self, label, width):
        key = (label, width)
        if key != self._cached_key:
            self._cached_key, self._cached = None, None
            factors = core.factor_table_for_scan(self.context.table, self.context.basis, label)
            build = self.adapter.build_synthetic_cache if self.domain == "synthetic" else self.adapter.build_telescope_cache
            self._cached = build(self.sources[label], factors, self.context.grid, width,
                                 bank_sha256=self.context.table.template_bank_sha256)
            self._cached_key = key
        return self._cached

    def build_store(self):
        c = self.context
        c.validate()
        arrays = {(kind, t, w): np.empty((3, c.grid.support_bin_count), dtype="<f4")
                  for kind in ("on", "off") for t in range(len(c.bank)) for w in core.M37_SPECTRAL_WIDTHS}
        inventory = []
        for scan in c.scans:
            for width in core.M37_SPECTRAL_WIDTHS:
                cache = self.cache(scan["label"], width)
                values = self.adapter.gather_bank_slice(cache, 0, c.grid.support_bin_count)
                for t in range(len(c.bank)):
                    arrays[scan["kind"], t, width][scan["epoch"]-1] = values[t]
                inventory.append({"scan": scan["label"], "width": width,
                    "source_identity": cache.source.identity, "cache_identity": cache.identity,
                    "full_support_score_sha256": synthetic.array_hash(values)})
        self._cached_key, self._cached = None, None
        return ScoreStore(arrays, {"schema": "radio-native-score-inventory-v1", "domain": self.domain,
            "context_sha256": c.identity, "source_ids": self.source_ids,
            "authority": self.authority, "native_caches": inventory,
            "modelled_array_bound_bytes": self.modelled_bytes})

    def validate_store(self, store):
        self.context.validate()
        p = store.provenance
        if (p["context_sha256"] != self.context.identity or p["domain"] != self.domain
                or p["source_ids"] != self.source_ids or p["authority"] != self.authority):
            raise ValueError("score store and receiver cadence differ")

    def receiver(self, records, bank, table):
        if core.template_bank_sha256(bank) != self.context.table.template_bank_sha256 or table is not self.context.table:
            raise ValueError("receiver catalogue changed")
        signatures = {r["record_id"]: [] for r in records}
        queries = defaultdict(list)
        for r in records:
            for e in r["active_epochs_zero_based"]:
                queries[f"epoch{e+1}_on", r["spectral_width_channels"]].append((r, e))
        receipts = []
        measure = synthetic_signature if self.domain == "synthetic" else telescope_signature
        for (label, width), entries in sorted(queries.items()):
            cache = self.cache(label, width)
            for r, e in entries:
                sig, receipt = measure(cache, r["template_index"], r["proxy_carrier_index"])
                signatures[r["record_id"]].append({"epoch_zero_based": e, **sig})
                receipts.append({"record_id": r["record_id"], "scan": label, **receipt})
        for entries in signatures.values():
            entries.sort(key=lambda item: item["epoch_zero_based"])
        self._cached_key, self._cached = None, None
        return signatures, {"schema": "radio-native-receiver-v1", "domain": self.domain,
            "context_sha256": self.context.identity, "source_ids": self.source_ids,
            "queries": receipts, "signatures_sha256": digest(signatures)}

    def calibrate(self, store, *, shifts, minimum_shift_bins, reference_floor, quantile, rank_ceiling):
        self.validate_store(store)
        acc, summary = detector.calibrate(**self.context.arguments(), store=store,
            shifts=shifts, minimum_shift_bins=minimum_shift_bins)
        threshold = core.calibrated_threshold([acc], expected_window_ids=[self.context.window],
            reference_floor=reference_floor, quantile=quantile, scientific_p_ceiling=rank_ceiling)
        binding = masks.bind_calibration(acc, threshold, "neighbor9")
        receipt = {"context_sha256": self.context.identity, "source_domain": self.domain,
                   "source_ids": self.source_ids, "store_provenance": store.provenance,
                   "summary": summary, "null_maxima": acc.null_maxima.tolist(),
                   "distinct_shift_rows": len(np.unique(shifts, axis=0)),
                   "shift_count": len(shifts), "binding": binding, "threshold": threshold.as_record(),
                   "independent_observations": False, "conditional_resampling_only": True}
        return Calibration(self.context.identity, acc, threshold, binding, receipt, digest(receipt))

    def execute(self, store, calibration):
        """No truth arguments; complete native search and all unchanged physical tests."""
        self.validate_store(store)
        calibration.validate(self.context)
        if calibration.receipt["source_domain"] != self.domain:
            raise ValueError("calibration source domain changed")
        result = detector.execute(**self.context.arguments(), store=store,
            calibration_binding=calibration.binding, calibration=calibration.accumulator,
            threshold=calibration.threshold, receiver_factory=self.receiver,
            maximum_records=self.context.maximum_records)
        clusters = complete_clusters(result)
        report = {"schema": "radio-integrated-diagnostic-v1", "source_domain": self.domain,
                  "context_sha256": self.context.identity, "source_ids": self.source_ids,
                  "calibration_receipt_sha256": calibration.receipt_sha256,
                  "score_provenance": store.provenance, "detector": result, "clusters": clusters,
                  "complete": True, "scientific_candidate_selection_authorized": False}
        report["report_sha256"] = digest(report)
        return report


def complete_clusters(result):
    """Expose the existing 20-Hz ON-track connected components without truncation.

    This is a presentation partition, not an extra veto or one physical source
    per cluster. Transitive components can span more than 20 Hz.
    """
    decisions = {d["record_id"]: d for d in result["decisions"]}
    groups = defaultdict(list)
    for r in result["receiver_alias"]["records"]:
        evidence = r["receiver_alias_evidence"]
        groups[evidence["alias_identity_component_sha256"]].append(r["record_id"])
    expected = {r["record_id"] for r in result["retained"]["on"]}
    members = [rid for ids in groups.values() for rid in ids]
    if len(members) != len(set(members)) or set(members) != expected or set(decisions) != expected:
        raise ValueError("cluster partition lost or duplicated retained members")
    return [{"cluster_sha256": key, "member_ids": sorted(ids), "member_count": len(ids),
             "physical_survivor_ids": sorted(r for r in ids if decisions[r]["passes_evaluated_physical_vetoes"]),
             "diagnostic_final_ids": sorted(r for r in ids if decisions[r]["passes_evaluated_physical_vetoes"]
                                          and decisions[r]["meets_diagnostic_rank_cut"])}
            for key, ids in sorted(groups.items())]
