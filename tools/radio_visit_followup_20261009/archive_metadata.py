"""Bounded public archive catalogue/directory GET; never opens telescope files."""
import argparse
import datetime
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output_stem")
    args = parser.parse_args()
    u = urllib.parse.urlsplit(args.url)
    permitted = (u.hostname == "bldata.berkeley.edu" and
                 re.fullmatch(r"/pipeline/(AGBT\w+/)?((holding|collate|blc[0-9]{2})/)?", u.path)) or (
        u.hostname == "seti.berkeley.edu" and u.path.startswith("/opendata/api/"))
    if not permitted:
        raise ValueError("Only catalogue API or observed directory listings permitted")
    cpu, wall = time.process_time(), time.monotonic()
    stem = Path(args.output_stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"requested_url": args.url, "attempt_utc": datetime.datetime.now(
        datetime.timezone.utc).isoformat(), "body_byte_ceiling": 1048576,
        "spectral_values": False, "retries": 0}
    try:
        request = urllib.request.Request(args.url, headers={"Accept-Encoding": "identity"})
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(1048577)
            receipt.update(status=response.status, final_url=response.geturl(),
                           body_bytes_received=len(body))
            if len(body) > 1048576:
                raise ValueError("Metadata body exceeds ceiling")
            if urllib.parse.urlsplit(response.geturl()).hostname != u.hostname:
                raise ValueError("Redirect host changed")
            stem.with_suffix(".body").write_bytes(body)
            receipt["body_sha256"] = hashlib.sha256(body).hexdigest()
            lines = body.decode("utf-8").splitlines()
            matches = [l.strip() for l in lines if "HIP98505" in l or
                       re.search(r'href=["\']holding/', l)]
            print(json.dumps({"stem": str(stem), "matches": matches}, ensure_ascii=False))
    except Exception as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
    finally:
        receipt.update(process_cpu_s=time.process_time()-cpu,
                       wall_s=time.monotonic()-wall)
        stem.with_suffix(".receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
        print(json.dumps(receipt))


if __name__ == "__main__":
    main()
