"""M43S finite fractional sinc-squared / linear-smear native injection model.

This is a defined sensitivity model, not an attestation of the instrument's
channelizer. Keep M43R injection and detector semantics unchanged.
"""
from dataclasses import dataclass
import math
import numpy as np
from . import search_v0p6 as core
from .detector_m43q import digest
from .transfer_m43g import immutable,array_hash
from .injection_m43r import NativeOverlay,ScoreStore,replace_and_integrate


@dataclass(frozen=True)
class PersistedNullInventory:
    """Read-only replay input; does not impersonate an executed accumulator."""
    null_maxima: np.ndarray
    calibration_artifact_sha256: str


def restore_calibration(record,expected_artifact_sha256,expected_certificate_sha256):
    payload=dict(record);seal=payload.pop('result_sha256')
    if seal!=expected_artifact_sha256 or digest(payload)!=seal:
        raise ValueError('persisted calibration identity differs')
    threshold=core.threshold_certificate_from_record(record['threshold'],expected_certificate_sha256=expected_certificate_sha256)
    nulls=immutable(np.asarray(record['null_maxima'],dtype='<f8'))
    if (len(nulls)!=threshold.global_null_count or core.float64_vector_sha256(nulls)!=threshold.global_null_maxima_sha256):
        raise ValueError('persisted null vector differs from certificate')
    return PersistedNullInventory(nulls,seal),threshold


def fractional_profile(positions,smear_channels=1.,half_extent=16,time_samples=17):
    """Equal midpoint time samples; finite packet normalized to total mass one."""
    positions=np.asarray(positions,dtype='<f8')
    if positions.ndim!=1 or not len(positions) or not np.isfinite(positions).all():
        raise ValueError('finite native positions required')
    if not 0<=smear_channels<=4 or half_extent!=16 or time_samples!=17:
        raise ValueError('outside M43S profile model')
    offsets=((np.arange(time_samples,dtype='<f8')+.5)/time_samples-.5)*smear_channels
    rows=[];receipts=[]
    for position in positions:
        start=math.floor(float(position)-smear_channels/2)-half_extent
        stop=math.ceil(float(position)+smear_channels/2)+half_extent+1
        raw=np.arange(start,stop,dtype=np.int64)
        response=np.mean(np.sinc(raw[:,None].astype('<f8')-position-offsets)**2,axis=1,dtype=np.float64)
        mass=float(np.sum(response,dtype=np.float64))
        if not math.isfinite(mass) or mass<=0:raise ValueError('invalid finite profile mass')
        values=immutable(response/mass)
        rows.append((start,values))
        receipts.append({'native_position':float(position),'start':start,'stop':stop,
            'unnormalized_finite_mass':mass,'normalized_profile_sha256':array_hash(values)})
    return rows,receipts


def filtered_profile_patch(values,profiles,width,per_row_strength):
    """Add a complete finite profile, then recompute every affected native window."""
    if (values.dtype!=np.dtype('<f4') or values.ndim!=2 or len(profiles)!=len(values)
            or width not in core.M37_SPECTRAL_WIDTHS or not np.isfinite(per_row_strength) or per_row_strength<0):
        raise ValueError('invalid native profile overlay')
    half=width//2;patches=[]
    for row,(start,profile) in enumerate(profiles):
        start=core._strict_int(start,'profile start')
        if (profile.ndim!=1 or not len(profile) or not np.isfinite(profile).all() or np.any(profile<0)
                or not math.isclose(float(np.sum(profile)),1.,abs_tol=1e-12)):
            raise ValueError('normalized nonnegative profile required')
        lo=start-2*half;hi=start+len(profile)+2*half
        if lo<0 or hi>values.shape[1]:raise core.V0P6CoverageError('incomplete native profile filter support')
        section=values[row,lo:hi].copy()
        section[2*half:2*half+len(profile)]+=(profile*per_row_strength).astype('<f4')
        windows=np.lib.stride_tricks.sliding_window_view(section,width)
        filtered=(np.sum(windows,axis=-1,dtype=np.float32)/np.sqrt(width)).astype('<f4')
        patches.append((start-half,immutable(filtered)))
    return patches


class ProfileOverlay(NativeOverlay):
    def truth_factors(self,truth):
        template={'coefficient_x':truth['coefficient_x'],'coefficient_y':truth['coefficient_y']}
        all_factors=core.template_factors_from_basis(self.basis,template)
        return {e:np.asarray([all_factors[i] for i,label in enumerate(self.basis.labels)
                if label.scan_label==f'epoch{e+1}_on'],dtype='<f8') for e in range(3)}

    def trial(self,truth,amplitude):
        if truth['profile']=='ideal-native-bin':return super().trial(truth,amplitude)
        if truth['profile']!='fractional-off-template-smear':raise ValueError('unknown M43S profile')
        self.patches={};details=[];factors=self.truth_factors(truth)
        q=float(self.grid.score_hz[truth['score_index']]+truth['fractional_proxy_bin']*self.grid.channel_width_hz)
        for e in truth['active_epochs']:
            src=self.receiver.cache(f'epoch{e+1}_on',1).source
            positions=(q*factors[e]-src.geometry.raw_zero_hz)/src.geometry.channel_width_hz
            profiles,receipts=fractional_profile(positions)
            strength=float(amplitude/math.sqrt(src.integration_count))
            details.append({'scan':f'epoch{e+1}_on','background_source_identity':src.identity,
                'per_row_total_strength':strength,'profiles':receipts})
            if amplitude:
                for w in core.M37_SPECTRAL_WIDTHS:
                    self.patches[e,w]=filtered_profile_patch(src.values,profiles,w,strength)
        self.overlay_receipt={'schema':'m43s-fractional-native-overlay-v1','truth':truth,'nominal_total_epoch_strength':amplitude,
            'placement':'after fixed normalization and before native filter/gather',
            'model':'finite sinc-squared normalized per row; 17 midpoint samples over one native channel',
            'background_provenance':self.baseline.provenance,'sources':details,
            'patch_payloads':{f'{e}:{w}':[{'start':lo,'sha256':array_hash(v)} for lo,v in p]
                for (e,w),p in sorted(self.patches.items())}}
        arrays={k:v.copy() for k,v in self.baseline.arrays.items()}
        for (e,w),patches in self.patches.items():
            for t in range(len(self.bank)):
                cols,values=replace_and_integrate(self.gathers[e,w][t],self.indices[e][t],patches)
                arrays['on',t,w][e,cols]=values
        return ScoreStore(arrays,{'baseline':self.baseline.provenance,'native_overlay_sha256':digest(self.overlay_receipt)})

    def __call__(self,records,bank,table):
        signatures,receipt=super().__call__(records,bank,table)
        receipt['source_family']='M43S-defined-profile-overlay-on-verified-M43R-background'
        return signatures,receipt


def truth_on_factors(basis,truth):
    f=core.template_factors_from_basis(basis,truth)
    return np.stack([[f[i] for i,label in enumerate(basis.labels) if label.scan_label==f'epoch{e+1}_on'] for e in range(3)])


def association_distances(members,truth,grid,on_factors,truth_factors):
    """Literal max center-track error over all integrations of exact active subset."""
    q=float(grid.score_hz[truth['score_index']]+truth['fractional_proxy_bin']*grid.channel_width_hz)
    active=truth['active_epochs'];distances={}
    for m in members:
        if m['active_epochs_zero_based']!=active:continue
        predicted=grid.score_hz[m['proxy_carrier_index']]*on_factors[m['template_index'],active,:]
        target=q*truth_factors[active,:]
        distances[m['record_id']]=float(np.max(np.abs(predicted-target)))
    return distances
