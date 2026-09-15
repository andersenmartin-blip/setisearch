#!/usr/bin/env python3
"""Fixed, separately scoped electronic-reference supplement to LS7U."""
import argparse
import ls7u_acquire_prescan as base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--offline',action='store_true')
    args = ap.parse_args()
    base.EXTENSION = 'SCI_RAW_BlankLeft'
    base.HEADER_FILE = 'SCI_RAW_SubArray_hdu02_header.txt'
    base.NCOLUMNS = 8
    base.RANGES = [(69134400,8640),(69143040,2764800)]
    base.LIMIT = sum(n for _,n in base.RANGES)
    base.OUT = base.ROOT/'results_ls7u_prescan/blank_reference'
    if not (base.ROOT/'LS7U_BLANK_SUPPLEMENT.md').exists():
        raise ValueError('Supplement specification absent')
    base.acquire(args.offline)


if __name__ == '__main__':
    main()
