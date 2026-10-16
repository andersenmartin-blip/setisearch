"""Authenticated input reader for one separately scoped descriptive real search.

Metadata/hash preparation has no NumPy import. Reading this module does not open
an input. The numerical caller must first authenticate every source-code pin.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import zipfile

IDENTITY = 'SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B00'
MODE = 'DESCRIPTIVE_POSTSELECTED_2017'
SCAN_IDS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ARCHIVE_BYTES = 48468705
ARCHIVE_SHA256 = '52b948958c89069a7afb563cf377ee33e4f1324e014428d597b4b3e3a20f6eb3'
METADATA_MEMBER = 'SETI_NATIVE_SPOR_2026-10-14/seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json'
METADATA_BYTES = 629588
METADATA_SHA256 = '31efe1e5eeba63d10fbc04ea60bd29eb3086f142b6111a185f821a40a0558522'
PREFIX = 'SETI_NATIVE_SPOR_2026-10-14/'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def bytes_sha(value):
    return hashlib.sha256(value).hexdigest()


def _member(archive, declaration, prefix=PREFIX):
    relative = Path(declaration['path'])
    require(not relative.is_absolute() and '..' not in relative.parts,
            'Pinned source member must remain relative')
    name = prefix + relative.as_posix()
    require(archive.namelist().count(name) == 1, 'Exactly one pinned ZIP member required')
    info = archive.getinfo(name)
    require(not info.is_dir() and info.file_size == declaration['bytes'],
            'Source member declared byte count differs')
    value = archive.read(name)  # ZIP CRC is checked before NPZ decoding.
    require(len(value) == declaration['bytes'] and bytes_sha(value) == declaration['sha256'],
            'Exact source member bytes differ: ' + name)
    return name, value


def prepare(scope, legacy_contract):
    """Check immutable metadata and all12 source members before NumPy import.

    Returns the copied real-band coordinate contract and authenticated NPZ bytes;
    these bytes are not interpreted as numerical arrays by this function.
    """
    require(scope['mode'] == MODE and scope['identity'] == IDENTITY,
            'Separate descriptive identity/mode required')
    declaration = scope['source_archive']
    require(declaration['bytes'] == ARCHIVE_BYTES and declaration['sha256'] == ARCHIVE_SHA256,
            'Original authenticated archive pin required; a truncated copy is not alternate packaging')
    path = Path(declaration['path'])
    require(path.is_file() and not path.is_symlink() and path.stat().st_size == ARCHIVE_BYTES
            and sha(path) == ARCHIVE_SHA256, 'Complete exact retained source ZIP required')
    require(zipfile.is_zipfile(path), 'Source must have a valid ZIP central directory')
    expected_metadata = {'member': METADATA_MEMBER, 'bytes': METADATA_BYTES, 'sha256': METADATA_SHA256}
    require(scope['source_metadata'] == expected_metadata, 'Original context-metadata pin differs')
    with zipfile.ZipFile(path) as archive:
        require(archive.namelist().count(METADATA_MEMBER) == 1, 'Unique context-metadata member required')
        value = archive.read(METADATA_MEMBER)
        require(len(value) == METADATA_BYTES and bytes_sha(value) == METADATA_SHA256,
                'Exact source context-metadata bytes differ')
        matrix = json.loads(value)
        groups = sorted({(c['native_chunk_index'], c['core_q']) for c in matrix['normalization_crops']})
        require(len(groups) == 9 and groups[0] == (170, 131),
                'Original canonical first-of-nine band selection differs')
        band = scope['band']
        require('case_id' not in band, 'Retired real-case identifier cannot be an active band identity')
        require((band['native_chunk_index'], band['core_q']) == groups[0],
                'Band cannot be selected using new outcomes')
        require(band['reference_source_channel_interval'] == [178794496,178798592]
                and band['loaded_source_channel_interval'] == [178790496,178802592]
                and band['source_rows_per_scan'] == 16,
                'Complete fixed original band coordinates required')
        require([s['scan_id'] for s in band['scans']] == list(SCAN_IDS),
                'Chronological original six-scan source order required')
        metadata = legacy_contract['geometry']['scan_metadata']
        require([m['scan_id'] for m in metadata] == list(SCAN_IDS)
                and [m['role'] for m in metadata] == ['ON','OFF']*3,
                'Original source acquisition roles/timing contract required')
        raw_values, source_receipts = {}, []
        for index, scan in enumerate(band['scans']):
            scan_id = scan['scan_id']
            matches = [c for c in matrix['normalization_crops']
                       if (c['scan_id'],c['native_chunk_index'],c['core_q']) == (scan_id,170,131)]
            require(len(matches) == 1, 'Exactly one original crop per selected scan required')
            crop = matches[0]
            require(crop['source_channel_interval_half_open'] == band['loaded_source_channel_interval']
                    and crop['normalization_source_channel_interval_half_open'] == band['reference_source_channel_interval'],
                    'Original source crop/core coordinates differ')
            for field, original in [('raw_crop',crop['raw_crop']), ('normalization',crop['normalization'])]:
                expected = {**original, 'path': 'seti_work/' + original['path']}
                require(scan[field] == expected, 'Selected source input declaration differs from original metadata')
                member, value = _member(archive, scan[field])
                source_receipts.append({'scan_id':scan_id,'field':field,'member':member,
                    'bytes':len(value),'sha256':bytes_sha(value)})
                if field == 'raw_crop':
                    raw_values[scan_id] = value
            headers = [s['original_header_full'] for s in matrix['source_compacts'] if s['scan_id'] == scan_id]
            require(len(headers) == 3 and all(h == metadata[index]['original_header_full'] for h in headers),
                    'Original complete source header differs across retained bands or coordinate contract')
            scalar = headers[0]['data_attributes']
            require(scalar['tstart'] == metadata[index]['tstart_mjd']
                    and scalar['tsamp'] == metadata[index]['tsamp_s']
                    and scalar['fch1']*1e6 == metadata[index]['fch1_hz']
                    and scalar['foff']*1e6 == metadata[index]['df_hz'],
                    'Source timestamp/frequency metadata differs from frozen numerical coordinate contract')
    contract = copy.deepcopy(legacy_contract)
    contract['geometry']['reference_source_channel_interval'] = list(band['reference_source_channel_interval'])
    contract['geometry']['loaded_source_channel_interval'] = list(band['loaded_source_channel_interval'])
    # The old contract remains a pinned coordinate/algorithm template. Its old
    # study/calibration metadata grants no admission and is never executed.
    receipt = {'schema':'SETI_NEW_DESCRIPTIVE_REAL_INPUT_AUTHENTICATION_V1',
        'identity':IDENTITY,'mode':MODE,'canonical_selection_index':0,
        'native_chunk_index':170,'core_q':131,'source_archive':declaration,
        'source_metadata':expected_metadata,'source_members':source_receipts,
        'all12_pins_authenticated_before_raw_array_decode':True,
        'original_contract_used_as_coordinate_template_only':True,
        'source_contract_only_geometry_intervals_changed':True,
        'old_study_or_exposed_phase_admitted':False,
        'new_telescope_requests':0,'new_telescope_bytes':0,'new_observation':False}
    return contract, raw_values, receipt


def decode(raw_values, contract, np):
    """Decode the six already byte-authenticated NPZ sources without alteration."""
    channel0, stop = contract['geometry']['loaded_source_channel_interval']
    corefirst, corestop = contract['geometry']['reference_source_channel_interval']
    require(stop-channel0 == 12096 and corestop-corefirst == 4096 and corefirst-channel0 == 4000,
            'Complete original input geometry required')
    arrays = []
    for scan_id in SCAN_IDS:
        with np.load(io.BytesIO(raw_values[scan_id]),allow_pickle=False) as source:
            raw = source['raw_power']
            require(type(raw) is np.ndarray and raw.dtype == np.dtype('<f4')
                    and raw.shape == (16,12096) and np.isfinite(raw).all() and (raw>=0).all(),
                    'Original complete finite nonnegative float32 raw array required')
            require(int(source['source_channel0']) == channel0
                    and np.array_equal(source['absolute_time_rows'],np.arange(16))
                    and np.array_equal(source['normalization_source_channels'],np.arange(corefirst,corestop)),
                    'Original NPZ source/core/time coordinate fields differ')
            raw.flags.writeable = False
            arrays.append(raw)
    return arrays
