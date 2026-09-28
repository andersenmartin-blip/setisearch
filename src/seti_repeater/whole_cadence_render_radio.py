"""Prospective Gaussian draw-plan binding and explicitly non-Gaussian mocks.

The real entry requires a fresh remotely published scientific consumption lease.
No activation or scientific store adapter is supplied by this module.
The mock shares row/injection/normalization arithmetic with the bound plan;
its source law is distinct and cannot be used as proposed Gaussian references.
"""
from dataclasses import dataclass
import hashlib
import json
import numpy as np
from . import receiver_bank_radio as received
from . import receiver_development_radio as renderer
from . import transfer_m43g as native
from .pipeline_receiver_radio import Context, NativeRun
from .empty_null_radio import canonical
from .whole_cadence_reference_radio import digest

PROPOSAL_SHA256='45d8309c8b23eea56ddee15e829b96a3936dba98141f124bf97c4057f35993e2'
NOISE_LAW_SHA256='e67450278cce0bf787ea128cd7eaabff4c9aac40dbe1463bb81dc055224c52eb'
MOCK_NAMESPACE='radio-whole-cadence-renderer-mock-20260928'
MOCK_LAW={'schema':'radio-whole-cadence-renderer-mock-law-v1','kind':'deterministic-row-provider',
          'gaussian_draws':False,'independent_draws':False,'scientific_calibration_reference':False}


@dataclass(frozen=True)
class DrawPlan:
    payload: bytes

    def record(self):
        r=json.loads(self.payload)
        if canonical(r)!=self.payload:raise ValueError('Noncanonical draw plan')
        sha=r.pop('plan_sha256')
        if digest(r)!=sha:raise ValueError('Draw plan changed')
        r['plan_sha256']=sha
        case=r['case'];base={k:v for k,v in case.items() if k!='identity'}
        if (r['schema']!='radio-whole-cadence-draw-plan-v1' or r['proposal_sha256']!=PROPOSAL_SHA256
                or digest(r['noise_law'])!=NOISE_LAW_SHA256 or case['noise_law_sha256']!=NOISE_LAW_SHA256
                or digest(base)!=case['identity'] or r['status']!='PROPOSED_NOT_ACTIVATED'
                or r['scientific_execution_authorized'] is not False or r['random_values_generated'] is not False):
            raise ValueError('Draw plan binding/activation changed')
        return r


def prepare(context, case, proposal_bytes):
    if not isinstance(context,Context):raise ValueError('Actual receiver Context required')
    context.validate()
    if hashlib.sha256(proposal_bytes).hexdigest()!=PROPOSAL_SHA256:raise ValueError('Exact immutable proposal required')
    proposal=json.loads(proposal_bytes)
    if proposal['status']!='PROPOSED_NOT_ACTIVATED' or case not in proposal['cases']:
        raise ValueError('Only an unchanged proposed case can be bound')
    source_sha=hashlib.sha256(context.factor_contract.source_contract_bytes).hexdigest()
    role='calibration' if case['role']=='calibration' else 'validation'
    if (case['context_sha256']!=context.identity or case['source_contract_sha256']!=source_sha
            or context.native_window['role']!=role or digest(proposal['noise_law'])!=case['noise_law_sha256']
            or case['proposed_only'] is not True or case['budget_charged'] is not False
            or case['executed'] is not False or case['outcomes_may_select_settings'] is not False):
        raise ValueError('Case/context/source/law or proposal status differs')
    seed=int.from_bytes(hashlib.sha256((case['namespace']+'/seed-v1').encode()).digest()[:8],'big')
    if type(case['seed']) is not int or case['seed']!=seed:raise ValueError('Seed derivation differs')
    r={'schema':'radio-whole-cadence-draw-plan-v1','proposal_sha256':PROPOSAL_SHA256,
        'case':case,'noise_law':proposal['noise_law'],'context_sha256':context.identity,
        'receiver_bank_sha256':context.factor_contract.factors.identity,
        'status':'PROPOSED_NOT_ACTIVATED','scientific_execution_authorized':False,
        'random_values_generated':False,
        'streams':[{'scan_index':i,'scan':s['label'],'seed_sequence_entropy':[seed,i],
            'normal_calls':16,'normal_arguments':[100.,1.,65536],'output_dtype':'<f4'} for i,s in enumerate(context.scans)]}
    r['plan_sha256']=digest(r);plan=DrawPlan(canonical(r));plan.record();return plan


