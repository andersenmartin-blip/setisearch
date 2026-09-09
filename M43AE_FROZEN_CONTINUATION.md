# M43AE prospective execution checkpoint

The M43AD package is already public; its completed publication receipt remains
in `M43AD_PUBLICATION_COMPLETED.md`. M43AE continues the integrated experiment
authorized by `PROJECT_DIRECTION.md`.

This checkpoint freezes `MILESTONE_43AE_JOINT_RESPONSE_PLAN.md`,
`config/m43ae_joint_response.json`, the implementation, independent audit and
19 passing focused tests before new endpoint evaluation. The operational
preflight restored all 96 anchor arrays, verified all 48 native gathers and
restored the existing calibration without new null rows. It evaluated no new
rule or additional input.

After this commit has been verified on the public scientific branch, write a
sealed `results_m43ae_joint_response/public_freeze.json` identifying that exact
public commit and tree. Execute only with that receipt and exact configuration.
The runner first checks the three declared upstream regression anchors, then
reuses 150 existing upstream audits and runs 112 additional inputs. It saves
sealed resumable records. Run the independent audit after all 262 inputs finish.

```bash
PYTHONPATH=src:scripts python scripts/m43ae_joint_response.py --runtime-root /path/to/m43ad_runtime --freeze PUBLIC_FREEZE_COMMIT
PYTHONPATH=src:scripts python scripts/m43ae_audit.py
```

Keep failed checks and original evidence intact. Report every acceptance gate,
including failures; no production change or candidate claim follows from this
development comparison. The existing one-sequence data and the 1,792-row prior
null exclusion remain unchanged. Publish the full result archive and readable
findings, then update README on main. No further owner approval is needed for
these already authorized publications; delegation remains deferred.

Native runtime verified for this run:
`/workspace/scratch/69269edb2f83/m43ad_runtime`.
