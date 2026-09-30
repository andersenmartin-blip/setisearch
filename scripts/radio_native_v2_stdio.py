#!/usr/bin/env python3
"""Direct-pipe persistent Store service; component only, no RNG/authority."""
import argparse
import sys

from seti_repeater.native_v2_bridge_radio import Store
from seti_repeater.native_v2_stdio_radio import StdioService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--session-id', default='stdio-session')
    parser.add_argument('--seconds', type=float, default=4800)
    parser.add_argument('--operation-seconds', type=float, default=120)
    parser.add_argument('--commands', type=int, default=512)
    args = parser.parse_args()
    service = StdioService(Store(args.root), session_id=args.session_id,
                           seconds=args.seconds, operation_seconds=args.operation_seconds,
                           commands=args.commands)
    service.serve(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == '__main__':
    main()