def _render(context, plan, stream_factory, *, budget, scientific_receipt=None):
    """Exercise exact planned row ordering with a declared deterministic provider.

    Each provider exposes normal(mean, sigma, channels), returning one float64
    row. It is not NumPy's real PRNG. All sources carry MOCK_LAW, never the
    intended Gaussian law or reserved case identity.
    """
    if not isinstance(plan,DrawPlan):raise ValueError('Bound DrawPlan required')
    context.validate();r=plan.record();case=r['case']
    if (r['context_sha256']!=context.identity or r['receiver_bank_sha256']!=context.factor_contract.factors.identity
            or case['context_sha256']!=context.identity):raise ValueError('Mock draw-plan context differs')
    if scientific_receipt is None and getattr(stream_factory,'domain',None)!='deterministic-renderer-contract-fixture':
        raise ValueError('Explicit deterministic provider required; real Gaussian activation absent')
    recipe=case['recipe'];kind=recipe['kind']
    active={'on_epochs_zero_based':[],'off_epochs_zero_based':[]} if kind in ('noise_only','noise_null') else recipe['activity_patterns'][kind]
    rate=recipe.get('rate_label_hz_s',0);width=recipe.get('injection_width_channels',0);power=recipe.get('total_digital_power',0)
    q=context.grid.center_mhz*1e6
    center=json.loads(context.factor_contract.factors.provenance_json)['center_hz']
    clock=received.clock(json.loads(context.factor_contract.source_contract_bytes))
    case_id=(case['identity'] if scientific_receipt is not None else
             digest({'namespace':MOCK_NAMESPACE,'draw_plan_sha256':r['plan_sha256']}))
    expected_streams=[{'scan_index':i,'scan':scan['label'],'seed_sequence_entropy':[case['seed'],i],
        'normal_calls':16,'normal_arguments':[100.,1.,65536],'output_dtype':'<f4'} for i,scan in enumerate(context.scans)]
    if r['streams']!=expected_streams:raise ValueError('Planned generator call schedule changed')
    sources={};receipts=[];max_mass_error=0.
    for i,scan in enumerate(context.scans):
        stream=r['streams'][i]
        budget();rng=stream_factory(tuple(stream['seed_sequence_entropy']));row_receipts=[]
        def reader(row):
            nonlocal max_mass_error
            if row!=len(row_receipts):raise ValueError('Native renderer row order changed')
            budget();supplied=np.asarray(rng.normal(100.,1.,65536))
            if supplied.dtype!=np.dtype('<f8') or supplied.shape!=(65536,) or not np.isfinite(supplied).all():
                raise ValueError('Complete finite float64 mock row required')
            base=supplied.astype('<f4');value=base.astype('<f8')
            injected=scan['epoch']-1 in active[scan['kind']+'_epochs_zero_based']
            evidence={'row':row,'generator_call_arguments':[100.,1.,65536],
                'background_sha256':native.array_hash(base),'injected':injected,
                'added_total_power_before_float32':0.}
            if injected:
                times=clock[i*16+row];midpoint=float(times[1]);duration=float(times[2]-times[0])
                position=(q*(1+rate*midpoint/center)-context.geometry.raw_zero_hz)/context.geometry.channel_width_hz
                sweep=q*rate/center*duration/context.geometry.channel_width_hz
                indices,mass=renderer.pixel_masses(position,sweep,width,65536)
                max_mass_error=max(max_mass_error,abs(float(mass.sum())-1.));value[indices]+=power*mass
                evidence.update(center_channel=position,sweep_channels=sweep,
                    support_channel_interval=[int(indices[0]),int(indices[-1])+1],
                    added_total_power_before_float32=float(power*mass.sum()))
            value=value.astype('<f4');evidence['raw_sha256']=native.array_hash(value);row_receipts.append(evidence)
            return value
        scope={'kind':'synthetic','input_domain':'deterministic-renderer-contract-fixture',
            'case_identity':case_id,'intended_proposed_case_identity':case['identity'],
            'context_sha256':context.identity,'scan':scan['label'],
            'receiver_factor_bank_sha256':context.factor_contract.factors.identity,
            'noise_law':MOCK_LAW,'noise_law_sha256':digest(MOCK_LAW),
            'intended_gaussian_law_sha256':NOISE_LAW_SHA256,'draw_plan_sha256':r['plan_sha256'],
            'actual_gaussian_draws':False,'telescope_provenance':False,'scientific_allocation_charged':False}
        if scientific_receipt is not None:
            scope={'kind':'synthetic','input_domain':'published-whole-cadence-gaussian',
                'case_identity':case_id,'context_sha256':context.identity,'scan':scan['label'],
                'receiver_factor_bank_sha256':context.factor_contract.factors.identity,
                'noise_law':r['noise_law'],'noise_law_sha256':NOISE_LAW_SHA256,
                'draw_plan_sha256':r['plan_sha256'],'consumption_receipt':scientific_receipt,
                'actual_gaussian_draws':True,'telescope_provenance':False,
                'scientific_allocation_charged':True}
        source=native.normalize_synthetic_rows(reader,context.geometry,16,input_orientation='ascending',scope=scope)
        for rec,row in zip(row_receipts,source.values,strict=True):rec['normalized_sha256']=native.array_hash(row)
        sources[scan['label']]=source;receipts.append({'scan':scan['label'],'source_identity':source.identity,'rows':row_receipts})
        budget()
    run=NativeRun(context,sources)
    receipt={'schema':'radio-whole-cadence-renderer-mock-receipt-v1','case_identity':case_id,
        'intended_proposed_case_identity':case['identity'],'draw_plan_sha256':r['plan_sha256'],
        'noise_law':MOCK_LAW,'noise_law_sha256':digest(MOCK_LAW),'source_ids':run.source_ids,
        'row_receipts':receipts,'maximum_mass_error':max_mass_error,
        'normal_calls':96,'native_values_are_gaussian':False,'scientific_allocation_charged':False,
        'new_random_values_generated':False,'telescope_values_opened':False}
    if scientific_receipt is not None:
        receipt.update(schema='radio-whole-cadence-gaussian-receipt-v1',
            noise_law=r['noise_law'],noise_law_sha256=NOISE_LAW_SHA256,
            consumption_receipt=scientific_receipt,native_values_are_gaussian=True,
            scientific_allocation_charged=True,new_random_values_generated=True)
    receipt['receipt_sha256']=digest(receipt);return run,receipt


