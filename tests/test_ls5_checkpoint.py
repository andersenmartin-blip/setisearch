import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ls5_screen import seal,validate_checkpoint
class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.scan={'label':'B1','role':'OFF','adjacent_off_labels':[],'medium_resolution':{'url':'https://example.org/B1.fil','expected_size_bytes':100}}
        self.receipt={'config_sha256':'abc','scan':{'label':'B1','role':'OFF','adjacent_off_labels':[],'source_url':'https://example.org/B1.fil','source_size_bytes':100}}
        self.receipt['checkpoint_sha256']=seal(self.receipt)
    def test_valid_checkpoint(self):
        self.assertEqual(validate_checkpoint(self.receipt,self.scan,'abc')['label'],'B1')
    def test_changed_configuration_rejected(self):
        with self.assertRaises(RuntimeError):validate_checkpoint(self.receipt,self.scan,'changed')
    def test_tampered_result_rejected(self):
        r=copy.deepcopy(self.receipt);r['scan']['source_size_bytes']=200
        with self.assertRaises(RuntimeError):validate_checkpoint(r,self.scan,'abc')
    def test_other_scan_rejected_even_if_resealed(self):
        r=copy.deepcopy(self.receipt);r['scan']['role']='ON';r['checkpoint_sha256']=seal({k:v for k,v in r.items() if k!='checkpoint_sha256'})
        with self.assertRaises(RuntimeError):validate_checkpoint(r,self.scan,'abc')
