# M43O — real three-epoch sum and active-cut qualification

After M43J/L/N established every per-epoch score for six M43H/M sources at
m37_1412p5, qualify their combination through unchanged stack_hypothesis.
Use all 1,701 templates, 747,793 support carriers and eight widths. Keep ON
and OFF separate, each in epoch1/epoch2/epoch3 chronological order. Use the
existing four subsets: (0,1), (0,2), (1,2), (0,1,2).

There are two declared endpoints: raw sum divided by float32 sqrt(active
count), and the same sum with the existing minimum-active-epoch SNR 3 rule.
The raw diagnostic makes arithmetic observable even where the active cut
rejects every cell. Each endpoint compares 81,407,737,152 cells; together
162,815,474,304. There are 16 kind/width jobs and 864 template batches. Each
batch has eight stack-rule records. Replay 61,055,802,864 per-epoch cells,
requiring their exact prior M43J/L/N batch hashes before stacking. These
replays are repeated numerical work, not new independent validation counts.

Freeze this plan, code, tests, source trust anchors, all ancestor checkpoints,
bank/factors/grid, runtime and exact rules publicly before real evaluation.
No new downloads. Production source loading, filtering, gather and stacking
remain unchanged. Parent score hashes prove that every input vector is the
previously qualified per-epoch vector. Refuse swapped epochs, mixed ON/OFF,
changed source/cache identities, altered payloads or incomplete batches.

The reference sums active epochs sequentially in float32 and independently
accumulates their >=3 conditions. Check all finite and rejected outputs.
Use 32 templates per batch and 4,096-carrier gather and stack chunks. Stack
chunks retain [epoch, template, carrier] before flattening only the last two
axes for production. Each stack digest is the ordered concatenation of
little-endian float32 chunk outputs, with templates then carriers inside each
chunk. It is a chunk-major stream digest, not a full template-major vector
hash; fixed chunk size is part of the contract. Preserve finite counts as
numerical diagnostics only, never candidate counts.

At most seven ordinary subprocesses; schedule descending width, ON then OFF.
Each job holds three sources/caches and three bounded per-epoch score batches;
stack comparison temporaries cover only a carrier chunk. Use the tested
M43L file stop marker. Stop queued peers and running peers at the next batch
boundary after failure. Seal every finished batch, mark a product complete
only after all 54 batches, and publish completed products during execution.
Reruns recompute rather than trusting self-sealed checkpoints to skip work.

The scope is sum arithmetic and the inherited active cut, with exclusion_mask
explicitly None. This does not qualify exclusion-mask construction, event
association, OFF vetoes, scrambles, threshold calibration or recovery. The
three epochs are scans in one observing sequence, not independent dates.
No candidates are selected and no scientific nondetection is claimed.
