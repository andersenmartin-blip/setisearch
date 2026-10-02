# HD189733: prospective source, acquisition and trial admission matrix

## 2 October: metadata component implemented; admission stays blocked

[The integrated metadata preparation](RADIO_HD189733_METADATA_PREPARATION_2026-10-02_RESULT.md)
adds a pure constructor and separately callable validator, with 42 candidate
tests and an independent 42-test review passing. All 25 raw inputs / 749,088
bytes match retained local Git pins and now have
[fresh immutable public byte/Git-blob readback](results_radio_hd189733_metadata_preparation_20261002a/public-input-readback.json)
at `1468a19d2603bde2b491b5400a2d3cdf8954c69f`. The nine current source/acquisition
pins expose four old-contract gaps, including the changed search implementation.
Six scans, 288 distinct chunk identities and the exact 96-integration rational
clock are reconstructed under the unchanged 226.840273 Hz / linear ±4 Hz/s scope.
The three canonical outputs are a permanently blocked wrapper, admission sidecar
and pending provenance receipt; no active contract, certificate, allocation or
spectral authority is issued. All 42 metadata tests pass in the final **401-test
suite**, with zero failures/errors/skips and 944 unchanged source/test pins.
The prior 398-test observer-publication failure and post-test exclusive-alias
error remain retained with explicit byte-exact final selection. Fresh o capture
and independent audit pass under actual ten-value `-I -S -B`, covering 36 inputs,
927 repository code files and 1,366 runtime paths, with execution blocked.
Public input custody is verified; new component/output publication/readback,
intended source-runtime admission and scientific gates remain pending.
No spectrum, holdout, reserved native input or RNG value was opened/generated.
LS remains paused; stop 9 October without extension. The original audited design
below is preserved as the implementation's historical requirements, not a claim
that its future admission gates have passed.

## Original metadata-only design and immutable evidence audit

**Disposition: METADATA_ONLY_ADMISSION_DESIGN; TELESCOPE_ACCESS_BLOCKED.**
This report identifies the next source-contract work independently of the
compact-eight engineering result. It creates no contract, allocation, ledger,
trial, detector certificate or execution authority. No project module was
imported, no deterministic fixture was repeated, and no spectrum, holdout,
native input or random value was opened/generated for this report.

The immutable evidence checkpoint is science commit
`58e7a883bf8ccf7951e8365f658d7b6645f161e4`. The file hashes below are SHA256 of
the complete raw bytes at that commit, including original formatting/newlines.
Embedded content digests are identified separately. This is a read-only local
Git-blob audit, not a new independent public readback or a runtime measurement.
Published preparation and completed results remain unchanged.

## Fixed source and actual searched scope

HD189733/HIP98505, cadence **85030**, remains the selected independent
astronomical preparation. The original source inventory content digest is
`3a925af307f8083647c39aad6393b08a1c05a296d056eea251dd6487ccf6530f`.
All six archive files are in `AGBT16A_999_97/holding/`, on the same observing
date, with the following frozen order. The complete URLs, sizes, strong ETags,
coordinates, filters and header fields are in the pinned source preparation.
No new HEAD, range GET or archive request was made.

| Source label | Archive scan identity | Header start MJD | Strong ETag |
|---|---|---:|---|
| `epoch1_on` | `guppi_57464_59616_HIP98505_0003.gpuspec.0000.h5` | 57464.69 | `"5a9ec9c6-2f104c575"` |
| `epoch1_off` | `guppi_57464_59946_HIP98505_OFF_0004.gpuspec.0000.h5` | 57464.693819444445 | `"5a9eca2e-2f1297e44"` |
| `epoch2_on` | `guppi_57464_60276_HIP98505_0005.gpuspec.0000.h5` | 57464.69763888889 | `"5a9ecab0-2f0f3628d"` |
| `epoch2_off` | `guppi_57464_60606_HIP98505_OFF_0006.gpuspec.0000.h5` | 57464.70145833334 | `"5a9ecb49-2f0f552b3"` |
| `epoch3_on` | `guppi_57464_60936_HIP98505_0007.gpuspec.0000.h5` | 57464.70527777778 | `"5a9ecbf3-2f0b546f5"` |
| `epoch3_off` | `guppi_57464_61265_HIP98505_OFF_0008.gpuspec.0000.h5` | 57464.709085648145 | `"5a9ecc81-2f0c732f4"` |

