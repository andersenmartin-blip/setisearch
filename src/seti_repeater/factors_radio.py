"""Direct, explicitly identified eccentric factors for engineering preparation.

This type is intentionally distinct from the legacy two-column FactorBasis.
It authorizes neither telescope access nor scientific candidate selection.
"""
from dataclasses import dataclass
import json
import numpy as np
from . import motion_radio as motion
from . import search_v0p6 as core
from . import transfer_m43g as native

SCHEMA = 'radio-direct-eccentric-factors-v1'
MODEL = 'first-order-emitter-optical-observer-first-on-midpoint-anchor-v1'
LABELS = tuple(f'epoch{e}_{kind}' for e in (1,2,3) for kind in ('on','off'))


@dataclass(frozen=True)
class DirectFactors:
    inputs_json: str
    factors: np.ndarray
    identity: str

    @property
    def template_count(self): return self.factors.shape[0]

    def record(self):
        return {'schema':SCHEMA,'model':MODEL,'inputs':json.loads(self.inputs_json),
            'shape':list(self.factors.shape),'encoding':'C-order little-endian float64',
            'axes':['template','scan-major integration','start-midpoint-end'],
            'factors_sha256':native.array_hash(self.factors),
            'source_spectral_access_authorized':False,'physical_model_qualified':False,
            'continuous_bank_coverage_certified':False}


def _evaluate(inputs):
    if set(inputs) != {'clock_seconds','observer_multipliers','templates','orbit','provenance'}:
        raise ValueError('exact direct-factor input fields required')
    times=np.asarray(inputs['clock_seconds'],dtype='<f8')
    observer=np.asarray(inputs['observer_multipliers'],dtype='<f8')
    if (times.shape!=(96,3) or observer.shape!=times.shape or not np.isfinite(times).all()
            or not np.isfinite(observer).all() or np.any(observer<=0) or np.any(observer>=2)
            or times[0,1]!=0 or np.any(np.diff(times,axis=1)<=0)
            or np.any(times[1:,0]<times[:-1,2]-1e-9)):
        raise ValueError('ordered complete 96-row start/mid/end clock and observer factors required')
    if np.max(np.abs(times[:,1]-(times[:,0]+times[:,2])/2))>1e-9:
        raise ValueError('midpoint does not bisect integration')
    provenance=inputs['provenance']
    if (set(provenance)!={'source_contract_sha256','clock_sha256','observer_evidence_sha256','coordinate_scenario','scan_labels'}
            or provenance['scan_labels']!=list(LABELS) or not isinstance(provenance['coordinate_scenario'],str)
            or not provenance['coordinate_scenario']):
        raise ValueError('complete explicit source/clock/observer/coordinate provenance required')
    for key in ('source_contract_sha256','clock_sha256','observer_evidence_sha256'):
        core._frozen_sha256(provenance[key],key)
    orbit=inputs['orbit']
    if set(orbit)!={'period_days','semi_major_axis_au','eccentricity','omega_deg'}:
        raise ValueError('explicit working orbital parameter set required')
    templates=inputs['templates']
    if not isinstance(templates,list) or not 1<=len(templates)<=128:
        raise ValueError('one to 128 explicit templates required')
    seen=set(); output=[]
    for index,t in enumerate(templates):
        if set(t)!={'template_index','projected_scale','phase_cycles'} or type(t['template_index']) is not int or t['template_index']!=index:
            raise ValueError('ordered explicit template identifiers required')
        scale,phase=float(t['projected_scale']),float(t['phase_cycles'])
        if not np.isfinite([scale,phase]).all() or not 0<=scale<=1 or not 0<=phase<1:
            raise ValueError('projected scale or mean-anomaly phase outside declared domain')
        key=(scale,0. if scale==0 else phase)
        if key in seen or (scale==0 and phase!=0): raise ValueError('duplicate or ambiguous zero template')
        seen.add(key)
        velocity=motion.kepler_velocity(times.ravel(),[phase],**orbit).reshape(96,3)*scale
        factors=observer*(1-velocity/motion.C_M_S)
        factors=factors/factors[0,1]
        if not np.isfinite(factors).all() or np.any(factors<=0) or np.any(factors>=2):
            raise ValueError('invalid direct frequency factor')
        output.append(factors)
    return np.asarray(output,dtype='<f8')


def build(*,clock_seconds,observer_multipliers,templates,orbit,provenance):
    inputs={'clock_seconds':np.asarray(clock_seconds).tolist(),
            'observer_multipliers':np.asarray(observer_multipliers).tolist(),
            'templates':templates,'orbit':orbit,'provenance':provenance}
    encoded=core.canonical_json_bytes(inputs).decode()
    arrays=native.immutable(np.ascontiguousarray(_evaluate(json.loads(encoded))))
    initial=DirectFactors(encoded,arrays,'')
    return DirectFactors(encoded,arrays,native.digest(initial.record()))


def validate(bank):
    if type(bank) is not DirectFactors:
        raise ValueError('direct factor type required; legacy basis is not interchangeable')
    if (bank.factors.dtype!=np.dtype('<f8') or bank.factors.flags.writeable
            or not bank.factors.flags.c_contiguous or native.digest(bank.record())!=bank.identity):
        raise ValueError('direct factor identity or immutable layout changed')
    expected=_evaluate(json.loads(bank.inputs_json))
    if expected.shape!=bank.factors.shape or not np.array_equal(expected.view('<u8'),bank.factors.view('<u8')):
        raise ValueError('direct factors do not reproduce from their declared model')


def for_scan(bank,label,*,sample='midpoint'):
    validate(bank)
    if label not in LABELS or sample not in ('start','midpoint','end'):
        raise ValueError('explicit scan label and start/midpoint/end selection required')
    i=LABELS.index(label); j=('start','midpoint','end').index(sample)
    return native.immutable(np.ascontiguousarray(bank.factors[:,16*i:16*(i+1),j]))


def synthetic_cache(source,bank,label,grid,width):
    """Bind the direct bank to the existing native synthetic filter without refitting."""
    validate(bank)
    if type(source) is not native.SyntheticSource:
        raise ValueError('only typed synthetic sources are supported by this handoff')
    scope=json.loads(source.scope_json)
    if (scope.get('scan')!=label or scope.get('direct_factor_bank_sha256')!=bank.identity):
        raise ValueError('synthetic source belongs to another scan or factor bank')
    return native.build_synthetic_cache(source,for_scan(bank,label),grid,width,bank_sha256=bank.identity)
