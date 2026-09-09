**Latest development result — M43AE completed; the joint response rules fail qualification.**
The publicly frozen comparison completed **262 case evaluations and 3,406 paired
policy endpoints**: 1,500 prior endpoints were reused and 1,906 newly evaluated.
Only 112 additional inputs received new detector executions; three declared
upstream regression anchors replay exactly.

| Comparison | Historical signals /83 | Historical leaking controls /66 | Additional signals /64 | Additional leaking controls /48 |
|---|---:|---:|---:|---:|
| Centered combination | 70 | 10 | 58 | 0 |
| Geometry + original OFF + aggregation | 65 | 6 | 57 | 0 |
| Geometry + aligned OFF + aggregation | 69 | 14 | 58 | 1 |
| Joint receiver mean + aggregation | 70 | 16 | 58 | 1 |
| Joint candidate track + aggregation | 70 | 17 | 58 | 1 |
| Joint dual hypothesis + aggregation | 70 | 16 | 58 | 1 |

Tying OFF amplitude to the actual compared profile restores the historical
width-17 signal lost in M43AD. Correlated controls still escape when their OFF
centers remain below the unchanged 5.5 floor. All three new policies preserve
the centered comparison's signals, but leave more control inputs with surviving
members. Three inherited weak-epoch signal losses remain. No rule is adopted.

The audit passes: **511 pinned files, 9,394 complete profiles, 12,014 profile
links, 55,707 new member decisions and 10,774 direct native comparisons**.
All 19 focused tests passed before the freeze. The lossless 14-part archive
reconstructs all 264 original files byte for byte. The 112 additional cases have
104 distinct native payloads with no overlap with the prior inventories;
the whole comparison has 246. All reuse one observing sequence. No new nulls,
sky coverage, physical false-alarm estimate or astronomical candidate is claimed.

[Read the M43AE result, exact costs and reproduction instructions](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AE_JOINT_RESPONSE_RESULT.md).
[Continue from completed M43AE](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/M43AE_COMPLETED_CONTINUATION.md).
Next: prospectively specify response-level amplitude evidence across profiles
and epochs, with explicit weak-support costs and independent qualification.

---