The basename prefix omitted in this table is exactly
`spliced_blc02030405_2bit_`. Each scan has float32 shape
`[16,1,264503296]`, chunks `[1,1,1048576]`, sampling duration
17.986224128 seconds, `fch1_mhz=1876.46484375` and
`foff_mhz=-2.835503418452676e-06`. The declared filter tuple is
`[32008,1,[0,3,4,0,2],"bitshuffle; see https://github.com/kiyo-masui/bitshuffle"]`.
Decimal MJD displays are identifiers for the retained binary64 header numbers;
the future bank must retain their existing exact-rational clock interpretation,
not reconstruct its clock through rounded text. Three ON/OFF pairs within one
session do not become three independent observing dates.

| Role | Native extraction interval, half-open | Lowest/highest extracted channel centers, Hz | First/last scored carrier centers at first ON midpoint, Hz |
|---|---|---|---|
| Calibration | `[167215104,167280640)` | 1402140020.024552–1402325844.7410803 | 1402232817.5449278–1402233044.3852012 |
| Validation | `[164069376,164134912)` | 1411059742.5220742–1411245567.2386024 | 1411152540.0424500–1411152766.8827233 |
| Inactive pilot | `[159875072,159940608)` | 1422952705.852104–1423138530.5686321 | 1423045503.3724797–1423045730.2127530 |

Each extraction contains 65,536 channels, while each role scores only **81
reference carriers spanning 226.840273 Hz**. Nine support bins on each side
and sixteen 4096-channel normalization blocks retain their distinct roles.
The 288 source/time/feed/chunk identities across the three roles are disjoint
payload identities in one cadence, not new observing sequences. Extraction
width is not searched bandwidth, and synthetic calibration geometry creates
no right to acquire its telescope window.

Keep `neighbor9`, widths `[1,3,5,9,17,33,65,129]`, the four two/three-epoch
activity subsets, minimum active-epoch S/N 3 and sum stacking. The bank has 81
rate labels from −4 to +4 Hz/s in 0.1 steps in **recorded topocentric frequency
and header-clock time**. Its factor is `F(t)=1+r*t/C`; carrier `q` has actual
slope `q*r/C`. Zero drift remains included. Whole-cadence linear tracks are
the declared family; curved/jumping tracks, other rates, barycentric motion,
planetary completeness and flux/EIRP sensitivity are not established.

The pilot bank identity is
`fe8793a7a74bce951f047834551430109f534674fda13c7be8671ae01a4dc194`;
its factor-payload digest is
`867e816e18d3d98fc5cb4c08730670e33fa1068374c69001dbe1e6526df7c436`.
The separate window-identity contract's embedded content digest is
`64dfa0f50252a86953b45c112687da9386147c0e70ad0d2a686efc5592f05ffa`.
Arithmetic containment remains reusable evidence, not a recovery or admission
certificate.

## Audited input and interface pins

