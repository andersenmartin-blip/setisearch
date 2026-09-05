import unittest
from seti_repeater.light_sail import apply_abacad_veto
class AbabTests(unittest.TestCase):
    def test_second_off_vetoes_only_second_on(self):
        def event(score):return {'score':score,'frequency_start_mhz':9900.,'frequency_stop_mhz':9903.,'time_start_s':10.,'time_stop_s':20.}
        scans=[{'label':'A1','role':'ON','adjacent_off_labels':['B1'],'search':{'events':[event(10)]}}, {'label':'B1','role':'OFF','adjacent_off_labels':[],'search':{'events':[]}}, {'label':'A2','role':'ON','adjacent_off_labels':['B1','B2'],'search':{'events':[event(10)]}}, {'label':'B2','role':'OFF','adjacent_off_labels':[],'search':{'events':[event(7)]}}]
        r=apply_abacad_veto(scans,on_threshold=8,off_threshold=6,minimum_frequency_overlap=.5)
        self.assertEqual([(x['on_label'],x['survives_adjacent_off_veto']) for x in r],[('A1',True),('A2',False)])