def render_mock(context, plan, stream_factory, *, budget=lambda:None):
    return _render(context,plan,stream_factory,budget=budget)


def render_gaussian(context,plan,*,lease=None):
    from .whole_cadence_journal_radio import Lease
    if type(lease) is not Lease:
        raise ValueError('PROPOSED_NOT_ACTIVATED: fresh durable allocation and published executable freeze required before real RNG')
    # Validate every stream before granting one-use generator permission.
    context.validate();r=plan.record();case=r['case']
    expected=[{'scan_index':i,'scan':s['label'],'seed_sequence_entropy':[case['seed'],i],
        'normal_calls':16,'normal_arguments':[100.,1.,65536],'output_dtype':'<f4'} for i,s in enumerate(context.scans)]
    if (r['context_sha256']!=context.identity or case['context_sha256']!=context.identity
            or r['receiver_bank_sha256']!=context.factor_contract.factors.identity or r['streams']!=expected):
        raise ValueError('Gaussian context/schedule differs before RNG')
    consumption=lease.begin_gaussian(plan)
    def factory(entropy):
        return np.random.Generator(np.random.PCG64(np.random.SeedSequence(list(entropy))))
    run,receipt=_render(context,plan,factory,budget=lease.budget,scientific_receipt=consumption)
    lease.budget(run.modelled_bytes)
    return run,receipt