| Exact repository path | Raw bytes | File SHA256 |
|---|---:|---|
| [Original source preparation](config/radio_hd189733_source_preparation_20260927.json) | 9707 | `98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1` |
| [Six retained headers](results_radio_alternate_2026-09-27/attempt01/85030/headers.json) | 7876 | `7cbd606c9eb08a3d16401cb184180746eff408ee40972ec0f9921763cba8edf5` |
| [Metadata/proximity qualification](results_radio_alternate_2026-09-27/source_qualification.json) | 6023 | `f2d943f768a40538180b771d894bbff714ebb70d90d9d74bd09cfa8a7e57549d` |
| [Three-role geometry](results_radio_hd189733_geometry_2026-09-27/window_geometry.json) | 35420 | `92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6` |
| [Window-identity contract v2](results_radio_hd189733_geometry_2026-09-27/window_identity_contract_v2.json) | 2453 | `0ffbadfacb9de8dd92d3d32b07e97b5c6fb16143483c225cb25bd60439ebe226` |
| [Three receiver-bank records](results_radio_hd189733_receiver_2026-09-28/bank_records.json) | 7871 | `51c1fde64957720e98adc7ecc63209d9b2e406b57dcd790829677a1ceb76b7c8` |
| [Receiver arithmetic/containment](results_radio_hd189733_receiver_2026-09-28/arithmetic_and_containment.json) | 10575 | `02d1361e1537f1d74470cc5b5e336233ec5c266da92fb5b416ded17eb2cabd60` |
| [Codec fixture source profile](results_radio_hd189733_codec_2026-09-28/fixture01/source_profile.json) | 1477 | `58b41ebdd2d7e407fc2ae49f594811e38c199f4914d34d0fe8e318bb0936894a` |
| [Historical codec runtime](results_radio_hd189733_codec_2026-09-28/fixture01/runtime.json) | 3768 | `2b93524d831627186635963b48ed32ef3c02b6ed7d37d3a0a0ee68e53dfa7ac0` |
| [Codec postflight](results_radio_hd189733_codec_2026-09-28/postflight.json) | 3711 | `812713dfe264fcd41638b6e6c65f9d9e7595523be8f1e38bf2c59802b81b8874` |
| [Whole-cadence handoff postflight](results_radio_whole_cadence_handoff_2026-09-28/postflight.json) | 3244 | `316dde2f3572679701732369786116c80ed9c39f5e8cc918f2485816dcafefa9` |
| [Inactive 127/24 proposal](config/radio_whole_cadence_null_proposal_20260928.json) | 158717 | `45d8309c8b23eea56ddee15e829b96a3936dba98141f124bf97c4057f35993e2` |
| [Guarded reader](src/seti_repeater/source_radio.py) | 10344 | `d189028cacf05482a8b9a74a9544d30a1c45cd60f95784be5f06b2ce093e677f` |
| [Filter contract](src/seti_repeater/hdf5_filter_contract_radio.py) | 1651 | `65533ad8ead2bd7283beee9645a18b3a652a3ede50425573b64aaca69120e6a6` |
| [Preparation-only window binder](src/seti_repeater/window_identity_radio_v2.py) | 5709 | `fe9b4a8ffe84eae428a382a48fcc46030fad93c25375e05c80cb6c79e24f672a` |
| [Receiver-bank provenance constructor](src/seti_repeater/receiver_bank_radio.py) | 7958 | `5945d37eeb8948d0dae0917784ab7837f6d00da58c8294024e011989580b41bf` |
| [Durable acquisition entry](src/seti_repeater/acquisition_radio.py) | 18640 | `c98d65aa8d46ef8f4a1003dc55cfc542c7c63bde01272325dc1d1a7054fa8712` |
| [Native runner authority/transport interfaces](src/seti_repeater/native_v2_runner_radio.py) | 32076 | `06b45e93542b4f07918e0d35ecc13c6877ec8bf2d8110b77a06b1a8c2481ea59` |
| [Distinct whole-cadence downstream interface](src/seti_repeater/whole_cadence_downstream_radio.py) | 18301 | `aa7179d566840c3011f5f68cbb4b1fcecf1f544d2b0753ca3ee20228dda2c9d7` |

These are evidence and code-selection inputs. Neither a pinned file nor a
historical runtime hash proves that the eventual execution environment is
currently identical. The new contract needs its own complete, independently
verified code/input/runtime freeze and execution evidence.

## Present admission matrix

The actual `source_radio.load_contract(root,path,expected_sha256)` validates
the source envelope, implementation pins and geometry before considering the
three gates `pointing`, `prospective_protocol` and `codec_integration`.
`acquisition_radio.start_source_session(...)` performs these checks before
ledger publication or networking; `extract_source(...)` additionally requires
a `DurableBudget` bound to that exact contract, source inventory, limits and
reservation location. An explicit `spectral_access_authorized=True` argument
is also required; this report never supplies it.

