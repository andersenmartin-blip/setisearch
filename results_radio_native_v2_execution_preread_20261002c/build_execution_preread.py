#!/usr/bin/env python3
"""Build a distinct, non-authorizing c preread from an independently pinned public proof.

This stdlib-only metadata tool never imports production source or re-measures
runtime, opens the historical workload, creates a control scope, calls a spender,
or creates an activation marker or launch configuration. Its public-readback
claims depend on an independently supplied raw proof pin from actual immutable
public GETs. Matching labels inside a proof are insufficient authentication.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ORIGINAL_ROOT = '/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002'
REPOSITORY = 'andersenmartin-blip/setisearch'
BRANCH = 'm43-support-qualification'
PREPARATION_COMMIT = 'e422fa4bb61778a5861c4376fd694c37c9208cf6'
PREPARATION_TREE = 'c17c72ee4b82b3c99c36dcfc545d363bfc88e58c'
PREPARATION_PARENT = '6fb17cac19f56741372430ed1bc1ca49369e56fb'
PLAN_PATH = 'config/radio_native_v2_compact_eight_input_control_20261002r.plan.json'
FREEZE_PATH = 'config/radio_native_v2_control_integration_20261002a.runtime.json'
PROOF_PATH = 'results_radio_native_v2_execution_preread_20261002c/preparation-public-readback.json'
OUTPUT_PATH = 'config/radio_native_v2_compact_control_20261002c.execution-preread.json'
RECEIPT_PATH = 'results_radio_native_v2_execution_preread_20261002c/build-execution-preread-receipt.json'
PLAN_PIN = {'bytes': 71857, 'sha256': 'b8bcccbf7570d803732ff5dfb4c199cb750913f1d5c2dba0eec86c4889fb5800'}
FREEZE_PIN = {'bytes': 1038989, 'sha256': '967cf86d953547695785f850621460969eeff16521f81f75e7ca897e1d1ffdc0'}
PROOF_PIN = {'bytes': 50357, 'sha256': '7f54f5977a07a5f077e2631f883af024c22a2a145d0a59b81409a7da81cd1ff5'}
PREREAD_SCHEMA = 'radio-native-v2-compact-eight-input-resource-control-v1-public-preread'
NAMESPACE = 'radio-native-v2-compact-eight-input-control-20261001a'
PROOF_SCHEMA = 'radio-native-v2-c-preread-preparation-public-readback-v1'
MAX_INPUT_BYTES = 16 * 1024**2
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'native_case_reservations': 0,
    'native_case_executions': 0, 'scientific_cases_run': 0, 'rng_draws': 0,
    'telescope_reads': 0, 'actual_functions_sdk_calls': 0, 'actual_connector_calls': 0,
    'network_fetches': 0, 'actual_git_processes': 0, 'real_public_github_mutations': 0,
    'automatic_retry': False, 'native_case_binding_verified': False,
    'host_ledger_join_complete': False, 'hidden_http_bytes_known': False}
MATERIAL_FILES = {'results_radio_native_v2_compact_control_20261002b/activation-receipt.json': {'bytes': 1332,
                                                                               'sha256': 'ba3533158ab34b0fe1bf3a71a879f508121e5126aadc197e2ccdc40327d78ee3'},
 'results_radio_native_v2_compact_control_20261002b/frozen-code/scripts/radio_native_v2_invocation_spending.py': {'bytes': 20163,
                                                                                                                  'sha256': 'd6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'},
 'results_radio_native_v2_compact_control_20261002b/invocation-spending.json': {'bytes': 1018,
                                                                                'sha256': 'f7beaea6e4855f1439c3ae1ecceadf3a4335607fc6940b7b0d0ec1d0c8150f89'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-manifest.json': {'bytes': 778,
                                                                                                                'sha256': 'f0281ae6b64015c7aaea5a634d58c69e123609f1d0bf26886f96f57d18267aee'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-observation.json': {'bytes': 1200,
                                                                                                                   'sha256': 'c96bc568502bbf14e2fe3ad9946dddac258e20d047008d4c4f3ed494c53558e1'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-spend-observation.json': {'bytes': 1293,
                                                                                                                         'sha256': '56a445db080250a7e39f17d18dd0f7b57a57d93f34664504410335abedfbbf05'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-manifest.json': {'bytes': 42900,
                                                                                                               'sha256': '6b3ce36a0e70169a4f97a57b60b6ef3abd4dbed06f90c83f8eb71baf71fea890'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-observation.json': {'bytes': 55112,
                                                                                                                  'sha256': '02fdb297790aad0d049bb006b11bf1fa1471e09106fb5ac09cf6c178646034cd'},
 'results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json': {'bytes': 81935,
                                                                                              'sha256': 'f49912dda98e557fce3991c141169bd207306e54317fffc07c107c8a99e14fb7'},
 'scripts/radio_native_v2_activation_environment.py': {'bytes': 11741,
                                                       'sha256': '059003934a8b51c544f72b488c41c19a6067c0ffb0e65c31afc6eacd35d76bfd'},
 'scripts/radio_native_v2_broker_host.js': {'bytes': 32557,
                                            'sha256': '29e7954f78be92e3af3cd2bdbf1f5449138e35e3839a923fbc9ceafb0a0d9c7f'},
 'scripts/radio_native_v2_caller_tail.py': {'bytes': 9215,
                                            'sha256': '8eb1d089f6b9f869f0aecb020a9d7fdf638ce9c3c666b208e8d227795a7a041c'},
 'scripts/radio_native_v2_compact_control_launch.py': {'bytes': 34274,
                                                       'sha256': '0db793b74b64f4b5f201d1c7d7e10f273eaf75623c6d4150033cf52f40e5cdf8'},
 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py': {'bytes': 128291,
                                                                    'sha256': 'c1acc2e3f7148fecedec507d1fd8fabba8a85e1be3907945653ffd0aeaa7c5b4'},
 'scripts/radio_native_v2_compact_preparation_audit.py': {'bytes': 25154,
                                                          'sha256': '8a7711b93cd520fb6f9ffc634722de3ff47eb8f03b899145bda443c77c111e05'},
 'scripts/radio_native_v2_compact_run_verifier.py': {'bytes': 22556,
                                                     'sha256': '689262de053151f46423feee965e8a2aa0f4205ee488f318ffbfbc683026720d'},
 'scripts/radio_native_v2_control_activation.py': {'bytes': 20022,
                                                   'sha256': 'b0fc36e2ed4b925f0ff51e812b18c79ef8e8f3d93ea4f6091159dc6cfc0bfb6a'},
 'scripts/radio_native_v2_historical_observation.py': {'bytes': 13863,
                                                       'sha256': 'f725ff94a2ff8f375fec1e477e0cb20902d179e6d43e7a6b8fa649f282b1a008'},
 'scripts/radio_native_v2_historical_storage.py': {'bytes': 21869,
                                                   'sha256': '37d7225a9b24ee0de6002653d4676417b0b2befb5ce32cd071719fc01694d717'},
 'scripts/radio_native_v2_invocation_spending.py': {'bytes': 20163,
                                                    'sha256': 'd6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'},
 'scripts/radio_native_v2_local_courier.js': {'bytes': 26823,
                                              'sha256': '7cd6ffad2b6bb0ccbd9d69809800a08006af59f13a3f57e333a36a3a68cd5a1f'},
 'scripts/radio_native_v2_local_git.js': {'bytes': 16038,
                                          'sha256': '2c81f7c418c3f7fef1206f82a3d49eb9acc962b2b1a7391c5a689d6b5389d09e'},
 'scripts/radio_native_v2_local_transport.js': {'bytes': 53229,
                                                'sha256': '6c6196dbe22d8e1edf8d05057f601a29cc47b39024186aec5354ed7b204ac46d'},
 'scripts/radio_native_v2_process_tree_supervisor.py': {'bytes': 82676,
                                                        'sha256': '897cdba99e28edaf64541a8af43674954bb1bf19c872d5b45f8c033d374c3881'},
 'scripts/radio_native_v2_prospective_spending.py': {'bytes': 22296,
                                                     'sha256': '189da9f870628573e85ae6943a63d79b1390fce0aee8a04e003318cc506e895f'},
 'scripts/radio_native_v2_qualified_courier_fixture.js': {'bytes': 29111,
                                                          'sha256': '21b6b622c51387103c53c44e390a9bbd80e2d2d967011de508f975ca7e35bd34'},
 'scripts/radio_native_v2_qualified_tool_courier.js': {'bytes': 17271,
                                                       'sha256': '8f9c90841eb49c383d6d9a4e63bdf6fc5441a1ec063af60a77afe74b99ad4db9'},
 'scripts/radio_native_v2_resource_finalization.py': {'bytes': 79175,
                                                      'sha256': '2b01fe89d65f0243d274ca290c45432c09841e1997559f601f544ef1cc174679'},
 'scripts/radio_native_v2_runner_freeze.py': {'bytes': 24313,
                                              'sha256': '74ea2fee48eccf6e74a7b3f34517c0c0ccb50ff9abaacd57ab0a187acd24482b'},
 'scripts/radio_native_v2_runtime_custody.py': {'bytes': 22519,
                                                'sha256': 'd0cd311c1615a2c299b101ca75b98ba2412b41bb1cfd668725461e4d307fb0b5'},
 'scripts/radio_native_v2_tool_courier_client.js': {'bytes': 19274,
                                                    'sha256': '5240193fb91c7f5f5bfe46dd0953ebfb7cc93bbd6377b4c278f0cae874b4ec70'},
 'scripts/radio_native_v2_worker_admission.py': {'bytes': 77783,
                                                 'sha256': '41e147d00488bb00c8be4825d26e964857b5f3841f07d3f908ad112e133c8fa1'},
 'src/seti_repeater/__init__.py': {'bytes': 84,
                                   'sha256': '975f6dd9aa18bc0a69cb77599ce6096571d931abc52c281b766b36338f895a6d'},
 'src/seti_repeater/empty_null_radio.py': {'bytes': 6714,
                                           'sha256': '8c5c29efbd851a5504389d0adfcb244dbf3489a611785b7206ac552f13fdff6f'},
 'src/seti_repeater/native_v2_transport_contract_radio.py': {'bytes': 28951,
                                                             'sha256': 'f6ad34a2c242e79331763f544482d4353328d80d8a9d9956f9979d498ed16a93'},
 'tests/test_radio_native_v2_activation_environment.py': {'bytes': 4399,
                                                          'sha256': 'd796199d089df343153045a3ec65a76820f519a3d5c1520b1cffa9ca26bf2c1e'},
 'tests/test_radio_native_v2_compact_control_launch.py': {'bytes': 25140,
                                                          'sha256': 'c30c07169f3d9a8ac798a97366e46be9776b010eb6c76fa44bc37696d086a5b0'},
 'tests/test_radio_native_v2_compact_eight_case_resource_fixture.py': {'bytes': 70396,
                                                                       'sha256': 'c9a63b2afbc67f3a284c4f7d3d0b8f94a0d61b53066de3c848b1e0aab657481f'},
 'tests/test_radio_native_v2_control_activation.py': {'bytes': 26450,
                                                      'sha256': '1f5792bd2c0b132cdc91d805cc87de7c81b639cc0226884da253e6042bed11ff'},
 'tests/test_radio_native_v2_historical_observation.py': {'bytes': 10538,
                                                          'sha256': '32014dac5d6595d52a0ecf6fd868550048ea67493c10ec5a3e35f01640632c76'},
 'tests/test_radio_native_v2_historical_spending_join.py': {'bytes': 8596,
                                                            'sha256': 'adce6f05c8be034fa3096eda3bfc8916fc5cd69b57cedcb5d29ad7b902b1eb55'},
 'tests/test_radio_native_v2_historical_storage.py': {'bytes': 18389,
                                                      'sha256': '254dff57abb7e441d027f5a1c9de0fcbd69fac9f4aa547690e67d23580763aa8'},
 'tests/test_radio_native_v2_invocation_spending.py': {'bytes': 25088,
                                                       'sha256': 'f16c916d773dc69d635d1da31b3ba34c7ee505ca99dfb77783d6ec73d9bb76aa'},
 'tests/test_radio_native_v2_process_tree_supervisor.py': {'bytes': 58203,
                                                           'sha256': '758c528479557633713e1a5a4a5205e3c50626e8f9b12ba533b91427f35ebd86'},
 'tests/test_radio_native_v2_prospective_spending.py': {'bytes': 34588,
                                                        'sha256': '6ecb69ec6c1505803632498db098c4c99d82ff9b3e6df17da67da3b193bcdeb5'},
 'tests/test_radio_native_v2_resource_finalization.py': {'bytes': 71792,
                                                         'sha256': '21f70804b935352044c06c1301edab43e6cc4c5368fd9fdbd7a409dbc9fb6d83'},
 'tests/test_radio_native_v2_runtime_custody.py': {'bytes': 13050,
                                                   'sha256': 'f333dd1ea5c054d642dc2f57c3f13a2e6e14a9019816fb973412aac1b6127428'},
 'tests/test_radio_native_v2_source_receipt.py': {'bytes': 18009,
                                                  'sha256': '53072a921ce7ac72111d8f3f6ab226b3a207128da55acf5bc49a1053faa8996f'},
 'tests/test_radio_native_v2_worker_admission.py': {'bytes': 64985,
                                                    'sha256': '64ca9542de17d7a230f4b1109e0f74c951e293ff28dc6b4bb4bc794985da163c'}}
HISTORICAL_FILES = {'results_radio_native_v2_compact_control_20261002b/activation-receipt.json': {'bytes': 1332,
                                                                               'sha256': 'ba3533158ab34b0fe1bf3a71a879f508121e5126aadc197e2ccdc40327d78ee3'},
 'results_radio_native_v2_compact_control_20261002b/frozen-code/scripts/radio_native_v2_invocation_spending.py': {'bytes': 20163,
                                                                                                                  'sha256': 'd6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'},
 'results_radio_native_v2_compact_control_20261002b/invocation-spending.json': {'bytes': 1018,
                                                                                'sha256': 'f7beaea6e4855f1439c3ae1ecceadf3a4335607fc6940b7b0d0ec1d0c8150f89'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-manifest.json': {'bytes': 778,
                                                                                                                'sha256': 'f0281ae6b64015c7aaea5a634d58c69e123609f1d0bf26886f96f57d18267aee'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-observation.json': {'bytes': 1200,
                                                                                                                   'sha256': 'c96bc568502bbf14e2fe3ad9946dddac258e20d047008d4c4f3ed494c53558e1'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-spend-observation.json': {'bytes': 1293,
                                                                                                                         'sha256': '56a445db080250a7e39f17d18dd0f7b57a57d93f34664504410335abedfbbf05'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-manifest.json': {'bytes': 42900,
                                                                                                               'sha256': '6b3ce36a0e70169a4f97a57b60b6ef3abd4dbed06f90c83f8eb71baf71fea890'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-observation.json': {'bytes': 55112,
                                                                                                                  'sha256': '02fdb297790aad0d049bb006b11bf1fa1471e09106fb5ac09cf6c178646034cd'},
 'results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json': {'bytes': 81935,
                                                                                              'sha256': 'f49912dda98e557fce3991c141169bd207306e54317fffc07c107c8a99e14fb7'}}
PUBLIC_FILES = {'PROJECT_STATUS.md': {'bytes': 287651,
                       'git_blob_sha': 'c6f1d6592cda229abc6d0f6c3e101ba63e9fb2b3',
                       'sha256': '352f90c7b5abbf839858ddb9faaa07a01fd2118a088722f4a0e350665c839b33'},
 'RADIO_NATIVE_V2_CONTROL_INTEGRATION_2026-10-02_RESULT.md': {'bytes': 9919,
                                                              'git_blob_sha': '6aae35f0d87b6b6d522ef8bd78e703c46a084e50',
                                                              'sha256': '42605f5eee395fd4c96e69fac90fc6522a82aaf4b1520ea2fbd210a846d744f8'},
 'RADIO_TWO_WEEK_PLAN_2026-09-26.md': {'bytes': 131659,
                                       'git_blob_sha': '680f07d18f6b01d8adbe66464f9d818e8eff3006',
                                       'sha256': 'ae9d71a6414a43da21a675020370b699e0a6069bb174b8c166e841335ed50012'},
 'README.md': {'bytes': 43177,
               'git_blob_sha': '4ce90c6dbb418e4fc04ec21099da5a5eff2db223',
               'sha256': '9e91c5fdb4b33291c08571cd2af1bf6f54912db0def75d2d32308dd852d8887d'},
 'config/radio_native_v2_compact_eight_input_control_20261002r.plan.json': {'bytes': 71857,
                                                                            'git_blob_sha': '8f7e897cdd592c5da7f2d21065b956879b3d5f4a',
                                                                            'sha256': 'b8bcccbf7570d803732ff5dfb4c199cb750913f1d5c2dba0eec86c4889fb5800'},
 'config/radio_native_v2_control_integration_20261002a.runtime.json': {'bytes': 1038989,
                                                                       'git_blob_sha': 'a987791f297f315e09990a74f00a2797cd56c135',
                                                                       'sha256': '967cf86d953547695785f850621460969eeff16521f81f75e7ca897e1d1ffdc0'},
 'results_radio_native_v2_compact_control_20261002b/activation-receipt.json': {'bytes': 1332,
                                                                               'git_blob_sha': '34ffdbda5ee8836603c5837a09a4427533ac518c',
                                                                               'sha256': 'ba3533158ab34b0fe1bf3a71a879f508121e5126aadc197e2ccdc40327d78ee3'},
 'results_radio_native_v2_compact_control_20261002b/frozen-code/scripts/radio_native_v2_invocation_spending.py': {'bytes': 20163,
                                                                                                                  'git_blob_sha': '7a1c28ae6e373d8c37468ae765c8222501143e7a',
                                                                                                                  'sha256': 'd6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'},
 'results_radio_native_v2_compact_control_20261002b/invocation-spending.json': {'bytes': 1018,
                                                                                'git_blob_sha': '5d733b393584fa855261683d0b39e8ebdec61730',
                                                                                'sha256': 'f7beaea6e4855f1439c3ae1ecceadf3a4335607fc6940b7b0d0ec1d0c8150f89'},
 'results_radio_native_v2_control_integration_20261002a/activation-worker-focused-test-result.json': {'bytes': 2062,
                                                                                                      'git_blob_sha': '44976d215cdcd5381908da541ccbace418d828ac',
                                                                                                      'sha256': 'bfe6e262a36471cb9bbefe649abd69d421ee6f24ed614455ff680d5031f66a45'},
 'results_radio_native_v2_control_integration_20261002a/bootstrap-pin-refresh.json': {'bytes': 1435,
                                                                                      'git_blob_sha': 'cfda51b1455c84f431efb2b579037591fb9cf8d4',
                                                                                      'sha256': 'c9b1f436c2edfdc97e60aa7f684718b32f1e7f16c7772a6d108bb0523c62a828'},
 'results_radio_native_v2_control_integration_20261002a/control-activation-focused-tests.log': {'bytes': 3747,
                                                                                                'git_blob_sha': '675c1f76a1872ec3183440c8972f735e4c805146',
                                                                                                'sha256': 'c74f5c27a3f73effc52a21bea98e0ae8f627886d1aff5ca47c61742af1bd48ce'},
 'results_radio_native_v2_control_integration_20261002a/final-document-review.json': {'bytes': 3884,
                                                                                      'git_blob_sha': 'b50242562dd3c53e196df2612213869aef801a27',
                                                                                      'sha256': '520e12a22bbd120e644d8cf5dd29dc069e92cc67b4af83f59a62793ef1c2a497'},
 'results_radio_native_v2_control_integration_20261002a/final-preparation-selection.json': {'bytes': 2962,
                                                                                            'git_blob_sha': '9e0c7eaf4becb6e6c3e0301fbceabdd3666221e4',
                                                                                            'sha256': 'dd7717549aab4971686e023dc231f9284caf3ada6ea8ba36b876258bad8a0975'},
 'results_radio_native_v2_control_integration_20261002a/final-suite-attempt-1-summary.json': {'bytes': 268139,
                                                                                              'git_blob_sha': '1e2d99d47edece4e18332eaebb7c563beb83c5b4',
                                                                                              'sha256': 'b07375967cc60e09ba8951ea104b84468a6fc4bfc0a03da2558ee3524de39399'},
 'results_radio_native_v2_control_integration_20261002a/final-suite-attempt-1.stderr.log': {'bytes': 121875,
                                                                                            'git_blob_sha': '4c739b3cb80e7cc8b5b853549e902439718ddfdc',
                                                                                            'sha256': 'f91a8ff5a92f8dd169cc6cca3be4801f46a18744f112e6ee513d3ff048081708'},
 'results_radio_native_v2_control_integration_20261002a/final-suite-attempt-1.stdout.log': {'bytes': 268139,
                                                                                            'git_blob_sha': '1e2d99d47edece4e18332eaebb7c563beb83c5b4',
                                                                                            'sha256': 'b07375967cc60e09ba8951ea104b84468a6fc4bfc0a03da2558ee3524de39399'},
 'results_radio_native_v2_control_integration_20261002a/final-suite-attempt-2-summary.json': {'bytes': 268139,
                                                                                              'git_blob_sha': '2933be0ceebec9b3f0253e875f9fa3d457c5052d',
                                                                                              'sha256': '3e57db4a2193864fbca4302ebb9f0ad185f171d0b28994fc241c598536b14912'},
 'results_radio_native_v2_control_integration_20261002a/final-suite-attempt-2.stderr.log': {'bytes': 113291,
                                                                                            'git_blob_sha': 'b4073e51110a5141773e5309d22b16c7648b121d',
                                                                                            'sha256': '9d997c7d8a20b32790a06ad17cf8d2755664e2a0cdc85c5d0efacf70dcaf840e'},
 'results_radio_native_v2_control_integration_20261002a/final-suite-attempt-2.stdout.log': {'bytes': 268139,
                                                                                            'git_blob_sha': '2933be0ceebec9b3f0253e875f9fa3d457c5052d',
                                                                                            'sha256': '3e57db4a2193864fbca4302ebb9f0ad185f171d0b28994fc241c598536b14912'},
 'results_radio_native_v2_control_integration_20261002a/independent-integration-review-attempt-2.log': {'bytes': 232,
                                                                                                        'git_blob_sha': '3bbbd908dff0dad4d0e8105c2d2f6d582252ea44',
                                                                                                        'sha256': '094c574f7b492ffcc9209dbd1cd44e9a7ab070780efaba98663d58830829d635'},
 'results_radio_native_v2_control_integration_20261002a/independent-integration-review-attempt-3.json': {'bytes': 16760,
                                                                                                         'git_blob_sha': 'f4ecaacb40ee4ab476aff202003ab6482090af56',
                                                                                                         'sha256': '5b544b6199d433ecbeb30e266bf1258a1f68c7f66b1b430eb891b78b6ae2004e'},
 'results_radio_native_v2_control_integration_20261002a/independent-integration-review-attempt-3.log': {'bytes': 232,
                                                                                                        'git_blob_sha': '6aba7c4ec5df8c4e7f66092c5bfe022c9e8526d9',
                                                                                                        'sha256': 'ecbf2ff98ee93dfdd1238dbad793739db82f36629ef6f3dbe0b8839221e64105'},
 'results_radio_native_v2_control_integration_20261002a/independent-integration-review.json': {'bytes': 16760,
                                                                                               'git_blob_sha': '60d46cae62049032fc196c976d066de8e60d4702',
                                                                                               'sha256': 'c3c5c1e4cacd4c2235b1003bb6b6509778c94058a05d5717592f3870eb452a40'},
 'results_radio_native_v2_control_integration_20261002a/independent-integration-review.log': {'bytes': 916,
                                                                                              'git_blob_sha': 'ccdb5bc826ffe5d67b60c1f68b176dd0da76ff7e',
                                                                                              'sha256': 'fe3a310444aa70961518d223b17f4eb42bfb74b8f6ae42f16ef166a600cbb4b4'},
 'results_radio_native_v2_control_integration_20261002a/initial-worker-admission-in-progress.json': {'bytes': 1045,
                                                                                                     'git_blob_sha': '56b6c94e206db972b701f2caf54baf5509675c40',
                                                                                                     'sha256': '419822f9dc36ec2c38e0dd087f9a1b3acb11964ecb8b328d5e042d69a3fe1eec'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-integration-evidence-attempt2.json': {'bytes': 10823,
                                                                                                            'git_blob_sha': 'ff54a89eab45c5d83a9046bf960aa83b95d2b29d',
                                                                                                            'sha256': 'a80820788b06f903007582faea278a1c59410cf9c8a66eeff91dcad317e069f1'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-integration-evidence-attempt2.py': {'bytes': 5016,
                                                                                                          'git_blob_sha': 'f26c313537777e24330800ddd2f91a2b1152c163',
                                                                                                          'sha256': 'f13c3a89a493a483af0ba0d11acbc28369f8077bb0964a28f97b017dd0d38e18'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-integration-evidence-finalpins.json': {'bytes': 10827,
                                                                                                             'git_blob_sha': 'e676cdd757de6197abe1b059bfe4dd6e74193bc5',
                                                                                                             'sha256': '8bc12a72b7a599c11ac5f9b730be61c26330d3af832624bde0f177eb73785309'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-integration-evidence-finalpins.source.txt': {'bytes': 5025,
                                                                                                                   'git_blob_sha': 'e36d9a545a52d6ce0c87b1edec1de772e7acae8b',
                                                                                                                   'sha256': '70c1ce7eded350b47a6559d93f73d4fc8005b52f7be1ef28604c436c2f22039a'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-integration-evidence.json': {'bytes': 10787,
                                                                                                   'git_blob_sha': '3c274bf7333b735c49bf6d369893d012b8e0c8f1',
                                                                                                   'sha256': '9e740b8faed6e021e08fa4ab186fb082b2bb2304e82c54e5253f2de787877494'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-integration-evidence.py': {'bytes': 4935,
                                                                                                 'git_blob_sha': 'e418ed6a21de8aca6b93eaba4388522105882e55',
                                                                                                 'sha256': '3e140b1c5be23a74adb063697a9b5aad2794ecd818cc9f4a62fa71002735e4ee'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-integration-tests-attempt2.stderr.log': {'bytes': 3434,
                                                                                                               'git_blob_sha': 'c5698b7e56835b08efe34f9c3a5f921cbee1d96a',
                                                                                                               'sha256': 'a8596df3e7f65b5987fd00a9e5b83e099410ef55b2311c1b9e64f5332076c149'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-integration-tests-attempt2.stdout.log': {'bytes': 0,
                                                                                                               'git_blob_sha': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
                                                                                                               'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-integration-tests-finalpins.stderr.log': {'bytes': 3434,
                                                                                                                'git_blob_sha': '2eb52b10d2e8f68c3458eeca219903f5140d3082',
                                                                                                                'sha256': '983ad7a46f19a308e200abdafd0cb91759b40ce62f66e0a171732fef977890b4'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-integration-tests-finalpins.stdout.log': {'bytes': 0,
                                                                                                                'git_blob_sha': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
                                                                                                                'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-integration-tests.stderr.log': {'bytes': 3434,
                                                                                                      'git_blob_sha': '229ff91f622cff1a55ae7da55a4844a5cb048a24',
                                                                                                      'sha256': '59a00d603355639b95851fea5e100eefcd3d46b10670a621184e051f9c81ff9e'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-integration-tests.stdout.log': {'bytes': 0,
                                                                                                      'git_blob_sha': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
                                                                                                      'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-live-b-ledger-observation-attempt2.json': {'bytes': 1200,
                                                                                                                 'git_blob_sha': '2156f005b27b98dd8244f21d7f35b1ce8afdc086',
                                                                                                                 'sha256': 'c96bc568502bbf14e2fe3ad9946dddac258e20d047008d4c4f3ed494c53558e1'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-live-b-ledger-observation-finalpins.json': {'bytes': 1200,
                                                                                                                  'git_blob_sha': '2156f005b27b98dd8244f21d7f35b1ce8afdc086',
                                                                                                                  'sha256': 'c96bc568502bbf14e2fe3ad9946dddac258e20d047008d4c4f3ed494c53558e1'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-live-b-ledger-observation.json': {'bytes': 1200,
                                                                                                        'git_blob_sha': '2156f005b27b98dd8244f21d7f35b1ce8afdc086',
                                                                                                        'sha256': 'c96bc568502bbf14e2fe3ad9946dddac258e20d047008d4c4f3ed494c53558e1'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-live-b-scope-observation-attempt2.json': {'bytes': 55112,
                                                                                                                'git_blob_sha': 'ab7c8086869776204284fa9ba07cd8dfa95bca62',
                                                                                                                'sha256': '02fdb297790aad0d049bb006b11bf1fa1471e09106fb5ac09cf6c178646034cd'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-live-b-scope-observation-finalpins.json': {'bytes': 55112,
                                                                                                                 'git_blob_sha': 'ab7c8086869776204284fa9ba07cd8dfa95bca62',
                                                                                                                 'sha256': '02fdb297790aad0d049bb006b11bf1fa1471e09106fb5ac09cf6c178646034cd'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-live-b-scope-observation.json': {'bytes': 55112,
                                                                                                       'git_blob_sha': 'ab7c8086869776204284fa9ba07cd8dfa95bca62',
                                                                                                       'sha256': '02fdb297790aad0d049bb006b11bf1fa1471e09106fb5ac09cf6c178646034cd'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-original-plan-reread-fixture.source.txt': {'bytes': 128081,
                                                                                                                 'git_blob_sha': 'cb3a9ae3f028d83e177f39c9a53cc063c91aad94',
                                                                                                                 'sha256': 'caca109cbd029f56c05861df183371349dd58f9c6ed0b96aedb8a7960a3feb30'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-plan-reread-probe.json': {'bytes': 878,
                                                                                                'git_blob_sha': '8d8c5a60ace64a890c288347896e39490ce20656',
                                                                                                'sha256': 'a75d39381749d9b308840206573e70fca90073d86b464ee4d7e0813342257474'},
 'results_radio_native_v2_control_integration_20261002a/ledger-review-plan-reread-probe.py': {'bytes': 5496,
                                                                                              'git_blob_sha': '054f7ef7730423786c7f00c7126036f11633773a',
                                                                                              'sha256': '1e6efdc9f5efef43734443c8a4d4d32478078ccc5fde0cf8558b3b50e611b302'},
 'results_radio_native_v2_control_integration_20261002a/live-historical-adapter-observation.json': {'bytes': 2963,
                                                                                                    'git_blob_sha': 'babc01d9e4b4438433f9bd9bd1cc672a041740f5',
                                                                                                    'sha256': '5a7a0d75338298e15e62781c29463210ff8b9fa74b24dd97bd31270c12bc960c'},
 'results_radio_native_v2_control_integration_20261002a/live-historical-adapter-observation.stderr.log': {'bytes': 0,
                                                                                                          'git_blob_sha': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
                                                                                                          'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
 'results_radio_native_v2_control_integration_20261002a/main-readme-candidate.md': {'bytes': 48633,
                                                                                    'git_blob_sha': 'af54a0f6a8cd2fc44fca33db6d7ada21b1ca0780',
                                                                                    'sha256': '28d26b5d1438cc973cf761006e6d86b39135dd620a99c4f255d436a8cda149bd'},
 'results_radio_native_v2_control_integration_20261002a/observe_historical_adapter.py': {'bytes': 5600,
                                                                                         'git_blob_sha': '51c301187a075d9ab03066632babc1a46cceb242',
                                                                                         'sha256': '158afbfb14096aa710ba2e7b049cb444f4fc57fc6e7ec4aa77373dd417e90a59'},
 'results_radio_native_v2_control_integration_20261002a/preparation-capture.json': {'bytes': 8282,
                                                                                    'git_blob_sha': '8613541c60ccf773df4351affc5c163cf9fee80e',
                                                                                    'sha256': 'ad85856b4e295f49203726ecc98088e56d680848d8466bf516d86906b724e5ee'},
 'results_radio_native_v2_control_integration_20261002a/preparation-capture.stderr.log': {'bytes': 0,
                                                                                          'git_blob_sha': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
                                                                                          'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
 'results_radio_native_v2_control_integration_20261002a/preparation-verification.json': {'bytes': 31956,
                                                                                         'git_blob_sha': '86fe41331d0f4b9e146e8e980909b68b4b744694',
                                                                                         'sha256': '28c8947ef60d0b6ea62d97b029a910cb2a4d1295f03bd6c42cbfbd62980524f4'},
 'results_radio_native_v2_control_integration_20261002a/preparation-verification.stderr.log': {'bytes': 0,
                                                                                               'git_blob_sha': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
                                                                                               'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
 'results_radio_native_v2_control_integration_20261002a/prepare_snapshot.py': {'bytes': 24214,
                                                                               'git_blob_sha': '8cc63bf13724a9c2ab3da8e0ccb617fc5b5e634f',
                                                                               'sha256': 'edbe7b4b4332abd8be670145e1c6716b495d189f9c687f979e4fb34eeb39218f'},
 'results_radio_native_v2_control_integration_20261002a/publication-manifest.json': {'bytes': 37677,
                                                                                     'git_blob_sha': '86c6dfee368c07bdc8ba77361bb36b497d5b8ecd',
                                                                                     'sha256': '5fe662fa202018da0c43f76b79f13b80ef53984bab98a2fb9774a44aeecd1a78'},
 'results_radio_native_v2_control_integration_20261002a/refresh_bootstrap_pins.py': {'bytes': 2824,
                                                                                     'git_blob_sha': '9521f1ca971f1c5cf1b27b844b123557da6a3e55',
                                                                                     'sha256': '79c9ab30dda2089ef3188c744134db5ad20cdbb6082d41b0aafc9692d6d0d4c2'},
 'results_radio_native_v2_control_integration_20261002a/resource-finalization-complete-tiny-tests.log': {'bytes': 14862,
                                                                                                         'git_blob_sha': '538eaad27715346e513fd04e9f2f06afd86ec23a',
                                                                                                         'sha256': 'e89ccc7a503222aabb1bcf17287425dcf5b95cae14d43df41db2a46f6fcca6ab'},
 'results_radio_native_v2_control_integration_20261002a/resource-finalization-isolated-fixture-pin-refusal.log': {'bytes': 178,
                                                                                                                  'git_blob_sha': 'bb336faa31f6831e9c85ddc1a8aa995a807e3d81',
                                                                                                                  'sha256': 'b8e7f3d768e7845c7679283dc329c7c354d97fe9fc46b3f98c8e5a5cac6f5e6c'},
 'results_radio_native_v2_control_integration_20261002a/resource-finalization-isolated-focused-tests.log': {'bytes': 2425,
                                                                                                            'git_blob_sha': '1de7ec364fffec5bc2ae0a8ec39e5948cdf3f1a2',
                                                                                                            'sha256': 'e28709303af14f25546933dfda9da8bbdcc17160c157232d16b8a51522eb266d'},
 'results_radio_native_v2_control_integration_20261002a/resource-finalization-unit-integration-summary.json': {'bytes': 2292,
                                                                                                               'git_blob_sha': '6c2948184e81e5ce5c5cd1d436b6d16fdc5ccfe8',
                                                                                                               'sha256': 'd3f6f1d506170fe9f89f87a0a10a9987c6b1205b06426b0b065961781cb439d2'},
 'results_radio_native_v2_control_integration_20261002a/review_control_integration.py': {'bytes': 17463,
                                                                                         'git_blob_sha': '51f03a0b4c375aa4c70af1f1ebcb834a9879e6ac',
                                                                                         'sha256': '8abfbabf0bee01cdc282969f5e0de0de7657b8b05041c8b043d538ec59b16edb'},
 'results_radio_native_v2_control_integration_20261002a/run_adjacent_suite.py': {'bytes': 9856,
                                                                                 'git_blob_sha': 'ca1a5e7d44aec125a130597ad13b80a6d1d0cb7c',
                                                                                 'sha256': '4bbae05ef13983c0cbe84355e24770eeb7d44c7166516dc72000d890e4126f8a'},
 'results_radio_native_v2_control_integration_20261002a/source-receipt-tests-attempt1.json': {'bytes': 2827,
                                                                                              'git_blob_sha': '27599384e85f98b207ae8c5d2437c074d4983805',
                                                                                              'sha256': 'c0034580faa73a77161c81192098175e9531661001334513c7efaaf0e5e9de5b'},
 'results_radio_native_v2_control_integration_20261002a/source-receipt-tests-attempt1.stderr.log': {'bytes': 2943,
                                                                                                    'git_blob_sha': '15908edf640bf3e07118cfc59ee3edeaa8ee1ecb',
                                                                                                    'sha256': '65c39d696077ee3c563027a2c5c09cf737f94376bc0b88f22e4157b75c6fc5cd'},
 'results_radio_native_v2_control_integration_20261002a/source-receipt-tests-attempt1.stdout.log': {'bytes': 0,
                                                                                                    'git_blob_sha': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
                                                                                                    'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-current-caller-mutation-probe.py': {'bytes': 3013,
                                                                                                           'git_blob_sha': 'd3d37c37899fa4114b888f3d22c8711f254ad80d',
                                                                                                           'sha256': '965fb0d7c6e004911fa7a853eda53ca587012dc6277254be10c98f1ef463f744'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-current-current-mutation-result.json': {'bytes': 905,
                                                                                                               'git_blob_sha': 'ecf9ba915a7bc7148515636ec4a4b4c11f8188b2',
                                                                                                               'sha256': '526b7435a06b4132d2336dba37d8c5ddcd9ec141857dfba8e4ec011ece11fdeb'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-current-finalizer-source.py': {'bytes': 79175,
                                                                                                      'git_blob_sha': '67c7cef2a0b42463b2b4e36f15bd9c6953610bbf',
                                                                                                      'sha256': 'b5e31f02fcef9499417bff59c2539e4ae58e3c6123dc7e9fa315d5cb830b1938'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-compact_control_launch-source.py': {'bytes': 34274,
                                                                                                                 'git_blob_sha': 'e01e07a1516f40fa8d74fb63b84fd269f40d70dd',
                                                                                                                 'sha256': '0db793b74b64f4b5f201d1c7d7e10f273eaf75623c6d4150033cf52f40e5cdf8'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-compact_eight_case_resource_fixture-source.py': {'bytes': 128291,
                                                                                                                              'git_blob_sha': 'e57bc2ebc782cdfcb6288d4f4770a6ed7e30d9f5',
                                                                                                                              'sha256': 'c1acc2e3f7148fecedec507d1fd8fabba8a85e1be3907945653ffd0aeaa7c5b4'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-control_activation-source.py': {'bytes': 20022,
                                                                                                             'git_blob_sha': '8dbbde2a375060c54e6628f23dd8b3f46c1ddbc2',
                                                                                                             'sha256': 'b0fc36e2ed4b925f0ff51e812b18c79ef8e8f3d93ea4f6091159dc6cfc0bfb6a'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-current-mutation-result.json': {'bytes': 915,
                                                                                                             'git_blob_sha': '1bb29ba44225c9b35a260d31873c627c1b66347a',
                                                                                                             'sha256': '9230b5d652d3fcd319d70191846c8aa3f82292199cdebfbdd522332c32a3420a'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-general-join-result.json': {'bytes': 3164,
                                                                                                         'git_blob_sha': '3884e50c735140b944bdb6d3f2f3e78efc1c6e7d',
                                                                                                         'sha256': 'cb6bd7c90a722b6c8c2386495a1d7ef56d1642501935fb3f52cf062276c3279c'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-held-plan-selection-result.json': {'bytes': 1010,
                                                                                                                'git_blob_sha': 'fae52590505b931bc794821686ce379d811e3195',
                                                                                                                'sha256': 'f043e0f1a152b888cbf7dd13ffbee7dac7b29dfb19a08d9ff010cf1f6170de6a'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-historical_observation-source.py': {'bytes': 13863,
                                                                                                                 'git_blob_sha': 'cc0d5197c1a9756a82c1b383f7cf2d82a55bdd60',
                                                                                                                 'sha256': 'f725ff94a2ff8f375fec1e477e0cb20902d179e6d43e7a6b8fa649f282b1a008'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-historical_storage-source.py': {'bytes': 21869,
                                                                                                             'git_blob_sha': 'a17a72f4da8484a6edb0f2de22bad66c2dbe06c8',
                                                                                                             'sha256': '37d7225a9b24ee0de6002653d4676417b0b2befb5ce32cd071719fc01694d717'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-nofollow-result.json': {'bytes': 3577,
                                                                                                     'git_blob_sha': 'cc6141e6e7c3564845d2818d0b74e47d588a8973',
                                                                                                     'sha256': '89a9b3109eb473b82a80e089417656cbab8fed3d2976619d27ac5c25e2745ce0'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-process_tree_supervisor-source.py': {'bytes': 82676,
                                                                                                                  'git_blob_sha': '019c31cf43fb926b46f23ef26f3431b8e3147337',
                                                                                                                  'sha256': '897cdba99e28edaf64541a8af43674954bb1bf19c872d5b45f8c033d374c3881'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-resource_finalization-source.py': {'bytes': 79175,
                                                                                                                'git_blob_sha': 'f89c826311f53d516ceb71e2b0d27a4eedffcd15',
                                                                                                                'sha256': '2b01fe89d65f0243d274ca290c45432c09841e1997559f601f544ef1cc174679'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-review.json': {'bytes': 15841,
                                                                                            'git_blob_sha': '2ca966066fe0aa8baa7f7d63d1d51dc777a4c38f',
                                                                                            'sha256': 'f84f52b9b3ba542fbf009d1f7ba5dcc244070ebe5aac56015a07578a8c11f5b8'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-root-contract-result.json': {'bytes': 3362,
                                                                                                          'git_blob_sha': 'dc0a5636153819911e720f9dab279b9c088eb0db',
                                                                                                          'sha256': '82df220755e9a47b7d162d431c83192bd795e6ba1be34158ca99a40c04450628'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-sampled-named-metadata-result.json': {'bytes': 1104,
                                                                                                                   'git_blob_sha': '42b2660e7a86156e02e1afa67d797d7fc1175237',
                                                                                                                   'sha256': 'fe40ba02f5ac1fbc37f2607d8262846313ada2998c20f22370acf801788cc117'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-final-worker_admission-source.py': {'bytes': 77783,
                                                                                                           'git_blob_sha': 'f998b2fc9860573315a9b8783fca39c631c9f708',
                                                                                                           'sha256': '41e147d00488bb00c8be4825d26e964857b5f3841f07d3f908ad112e133c8fa1'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-finalize.py': {'bytes': 13027,
                                                                                      'git_blob_sha': '4b5f3f5e25274cc136d22fda9aa740d2e7a46a10',
                                                                                      'sha256': 'a0dac0d5cc5ec2714b4bf3b5b9d8ecd8d2354f9d569f7b4bf4c253adf5e95b10'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-first-sampled-named-metadata-result.json': {'bytes': 1099,
                                                                                                                   'git_blob_sha': 'a8c9713552162e28b52e23dc68d24cc98cb2b8a7',
                                                                                                                   'sha256': 'de5f14093fc39ceee8a14cdc1316d0d59466f607958904e2166afbed438aa0e3'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-first-sampled-supervisor-source.py': {'bytes': 82676,
                                                                                                             'git_blob_sha': '6fd3a6a8f903cdf69358dc49617f62747185db21',
                                                                                                             'sha256': '0e01c198660736b6400e61f74aa690c97594c1421221bb0095f0eeebf45b651b'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-fixed-held-plan-selection-result.json': {'bytes': 1023,
                                                                                                                'git_blob_sha': 'f907339ff77c02cdd96d0028327c0e9452981e23',
                                                                                                                'sha256': 'c766ba5ad3d9534072c96e4ff9827061b0e145af8315ec28c3da2dc011266154'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-general-join-probe.py': {'bytes': 7412,
                                                                                                'git_blob_sha': 'a95e1c5f751986194c13ef4db4612a897f8c0830',
                                                                                                'sha256': '94ba8c5402319f092b615384865ab89e963fa825680b54d0e9b09bf5787e8191'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-held-plan-selection-probe.py': {'bytes': 2560,
                                                                                                       'git_blob_sha': '3bbd7eea08dc4575a49dbe03466ba40aca03dc1d',
                                                                                                       'sha256': 'e949c54e37d22f1f3f6116764352a52a9a206124d950844707a79a55c6b8a0ab'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-initial-historical_observation-source.py': {'bytes': 13863,
                                                                                                                   'git_blob_sha': 'cc0d5197c1a9756a82c1b383f7cf2d82a55bdd60',
                                                                                                                   'sha256': 'f725ff94a2ff8f375fec1e477e0cb20902d179e6d43e7a6b8fa649f282b1a008'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-initial-historical_storage-source.py': {'bytes': 21869,
                                                                                                               'git_blob_sha': 'a17a72f4da8484a6edb0f2de22bad66c2dbe06c8',
                                                                                                               'sha256': '37d7225a9b24ee0de6002653d4676417b0b2befb5ce32cd071719fc01694d717'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-initial-nofollow-result.json': {'bytes': 3579,
                                                                                                       'git_blob_sha': 'e7510cf4043c838db9ec21d4dc984c6fb9078d5a',
                                                                                                       'sha256': '061b38c4dd7fb44a15219622a185aad36c5a08abd1cbcb69f1515adea5762cce'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-initial-root-contract-result.json': {'bytes': 3364,
                                                                                                            'git_blob_sha': '9154f9ddb34bf1e1b9debe4ad120e269034ae83b',
                                                                                                            'sha256': 'f6f17932402a89eddeb19c1b091c69fdae24086809e0a353763672e426eafa08'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-nofollow-probe.py': {'bytes': 4672,
                                                                                            'git_blob_sha': 'a80382ab439cd02b3c95ab4161113de7ea43199b',
                                                                                            'sha256': '6e4d3a24501e5b521009a715a83f01c5dd36e77d22ad8503bd8732f9fa8effcd'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-original-current-mutation-result.json': {'bytes': 903,
                                                                                                                'git_blob_sha': '37032004bc8c8fab949a5b532c90c2562fd91ef5',
                                                                                                                'sha256': '636c0221f20aa63c68a8cc0f267099979334c0202f4b1e41a57eaacc4e437e7e'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-original-finalizer-source.py': {'bytes': 78737,
                                                                                                       'git_blob_sha': 'f67983c3bc76820b49ab435dbc3f65edb6a9498f',
                                                                                                       'sha256': '0511627e8b45b696d549123a19b27fd8afa4528647981cd162cf2a83810c9a92'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-original-general-join-result.json': {'bytes': 3155,
                                                                                                            'git_blob_sha': '39946956bca2c8ead509980048513750b8bf65a5',
                                                                                                            'sha256': '8e1a255617fad1c2d2af7796d7e6b7b2bb1f673f40c3445d79bc37da99c9b023'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-original-held-plan-selection-result.json': {'bytes': 1023,
                                                                                                                   'git_blob_sha': 'd8fc596e33b2dab476326d7b6b50fadddfe3c2b0',
                                                                                                                   'sha256': '3ba7be4e876e760ac6a26e6f8e29efde91edba3ee9bbb57c38ceb5689fc26f9c'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-precreated-quota-attempt-1.json': {'bytes': 2330,
                                                                                                          'git_blob_sha': 'b8ee7d4878d577770ac5d953bac26d3f935b70e1',
                                                                                                          'sha256': '73ccdf46a2ab431af817b02a86feb1a18a6abaf7994c03561c6f418b94d6c428'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-precreated-quota-attempt-1.log': {'bytes': 193,
                                                                                                         'git_blob_sha': '7a792059ca8e765ddcfbb26300b286523ef55834',
                                                                                                         'sha256': 'de473b2bd560f9b3ef8e855ef725c7ea8c33de1d541c662fe33789efbd1de4f9'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-precreated-quota.json': {'bytes': 2329,
                                                                                                'git_blob_sha': 'e2c63ff9df563ac2fd5ab0d4b3705678962a62e7',
                                                                                                'sha256': 'c7fa35b006c46a1d6ba83aa97580059b32d6bf6f93fd7716d51326bae78255f5'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-precreated-quota.log': {'bytes': 193,
                                                                                               'git_blob_sha': '7a792059ca8e765ddcfbb26300b286523ef55834',
                                                                                               'sha256': 'de473b2bd560f9b3ef8e855ef725c7ea8c33de1d541c662fe33789efbd1de4f9'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-precreated-quota.py': {'bytes': 9089,
                                                                                              'git_blob_sha': '45588c3e652a5675c6f1abc80f4fe92293bc2932',
                                                                                              'sha256': '27ac25dd816b07e32568dd50b8772a124bf169bafe8cf28326c203256254995d'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-reviewed-compact_control_launch-source.py': {'bytes': 33979,
                                                                                                                    'git_blob_sha': '2d37d7be633073ae35ddf2335d46d0ca5dae9439',
                                                                                                                    'sha256': '530de9c15c0fc5402b87588a4068a0feb869a7f234ca8e3fdda27e136c4929c7'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-reviewed-compact_eight_case_resource_fixture-held-plan-source.py': {'bytes': 128291,
                                                                                                                                           'git_blob_sha': 'e57bc2ebc782cdfcb6288d4f4770a6ed7e30d9f5',
                                                                                                                                           'sha256': 'c1acc2e3f7148fecedec507d1fd8fabba8a85e1be3907945653ffd0aeaa7c5b4'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-reviewed-compact_eight_case_resource_fixture-quota-source.py': {'bytes': 128081,
                                                                                                                                       'git_blob_sha': 'cb3a9ae3f028d83e177f39c9a53cc063c91aad94',
                                                                                                                                       'sha256': 'caca109cbd029f56c05861df183371349dd58f9c6ed0b96aedb8a7960a3feb30'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-reviewed-compact_eight_case_resource_fixture-source.py': {'bytes': 127332,
                                                                                                                                 'git_blob_sha': '46e93570dc468940dca51031222a45805899f2a9',
                                                                                                                                 'sha256': 'be276219225dd98d5eb2e917271a6859232cceb6ac8d505a92536207cfb0ac7b'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-reviewed-control_activation-source.py': {'bytes': 20022,
                                                                                                                'git_blob_sha': '8dbbde2a375060c54e6628f23dd8b3f46c1ddbc2',
                                                                                                                'sha256': 'b0fc36e2ed4b925f0ff51e812b18c79ef8e8f3d93ea4f6091159dc6cfc0bfb6a'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-reviewed-process_tree_supervisor-quota-source.py': {'bytes': 82676,
                                                                                                                           'git_blob_sha': '019c31cf43fb926b46f23ef26f3431b8e3147337',
                                                                                                                           'sha256': '897cdba99e28edaf64541a8af43674954bb1bf19c872d5b45f8c033d374c3881'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-reviewed-process_tree_supervisor-source.py': {'bytes': 72304,
                                                                                                                     'git_blob_sha': '14013584df0c00387cf254682c84e0a95f28c47f',
                                                                                                                     'sha256': 'ce089dc2fbfbf5a965fea1ee5143683019792ff81a418bfbea0927632e923d5a'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-reviewed-worker_admission-history-first-source.py': {'bytes': 77783,
                                                                                                                            'git_blob_sha': 'f998b2fc9860573315a9b8783fca39c631c9f708',
                                                                                                                            'sha256': '41e147d00488bb00c8be4825d26e964857b5f3841f07d3f908ad112e133c8fa1'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-reviewed-worker_admission-source.py': {'bytes': 77783,
                                                                                                              'git_blob_sha': 'a3fe93b7c28885b56efecb72c99595ea53e80dca',
                                                                                                              'sha256': '4c89bf5482554a1568f2c60e3d9dd8905e11d28407417edbf465eb6749214819'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-root-contract-probe.py': {'bytes': 4798,
                                                                                                 'git_blob_sha': '663d147ca0ee574e63ef6c170bbc3812dfbd274f',
                                                                                                 'sha256': '4c032233b8416a7d3c7d5bceaf5811e1e256873ff9f215f50a217fbb7726bbb7'},
 'results_radio_native_v2_control_integration_20261002a/storage-review-sampled-named-metadata-probe.py': {'bytes': 2660,
                                                                                                          'git_blob_sha': '28fd0599f1813728dd508343e11db4435ed66e38',
                                                                                                          'sha256': '14f5f89f51c701abd5b7a291098a7c90d783799c125a8a8beded0e9d55e7fbce'},
 'results_radio_native_v2_control_integration_20261002a/supervisor-root-propagation-isolated-tests-attempt-2.log': {'bytes': 21374,
                                                                                                                    'git_blob_sha': 'dfd578424d28573a50cb28349484a1a7da0e019c',
                                                                                                                    'sha256': '81651181bd0654f3bf07d8de5785eece58a05ebaec7096e999895e0bc65208f7'},
 'results_radio_native_v2_control_integration_20261002a/supervisor-root-propagation-isolated-tests-attempt-3.log': {'bytes': 10425,
                                                                                                                    'git_blob_sha': '6afadca2396007d6d22fc179c67b11b573a05147',
                                                                                                                    'sha256': '8d2f9d789fd12e6040ef45d91b2ed555761dcb33444d708d73b0791c922dafce'},
 'results_radio_native_v2_control_integration_20261002a/supervisor-root-propagation-isolated-tests.log': {'bytes': 15680,
                                                                                                          'git_blob_sha': '572761b96cc2346e4a0271a703452f8ae7014bbb',
                                                                                                          'sha256': '493f26c120f6135a452e5beee00e0564fe856ebcd58b0c980d757cd72f39ecd5'},
 'results_radio_native_v2_control_integration_20261002a/verify_preparation.py': {'bytes': 12835,
                                                                                 'git_blob_sha': 'f410b53edbc45a494ad68a19e8c150798470a14f',
                                                                                 'sha256': 'aeff9f7b8ec40cc850385c4db4a292f474fbdaa55efcf14d22799025a14ad851'},
 'results_radio_native_v2_control_integration_20261002a/worker-admission-in-progress-missing-helper-test.json': {'bytes': 881,
                                                                                                                 'git_blob_sha': '05b4b61ba868eec1d64b2377073b3418403b66b0',
                                                                                                                 'sha256': '2144b64d8072f94cc0218ace07ad54f2e0f8f25c62ba016debea99d5783b941e'},
 'results_radio_native_v2_control_integration_20261002a/worker-admission-in-progress-missing-helper-test.log': {'bytes': 127066,
                                                                                                                'git_blob_sha': '04be60536cc2148e0381f8261f08024fbb5728ed',
                                                                                                                'sha256': 'b70a794607de09994359af5aa1c047a3bc1a6d6b99494227582838dafc4b675a'},
 'results_radio_native_v2_control_integration_20261002a/worker-root-history-attempt-1-tests.log': {'bytes': 3129,
                                                                                                   'git_blob_sha': '17c278d74ee5fadbc932188f9f4b49c5be284d5a',
                                                                                                   'sha256': '736a93cbf9980014987565e39156b95184ca7c916156e944a4b241dea74a1e76'},
 'results_radio_native_v2_control_integration_20261002a/worker-root-history-focused-tests.log': {'bytes': 2101,
                                                                                                 'git_blob_sha': '7aad3d454f1515a9efae9bdfb9a99af436d6bcc0',
                                                                                                 'sha256': '69ff39323ba85cf45f08759581d7f6064ec39968e6bc8a6098c2c28825b24990'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-manifest.json': {'bytes': 778,
                                                                                                                'git_blob_sha': '822d1cf7a3392036c691319d38b55eb847f4af58',
                                                                                                                'sha256': 'f0281ae6b64015c7aaea5a634d58c69e123609f1d0bf26886f96f57d18267aee'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-observation.json': {'bytes': 1200,
                                                                                                                   'git_blob_sha': '2156f005b27b98dd8244f21d7f35b1ce8afdc086',
                                                                                                                   'sha256': 'c96bc568502bbf14e2fe3ad9946dddac258e20d047008d4c4f3ed494c53558e1'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-spend-observation.json': {'bytes': 1293,
                                                                                                                         'git_blob_sha': '6a6457cf5749d5dc9647562c338d8d30a05280af',
                                                                                                                         'sha256': '56a445db080250a7e39f17d18dd0f7b57a57d93f34664504410335abedfbbf05'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-manifest.json': {'bytes': 42900,
                                                                                                               'git_blob_sha': '066ff63db3b05c8330c1a4da3c9bf31229a6cea7',
                                                                                                               'sha256': '6b3ce36a0e70169a4f97a57b60b6ef3abd4dbed06f90c83f8eb71baf71fea890'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-observation.json': {'bytes': 55112,
                                                                                                                  'git_blob_sha': 'ab7c8086869776204284fa9ba07cd8dfa95bca62',
                                                                                                                  'sha256': '02fdb297790aad0d049bb006b11bf1fa1471e09106fb5ac09cf6c178646034cd'},
 'results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json': {'bytes': 81935,
                                                                                              'git_blob_sha': '80155f3880be4040e24ea84288b9b74eab5cb1b3',
                                                                                              'sha256': 'f49912dda98e557fce3991c141169bd207306e54317fffc07c107c8a99e14fb7'},
 'scripts/radio_native_v2_activation_environment.py': {'bytes': 11741,
                                                       'git_blob_sha': '31fc8d86740367196e53f0035efba20224c981fd',
                                                       'sha256': '059003934a8b51c544f72b488c41c19a6067c0ffb0e65c31afc6eacd35d76bfd'},
 'scripts/radio_native_v2_broker_host.js': {'bytes': 32557,
                                            'git_blob_sha': '3339de9e866e36a96c1b13d5f335881cc2e6e2b5',
                                            'sha256': '29e7954f78be92e3af3cd2bdbf1f5449138e35e3839a923fbc9ceafb0a0d9c7f'},
 'scripts/radio_native_v2_caller_tail.py': {'bytes': 9215,
                                            'git_blob_sha': '79e702c88cf9fafdc63fd3e6745e651d0ade453c',
                                            'sha256': '8eb1d089f6b9f869f0aecb020a9d7fdf638ce9c3c666b208e8d227795a7a041c'},
 'scripts/radio_native_v2_compact_control_launch.py': {'bytes': 34274,
                                                       'git_blob_sha': 'e01e07a1516f40fa8d74fb63b84fd269f40d70dd',
                                                       'sha256': '0db793b74b64f4b5f201d1c7d7e10f273eaf75623c6d4150033cf52f40e5cdf8'},
 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py': {'bytes': 128291,
                                                                    'git_blob_sha': 'e57bc2ebc782cdfcb6288d4f4770a6ed7e30d9f5',
                                                                    'sha256': 'c1acc2e3f7148fecedec507d1fd8fabba8a85e1be3907945653ffd0aeaa7c5b4'},
 'scripts/radio_native_v2_compact_preparation_audit.py': {'bytes': 25154,
                                                          'git_blob_sha': '796e83505c2aec101d2ab58325856e3e2db972dc',
                                                          'sha256': '8a7711b93cd520fb6f9ffc634722de3ff47eb8f03b899145bda443c77c111e05'},
 'scripts/radio_native_v2_compact_run_verifier.py': {'bytes': 22556,
                                                     'git_blob_sha': '4868b7c6725dde39530e7ec1f204ab1b39dd4545',
                                                     'sha256': '689262de053151f46423feee965e8a2aa0f4205ee488f318ffbfbc683026720d'},
 'scripts/radio_native_v2_control_activation.py': {'bytes': 20022,
                                                   'git_blob_sha': '8dbbde2a375060c54e6628f23dd8b3f46c1ddbc2',
                                                   'sha256': 'b0fc36e2ed4b925f0ff51e812b18c79ef8e8f3d93ea4f6091159dc6cfc0bfb6a'},
 'scripts/radio_native_v2_historical_observation.py': {'bytes': 13863,
                                                       'git_blob_sha': 'cc0d5197c1a9756a82c1b383f7cf2d82a55bdd60',
                                                       'sha256': 'f725ff94a2ff8f375fec1e477e0cb20902d179e6d43e7a6b8fa649f282b1a008'},
 'scripts/radio_native_v2_historical_storage.py': {'bytes': 21869,
                                                   'git_blob_sha': 'a17a72f4da8484a6edb0f2de22bad66c2dbe06c8',
                                                   'sha256': '37d7225a9b24ee0de6002653d4676417b0b2befb5ce32cd071719fc01694d717'},
 'scripts/radio_native_v2_invocation_spending.py': {'bytes': 20163,
                                                    'git_blob_sha': '7a1c28ae6e373d8c37468ae765c8222501143e7a',
                                                    'sha256': 'd6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'},
 'scripts/radio_native_v2_local_courier.js': {'bytes': 26823,
                                              'git_blob_sha': '2e14407f8a6a1cfd5472e1abceac1b5d7e856724',
                                              'sha256': '7cd6ffad2b6bb0ccbd9d69809800a08006af59f13a3f57e333a36a3a68cd5a1f'},
 'scripts/radio_native_v2_local_git.js': {'bytes': 16038,
                                          'git_blob_sha': '1d4868ed665c3c5202054ea52f7f0a28c6076175',
                                          'sha256': '2c81f7c418c3f7fef1206f82a3d49eb9acc962b2b1a7391c5a689d6b5389d09e'},
 'scripts/radio_native_v2_local_transport.js': {'bytes': 53229,
                                                'git_blob_sha': '390253a67ee1bc6f59c406c9d3854186f57e0679',
                                                'sha256': '6c6196dbe22d8e1edf8d05057f601a29cc47b39024186aec5354ed7b204ac46d'},
 'scripts/radio_native_v2_process_tree_supervisor.py': {'bytes': 82676,
                                                        'git_blob_sha': '019c31cf43fb926b46f23ef26f3431b8e3147337',
                                                        'sha256': '897cdba99e28edaf64541a8af43674954bb1bf19c872d5b45f8c033d374c3881'},
 'scripts/radio_native_v2_prospective_spending.py': {'bytes': 22296,
                                                     'git_blob_sha': '3572074fffdad17bba69a54bcbe8f44ef2f8f7ed',
                                                     'sha256': '189da9f870628573e85ae6943a63d79b1390fce0aee8a04e003318cc506e895f'},
 'scripts/radio_native_v2_qualified_courier_fixture.js': {'bytes': 29111,
                                                          'git_blob_sha': '76681a3a38deb9a434f1abcbea6dae514ff01c68',
                                                          'sha256': '21b6b622c51387103c53c44e390a9bbd80e2d2d967011de508f975ca7e35bd34'},
 'scripts/radio_native_v2_qualified_tool_courier.js': {'bytes': 17271,
                                                       'git_blob_sha': '95bfa047d5e43e3bdf8fa0d52d69ff84652d33ec',
                                                       'sha256': '8f9c90841eb49c383d6d9a4e63bdf6fc5441a1ec063af60a77afe74b99ad4db9'},
 'scripts/radio_native_v2_resource_finalization.py': {'bytes': 79175,
                                                      'git_blob_sha': 'f89c826311f53d516ceb71e2b0d27a4eedffcd15',
                                                      'sha256': '2b01fe89d65f0243d274ca290c45432c09841e1997559f601f544ef1cc174679'},
 'scripts/radio_native_v2_runner_freeze.py': {'bytes': 24313,
                                              'git_blob_sha': 'c140f9fdfb04a42106cbe0932abf17b946a99b84',
                                              'sha256': '74ea2fee48eccf6e74a7b3f34517c0c0ccb50ff9abaacd57ab0a187acd24482b'},
 'scripts/radio_native_v2_runtime_custody.py': {'bytes': 22519,
                                                'git_blob_sha': 'e2b2049b6af1e0586404867534769dfaf8f6cb1a',
                                                'sha256': 'd0cd311c1615a2c299b101ca75b98ba2412b41bb1cfd668725461e4d307fb0b5'},
 'scripts/radio_native_v2_tool_courier_client.js': {'bytes': 19274,
                                                    'git_blob_sha': '53b0065cc34fb0a8e4c992c8fd0e8656ccd5ca9d',
                                                    'sha256': '5240193fb91c7f5f5bfe46dd0953ebfb7cc93bbd6377b4c278f0cae874b4ec70'},
 'scripts/radio_native_v2_worker_admission.py': {'bytes': 77783,
                                                 'git_blob_sha': 'f998b2fc9860573315a9b8783fca39c631c9f708',
                                                 'sha256': '41e147d00488bb00c8be4825d26e964857b5f3841f07d3f908ad112e133c8fa1'},
 'src/seti_repeater/__init__.py': {'bytes': 84,
                                   'git_blob_sha': 'e8da26af9e2db9faefb5a43407d2a640b77fec77',
                                   'sha256': '975f6dd9aa18bc0a69cb77599ce6096571d931abc52c281b766b36338f895a6d'},
 'src/seti_repeater/empty_null_radio.py': {'bytes': 6714,
                                           'git_blob_sha': 'dfeca0910062996884afefbbd37f6115831bcace',
                                           'sha256': '8c5c29efbd851a5504389d0adfcb244dbf3489a611785b7206ac552f13fdff6f'},
 'src/seti_repeater/native_v2_transport_contract_radio.py': {'bytes': 28951,
                                                             'git_blob_sha': 'b2d272b680ea038b36402b6e6209c50e22e22150',
                                                             'sha256': 'f6ad34a2c242e79331763f544482d4353328d80d8a9d9956f9979d498ed16a93'},
 'tests/test_radio_native_v2_activation_environment.py': {'bytes': 4399,
                                                          'git_blob_sha': '050561a9aeca10bf3bcc04f3369836a1536a2ccb',
                                                          'sha256': 'd796199d089df343153045a3ec65a76820f519a3d5c1520b1cffa9ca26bf2c1e'},
 'tests/test_radio_native_v2_compact_control_launch.py': {'bytes': 25140,
                                                          'git_blob_sha': '5b55467239fecfc3187c744f08d8702110f3f3fa',
                                                          'sha256': 'c30c07169f3d9a8ac798a97366e46be9776b010eb6c76fa44bc37696d086a5b0'},
 'tests/test_radio_native_v2_compact_eight_case_resource_fixture.py': {'bytes': 70396,
                                                                       'git_blob_sha': 'fc3cacba3bfdfdf5cf7e565cdd6d9fe8c7b75f4a',
                                                                       'sha256': 'c9a63b2afbc67f3a284c4f7d3d0b8f94a0d61b53066de3c848b1e0aab657481f'},
 'tests/test_radio_native_v2_compact_preparation_audit.py': {'bytes': 25229,
                                                             'git_blob_sha': 'be6bca3b257d17c706f5d9b913cdbfe2764400da',
                                                             'sha256': '0fd9afaa711d85527cfb045be8f7278bd3dba8ab81f1060144e0f7c5b0b5609b'},
 'tests/test_radio_native_v2_control_activation.py': {'bytes': 26450,
                                                      'git_blob_sha': '9d5d2422ce66420336d0cf149e55bd9f4006dc86',
                                                      'sha256': '1f5792bd2c0b132cdc91d805cc87de7c81b639cc0226884da253e6042bed11ff'},
 'tests/test_radio_native_v2_historical_observation.py': {'bytes': 10538,
                                                          'git_blob_sha': 'dcc112ad7781b1fb790f14e15a4727826d7cc751',
                                                          'sha256': '32014dac5d6595d52a0ecf6fd868550048ea67493c10ec5a3e35f01640632c76'},
 'tests/test_radio_native_v2_historical_spending_join.py': {'bytes': 8596,
                                                            'git_blob_sha': '9902bf35eb18309e482cca3424ea889eeaa437a3',
                                                            'sha256': 'adce6f05c8be034fa3096eda3bfc8916fc5cd69b57cedcb5d29ad7b902b1eb55'},
 'tests/test_radio_native_v2_historical_storage.py': {'bytes': 18389,
                                                      'git_blob_sha': '0119d0658349c221e29a42d75d81774fdc14409a',
                                                      'sha256': '254dff57abb7e441d027f5a1c9de0fcbd69fac9f4aa547690e67d23580763aa8'},
 'tests/test_radio_native_v2_invocation_spending.py': {'bytes': 25088,
                                                       'git_blob_sha': '6edc01deecbcdb7d9a4666ef3e6fd9d1de47398f',
                                                       'sha256': 'f16c916d773dc69d635d1da31b3ba34c7ee505ca99dfb77783d6ec73d9bb76aa'},
 'tests/test_radio_native_v2_process_tree_supervisor.py': {'bytes': 58203,
                                                           'git_blob_sha': 'd668c9d29287c460818e45d0570b9d93401214fe',
                                                           'sha256': '758c528479557633713e1a5a4a5205e3c50626e8f9b12ba533b91427f35ebd86'},
 'tests/test_radio_native_v2_prospective_spending.py': {'bytes': 34588,
                                                        'git_blob_sha': 'd83543adfdaf130d419e590ea5f7ac86ce2b4195',
                                                        'sha256': '6ecb69ec6c1505803632498db098c4c99d82ff9b3e6df17da67da3b193bcdeb5'},
 'tests/test_radio_native_v2_resource_finalization.py': {'bytes': 71792,
                                                         'git_blob_sha': '483b824927529e14f6033a62b350f13d7f1afbe5',
                                                         'sha256': '21f70804b935352044c06c1301edab43e6cc4c5368fd9fdbd7a409dbc9fb6d83'},
 'tests/test_radio_native_v2_runtime_custody.py': {'bytes': 13050,
                                                   'git_blob_sha': '4098cdee84effa85baff8a5c0fccc441a50ce917',
                                                   'sha256': 'f333dd1ea5c054d642dc2f57c3f13a2e6e14a9019816fb973412aac1b6127428'},
 'tests/test_radio_native_v2_source_receipt.py': {'bytes': 18009,
                                                  'git_blob_sha': '60e01e3147dcd050e6e24f40643a32ad90ca81ce',
                                                  'sha256': '53072a921ce7ac72111d8f3f6ab226b3a207128da55acf5bc49a1053faa8996f'},
 'tests/test_radio_native_v2_worker_admission.py': {'bytes': 64985,
                                                    'git_blob_sha': '5e05c90262bde95d48beeef581e1490cb6a08ade',
                                                    'sha256': '64ca9542de17d7a230f4b1109e0f74c951e293ff28dc6b4bb4bc794985da163c'}}
ORIGINAL_BLOCKERS = ['The current runtime freeze, exact parent environment and bounded platform contract require one '
 'integrated activation-time recheck against a distinct immutable execution preread.',
 'Every source-generating worker must independently enforce the outer public-preread admission and '
 'materialized code/derived pins.',
 'An independent measurement harness must cover the material runner through final metadata fsync '
 'and process termination; the final authoritative disposition must follow all storage/time '
 'checks.',
 'Whole-scope timing and final shared storage reservations must include every preparation, '
 'observer, directory and finalization entry under original limits.',
 'Fresh prepared source and terminal identities must be explicitly audited against the frozen '
 'source domain, archive prefix and outer ordinal; host/native joins remain unqualified.']
ORIGINAL_LIMITS = {'case_calls': 64,
 'case_request_bytes': 50331648,
 'case_response_bytes': 67108864,
 'case_seconds': 600,
 'case_storage_bytes': 201326592,
 'rss_bytes': 536870912,
 'run_calls': 512,
 'run_request_bytes': 402653184,
 'run_response_bytes': 536870912,
 'run_seconds': 4800,
 'run_storage_bytes': 1610612736}
PROTECTED_ABSENT = (
    '.radio-native-v2-invocation-ledger-20261002c',
    'config/radio_native_v2_control_activation_20261002c.activate.json',
    'config/radio_native_v2_compact_control_launch_20261002c.launch.json',
    'results_radio_native_v2_compact_control_20261002c')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def raw_pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def exact(value, expected, label):
    if (type(value) is not type(expected) or value != expected
            or (type(expected) in (dict, list) and canonical(value) != canonical(expected))):
        raise ValueError('Exact ' + label + ' required')


def _relative(value):
    if (type(value) is not str or not value or value.startswith('/') or '\\' in value
            or len(value.encode()) > 4096 or re.search(r'[\x00-\x1f\x7f]', value)
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Canonical repository-relative path required')
    return value


def repository_root(value):
    # Require the independent literal before any candidate/proof file is opened.
    exact(os.fspath(value), ORIGINAL_ROOT, 'independently selected original repository root')
    return ORIGINAL_ROOT


def validate_pin(pin):
    if (type(pin) is not dict or set(pin) != {'bytes', 'sha256'}
            or type(pin['bytes']) is not int or not 0 < pin['bytes'] <= MAX_INPUT_BYTES
            or type(pin['sha256']) is not str or not re.fullmatch('[a-f0-9]{64}', pin['sha256'])):
        raise ValueError('Independent bounded raw-file pin required')
    return pin


def _directory_identity(info):
    if not stat.S_ISDIR(info.st_mode): raise ValueError('Ordinary nofollow directory required')
    return (info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)


def _open_parent(absolute):
    if (type(absolute) is not str or not absolute.startswith('/') or absolute == '/'
            or '\\' in absolute or any(part in ('', '.', '..') for part in absolute[1:].split('/'))
            or len(absolute.encode()) > 4096 or re.search(r'[\x00-\x1f\x7f]', absolute)):
        raise ValueError('Canonical absolute input path required')
    opened = []; chain = []
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW); opened.append(fd)
        chain.append((fd, None, None, _directory_identity(os.fstat(fd))))
        for name in absolute[1:].split('/')[:-1]:
            parent = fd; identity = _directory_identity(os.stat(name, dir_fd=parent, follow_symlinks=False))
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent); opened.append(fd)
            if _directory_identity(os.fstat(fd)) != identity:
                raise ValueError('Directory changed during pinned input open')
            chain.append((fd, parent, name, identity))
        return fd, absolute.rsplit('/', 1)[1], opened, chain
    except BaseException:
        for fd in reversed(opened): os.close(fd)
        raise


def _check_chain(chain):
    for fd, parent, name, identity in chain:
        if (_directory_identity(os.fstat(fd)) != identity or (parent is not None
                and _directory_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != identity)):
            raise ValueError('Pinned input directory binding changed')


def read_pinned(root, relative, expected):
    root = repository_root(root); relative = _relative(relative); validate_pin(expected)
    parent, name, opened, chain = _open_parent(root + '/' + relative)
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent); opened.append(fd)
        before = os.fstat(fd)
        key = lambda info:(info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != expected['bytes']:
            raise ValueError('Pinned sole-link regular input required')
        chunks = []; remaining = before.st_size+1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk: break
            chunks.append(chunk); remaining -= len(chunk)
        raw = b''.join(chunks)
        if (key(before) != key(os.fstat(fd)) or key(before) != key(os.stat(name, dir_fd=parent, follow_symlinks=False))
                or raw_pin(raw) != expected):
            raise ValueError('Input differs from independently pinned bytes or changed during read')
        _check_chain(chain)
        return raw
    finally:
        for fd in reversed(opened): os.close(fd)


def strict_json(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_INPUT_BYTES:
        raise ValueError('Bounded canonical JSON bytes required')
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result: raise ValueError('Duplicate JSON object key refused')
            result[key] = value
        return result
    def nonfinite(value): raise ValueError('Nonfinite JSON value refused')
    try: value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (UnicodeError, json.JSONDecodeError) as failure:
        raise ValueError('Valid UTF-8 JSON required') from failure
    if type(value) is not dict or canonical(value)+b'\n' != raw:
        raise ValueError('Exact canonical JSON object plus newline required')
    return value


def _hash_maps(freeze):
    for inventory, mapping in (
            ('repository_code_inventory', 'code_sha256s'),
            ('input_file_inventory', 'input_sha256s'),
            ('runtime_file_inventory', 'runtime_sha256s')):
        values = freeze.get(mapping)
        if type(values) is not dict or freeze.get(inventory) != sorted(values):
            raise ValueError('Exact complete freeze inventory/hash map required: ' + mapping)
        if any(type(digest) is not str or not re.fullmatch('[a-f0-9]{64}', digest) for digest in values.values()):
            raise ValueError('Exact frozen SHA256 values required')


def validate_material(plan, freeze, *, root):
    root = repository_root(root)
    exact(plan.get('schema'), PREREAD_SCHEMA.removesuffix('-public-preread')+'-prospective-plan', 'plan schema')
    exact(plan.get('namespace'), NAMESPACE, 'plan namespace')
    exact(plan.get('mode'), 'PROSPECTIVE_NOT_EXECUTED', 'plan mode')
    exact(plan.get('execution_status'), 'BLOCKED_PREPARATION_REVIEW', 'blocked plan status')
    exact(plan.get('invocation_repository_root'), root, 'plan independent original root')
    exact(plan.get('invocation_ledger_root'), root+'/.radio-native-v2-invocation-ledger-20261002c', 'separate c journal')
    exact(plan.get('execution_blockers'), ORIGINAL_BLOCKERS, 'original execution blockers')
    exact(plan.get('original_limits'), ORIGINAL_LIMITS, 'original limits')
    exact(plan.get('code_files'), MATERIAL_FILES, 'full 49 material file mapping')
    exact(plan.get('historical_storage_inputs'), HISTORICAL_FILES, 'literal nine historical input mapping')
    for key, wanted in AUTHORITY.items(): exact(plan.get(key), wanted, 'non-authorizing plan ' + key)
    for key in ('historical_storage_accounting_prepared', 'historical_storage_live_reobservation_required',
            'complete_runtime_freeze_required', 'public_immutable_preread_required'):
        exact(plan.get(key), True, 'required preparation ' + key)
    for key in ('historical_storage_lifetime_qualified', 'one_invocation_spending_enforced',
            'complete_resource_measurement_join_qualified', 'activation_guard_complete',
            'large_source_generation_admitted', 'large_inputs_generated', 'spent_control_rearmed'):
        exact(plan.get(key), False, 'blocked completion ' + key)
    exact(freeze.get('schema'), 'radio-native-v2-runner-broker-runtime-freeze-v1', 'freeze schema')
    exact(freeze.get('freeze_kind'), 'COMPLETE_RUNNER_BROKER_RUNTIME', 'complete freeze kind')
    exact(freeze.get('mode'), 'PROSPECTIVE_ENGINEERING_ONLY', 'freeze mode')
    exact(freeze.get('namespace'), 'radio-native-v2-engineering-20260930a', 'freeze namespace')
    for key in ('execution_authorized', 'reservation_authorized', 'scientific_execution_authorized',
            'restart_authorized', 'rng_authorized', 'transport_integration_qualified'):
        exact(freeze.get(key), False, 'non-authorizing freeze ' + key)
    exact(freeze.get('transport_qualification'), None, 'absent transport qualification')
    _hash_maps(freeze)
    for relative, wanted in MATERIAL_FILES.items():
        # Tests and archived JSON/Python inputs travel via input_sha256s;
        # ordinary current scripts/src travel via repository code_sha256s.
        mapping = freeze['input_sha256s'] if relative.startswith('tests/') or relative in HISTORICAL_FILES else freeze['code_sha256s']
        exact(mapping.get(relative), wanted['sha256'], 'correct freeze route for ' + relative)
    exact(freeze['input_sha256s'].get(PLAN_PATH), PLAN_PIN['sha256'], 'frozen raw plan input pin')


def validate_public_proof(proof):
    expected = {'schema': PROOF_SCHEMA, 'repository': REPOSITORY, 'branch': BRANCH,
        'commit': PREPARATION_COMMIT, 'tree': PREPARATION_TREE, 'parents': [PREPARATION_PARENT],
        'file_count': len(PUBLIC_FILES), 'raw_bytes': sum(row['bytes'] for row in PUBLIC_FILES.values()),
        'material_file_count': len(MATERIAL_FILES), 'all_material_files_verified': True,
        'all_content_and_git_blob_readbacks_match': True,
        'execution_authorized': False, 'scientific_execution_authorized': False,
        'whole_control_qualified': False, 'lifetime_accounting_proved': False,
        'protected_control_invocations': 0, 'telescope_reads': 0,
        'new_project_c_scope_journal_marker_launch_config_absent': True}
    if type(proof) is not dict or set(proof) != {*expected, 'files'}:
        raise ValueError('Exact bounded immutable preparation public-proof fields required')
    for key, wanted in expected.items(): exact(proof[key], wanted, 'immutable preparation proof ' + key)
    rows = proof['files']
    if type(rows) is not list or len(rows) != len(PUBLIC_FILES):
        raise ValueError('Exact 171 public file rows required')
    paths = []
    for row in rows:
        if type(row) is not dict or set(row) != {'path', 'bytes', 'sha256', 'git_blob_sha', 'content_matches', 'git_blob_matches'}:
            raise ValueError('Exact public raw content/Git blob row required')
        relative = _relative(row['path']); paths.append(relative)
        if relative not in PUBLIC_FILES: raise ValueError('Unexpected public preparation file')
        for key, wanted in PUBLIC_FILES[relative].items(): exact(row[key], wanted, 'public ' + relative + ' ' + key)
        exact(row['content_matches'], True, 'actual public content readback match')
        exact(row['git_blob_matches'], True, 'actual public Git blob readback match')
    exact(paths, sorted(PUBLIC_FILES), 'unique sorted complete public preparation files')
    for path, wanted in MATERIAL_FILES.items():
        actual = PUBLIC_FILES[path]
        exact({key: actual[key] for key in ('bytes', 'sha256')}, wanted, 'public material join')
    exact({key: PUBLIC_FILES[PLAN_PATH][key] for key in ('bytes', 'sha256')}, PLAN_PIN, 'public pinned plan')
    exact({key: PUBLIC_FILES[FREEZE_PATH][key] for key in ('bytes', 'sha256')}, FREEZE_PIN, 'public pinned freeze')


def build_preread(plan_raw, freeze_raw, proof_raw, *, root, expected_proof_pin):
    repository_root(root); validate_pin(expected_proof_pin)
    exact(expected_proof_pin, PROOF_PIN, 'independently retained public proof raw pin policy')
    if raw_pin(plan_raw) != PLAN_PIN or raw_pin(freeze_raw) != FREEZE_PIN:
        raise ValueError('Independent immutable plan/freeze raw pins differ')
    if raw_pin(proof_raw) != expected_proof_pin:
        raise ValueError('Independent caller raw public-proof pin differs')
    plan = strict_json(plan_raw); freeze = strict_json(freeze_raw); proof = strict_json(proof_raw)
    validate_material(plan, freeze, root=root); validate_public_proof(proof)
    return {'schema': PREREAD_SCHEMA, 'namespace': NAMESPACE,
        'plan_sha256': hashlib.sha256(canonical(plan)).hexdigest(),
        'complete_freeze_sha256': hashlib.sha256(canonical(freeze)).hexdigest(),
        'public_immutable_readback_verified': True, 'engineering_control_admitted': True,
        'code_files_verified': json.loads(canonical(MATERIAL_FILES)),
        'preparation_commit': PREPARATION_COMMIT, **AUTHORITY}


def require_protected_absent(root):
    root = repository_root(root)
    for relative in PROTECTED_ABSENT:
        parent, name, opened, chain = _open_parent(root + '/' + relative)
        try:
            try: os.stat(name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError: pass
            else: raise ValueError('Prospective c scope/journal/marker/launch must remain absent')
            _check_chain(chain)
        finally:
            for fd in reversed(opened): os.close(fd)


def write_exclusive(root, relative, raw):
    root = repository_root(root); relative = _relative(relative)
    if relative not in (OUTPUT_PATH, RECEIPT_PATH):
        raise ValueError('Only distinct c preread and its retained build receipt may be written')
    strict_json(raw)
    parent, name, opened, chain = _open_parent(root + '/' + relative)
    try:
        fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            created = os.fstat(fd)
            if not stat.S_ISREG(created.st_mode) or created.st_nlink != 1 or created.st_size != 0:
                raise ValueError('Fresh sole-link regular output descriptor required')
            position = 0
            while position < len(raw):
                written = os.write(fd, raw[position:])
                if written <= 0: raise OSError('Incomplete exclusive preread write')
                position += written
            os.fsync(fd)
            held = os.fstat(fd)
            key = lambda info:(info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
                info.st_uid, info.st_gid, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            if (held.st_dev != created.st_dev or held.st_ino != created.st_ino
                    or held.st_nlink != 1 or held.st_size != len(raw)
                    or key(held) != key(os.stat(name, dir_fd=parent, follow_symlinks=False))):
                raise ValueError('Held output descriptor differs from named fsynced output')
            os.lseek(fd, 0, os.SEEK_SET); chunks = []; remaining = len(raw)+1
            while remaining:
                chunk = os.read(fd, min(65536, remaining))
                if not chunk: break
                chunks.append(chunk); remaining -= len(chunk)
            if b''.join(chunks) != raw or key(held) != key(os.fstat(fd)):
                raise ValueError('Held output bytes changed after file fsync')
            os.fsync(parent); _check_chain(chain)
            if (key(held) != key(os.fstat(fd))
                    or key(held) != key(os.stat(name, dir_fd=parent, follow_symlinks=False))):
                raise ValueError('Named output binding changed through directory fsync')
        finally: os.close(fd)
    finally:
        for fd in reversed(opened): os.close(fd)


def run(action, *, root, expected_proof_pin):
    root = repository_root(root); require_protected_absent(root)
    plan_raw = read_pinned(root, PLAN_PATH, PLAN_PIN)
    freeze_raw = read_pinned(root, FREEZE_PATH, FREEZE_PIN)
    proof_raw = read_pinned(root, PROOF_PATH, expected_proof_pin)
    preread = build_preread(plan_raw, freeze_raw, proof_raw, root=root, expected_proof_pin=expected_proof_pin)
    held = {relative: read_pinned(root, relative, wanted) for relative, wanted in MATERIAL_FILES.items()}
    output_raw = canonical(preread)+b'\n'
    if action == 'build':
        # Precheck both outputs; a partial write/failure is retained, never reset.
        for relative in (OUTPUT_PATH, RECEIPT_PATH):
            try: os.lstat(root + '/' + relative)
            except FileNotFoundError: pass
            else: raise FileExistsError('Existing preread/build receipt must be retained')
        write_exclusive(root, OUTPUT_PATH, output_raw)
        exact(read_pinned(root, OUTPUT_PATH, raw_pin(output_raw)), output_raw, 'named preread after exclusive fsync')
    elif action == 'verify':
        exact(read_pinned(root, OUTPUT_PATH, raw_pin(output_raw)), output_raw, 'existing exact c preread')
    else: raise ValueError('Supported metadata action required')
    # Re-read held source bytes and all metadata after exclusive output fsync.
    for relative, wanted in MATERIAL_FILES.items():
        exact(read_pinned(root, relative, wanted), held[relative], 'unchanged held material after preread')
    exact(read_pinned(root, PLAN_PATH, PLAN_PIN), plan_raw, 'unchanged held plan')
    exact(read_pinned(root, FREEZE_PATH, FREEZE_PIN), freeze_raw, 'unchanged held freeze')
    exact(read_pinned(root, PROOF_PATH, expected_proof_pin), proof_raw, 'unchanged independently pinned public proof')
    require_protected_absent(root)
    exact(read_pinned(root, OUTPUT_PATH, raw_pin(output_raw)), output_raw, 'final named preread before receipt')
    receipt = {'schema': 'radio-native-v2-distinct-c-execution-preread-build-receipt-v1',
        'status': 'DISTINCT_C_PREREAD_BUILT_EXECUTION_BLOCKED' if action == 'build' else 'DISTINCT_C_PREREAD_VERIFIED_EXECUTION_BLOCKED',
        'repository_root': root, 'preparation_commit': PREPARATION_COMMIT,
        'preparation_tree': PREPARATION_TREE, 'plan_raw_pin': PLAN_PIN, 'complete_freeze_raw_pin': FREEZE_PIN,
        'public_proof_path': PROOF_PATH, 'independently_supplied_public_proof_raw_pin': expected_proof_pin,
        'public_gets_performed_by_builder': 0,
        'public_proof_authentication': 'Independent caller raw pin plus fixed immutable metadata, 171 content/blob rows and all 49 material joins; the builder makes no remote calls.',
        'public_files_verified': len(PUBLIC_FILES), 'material_files_verified': len(MATERIAL_FILES),
        'historical_inputs_verified': len(HISTORICAL_FILES), 'held_material_unchanged': True,
        'output_path': OUTPUT_PATH, 'output_raw_pin': raw_pin(output_raw),
        'output_canonical_sha256': hashlib.sha256(canonical(preread)).hexdigest(),
        'preread_field_count': len(preread), 'original_execution_blockers': ORIGINAL_BLOCKERS,
        'new_tool_not_part_of_frozen_production_inventory': True,
        'metadata_only': True, 'protected_control_invocations': 0,
        'prospective_c_scope_journal_marker_launch_absent': True,
        'whole_control_qualified': False, 'lifetime_accounting_proved': False, **AUTHORITY}
    if action == 'build': write_exclusive(root, RECEIPT_PATH, canonical(receipt)+b'\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'verify'))
    parser.add_argument('--repository-root', required=True)
    parser.add_argument('--proof-sha256', required=True)
    parser.add_argument('--proof-bytes', type=int, required=True)
    args = parser.parse_args()
    receipt = run(args.action, root=args.repository_root,
        expected_proof_pin={'bytes': args.proof_bytes, 'sha256': args.proof_sha256})
    print((canonical(receipt)+b'\n').decode(), end='')


if __name__ == '__main__': main()
