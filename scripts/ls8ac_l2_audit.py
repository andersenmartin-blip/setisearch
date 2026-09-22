#!/usr/bin/env python3
"""Unchanged independent LS8K scalar auditor, redirected to the frozen LS8AC pair."""
import hashlib
from pathlib import Path
import ls8k_l2_audit as independent

ROOT = Path(__file__).resolve().parents[1]
PIN = '75bccbefd1cdf96cc80380c969843b572aab95ed4300271c70219b7c98bbe25d'


def main():
    assert hashlib.sha256((ROOT / 'scripts/ls8k_l2_audit.py').read_bytes()).hexdigest() == PIN
    independent.META = ROOT / 'results_ls8ac_l2_metadata'
    independent.OUT = ROOT / 'results_ls8ac_l2_screen'
    independent.KEYS = ['CH_PR100002_TG006401_V0300', 'CH_PR100002_TG006402_V0300']
    independent.main()


if __name__ == '__main__':
    main()
