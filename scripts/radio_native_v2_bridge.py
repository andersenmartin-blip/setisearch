#!/usr/bin/env python3
"""Bounded one-command JSON stdin interface; no RNG or execution authority."""
import json
import sys

from seti_repeater.empty_null_radio import canonical
from seti_repeater.native_v2_bridge_radio import dispatch, MAX_INPUT_BYTES


def main():
    raw=sys.stdin.buffer.read(MAX_INPUT_BYTES+1)
    if len(raw)>MAX_INPUT_BYTES:
        raise ValueError('Bridge command input exceeds fixed bound')
    value=json.loads(raw)
    result=dispatch(value)
    sys.stdout.buffer.write(canonical(result)+b'\n')


if __name__=='__main__':
    main()
