"""Pinned inputs for the receiver adapter; metadata-only context construction."""
import hashlib
import json
from pathlib import Path
from seti_repeater import receiver_bank_radio as bank
from seti_repeater import pipeline_receiver_radio as pipeline
from seti_repeater import search_v0p6 as core

ROOT=Path(__file__).resolve().parents[1]
PINS={
 'config/radio_hd189733_source_preparation_20260927.json':'98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1',
 'results_radio_hd189733_geometry_2026-09-27/window_geometry.json':'92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6',
 'results_radio_hd189733_receiver_2026-09-28/bank_records.json':'51c1fde64957720e98adc7ecc63209d9b2e406b57dcd790829677a1ceb76b7c8',
 'results_radio_hd189733_receiver_2026-09-28/control_identity_reservation.json':'afeca9efdd4ee5cc767fcc4c2c042d437c9a438ad6a8bb71dc9507babb102ad7'}


def read_inputs():
    raw={p:(ROOT/p).read_bytes() for p in PINS}
    for p,h in PINS.items():
        if hashlib.sha256(raw[p]).hexdigest()!=h:raise ValueError('Published input changed: '+p)
    return raw


def context(role='validation'):
    raw=read_inputs();paths=list(PINS)
    source=json.loads(raw[paths[0]]);design=json.loads(raw[paths[1]])
    factors=bank.build(raw[paths[0]],PINS[paths[0]],raw[paths[1]],PINS[paths[1]],role)
    record=next(x for x in json.loads(raw[paths[2]]) if x['provenance']['role']==role)
    if factors.identity!=record['bank_identity']:raise ValueError('Receiver bank differs from published record')
    scans=[{**s,'kind':s['role'],'epoch':i//2+1} for i,s in enumerate(source['scans'])]
    w=next(x for x in design['windows'] if x['role']==role)
    grid=core.make_proxy_carrier_grid(w['proposed_first_on_midpoint_carrier_center_hz']/1e6,
            abs(scans[0]['expected_header']['foff_mhz'])*1e6,40,9)
    return pipeline.Context(scans=scans,factors=factors,grid=grid,
        window='hd189733_'+role+'_receiver_v1',trusted_bank_identity=record['bank_identity'],
        source_contract_bytes=raw[paths[0]],design_bytes=raw[paths[1]])
