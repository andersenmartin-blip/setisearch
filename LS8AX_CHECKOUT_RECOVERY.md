# LS8AX — checkout-only recovery, before archive access

23 September 2026. The original GJ 536 header freeze remains
`b28022d5ac230ce70906e651ea9d2df71f96df63`. The selected pair, exposure
representation rule, header reader and independent header-audit source are
unchanged. No GJ 536 headers or values have been read.

## Preserved obstruction

[Workflow 35879603888](https://github.com/andersenmartin-blip/setisearch/actions/runs/35879603888)
completed with conclusion **cancelled**. Job 107244338553 started at
15:10:32 UTC. Its unfiltered Git fetch began at 15:10:34 and was cancelled
at 15:25:34 under the 15-minute job limit. The setup, dependency installation
and exact header-only preflight steps were **skipped**. Archive product
bytes read: **zero**. There is no scientific result from this attempt.

The fallback preservation step ran in an incomplete checkout and created
an unrelated local root commit containing status/environment files. Its
non-fast-forward push was rejected; the public branch remained at the
original freeze. Those executor-local files are unavailable here and are
not reconstructed. Preserve the complete decoded job log and terminal
run/step evidence in verification_ls8ax_checkout_failure, with SHA256SUMS.
This records both the original obstruction and the failed preservation attempt.

## Exact execution repair

Before the first archive access, change only the metadata workflow's checkout
to the documented actions/checkout@v4 sparse-checkout mechanism. Include
all root files, `.github`, `config`, `scripts`, `src`, `tests`, the original
selection/reconciliation, LS8K reference metadata, this stage's metadata
output, header verification and failure evidence. Every pinned header input
has been checked against that inclusion list. Include output paths so Git
can publish the stage result normally.

The upstream [checkout source](https://github.com/actions/checkout/blob/v4/src/git-source-provider.ts)
uses `blob:none` fetching when sparse-checkout is set; the
[documented cone-mode example](https://github.com/actions/checkout/blob/v4/README.md#fetch-only-the-root-files-and-github-and-src-folder)
retains root files plus named directories. This reduces historical repository
payload transfer. No archival data selection or acquisition request changes.

Give the checkout step an identifier and require its success before the
result-preservation step. A checkout failure therefore cannot try to publish
an unrelated root commit. The final scientific-success gate still fails if
the header program does not succeed. Keep the original job time limit,
Python/dependency versions, five transport tests, timeout policy and header
budgets. Re-execute the unchanged reader only after this repair is public.

Use the same checkout pattern and guard for the later L2 workflow, with all
its pinned inputs and output path included before its separate public freeze.
The original header protocol and both scientific programs remain immutable.
This is an infrastructure recovery before data access, not a scientific
rerun or a relaxation of a failed data check.
