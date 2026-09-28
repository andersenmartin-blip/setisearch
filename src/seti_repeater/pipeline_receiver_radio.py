"""Synthetic-only downstream integration for ReceiverBank.

The module has no telescope constructor.  It qualifies the distinct receiver
factor contract through calibration, retention and physical stages without
modifying or impersonating the legacy radio Context/FactorBasis path.
"""
from collections import defaultdict
from dataclasses import dataclass
import json
from types import MappingProxyType
import numpy as np

from . import receiver_contract_radio as contracts
from . import detector_receiver_radio as detector
from . import receiver_bank_radio as received
from . import mask_m43u as masks
from . import pipeline_radio as legacy
from . import search_v0p6 as core
from . import transfer_m43g as native
from .injection_m43r import ScoreStore

SCHEMA = "radio-receiver-downstream-context-v1"
digest = detector.digest


class Context:
    def __init__(self, *, scans, factors, grid, window,
                 trusted_bank_identity, source_contract_bytes, design_bytes,
                 maximum_records=10000, memory_limit_bytes=256*1024**2):
        self.factor_contract = contracts.build(factors, scans,
            trusted_bank_identity=trusted_bank_identity, source_contract_bytes=source_contract_bytes)
        p = json.loads(factors.provenance_json)
        if received.sha(design_bytes) != p['window_design_sha256']:
            raise ValueError('Window design differs from pinned receiver source')
        self.design_bytes = design_bytes
        matches = [w for w in json.loads(design_bytes)['windows'] if w['identity'] == p['window_identity']]
        if len(matches) != 1:
            raise ValueError('Receiver window absent from pinned design')
        self.native_window = matches[0]
        self.geometry = core.NativeFrequencyGeometry(
            self.native_window['native_frequency_low_hz'],
            abs(scans[0]['expected_header']['foff_mhz'])*1e6,
            self.native_window['native_channel_count'])
        self.scans = self.factor_contract.scans
        self.bank = self.factor_contract.bank
        self.grid = grid
        self.window = str(window)
        self.maximum_records = native.integer(maximum_records, "receiver retention cap")
        self.memory_limit_bytes = native.integer(memory_limit_bytes, "receiver memory cap")
        if (not self.window or self.maximum_records > 10000
                or self.memory_limit_bytes > 512*1024**2):
            raise ValueError("invalid bounded receiver radio context")
        self.identity = digest(self.record())
        self.validate()

    def record(self):
        return {"schema": SCHEMA, "window": self.window, "scans": self.scans,
            "receiver_factor_contract_sha256": self.factor_contract.identity,
            "template_bank_sha256": core.template_bank_sha256(self.bank),
            "grid_sha256": core.proxy_carrier_grid_sha256(self.grid),
            "primary": "neighbor9", "maximum_records": self.maximum_records,
            "memory_limit_bytes": self.memory_limit_bytes,
            "telescope_constructor_available": False,
            "scientific_candidate_selection_authorized": False}

    def validate(self):
        self.factor_contract.validate()
        p = json.loads(self.factor_contract.factors.provenance_json)
        if (received.sha(self.design_bytes) != p['window_design_sha256']
                or self.native_window not in json.loads(self.design_bytes)['windows']
                or self.native_window['identity'] != p['window_identity']
                or self.window != 'hd189733_'+p['role']+'_receiver_v1'
                or self.grid.score_half_bins != 40 or self.grid.support_guard_bins != 9
                or abs(self.grid.center_mhz*1e6-p['center_hz']) > 1e-6
                or self.grid.channel_width_hz != self.geometry.channel_width_hz
                or self.geometry.raw_zero_hz != self.native_window['native_frequency_low_hz']
                or self.geometry.channel_count != 65536):
            raise ValueError('Receiver role/grid/native geometry differs from published design')
        if self.bank != self.factor_contract.bank or self.scans != self.factor_contract.scans:
            raise ValueError("receiver context catalogue or scans changed")
        if digest(self.record()) != self.identity:
            raise ValueError("receiver downstream context changed")


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
            raise ValueError("receiver calibration context or receipt changed")
        core.validate_threshold_certificate(self.threshold)
        masks.validate_binding(self.binding, "neighbor9", self.accumulator, self.threshold)
        if (self.receipt["threshold"] != self.threshold.as_record()
                or self.receipt["binding"] != self.binding
                or self.receipt["null_maxima"] != self.accumulator.null_maxima.tolist()):
            raise ValueError("receiver calibration payload changed")