| Boundary | Current evidence/state | Concrete new-contract requirement |
|---|---|---|
| Target, six scans, source identity | Metadata/proximity gate passed for the source inventory above. Pointing criterion is metadata/proximity, not an independently measured telescope pointing calibration. | Copy exact scan definitions, URL/size/ETag/header/filter identity and fixed pairing into a new contract; pin the source qualification. Identity/schema drift must stop acquisition without replacement. |
| Reader implementation closure | The old contract pins `source_radio.py` at `095f3e5f5d5d75ffcfbc6775a5f003241588d7b04c604ad2add429723680aaf8`, different from the guarded reader above. It omits the now-mandatory filter-contract dependency. | Bind every current `source_radio.IMPLEMENTATION_PATHS` entry, including the guarded reader and filter contract. The old contract cannot pass the present implementation-pin gate or be toggled to ready in place. |
| Extraction geometry | Original contract has `windows=[]`; role geometry and 288 disjoint identities exist separately. | Bind exact role windows, clock, normalization partition and window-identity digest. Keep pilot role inactive until its separate trial admission passes; no silent all-band or calibration-window telescope acquisition. |
| Window/bank provenance rebinding | `window_identity_radio_v2.build` requires the old preparation-only stage with `windows=[]`; window records and bank provenance bind the old source-contract file SHA. A new executable contract necessarily has different bytes. | Implement a distinct, reviewed metadata rebinding receipt: retain original source/window/bank pins as ancestry, prove identical six-scan/role/clock/factor semantics and bind the new executable-contract SHA explicitly. Do not feed the new contract to the old preparation binder or relabel old window/bank identities as current. |
| Codec and native source handoff | Codec fixture/runtime and deterministic codec-to-receiver/source-law handoff are completed component evidence. Original contract still says `codec_integration: not-qualified-for-this-source-contract`. | Pin source-shaped evidence, the exact filter guard, source/runtime/case/law receipt schemas and changed reader dependencies. A future gate receipt must name this new source inventory and executable freeze; fixture texture is not archive provenance or six independent scans. |
| HDF5/runtime | Original `hdf5_runtime=null`. Historical codec record gives Python 3.12.14, NumPy 2.3.5, h5py 3.16.0, HDF5 2.0.0 and hdf5plugin 7.1.0 plus 30 binary hashes. | Freeze the actual intended source runtime and dependency/loader closure; satisfy the existing exact `cfg['hdf5_runtime'] == source.runtime()` handoff. Version strings alone and an older ephemeral host inventory are insufficient. |
| Scientific detector certificate | 127/24 is `PROPOSED_NOT_ACTIVATED`. Completed empty-aware threshold/retention, physical and counting fixtures supply interface semantics only. | Independently bind a complete scientific execution/result certificate to the exact primary, ordered 127 reference identities, 24 evaluation recipes, law/family/context/translation and complete recovery/RFI/null outcomes. Preserve failures and incomplete cases; no Boolean gate copied from a test pass. |
| Real runner/transport | Compact8 is offline and uses mock connector/delivery operations. The measurable Actions publication component does not join the complete native worker/host/publication lifecycle. | A separately frozen qualified hosted runtime and actual controller/host/native-worker, durable raw-receipt/state, broker, publication/readback and complete original resource joins. `native_v2_runner_radio.validate_authority` requires the verified `COMPLETE_RUNNER_BROKER_RUNTIME` authority plus a separate immutable eight-case reservation. |
| Source-specific scientific protocol | Original `prospective_protocol: not-frozen-for-new-source`; no current executable source trial is admitted. | Publish/read back a distinct protocol binding the narrow searched scope, current interfaces, fixed gates, every trigger/veto/component, missed/unassessed intervals and immutable trial identity/stop rule. A Gaussian-law pass does not prove telescope noise exchangeability or justify transferring absolute-frequency vetoes. |
| Durable source acquisition | Original contract omits `acquisition_radio.py`, `acquisition_policy`, `cumulative_limits` and `reservation_store`. Its illustrative session cap is 500 requests / 512 MiB / 1200 s; it is not a joined cumulative telescope allocation. | Use the exact existing field names and policy; pin acquisition implementation, source-specific public GitHub ledger location, genesis/revision/hash and cumulative/session quotas. `reservation_store.kind` must be `github`. Preserve full leases after crash or uncertain acknowledgement; no refund/rearm or local-fixture substitution. |
| Trial allocation and first spectral access | Telescope ledger remains inactive; no pilot trial is consumed. | Only after the source-specific certificate/transport/protocol gates, independently publish/read back a new irrevocable acquisition/trial allocation. Bind every range to the contract/scan/window and every result to the fixed hypothesis inventory; no payload request as a preparation probe. |

