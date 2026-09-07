"""Joint native ON/OFF overlays with complete overlap-aware filter windows."""
import math
import numpy as np
from . import search_v0p6 as core
from .detector_m43q import digest
from .transfer_m43g import immutable, array_hash
from .injection_m43r import NativeOverlay, ScoreStore, replace_and_integrate
from .injection_m43s import fractional_profile


def joint_filtered_patch(values, additions, width):
    """additions are ordered (per-row profiles, per-row total strength) pairs."""
    if values.dtype != np.dtype('<f4') or values.ndim != 2 or not additions:
        raise ValueError('native rows and nonempty additions required')
    if width not in core.M37_SPECTRAL_WIDTHS:
        raise ValueError('unknown width')
    for profiles, strength in additions:
        if len(profiles) != len(values) or not math.isfinite(strength) or strength < 0:
            raise ValueError('invalid addition')
        for start, profile in profiles:
            if (type(start) is not int or profile.ndim != 1 or not len(profile)
                    or not np.isfinite(profile).all() or np.any(profile < 0)
                    or not math.isclose(float(profile.sum()), 1., abs_tol=1e-12)):
                raise ValueError('invalid profile')
    half = width // 2; patches = []
    for row in range(len(values)):
        start = min(profiles[row][0] for profiles, _ in additions)
        stop = max(profiles[row][0] + len(profiles[row][1]) for profiles, _ in additions)
        lo, hi = start - 2*half, stop + 2*half
        if lo < 0 or hi > values.shape[1]:
            raise core.V0P6CoverageError('joint profile filter support incomplete')
        section = values[row, lo:hi].copy()
        for profiles, strength in additions:
            offset, profile = profiles[row]
            section[offset-lo:offset-lo+len(profile)] += (profile*strength).astype('<f4')
        windows = np.lib.stride_tricks.sliding_window_view(section, width)
        filtered = (np.sum(windows, axis=-1, dtype=np.float32)/np.sqrt(width)).astype('<f4')
        patches.append((start-half, immutable(filtered)))
    return patches


class JointOverlay(NativeOverlay):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.joint_indices = {('on', e): v for e, v in self.indices.items()}
        self.joint_gathers = {('on', e, w): v for (e, w), v in self.gathers.items()}
        for e in range(3):
            label = f'epoch{e+1}_off'
            factors = core.factor_table_for_scan(self.table, self.basis, label)
            for width in core.M37_SPECTRAL_WIDTHS:
                cache = self.receiver.cache(label, width)
                key = ('off', e)
                if key not in self.joint_indices:
                    self.joint_indices[key] = core.nearest_native_indices(cache.source.geometry, factors[:,:,None]*self.grid.support_hz)
                indices = self.joint_indices[key]
                rows = np.stack([cache.values[r, indices[:,r,:]-width//2] for r in range(cache.source.integration_count)], axis=1)
                sums = np.zeros((len(self.bank), self.grid.support_bin_count), dtype='<f4')
                for r in range(cache.source.integration_count):
                    sums += rows[:,r,:]
                sums /= np.float32(math.sqrt(cache.source.integration_count))
                expected = np.stack([self.baseline.get('off', t, width)[0][e] for t in range(len(self.bank))])
                if not np.array_equal(sums.view('<u4'), expected.view('<u4')):
                    raise ValueError('OFF native gather differs from original anchor')
                self.joint_gathers['off', e, width] = immutable(rows)
                self.cache_inventory.append({'scan': label, 'width': width, 'source_identity': cache.source.identity,
                    'cache_identity': cache.identity, 'row_gather_sha256': array_hash(rows), 'anchor_exact': True})

    def trial(self, components):
        additions = {}; receipts = []
        for component in components:
            truth = component['truth']; kind = component['kind']
            if kind not in ('on', 'off') or component['shape'] not in ('point', 'sinc'):
                raise ValueError('unknown component')
            factors = core.template_factors_from_basis(self.basis, truth)
            q = float(self.grid.score_hz[truth['score_index']] + truth['fractional_proxy_bin']*self.grid.channel_width_hz)
            for epoch in component['epochs']:
                label = f'epoch{epoch+1}_{kind}'; src = self.receiver.cache(label, 1).source
                f = np.asarray([factors[i] for i, x in enumerate(self.basis.labels) if x.scan_label == label])
                positions = (q*f-src.geometry.raw_zero_hz)/src.geometry.channel_width_hz
                if component['snap_native']:
                    positions = np.rint(positions)
                if component['shape'] == 'point':
                    if not component['snap_native']:
                        raise ValueError('point profiles require explicit native snapping')
                    profiles = [(int(x), np.ones(1, dtype='<f8')) for x in positions]
                else:
                    profiles, _ = fractional_profile(positions, smear_channels=component['smear_channels'])
                strength = float(component['strength']/math.sqrt(src.integration_count))
                additions.setdefault((kind, epoch), []).append((profiles, strength))
                receipts.append({'component_id': component['component_id'], 'scan': label,
                    'source_identity': src.identity, 'per_row_total_strength': strength,
                    'profiles': [{'start': lo, 'sha256': array_hash(p)} for lo, p in profiles]})
        all_patches = {}; self.patches = {}
        for (kind, epoch), parts in additions.items():
            src = self.receiver.cache(f'epoch{epoch+1}_{kind}', 1).source
            for width in core.M37_SPECTRAL_WIDTHS:
                patches = joint_filtered_patch(src.values, parts, width)
                all_patches[kind, epoch, width] = patches
                if kind == 'on':
                    self.patches[epoch, width] = patches
        self.overlay_receipt = {'schema': 'm43u-joint-native-overlay-v1', 'components': components,
            'placement': 'after fixed normalization, before complete native filtering and gathering',
            'addition_order': 'declared component order, float32 additions before one complete filter sum',
            'background_provenance': self.baseline.provenance, 'sources': receipts,
            'patch_payloads': {f'{k}:{e}:{w}': [{'start': lo, 'sha256': array_hash(p)} for lo, p in ps]
                for (k,e,w), ps in sorted(all_patches.items())}}
        arrays = {k: v.copy() for k, v in self.baseline.arrays.items()}
        for (kind, epoch, width), patches in all_patches.items():
            for template in range(len(self.bank)):
                cols, values = replace_and_integrate(self.joint_gathers[kind, epoch, width][template],
                    self.joint_indices[kind, epoch][template], patches)
                arrays[kind, template, width][epoch, cols] = values
        return ScoreStore(arrays, {'baseline': self.baseline.provenance, 'native_overlay_sha256': digest(self.overlay_receipt)})

    def __call__(self, records, bank, table):
        signatures, receipt = super().__call__(records, bank, table)
        receipt['source_family'] = 'M43U-joint-native-ON-OFF-overlay'
        return signatures, receipt