class NativeRun:
    def __init__(self, context, sources):
        context.validate()
        if set(sources) != {s["label"] for s in context.scans}:
            raise ValueError("exact six-source receiver inventory required")
        for label, source in sources.items():
            native.validate_source(source)
            scope = json.loads(source.scope_json)
            if (source.integration_count != 16 or scope.get("scan") != label
                    or source.geometry != context.geometry or scope.get('context_sha256') != context.identity
                    or scope.get("receiver_factor_bank_sha256")
                    != context.factor_contract.factors.identity):
                raise ValueError("synthetic source does not belong to the receiver context")
        geometries = {tuple(source.geometry.__dict__.values()) for source in sources.values()}
        if len(geometries) != 1:
            raise ValueError("receiver native cadence geometry differs")
        self.context = context
        self.sources = MappingProxyType(dict(sources))
        self.source_ids = {key: value.identity for key, value in sorted(sources.items())}
        self._cached_key = self._cached = None
        first = next(iter(sources.values()))
        self.modelled_bytes = legacy.modelled_array_bytes(
            context, first.integration_count, first.geometry.channel_count)
        if self.modelled_bytes > context.memory_limit_bytes:
            raise core.V0P6CapacityError("receiver source/score buffers exceed cap")

    def cache(self, label, width):
        key = label, width
        if key != self._cached_key:
            self._cached_key = self._cached = None
            self._cached = native.build_synthetic_cache(
                self.sources[label], self.context.factor_contract.for_scan(label),
                self.context.grid, width, bank_sha256=self.context.factor_contract.factors.identity)
            self._cached_key = key
        return self._cached

    def build_store(self):
        c = self.context; c.validate()
        arrays = {(kind, t, width): np.empty((3, c.grid.support_bin_count), dtype="<f4")
                  for kind in ("on", "off") for t in range(len(c.bank))
                  for width in core.M37_SPECTRAL_WIDTHS}
        inventory = []
        for scan in c.scans:
            for width in core.M37_SPECTRAL_WIDTHS:
                cache = self.cache(scan["label"], width)
                values = native.gather_bank_slice(cache, 0, c.grid.support_bin_count)
                for t in range(len(c.bank)):
                    arrays[scan["kind"], t, width][scan["epoch"]-1] = values[t]
                inventory.append({"scan": scan["label"], "width": width,
                    "source_identity": cache.source.identity, "cache_identity": cache.identity,
                    "full_support_score_sha256": native.array_hash(values)})
        self._cached_key = self._cached = None
        return ScoreStore(arrays, {"schema": "radio-receiver-native-score-inventory-v1",
            "context_sha256": c.identity,
            "receiver_factor_contract_sha256": c.factor_contract.identity,
            "source_ids": self.source_ids, "native_caches": inventory,
            "modelled_array_bound_bytes": self.modelled_bytes,
            "source_domain": "synthetic", "telescope_values_opened": False})

    def validate_store(self, store):
        self.context.validate(); p = store.provenance
        if (p.get("context_sha256") != self.context.identity
                or p.get("receiver_factor_contract_sha256") != self.context.factor_contract.identity
                or p.get("source_ids") != self.source_ids
                or p.get("source_domain") != "synthetic"):
            raise ValueError("receiver score store and cadence differ")
        expected = {(kind,t,w) for kind in ('on','off') for t in range(len(self.context.bank))
                    for w in core.M37_SPECTRAL_WIDTHS}
        if set(store.arrays) != expected or set(store.expected_ids) != expected:
            raise ValueError('Receiver score inventory changed')
        entries = p.get('native_caches',[])
        expected_entries = [(s,w) for s in self.context.scans for w in core.M37_SPECTRAL_WIDTHS]
        if len(entries) != len(expected_entries):
            raise ValueError('Receiver cache ancestry incomplete')
        for entry,(scan,width) in zip(entries,expected_entries):
            source=self.sources[scan['label']];native.validate_source(source)
            if (entry['scan'] != scan['label'] or entry['width'] != width
                    or entry['source_identity'] != source.identity):
                raise ValueError('Receiver cache source ancestry changed')
            values=np.stack([detector.checked_vectors(store,scan['kind'],t,width,self.context.grid)[scan['epoch']-1]
                             for t in range(len(self.context.bank))])
            if native.array_hash(values) != entry['full_support_score_sha256']:
                raise ValueError('Receiver score bytes disagree with cache receipt')

    def receiver(self, records, bank):
        if core.template_bank_sha256(bank) != core.template_bank_sha256(self.context.bank):
            raise ValueError("receiver-frame catalogue changed")
        signatures = {r["record_id"]: [] for r in records}
        queries = defaultdict(list)
        for record in records:
            for epoch in record["active_epochs_zero_based"]:
                queries[f"epoch{epoch+1}_on", record["spectral_width_channels"]].append((record, epoch))
        receipts = []
        for (label, width), entries in sorted(queries.items()):
            cache = self.cache(label, width)
            for record, epoch in entries:
                signature, receipt = legacy.synthetic_signature(
                    cache, record["template_index"], record["proxy_carrier_index"])
                signatures[record["record_id"]].append({"epoch_zero_based": epoch, **signature})
                receipts.append({"record_id": record["record_id"], "scan": label, **receipt})
        for values in signatures.values():
            values.sort(key=lambda item: item["epoch_zero_based"])
        self._cached_key = self._cached = None
        return signatures, {"schema": "radio-receiver-native-receiver-v1",
            "context_sha256": self.context.identity,
            "receiver_factor_contract_sha256": self.context.factor_contract.identity,
            "source_ids": self.source_ids, "queries": receipts,
            "signatures_sha256": digest(signatures)}

    def calibrate(self, store, *, shifts, minimum_shift_bins,
                  reference_floor, quantile, rank_ceiling):
        self.validate_store(store)
        accumulator, summary = detector.calibrate(
            self.context, store, shifts, minimum_shift_bins)
        threshold = core.calibrated_threshold(
            [accumulator], expected_window_ids=[self.context.window],
            reference_floor=reference_floor, quantile=quantile,
            scientific_p_ceiling=rank_ceiling)
        binding = masks.bind_calibration(accumulator, threshold, "neighbor9")
        receipt = {"schema": "radio-receiver-calibration-v1",
            "context_sha256": self.context.identity,
            "receiver_factor_contract_sha256": self.context.factor_contract.identity,
            "source_ids": self.source_ids, "store_provenance": store.provenance,
            "summary": summary, "null_maxima": accumulator.null_maxima.tolist(),
            "distinct_shift_rows": len(np.unique(shifts, axis=0)),
            "shift_count": len(shifts), "binding": binding,
            "threshold": threshold.as_record(), "independent_observations": False,
            "conditional_resampling_only": True,
            "cross_window_transfer_qualified": False}
        return Calibration(self.context.identity, accumulator, threshold,
                           binding, receipt, digest(receipt))

    def execute(self, store, calibration):
        self.validate_store(store); calibration.validate(self.context)
        result = detector.execute(self.context, store, calibration.binding,
                                  calibration.accumulator, calibration.threshold,
                                  self.receiver)
        clusters = legacy.complete_clusters(result)
        report = {"schema": "radio-receiver-integrated-diagnostic-v1",
            "context_sha256": self.context.identity,
            "receiver_factor_contract_sha256": self.context.factor_contract.identity,
            "source_ids": self.source_ids,
            "calibration_receipt_sha256": calibration.receipt_sha256,
            "score_provenance": store.provenance, "detector": result,
            "clusters": clusters, "complete": True,
            "scientific_candidate_selection_authorized": False,
            "cross_window_transfer_qualified": False,
            "telescope_values_opened": False}
        report["report_sha256"] = digest(report)
        return report
