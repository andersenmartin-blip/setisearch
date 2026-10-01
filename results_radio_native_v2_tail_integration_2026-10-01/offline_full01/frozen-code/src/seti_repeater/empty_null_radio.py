"""Typed empty maxima and arithmetic ranks, without a detector certificate.

No experiment, spectrum reader, RNG or old calibration adapter is imported.
Rank validity requires a separately justified exchangeable reference design.
"""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
from typing import Iterable


SCHEMA = 'radio-empty-aware-maximum-v1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


@dataclass(frozen=True)
class Maximum:
    kind: str
    value: float | None = None

    def __post_init__(self):
        if self.kind == 'empty':
            if self.value is not None:
                raise ValueError('Empty outcome cannot carry a numerical score')
        elif self.kind == 'finite':
            if (isinstance(self.value, bool) or not isinstance(self.value, (int, float))
                    or not math.isfinite(self.value)):
                raise ValueError('Finite outcome requires a finite JSON number')
            object.__setattr__(self, 'value', float(self.value))
        else:
            raise ValueError('Unknown maximum kind')

    @property
    def order_key(self):
        return (0, 0.) if self.kind == 'empty' else (1, self.value)

    def record(self):
        return {'schema': SCHEMA, 'kind': self.kind, 'value': self.value}

    @classmethod
    def from_record(cls, record):
        if set(record) != {'schema', 'kind', 'value'} or record['schema'] != SCHEMA:
            raise ValueError('Maximum record schema changed')
        return cls(record['kind'], record['value'])


EMPTY = Maximum('empty')


def maximum(values: Iterable[Maximum]) -> Maximum:
    result = EMPTY
    for value in values:
        if not isinstance(value, Maximum):
            raise TypeError('Typed maxima required')
        if value.order_key > result.order_key:
            result = value
    return result


def inclusive_rank(observed: Maximum, reference: Iterable[Maximum]) -> Fraction:
    """Arithmetic only: (1 + number(reference >= observed))/(B + 1)."""
    if not isinstance(observed, Maximum):
        raise TypeError('Typed observation required')
    values = tuple(reference)
    if not values or any(not isinstance(x, Maximum) for x in values):
        raise ValueError('At least one typed reference maximum required')
    return Fraction(1 + sum(x.order_key >= observed.order_key for x in values), len(values)+1)


def higher_quantile(reference: Iterable[Maximum], quantile=Fraction(1)) -> Maximum:
    values = tuple(reference)
    if not values or any(not isinstance(x, Maximum) for x in values):
        raise ValueError('A complete nonempty typed reference required')
    if not isinstance(quantile, Fraction) or not 0 <= quantile <= 1:
        raise ValueError('Exact Fraction quantile in [0,1] required')
    index = math.ceil((len(values)-1)*quantile)
    return sorted(values, key=lambda x: x.order_key)[index]


def arithmetic_screen(observed, reference, *, floor=10., rank_ceiling=Fraction(1,100)):
    """Proposed screen arithmetic; never emits scientific/admission authority."""
    reference = tuple(reference)
    if isinstance(floor,bool) or not isinstance(floor,(int,float)) or not math.isfinite(floor):
        raise ValueError('Finite floor required')
    if not isinstance(rank_ceiling,Fraction) or not 0 < rank_ceiling <= 1:
        raise ValueError('Exact positive rank ceiling required')
    rank = inclusive_rank(observed, reference)
    empirical = higher_quantile(reference)
    threshold = maximum((Maximum('finite',floor), empirical))
    selected = observed.kind == 'finite' and observed.value >= threshold.value and rank <= rank_ceiling
    return {'schema':'radio-empty-aware-arithmetic-screen-v1',
        'observed':observed.record(), 'reference_count':len(reference),
        'reference_empty_count':sum(x.kind=='empty' for x in reference),
        'reference_sha256':hashlib.sha256(canonical([x.record() for x in reference])).hexdigest(),
        'inclusive_rank_numerator':rank.numerator,'inclusive_rank_denominator':rank.denominator,
        'higher_quantile':empirical.record(),'operational_floor_or_maximum':threshold.record(),
        'passes_arithmetic_rule':selected,
        'null_exchangeability_established':False,'telescope_admission_authorized':False,
        'detector_certificate_issued':False}


@dataclass(frozen=True)
class ProposedReferenceDesign:
    """An identity proposal, deliberately unable to activate a trial budget."""
    design_id: str
    null_namespaces: tuple[str, ...]
    evaluation_namespaces: tuple[str, ...]
    control_seeds: tuple[int, ...]
    noise_law_sha256: str
    source_context_sha256: str
    destination_context_sha256: str

    def validate(self):
        names = self.null_namespaces + self.evaluation_namespaces
        if (len(self.null_namespaces)!=127 or len(self.evaluation_namespaces)!=24
                or len(set(names))!=151 or len(self.control_seeds)!=151
                or len(set(self.control_seeds))!=151):
            raise ValueError('Proposed 127/24 identities must be distinct')
        if any(not isinstance(x,str) or not x.startswith(self.design_id+'/') for x in names):
            raise ValueError('Proposal namespace mismatch')
        if any(isinstance(x,bool) or not isinstance(x,int) or not 0 <= x < 2**64 for x in self.control_seeds):
            raise ValueError('Exact 64-bit seed identities required')
        for h in (self.noise_law_sha256,self.source_context_sha256,self.destination_context_sha256):
            if not isinstance(h,str) or len(h)!=64 or any(x not in '0123456789abcdef' for x in h):
                raise ValueError('External input identity missing')
        if self.source_context_sha256==self.destination_context_sha256:
            raise ValueError('Calibration and evaluation contexts must be distinct')

    def record(self):
        self.validate()
        return {'schema':'radio-whole-cadence-null-design-proposal-v1',
            'design_id':self.design_id,'null_namespaces':list(self.null_namespaces),
            'evaluation_namespaces':list(self.evaluation_namespaces),
            'control_seeds':list(self.control_seeds),'noise_law_sha256':self.noise_law_sha256,
            'source_context_sha256':self.source_context_sha256,
            'destination_context_sha256':self.destination_context_sha256,
            'reference_unit':'complete independent synthetic cadence maximum',
            'score_shift_resampling':False,'empty_samples_retained':True,
            'status':'PROPOSED_NOT_ACTIVATED','budget_charged':False,
            'new_values_generated':False,'telescope_access_authorized':False}
