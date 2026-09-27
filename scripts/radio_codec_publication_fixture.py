"""Reproducible codec/direct handoff fixture, separate from scientific panels."""
import json
from pathlib import Path
from unittest.mock import patch

import h5py
import hdf5plugin
import numpy as np

from seti_repeater import codec_direct_radio as adapter
from seti_repeater import factors_radio as direct
from seti_repeater import pipeline_direct_radio as pipeline
from seti_repeater import search_v0p6 as core
from seti_repeater import source_m43h as rows
from seti_repeater import source_radio as source
from seti_repeater import transport_radio as net
from seti_repeater import transfer_m43g as native

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/radio_codec_publication_engineering_20260927.json"


def configuration():
    cfg = json.loads(CONFIG.read_text())
    for path, expected in cfg["input_sha256"].items():
        if rows.file_hash(ROOT / path) != expected:
            raise ValueError("preserved input changed: " + path)
    if cfg["runtime"] != source.runtime():
        raise ValueError("codec fixture runtime changed")
    return cfg


class Response:
    def __init__(self, url, payload, status, headers):
        self.url, self.payload, self.status, self.headers = url, payload, status, headers
    def geturl(self): return self.url
    def read(self, count): return self.payload[:count]
    def __enter__(self): return self
    def __exit__(self, *args): pass


class LocalBytes:
    """No sockets; every request must match a generated .invalid fixture."""
    def __init__(self, definition, payload):
        self.definition, self.payload, self.calls = definition, payload, []

    def __call__(self, request, timeout):
        if request.full_url != self.definition["url"]:
            raise AssertionError("fixture URL changed")
        self.calls.append([request.get_method(), request.headers.get("Range")])
        headers = {"ETag": self.definition["expected_etag"],
            "Accept-Ranges": "bytes", "Content-Length": str(len(self.payload))}
        if request.get_method() == "HEAD":
            return Response(request.full_url, b"", 200, headers)
        first, last = map(int, request.headers["Range"].removeprefix("bytes=").split("-"))
        if request.headers.get("If-match") != self.definition["expected_etag"]:
            raise AssertionError("fixture request lost If-Match")
        headers.update({"Content-Range": f"bytes {first}-{last}/{len(self.payload)}",
                        "Content-Length": str(last-first+1)})
        return Response(request.full_url, self.payload[first:last+1], 206, headers)


def prepare(directory, codec_name):
    cfg = configuration()
    if codec_name not in cfg["codecs"]:
        raise ValueError("codec outside engineering scope")
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    codec = ({"compression": "gzip", "compression_opts": 1} if codec_name == "gzip"
             else dict(hdf5plugin.Bitshuffle(cname="lz4")))
    contract_sha = rows.file_hash(CONFIG)
    window = {"name": cfg["window"], "archive_interval": cfg["archive_interval"]}
    receipts, definitions, raw, directories, transports = {}, [], {}, {}, {}
    rng = np.random.default_rng(cfg["fixture_seed"])
    for index, label in enumerate(direct.LABELS):
        role = "on" if index % 2 == 0 else "off"
        values = np.asarray(25 + rng.standard_normal((16, 1, cfg["dataset_channels"])), dtype="<f4")
        header = {"source_name": "local-"+label, "src_raj_hours": 1., "src_dej_deg": -2.,
            "tstart_mjd": 50000. + index*100/86400, "tsamp_s": 3.,
            "dataset_shape": list(values.shape), "dataset_dtype": "float32",
            "fch1_mhz": 1500., "foff_mhz": -0.000003}
        path = directory / (label + ".h5")
        with h5py.File(path, "w") as handle:
            handle.create_dataset("data", data=values, chunks=tuple(cfg["chunks"]),
                                  track_times=False, **codec)
            handle.attrs.update({"source_name": header["source_name"],
                "src_raj": 1., "src_dej": -2., "tstart": header["tstart_mjd"],
                "tsamp": 3., "fch1": 1500., "foff": -0.000003})
        payload = path.read_bytes()
        definition = {"label": label, "role": role,
            "url": f"https://codec-boundary.invalid/{codec_name}/{label}.h5",
            "expected_etag": '"'+rows.file_hash(path)+'"',
            "expected_remote_size_bytes": len(payload),
            "expected_chunks": cfg["chunks"], "expected_header": header}
        server = LocalBytes(definition, payload)
        destination = directory / label
        with patch.object(net, "open_response", side_effect=server):
            receipt, _ = source._extract_bound_source(definition, window, contract_sha,
                destination, directory / "mirrors", net.Budget(900, 16*1024**2, 120),
                kind="local-fixture")
        definitions.append(definition); receipts[label] = receipt
        raw[label] = values[:, 0, cfg["archive_interval"][0]:cfg["archive_interval"][1]]
        directories[label] = destination
        transports[label] = {"simulated_calls": server.calls,
            "input_hdf5_sha256": rows.file_hash(path),
            "input_hdf5_bytes": len(payload), "real_network_requests": 0}
    scopes = [receipts[label]["scope"] for label in direct.LABELS]
    clock = adapter.header_clock(scopes)
    observer = 1 + clock*1e-11
    bank = direct.build(clock_seconds=clock, observer_multipliers=observer,
        templates=[{"template_index": 0, "projected_scale": 0., "phase_cycles": 0.},
                   {"template_index": 1, "projected_scale": .25, "phase_cycles": .25},
                   {"template_index": 2, "projected_scale": .25, "phase_cycles": .75}],
        orbit={"period_days": 6., "semi_major_axis_au": .001,
               "eccentricity": .1, "omega_deg": 10.},
        provenance={"source_contract_sha256": contract_sha,
            "clock_sha256": native.digest(clock.tolist()),
            "observer_evidence_sha256": native.digest(observer.tolist()),
            "coordinate_scenario": "local-clock-fixture-no-physical-ephemeris",
            "scan_labels": list(direct.LABELS)})
    manifest = {"schema": adapter.SCHEMA, "domain": "local-fixture",
        "window": cfg["window"], "source_contract_sha256": contract_sha,
        "direct_factor_bank_sha256": bank.identity, "runtime": cfg["runtime"],
        "scans": [{"label": label, "scope": receipts[label]["scope"],
                   "receipt_sha256": receipts[label]["receipt_sha256"]}
                  for label in direct.LABELS]}
    binding = adapter.bind(manifest, native.digest(manifest), bank)
    geometry = core.NativeFrequencyGeometry(**scopes[0]["geometry"])
    grid = core.make_proxy_carrier_grid(
        (geometry.raw_zero_hz + 4256*geometry.channel_width_hz)/1e6,
        geometry.channel_width_hz, 16, 8)
    scans = [{"epoch": i//2+1, "kind": d["role"], "label": d["label"],
              "source_domain": "synthetic", "expected_header": {
                  "dataset_shape": [16, 1, geometry.channel_count]}}
             for i, d in enumerate(definitions)]
    context = pipeline.Context(scans=scans, factors=bank, grid=grid, window=cfg["window"])
    return {"config": cfg, "bank": bank, "manifest": manifest, "binding": binding,
        "directories": directories, "receipts": receipts, "raw": raw,
        "geometry": geometry, "context": context, "transports": transports}
