# M43L runtime amendment — ordinary processes and a file stop marker

The initial public freeze `65a7f25872074770530436179c8653d6e3e94b3b`
failed while starting Python's multiprocessing SyncManager. Creating its local
listening socket raised `PermissionError: [Errno 1] Operation not permitted`,
followed by an EOFError in the parent. The preserved traceback identifies this
startup stage. No width jobs had been submitted, no telescope source products
were loaded and no M43L score cells were evaluated.

Retain the initial configuration, raw traceback and sealed failure record.
Replace only job coordination: seven normal Python subprocesses, launched by
lightweight parent threads, use an ephemeral shared file as a cooperative stop
marker. No listening socket, socket service, sandbox escalation or permission
change is required. A fresh temporary control directory is used on each run;
failing workers set the marker, and peers stop at their next batch boundary.

A separate preflight launches seven real child processes, verifies their initial
markers, sets the common stop file and verifies that all seven children observe
it. This passes without telescope source loads or score evaluation. Its exact
script and result are pinned in the amended configuration. The 76 M43-family
numerical/inventory tests also pass after the coordination change.

The seven widths, two sources, bank, factors, all 17,807,942,502 prescribed score
cells, reference construction, arithmetic, batch order, success criteria and
source/width checkpoint contents are unchanged. This amendment and the updated
configuration/code must be public before the first successful real evaluation.
It is an execution repair, not a changed scientific endpoint. Future reports
must retain and disclose this initial startup failure rather than imply that
the first freeze ran successfully.
