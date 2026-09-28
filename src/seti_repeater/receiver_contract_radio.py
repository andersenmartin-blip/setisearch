"""Distinct downstream ancestry for a published ReceiverBank, never orbital inputs."""
from dataclasses import dataclass
import json
import numpy as np

from . import receiver_bank_radio as received
from . import search_v0p6 as core
from . import transfer_m43g as native


@dataclass(frozen=True)
class ReceiverContract:
    factors: received.ReceiverBank
    source_contract_bytes: bytes
    scans_json: str
    bank_json: str
    labels_sha256: str
    factor_table_sha256: str
    identity: str

    @property
    def scans(self): return json.loads(self.scans_json)

    @property
    def bank(self): return json.loads(self.bank_json)

    def for_scan(self, label):
        self.validate()
        if label not in received.LABELS: raise ValueError('Unknown receiver scan')
        i = received.LABELS.index(label)
        return native.immutable(np.ascontiguousarray(self.factors.factors[:,i*16:(i+1)*16,1]))

    def matrix_for_kind(self, kind):
        indices = core.m37_scan_indices_for_kind(self.scans, kind)
        return native.immutable(np.ascontiguousarray(np.concatenate(
            [self.for_scan(self.scans[i]['label']) for i in indices],axis=1)))

    def row_selection_sha256(self, kind):
        indices = core.m37_scan_indices_for_kind(self.scans, kind)
        return native.digest({'schema':'radio-receiver-row-selection-v1',
            'receiver_bank_sha256':self.factors.identity,'labels_sha256':self.labels_sha256,
            'scan_inventory_sha256':core.scan_inventory_sha256(self.scans),
            'scan_kind':kind,'scan_indices':list(indices),'sample':'midpoint'})

    def record(self):
        return {'schema':'radio-receiver-downstream-factor-contract-v1',
            'receiver_bank_sha256':self.factors.identity,
            'labels_sha256':self.labels_sha256,'factor_table_sha256':self.factor_table_sha256,
            'template_bank_sha256':core.template_bank_sha256(self.bank),
            'scan_inventory_sha256':core.scan_inventory_sha256(self.scans),
            'legacy_certificate_slot_mapping':{
                'factor_basis_sha256':'receiver_bank_sha256 (literal factors; no FactorBasis)',
                'factor_basis_labels_sha256':'receiver midpoint labels_sha256'},
            'orbital_fields_constructed':False,'telescope_access_authorized':False}

    def validate(self):
        if type(self.factors) is not received.ReceiverBank:
            raise ValueError('ReceiverBank required')
        self.factors.validate()
        provenance = json.loads(self.factors.provenance_json)
        if received.sha(self.source_contract_bytes) != provenance['source_contract_sha256']:
            raise ValueError('Source bytes differ from receiver bank pin')
        source = json.loads(self.source_contract_bytes)
        expected = [{**s, 'kind':s['role'], 'epoch':i//2+1} for i,s in enumerate(source['scans'])]
        if self.scans != expected:
            raise ValueError('Scans differ from exact pinned source inventory')
        if (tuple(s['label'] for s in self.scans) != received.LABELS
                or self.bank != catalogue(self.factors)
                or self.labels_sha256 != labels(self.factors)
                or self.factor_table_sha256 != core.factor_table_sha256(self.factors.factors[:,:,1])
                or self.identity != native.digest(self.record())):
            raise ValueError('Receiver downstream ancestry changed')
        core.m37_scan_indices_for_kind(self.scans,'on')
        core.m37_scan_indices_for_kind(self.scans,'off')


def labels(bank):
    return native.digest({'schema':'radio-receiver-midpoint-labels-v1',
        'receiver_bank_sha256':bank.identity,'scan_labels':list(received.LABELS),
        'integrations_per_scan':16,'sample':'midpoint'})


def catalogue(bank):
    p=json.loads(bank.provenance_json)
    return [{'schema':'radio-received-linear-template-v1','template_index':i,
             'line_index':i,'line_coefficient':j/10,
             'rate_label_hz_s':j/10,'rate_reference_hz':p['center_hz'],
             'actual_slope_formula':'q*rate_label_hz_s/rate_reference_hz',
             'receiver_bank_sha256':bank.identity,
             'line_fields_are_retention_compatibility_metadata':True}
            for i,j in enumerate(received.RATE_TENTHS)]


def build(bank, scans, *, trusted_bank_identity, source_contract_bytes):
    if type(bank) is not received.ReceiverBank or bank.identity != trusted_bank_identity:
        raise ValueError('Externally pinned receiver bank required')
    bank.validate()
    result=ReceiverContract(bank,source_contract_bytes,core.canonical_json_bytes(scans).decode(),
        core.canonical_json_bytes(catalogue(bank)).decode(),labels(bank),
        core.factor_table_sha256(bank.factors[:,:,1]),'')
    result=ReceiverContract(**{**result.__dict__,'identity':native.digest(result.record())})
    result.validate()
    return result