`source_radio` verifies pinned evidence files and their source inventory, but its
three gate labels are not themselves a complete scientific certificate verifier.
A future builder/admission validator must check the required certificate contents
and ancestry explicitly before promoting any protocol gate. This report does
not modify that code or claim such a verifier already exists.

## Concrete metadata-only builder interface and output contract

The next bounded implementation deliverable can be a **new prospective builder
and independent admission validator**, with no networking, source runtime import,
payload decoding, scoring, RNG construction, reservation or publication mutation
inside either operation. Read only independently supplied file pins and retained
metadata. Recompute the scan/window/bank identities rather than trusting copied
embedded hashes.

Identity reconstruction uses the immutable original preparation and its design
as the historical input pair. Connecting their result to a new executable
source contract needs the separate provenance rebinding interface identified
above. The existing preparation binder deliberately rejects a source with
nonempty windows; bypassing that condition or substituting the new file hash
would erase the evidence boundary. A proposed rebinding schema must record
both raw source-contract pins, old window/bank/factor/clock identities, exact
six-scan and role semantic comparisons and the new protocol/certificate pins.
It must retain `spectral_access_authorized=false` until independently admitted.

Proposed interface (a design requirement, not executable code added here):

```text
build_prospective_source_contract(
  evidence_file_pins, expected_source_inventory_sha256,
  role_windows, receiver_bank_pins, intended_code_runtime_binding,
  scientific_certificate_pin=None, joined_transport_certificate_pin=None,
  reservation_store=None, cumulative_limits=None, trial_protocol_pin=None
) -> {prospective_source_contract, admission_matrix}
```

The two canonical outputs must be separate, fresh artifacts:

| Output | Required envelope and bindings | Required initial disposition |
|---|---|---|
| Prospective source contract | Existing `artifact_type='radio-source-contract-v1'`; unchanged target/cadence/source inventory and six scans; exact role windows; full current implementation pins; source-bound three-gate evidence; intended `hdf5_runtime`; exact `acquisition_policy`, `session_limits`, `cumulative_limits`, `reservation_store`; a pinned distinct trial protocol and certificate bindings. | Metadata preparation only. Missing/unverified certificate, transport, runtime or allocation leaves the relevant gate pending and spectral authority false. No inherited allocation or genesis activation. |
| Admission matrix | Proposed distinct schema `radio-new-source-admission-matrix-v1`; immutable evidence checkpoint; externally verified raw file pins; source/window/bank identities; each required field, dependency and status; rejected/missing obligations; prospective contract file pin; qualification boundaries and stop date. | `TELESCOPE_ACCESS_BLOCKED`; explicit `spectral_access_authorized=false`, `execution_authorized=false`, `reservation_authorized=false`, `rng_authorized=false`, `scientific_execution_authorized=false`; all workload counters zero for builder work. |

The validator must reject missing implementation/dependency pins, changed last
OFF scan or ETag, source-inventory substitution, overlapping role payloads,
rounded/replaced clock conventions, expanded carrier/rate/width scope, obsolete
reader/runtime receipts, source/context/noise-law mismatch, incomplete scientific
outcomes, synthetic Boolean authority and a local or wrong public ledger. These
are distinct joined-admission negatives; they do not require repeating the
already completed detector/codec fixtures or spending any reserved case.

The proposed scientific certificate must retain all 127 complete whole-cadence
maxima, including tagged EMPTY, and all 24 fixed evaluation outcomes: ten ON-only
signals, ten matched ON/OFF controls, two adjacent-OFF controls and two noise
nulls. Keep threshold `max(10,higher-quantile-at-1)` and inclusive rank
`(1+count(reference maximum >= score))/128 <= 0.01`, plus every unchanged physical
veto. Ties count against the member; EMPTY is not missing computation. Recovery
requires an associated final member and component in every ON-only case; the
other controls require zero final members/components, including broad-width
unassociated leakage. Truth is for post-decision association only. A missing,
corrupt, capacity-exhausted or incomplete result cannot be converted to EMPTY,
zero-control success or a source-ready certificate.

