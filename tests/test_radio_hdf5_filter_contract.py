"""Filter admission tests; no file, dataset payload or network access."""
import copy
from contextlib import ExitStack
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from seti_repeater import hdf5_filter_contract_radio as filters
from seti_repeater import source_radio


EXPECTED=[[32008,1,[0,3,4,0,2],'archive display name']]


class MetadataDataset:
    def __init__(self, pipeline):
        self.pipeline=pipeline;self.id=self;self.chunks=(1,1,1048576);self.shape=(16,1,264503296)
    def get_create_plist(self):return self
    def get_nfilters(self):return len(self.pipeline)
    def get_filter(self,index):return self.pipeline[index]
    def __getitem__(self,key):raise AssertionError('Payload access before filter admission')


class FilterContractTests(unittest.TestCase):
    def test_exact_legacy_source_declaration_passes_metadata_only(self):
        self.assertEqual(filters.check_dataset(MetadataDataset(EXPECTED),EXPECTED),[[32008,1,[0,3,4,0,2]]])

    def test_display_name_does_not_change_codec_semantics(self):
        changed=copy.deepcopy(EXPECTED);changed[0][3]=b'current plugin display name'
        self.assertEqual(filters.check_dataset(MetadataDataset(changed),EXPECTED),[[32008,1,[0,3,4,0,2]]])

    def test_version_element_size_block_size_and_compressor_mismatch_rejected(self):
        for index,value in [(0,1),(1,5),(2,8),(3,8192),(4,3)]:
            with self.subTest(index=index):
                changed=copy.deepcopy(EXPECTED);changed[0][2][index]=value
                with self.assertRaisesRegex(ValueError,'differs'):
                    filters.check_dataset(MetadataDataset(changed),EXPECTED)

    def test_filter_id_or_optional_flag_mismatch_rejected(self):
        for index,value in [(0,32004),(1,0)]:
            changed=copy.deepcopy(EXPECTED);changed[0][index]=value
            with self.assertRaises(ValueError):filters.check_dataset(MetadataDataset(changed),EXPECTED)

    def test_missing_extra_or_reordered_pipeline_rejected(self):
        expected=EXPECTED+[[1,1,[4]]]
        for changed in [[],EXPECTED,expected[::-1],expected+[[2,1,[]]]]:
            with self.assertRaises(ValueError):filters.check_dataset(MetadataDataset(changed),expected)

    def test_invalid_client_values_rejected_without_coercion(self):
        for value in (True,-1,2.,'2'):
            changed=copy.deepcopy(EXPECTED);changed[0][2][4]=value
            with self.assertRaises(ValueError):filters.signature(changed)

    def test_explicit_unfiltered_definition_differs_from_missing_definition(self):
        self.assertEqual(filters.declared({'observed_hdf5_filters':[]},required=True),[])
        with self.assertRaises(ValueError):filters.declared({},required=True)
        self.assertIsNone(filters.declared({},required=False))

    def test_missing_telescope_declaration_fails_before_any_identity_request(self):
        with patch.object(source_radio.net,'live_identity',side_effect=AssertionError('Network invoked')) as net:
            with self.assertRaisesRegex(ValueError,'declaration required'):
                source_radio._extract_bound_source({}, {}, 'a'*64, None, None, None,kind='telescope-remote')
            net.assert_not_called()

    def test_invalid_declaration_fails_before_any_identity_request(self):
        definition={'observed_hdf5_filters':[[32008,1,[False]]]}
        with patch.object(source_radio.net,'live_identity',side_effect=AssertionError('Network invoked')) as net:
            with self.assertRaises(ValueError):
                source_radio._extract_bound_source(definition,{},'a'*64,None,None,None,kind='telescope-remote')
            net.assert_not_called()

    def test_new_reader_dependency_is_a_required_future_contract_pin(self):
        self.assertIn('src/seti_repeater/hdf5_filter_contract_radio.py',source_radio.IMPLEMENTATION_PATHS)

    def reader_guard(self, datasets):
        mirror=MagicMock();mirror.__enter__.return_value=mirror
        file=MagicMock();file.__enter__.return_value=file
        identity=SimpleNamespace(size=100,etag='"fixture"')
        definition={'url':'https://fixture.invalid/test.h5','label':'fixture',
            'expected_remote_size_bytes':100,'expected_etag':'"fixture"',
            'expected_chunks':[1,1,1048576],'observed_hdf5_filters':EXPECTED}
        with ExitStack() as stack:
            directory=stack.enter_context(tempfile.TemporaryDirectory())
            stack.enter_context(patch.dict('sys.modules',{'h5py':SimpleNamespace(File=lambda *a,**k:file),
                                                         'hdf5plugin':SimpleNamespace()}))
            stack.enter_context(patch.object(source_radio.rows,'make_scope',return_value={}))
            stack.enter_context(patch.object(source_radio.rows,'validate_dataset',side_effect=datasets))
            stack.enter_context(patch.object(source_radio.net,'live_identity',return_value=identity))
            stack.enter_context(patch.object(source_radio.net,'RadioMirror',return_value=mirror))
            discover=stack.enter_context(patch.object(source_radio.old,'discover_hdf5_chunk_ranges',return_value=[]))
            stack.enter_context(patch.object(source_radio.old,'range_plan_record',return_value={}))
            stack.enter_context(patch.object(source_radio.old,'publish_range_plan',return_value='f'*64))
            extract=stack.enter_context(patch.object(source_radio.rows,'_extract_rows',side_effect=AssertionError('Payload read')))
            with self.assertRaisesRegex(ValueError,'filter pipeline differs'):
                source_radio._extract_bound_source(definition,{'name':'fixture','archive_interval':[1,2]},
                    'a'*64,directory,directory,None,kind='telescope-remote')
            extract.assert_not_called()
            return discover.call_count,mirror.prefetch.call_count

    def test_first_open_profile_mismatch_stops_before_chunk_discovery(self):
        self.assertEqual(self.reader_guard([MetadataDataset([])]),(0,0))

    def test_second_open_profile_change_stops_before_native_row_read(self):
        self.assertEqual(self.reader_guard([MetadataDataset(EXPECTED),MetadataDataset([])]),(1,1))


if __name__=='__main__':unittest.main()
