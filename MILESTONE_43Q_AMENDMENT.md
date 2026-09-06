# M43Q — preserved initial failure and reference/serialization amendment

The initial public freeze was `e9ceca61e8db7c0dca0076e1a8b0c3e1f8e9b17c`.
Its execution stopped at the first native receiver anchor, before any full
real-data calibration/retention pass or completed receiver-width checkpoint.
The original configuration, test log, run log, failure record and synthetic
artifact are preserved under `results_m43q_integrated_detector/initial_attempt`.
The exact original code remains available at that public commit.

Two implementation issues were found:

1. The new receiver reference used Python's built-in `sum`. Python 3.12.13
   uses a different floating-point reduction from the inherited detector's
   sequential binary64 addition. At epoch1_on, width 1, template 0, first
   score carrier, production predicted 1411.5212324720146 MHz whereas the
   reference predicted 1411.5212324720144 MHz. The numerical rule requires
   the inherited operation order. Replace only the reference midpoint
   reduction with explicit sequential addition and pin the Python version.
   Native filtering, production midpoint/peak measurement, masks, thresholds,
   matching rules and comparison strictness are unchanged.
2. The synthetic fixture's expected-disposition mapping had integer keys.
   JSON converted them to strings after the artifact was sealed, changing
   canonical key order on re-reading. The original synthetic artifact's
   outer seal is therefore invalid and is retained as failed evidence.
   Convert those keys to strings before sealing. The inner pipeline result
   and its known-answer dispositions are unchanged.

Two focused regression tests now cover binary64 midpoint order and a complete
synthetic-artifact write/read/seal round trip. Re-freeze these changes and the
retained initial evidence publicly before rerunning the same protocol from
the beginning. No tolerance is relaxed, no diagnostic threshold is adjusted,
and no new astronomical search endpoint is introduced. Both defects concern
the new qualification/reporting path; neither establishes an error in the
previously qualified telescope score arithmetic.