The present session numbers may be carried only as an unchanged historical
declaration. A new cumulative acquisition/trial budget must be prospectively
specified, reviewed, frozen and allocated; this report assigns no new numbers.
Unknown compressed wire cost, full native runtime overhead and scientific
40/80-second feasibility remain measured-evidence requirements rather than
arithmetic estimates from the extraction volume or compact8 caps.

## Compact8 fork and ordered advancement

| Event | Permitted continuation | Boundary preserved |
|---|---|---|
| Compact8 refuses or exhausts a bound | Retain final/partial receipts, logs and spent invocation; identify the demonstrated integrity/custody/resource cause on retained evidence. If justified, prepare a separately named bounded code/contract repair with meaningful negative tests. | No retry, resume, marker reuse, source substitution or retrospective pass. No native/scientific reservation arises; the metadata-only builder can still be prepared. |
| Compact8 passes every declared offline resource/lifetime join | Preserve the exact scope and original caps, then prepare the separately frozen actual hosted runner/transport qualification and its independent admission proof. | Offline mock connector/delivery success is not an actual HTTP/native host join and does not authorize native8 or telescope data. |
| Actual joined host/runner qualification later passes | Consider only a separately verified fresh native8 execution freeze and immutable reservation: four reference cadences, wide/narrow ON, matched ON/OFF and fresh null. Measure complete native physical/recovery/RFI/null evidence and full resource feasibility. | Four references have minimum rank 1/5; the 1/100 scientific gate remains unavailable. A 600-second engineering limit does not prove the scientific 40/80-second phase limits. |
| Native engineering/scientific feasibility later passes | A distinct executable scientific freeze and fresh allocation are still required for the unchanged 127-reference/24-evaluation proposal. | No proposed scientific values are generated to debug implementation, no old 24-case evaluation is restarted and no threshold/bank/recipe is selected from exposed outcomes. |
| Fixed scientific gate later passes | Require this source's separately frozen integrated acquisition/trial admission and public durable allocation before the first spectral access. | Synthetic success grants neither telescope provenance/noise-law transfer nor automatic access to the selected pilot. |

The [readiness decision](RADIO_READINESS_2026-09-29_DECISION.md),
[measurable publication result](RADIO_NATIVE_V2_ACTIONS_PUBLICATION_2026-10-01_RESULT.md),
[inactive scientific protocol](RADIO_WHOLE_CADENCE_NULL_2026-09-28_PROTOCOL_PROPOSAL.md)
and [midpoint review](RADIO_TWO_WEEK_REVIEW_2026-10-02.md) establish these distinct
boundaries. Later code preparation can close named interface gaps; it cannot
upgrade an earlier workload's evidence or grant an unexecuted scientific gate.

## Period closure and preserved dispositions

Close the [26 September–9 October period](RADIO_TWO_WEEK_PLAN_2026-09-26.md) on
**9 October 2026**. If admission remains blocked, publish the achieved evidence,
absence of a new astronomical search result, exact missing observation/contract
and a decision to pause the route or undertake one named bounded study. No
automatic extension, target switch or return to LS follows from unused calendar
days or a software-test pass.

HD1461/71139 remains on provenance HOLD; GJ724/73005 remains untouched reserve.
Original M43AF 112 injection/control inputs and 128 native nulls stay reserved
and unopened. Closed M43/native/engineering outcomes and spent identities remain
closed. The failed HD189733 calibration attempt, old 24 unopened evaluations
and its completed single diagnosis remain unusable for restart; this report
creates no second diagnosis/remedy allocation. `native8` remains unreserved
and 127/24 NOT ACTIVATED. LS stays paused at LS8BD–LS8BE with LS8BF saved;
CHEOPS remains UNSENT. No external messages, telescope booking, paid service or
background task is authorized by this report.
