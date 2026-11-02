This is a separately authorized **syntax-only correction** of the failed first metadata query. The original `../metadata_search/` plan, code, requests, HTTP 400 response and results remain immutable. No valid observation rows were returned before this amendment.

The [official IVOA ADQL 2.0 grammar](https://wiki.ivoa.net/internal/IVOA/IvoaVOQL/adql-bnf-v2.0.html) distinguishes an unqualified sort-key identifier from a qualified column reference. `OFFICIAL_SYNTAX_EVIDENCE.json` records the inspected grammar productions and retrieval method; no raw-document hash is asserted. The only ADQL change removes the qualifiers in the final clause:

```sql
ORDER BY t_min ASC, dp_id ASC, source_file ASC
```

All selected columns, joins, target identity/position guards, public-release cutoff, whole-exposure date exclusion, old 300 DP/raw exclusions and selection rules remain unchanged. `AMENDMENT.json` records exact old/new query hashes and verifies that this substitution is the only query difference. The executor is byte-identical to the independently tested original.

This amended run allows at most **two new target requests**, one attempt each for HD122640 then HD135204, with unchanged 30-second / 1,000-row / 4-MiB caps, zero redirects/retries and no science payloads. The full continuation therefore permits at most **three target requests including the original failed request**. Any failure activates the same stop rule; there is no further automatic correction or retry loop. Documentation research is not an archive target-query test.

`PLAN.json` hashes the original failed-run evidence in addition to the historical scientific inputs. Its source guard verifies that the original run still records exactly one failed request with zero returned products before the amended run can execute. The two exclusive new run/attempt markers enforce the separately frozen request scope. The scientific target list and all 185 U / 35 M classifications remain unchanged.

The root must publish and verify this directory's own `PREFLIGHT_FREEZE.json`, then write its own `ROOT_RELEASE.json` before `python3 search_metadata.py --execute`. No original release receipt may be reused. Responses and metadata candidates will be saved in this directory; any later header identity/BERV retrieval requires a separate prospective scope. An empty file after a failure must never be interpreted as absence of suitable observations.
