"""New deterministic interface risks only; never generate reserved controls."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import radio_receiver_adapter_common as common
from seti_repeater import search_v0p6 as core
from seti_repeater import receiver_panel_radio as panel
from seti_repeater import detector_receiver_radio as detector
from seti_repeater import pipeline_radio as legacy
from seti_repeater import transfer_m43g as native
from seti_repeater.injection_m43r import ScoreStore


def fixture_context(orbital=False):
    original=common.context()
    t=copy.deepcopy(original.bank[60]);t['template_index']=0
    if orbital:
        t={'template_index':0,'line_index':60,'line_coefficient':2.,'projected_scale':2.,'phase_cycles':0.}
    f0=original.factor_contract
    f=SimpleNamespace(bank=[t],identity=f0.identity,labels_sha256=f0.labels_sha256,
        factors=f0.factors,factor_table_sha256=f0.factor_table_sha256,
        row_selection_sha256=f0.row_selection_sha256,
        matrix_for_kind=lambda kind:f0.matrix_for_kind(kind)[60:61],
        record=f0.record)
    return SimpleNamespace(validate=lambda:None,window=original.window,grid=original.grid,
        bank=[t],scans=original.scans,factor_contract=f,maximum_records=1000,identity='f'*64)


def constant_store(c,value):
    return ScoreStore({(kind,0,w):np.full((3,99),value,dtype='<f4')
        for kind in ('on','off') for w in core.M37_SPECTRAL_WIDTHS},{'source_domain':'analytic-interface-fixture'})


def receiver_fixture(records,bank):
    signatures={r['record_id']:[{'epoch_zero_based':e,
        'predicted_mid_mhz':r['proxy_carrier_mhz'],'peak_frequency_mhz':r['proxy_carrier_mhz'],
        'peak_snr':0.,'offset_from_prediction_hz':0.} for e in r['active_epochs_zero_based']]
        for r in records}
    return signatures,{'signatures_sha256':native.digest(signatures),'fixture':True}


class ReceiverPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=fixture_context()
        cls.shifts=np.array([(0,a,b) for a in range(32,49) for b in range(32,49)][:127],dtype='<i8')
        cls.acc,cls.support=panel.accumulate(cls.c,constant_store(cls.c,4.),cls.shifts)
        cls.cal=panel.bind_calibration(cls.c,cls.acc,cls.support,{'fixture':True})

    def test_explicit_receiver_metadata_has_no_orbital_placeholders(self):
        m=core._template_retention_metadata(self.c.bank[0])
        self.assertEqual(m['rate_label_hz_s'],2.)
        self.assertNotIn('projected_scale',m);self.assertNotIn('phase_offset_cycles',m)

    def test_receiver_orbit_mix_rejected(self):
        t=copy.deepcopy(self.c.bank[0]);t['phase_cycles']=0.
        with self.assertRaises(core.V0P6ContractError):core._template_retention_metadata(t)

    def test_receiver_bad_rate_and_reference_rejected(self):
        for key,value in [('rate_reference_hz',0),('rate_label_hz_s',3),('receiver_bank_sha256','bad')]:
            t=copy.deepcopy(self.c.bank[0]);t[key]=value
            with self.assertRaises(core.V0P6ContractError):core._template_retention_metadata(t)

    def test_legacy_metadata_bytes_unchanged(self):
        t={'line_index':2,'line_coefficient':1.25,'projected_scale':1.25,'phase_cycles':.5}
        self.assertEqual(core._template_retention_metadata(t),
            {'line_index':2,'line_coefficient':1.25,'projected_scale':1.25,'phase_offset_cycles':.5})

    def test_finite_calibration_uses_fixed_floor_and_inclusive_rank(self):
        self.assertEqual(self.support['finite_null_count'],127)
        self.assertEqual(self.cal.threshold.operational_threshold_snr,10.)
        self.assertEqual(self.cal.threshold.inclusive_rank_p_at_threshold,1/128)
        self.assertEqual(self.cal.threshold.scientific_empirical_p_ceiling,.01)

    def test_empty_null_is_retained_failure_not_fabricated_finite_tail(self):
        acc,r=panel.accumulate(self.c,constant_store(self.c,0.),self.shifts[:2])
        self.assertIsNone(acc);self.assertEqual(r['null_maxima'],[None,None])
        self.assertEqual(r['status'],'FAILED_EMPTY_CONDITIONAL_NULL_SUPPORT')
        self.assertTrue(r['complete_hypothesis_inventory'])

    def test_receiver_metadata_reaches_full_decision_chain(self):
        store=constant_store(self.c,0.)
        arrays={k:v.copy() for k,v in store.arrays.items()}
        # Prescribed score fixture, not a native injection/recovery realization.
        arrays['on',0,1][:,49]=20.
        store=ScoreStore(arrays,store.provenance)
        r=detector.execute(self.c,store,self.cal.binding,self.cal.accumulator,self.cal.threshold,receiver_fixture)
        self.assertEqual(len(r['decisions']),4)
        self.assertTrue(all(d['passes_evaluated_physical_vetoes'] and d['meets_diagnostic_rank_cut'] for d in r['decisions']))
        self.assertTrue(all(x['rate_label_hz_s']==2. for x in r['retained']['on']))
        self.assertTrue(all('projected_scale' not in x for x in r['retained']['on']))
        self.assertEqual(sum(c['member_count'] for c in legacy.complete_clusters(r)),4)

    def test_matched_and_adjacent_veto_still_execute(self):
        for kind in ('matched','adjacent'):
            store=constant_store(self.c,0.)
            arrays={k:v.copy() for k,v in store.arrays.items()}
            arrays['on',0,1][:,49]=20.
            if kind=='matched':arrays['off',0,1][:,49]=20.
            else:arrays['off',0,1][0,49]=8.
            store=ScoreStore(arrays,store.provenance)
            r=detector.execute(self.c,store,self.cal.binding,self.cal.accumulator,self.cal.threshold,receiver_fixture)
            dispositions={d['physical_disposition'] for d in r['decisions']}
            self.assertIn('rfi_veto_matched_off_same_hypothesis' if kind=='matched' else 'rfi_veto_single_adjacent_off',dispositions)

    def test_score_and_decision_numeric_kernels_unchanged(self):
        old=subprocess.check_output(['git','show','29e57ba2785e154b0008cd97947fdf1bd088ebf8:src/seti_repeater/search_v0p6.py'],cwd=ROOT).decode()
        new=(ROOT/'src/seti_repeater/search_v0p6.py').read_text()
        def funcs(s):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        before,after=funcs(old),funcs(new)
        changed={k for k in before if before[k]!=after[k]}
        self.assertEqual(changed,{'_validate_retained_record_json_numeric_types','_validated_retained_records'})

    def test_shift_guard_remains_unchanged(self):
        bad=self.shifts.copy();bad[0,1]=31
        with self.assertRaises(core.V0P6ContractError):panel.accumulate(self.c,constant_store(self.c,4.),bad)

    def test_translation_rejects_unpinned_proof(self):
        run=SimpleNamespace(validate_store=lambda x:None)
        with self.assertRaisesRegex(ValueError,'external pin'):
            panel.translate_calibration_scores(run,None,self.c,b'{}','0'*64)

    def test_translation_rejects_pilot_shortcut(self):
        p=ROOT/'results_radio_hd189733_score_map_2026-09-28/result.json';raw=p.read_bytes()
        run=SimpleNamespace(validate_store=lambda x:None,context=common.context('calibration'))
        with self.assertRaisesRegex(ValueError,'calibration-to-validation'):
            panel.translate_calibration_scores(run,None,common.context('pilot'),raw,hashlib.sha256(raw).hexdigest())

    def test_legacy_records_still_complete_full_chain(self):
        c=fixture_context(orbital=True)
        acc,support=panel.accumulate(c,constant_store(c,4.),self.shifts)
        cal=panel.bind_calibration(c,acc,support,{'fixture':True})
        s=constant_store(c,0.);a={k:v.copy() for k,v in s.arrays.items()};a['on',0,1][:,49]=20.
        # The receiver diagnostic presentation expects rate fields. Exercise
        # the unchanged legacy direct adapter for orbital metadata instead.
        from seti_repeater import detector_direct_radio as direct
        r=direct.execute(c,ScoreStore(a,s.provenance),cal.binding,acc,cal.threshold,receiver_fixture)
        self.assertEqual(len(r['decisions']),4)
        self.assertTrue(all(d['passes_evaluated_physical_vetoes'] and d['meets_diagnostic_rank_cut'] for d in r['decisions']))
        self.assertTrue(all('projected_scale' in x and 'template_schema' not in x for x in r['retained']['on']))

    def test_translation_preserves_payload_and_source_ancestry(self):
        raw=(ROOT/'results_radio_hd189733_score_map_2026-09-28/result.json').read_bytes()
        run=SimpleNamespace(validate_store=lambda x:None,context=common.context('calibration'))
        s=constant_store(self.c,4.)
        t,r=panel.translate_calibration_scores(run,s,common.context(),raw,hashlib.sha256(raw).hexdigest())
        for k in s.arrays:np.testing.assert_array_equal(s.arrays[k].view('<u4'),t.arrays[k].view('<u4'))
        self.assertEqual(r['source_provenance'],s.provenance)
        self.assertFalse(r['destination_is_new_native_measurement'])
        self.assertFalse(r['telescope_noise_exchangeability_claimed'])

    def test_activity_renderer_uses_exact_scan_roles(self):
        c=common.context()
        patterns={'single_adjacent_off':{'on_epochs_zero_based':[0,2],'off_epochs_zero_based':[0]}}
        case={'role':'evaluation','seed':123456789,'identity':'analytic-unit-fixture',
              'recipe':{'kind':'single_adjacent_off','activity_patterns':patterns,
                        'injection_width_channels':65,'total_digital_power':500.,'rate_label_hz_s':2.}}
        def sample_one_row(reader,geometry,count,**kwargs):
            values=np.array([reader(0)])
            return SimpleNamespace(values=values,identity='fixture')
        with patch.object(native,'normalize_synthetic_rows',sample_one_row):
            _,r=panel.render_case(c,case)
        self.assertEqual([x['rows'][0]['injected'] for x in r['row_receipts']],[True,True,False,False,True,False])
        self.assertTrue(all(abs(x['rows'][0]['added_total_power_before_float32']-500)<1e-10
                            for x in r['row_receipts'] if x['rows'][0]['injected']))

    def test_renderer_refuses_closed_development_identity(self):
        with self.assertRaisesRegex(ValueError,'Closed development'):
            panel.render_case(common.context(),{'role':'development','recipe':{}})


class AccountingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=common.context()

    def fixture(self,kind='on_signal',offset=0.,active=(0,1,2),physical=True):
        c=self.c;t=40;rid='fixture';q=c.grid.center_mhz*1e6+offset
        case={'identity':'fixture','recipe':{'case_id':'fixture','kind':kind,'rate_label_hz_s':0.,
            'activity_patterns':{kind:{'on_epochs_zero_based':[0,1,2] if kind!='single_adjacent_off' else [0,2]}}}}
        r={'detector':{'retained':{'on':[{'record_id':rid,'active_epochs_zero_based':list(active),
            'template_index':t,'proxy_carrier_hz':q,'spectral_width_channels':65}]},
            'decisions':[{'record_id':rid,'passes_evaluated_physical_vetoes':physical,'meets_diagnostic_rank_cut':True}]},
           'clusters':[{'diagnostic_final_ids':[rid] if physical else [],'member_ids':[rid]}]}
        return r,case

    def test_signal_association_and_recovery(self):
        r,c=self.fixture();out=panel.classify(r,self.c,c)
        self.assertTrue(out['gate_pass']);self.assertEqual(out['counts']['associated_final_members'],1)

    def test_unassociated_signal_reported_without_counting_recovery(self):
        r,c=self.fixture(offset=3*self.c.geometry.channel_width_hz);out=panel.classify(r,self.c,c)
        self.assertFalse(out['gate_pass']);self.assertEqual(out['counts']['unassociated_final_members'],1)

    def test_wrong_active_epoch_cannot_be_associated(self):
        r,c=self.fixture(kind='single_adjacent_off');out=panel.classify(r,self.c,c)
        self.assertFalse(out['gate_pass']);self.assertEqual(out['counts']['unassociated_final_members'],1)

    def test_control_survivor_fails_zero_gate(self):
        for kind in ('matched_on_off','noise_null'):
            r,c=self.fixture(kind=kind);self.assertFalse(panel.classify(r,self.c,c)['gate_pass'])

    def test_vetoed_member_is_not_final(self):
        r,c=self.fixture(kind='matched_on_off',physical=False)
        self.assertTrue(panel.classify(r,self.c,c)['gate_pass'])

    def test_missing_cluster_member_is_integrity_failure(self):
        r,c=self.fixture();r['clusters']=[]
        with self.assertRaisesRegex(ValueError,'partition'):panel.classify(r,self.c,c)


if __name__=='__main__':unittest.main()
