# M43U startup correction before score evaluation

The first invocation at public freeze `6091ff8907e4e882e7227ee6e9ec97c98dfe5331`
stopped inside the numerical-runtime guard: the NumPy version attribute was
misspelled `np.__version()` instead of `np.__version__`. The retained traceback
is `results_m43u_signal_interference/startup_failure_initial.log`.

No original-array preparation, calibration, held-out calculation or injected
score evaluation began. Fix only that attribute lookup, add a focused startup
guard regression test, and update the corresponding pinned file hashes. All
72 cases, coordinates, components, three policies, shift rows, thresholds,
association rules and decision gates remain byte-for-byte identical as JSON
values. The original six substantive numerical tests remain valid and their
original log is retained. The additional guard test is logged separately.

Publish this amendment and corrected exact configuration before retrying.
This is an operational startup repair, not tuning after new observations.
