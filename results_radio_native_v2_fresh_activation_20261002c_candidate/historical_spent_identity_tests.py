"""Extra synthetic checks for preserved a/b spent identities; no project marker."""
import copy
from unittest import mock
import tempfile


def install_cases(base, activation):
    class HistoricalSpentIdentityTests(base):
        def test_both_old_marker_paths_refused_before_git(self):
            for path in activation.SPENT_MARKERS:
                with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                    root, paths, values, readback = self.fixture(directory)
                    with mock.patch.object(activation, '_git') as launch:
                        with self.assertRaisesRegex(ValueError, 'spent'):
                            self.verify(root, paths, readback, marker_path=path)
                        launch.assert_not_called()

        def test_both_old_commits_refused_even_with_current_marker_namespace_and_pins(self):
            with tempfile.TemporaryDirectory() as directory:
                root, paths, values, readback = self.fixture(directory)
                receipt = self.verify(root, paths, readback)
                for commit in activation.SPENT_ACTIVATION_COMMITS:
                    changed = copy.deepcopy(receipt)
                    changed['activation_commit'] = commit
                    with self.subTest(commit=commit), self.assertRaisesRegex(ValueError, 'spent'):
                        activation.validate_worker_receipt(changed, plan=values['plan'],
                            complete_freeze=values['complete_freeze'],
                            execution_preread=values['execution_preread'])

        def test_old_transition_namespace_is_not_current_authority(self):
            with tempfile.TemporaryDirectory() as directory:
                root, paths, values, readback = self.fixture(directory)
                receipt = self.verify(root, paths, readback)
                for namespace in ('radio-native-v2-control-activation-transition-20261002a',
                        'radio-native-v2-control-activation-transition-20261002b'):
                    changed = copy.deepcopy(receipt); changed['namespace'] = namespace
                    with self.subTest(namespace=namespace), self.assertRaises(ValueError):
                        activation.validate_worker_receipt(changed, plan=values['plan'],
                            complete_freeze=values['complete_freeze'],
                            execution_preread=values['execution_preread'])
    # Load only the three newly declared methods; do not duplicate the inherited suite.
    return HistoricalSpentIdentityTests
