"""Fixed entry for a single externally pinned, synthetic engineering scope.

The publication/readback is performed before this command by the operator.
This entry is not a transport, runtime or scientific authorization certificate.
No producer or scope retry is performed here.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runner_v2 as runner


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('scope_path')
    parser.add_argument('scope_sha256')
    parser.add_argument('scope_bytes', type=int)
    parser.add_argument('claim_root')
    parser.add_argument('claim_device', type=int)
    parser.add_argument('claim_inode', type=int)
    args = parser.parse_args()
    expected = {'bytes': args.scope_bytes, 'sha256': args.scope_sha256}
    raw = runner.read_checked({'path': args.scope_path, 'mode': 0o400, **expected})
    result = runner.dispatch(raw, expected, scope_path=args.scope_path,
        expected_claim_root={'path': args.claim_root,
            'device': args.claim_device, 'inode': args.claim_inode})
    sys.stdout.buffer.write(result.payload)
    return 0 if result.record()['status'] == 'SYNTHETIC_PROCESS_QUALIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
