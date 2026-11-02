#!/usr/bin/env python3
"""Execute only the frozen, single-request aggregate metadata plan."""
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2) + "\n")


def main():
    plan = json.loads((HERE / "NEXT_METADATA_PLAN.json").read_text())
    freeze = json.loads((HERE / "PREFLIGHT_FREEZE.json").read_text())
    for name, digest in freeze["files"].items():
        assert sha(HERE / name) == digest, name
    code_freeze = json.loads((HERE / "EXECUTION_CODE_FREEZE.json").read_text())
    assert sha(Path(__file__).resolve()) == code_freeze["script_sha256"]
    assert plan["parameters"] == {
        "date": "202609", "columns": "f:night,f:alerts,f:objects,f:visits",
        "output-format": "json",
    }
    assert plan["max_requests"] == 1 and plan["retries"] == 0
    # Exclusive marker prevents any accidental repeat of this plan.
    with (HERE / "REQUEST_STARTED.json").open("x") as handle:
        json.dump({"started_utc": datetime.now(timezone.utc).isoformat()}, handle)
        handle.write("\n")
    receipt = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": sha(HERE / "NEXT_METADATA_PLAN.json"),
        "preflight_freeze_sha256": sha(HERE / "PREFLIGHT_FREEZE.json"),
        "script_sha256": sha(Path(__file__).resolve()),
        "method": "GET", "requests_attempted": 1, "retries": 0,
        "redirects_followed": 0, "http_status": None,
        "error": None, "complete": False,
    }
    url = plan["endpoint"] + "?" + urllib.parse.urlencode(plan["parameters"])
    receipt["url"] = url
    started = time.monotonic()
    body = b""
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(request, timeout=plan["timeout_seconds"]) as response:
            receipt["http_status"] = response.status
            receipt["headers"] = {
                key: response.headers.get(key)
                for key in ("Date", "Content-Type", "Content-Length")
            }
            body = response.read(plan["max_response_bytes"] + 1)
        if len(body) > plan["max_response_bytes"]:
            raise ValueError("Response exceeded frozen byte cap")
        receipt["complete"] = True
    except urllib.error.HTTPError as error:
        receipt["http_status"] = error.code
        receipt["error"] = str(error)
        body = error.read(plan["max_response_bytes"] + 1)
    except Exception as error:
        receipt["error"] = type(error).__name__ + ": " + str(error)
    receipt["elapsed_seconds"] = time.monotonic() - started
    (HERE / "september_statistics.body").write_bytes(body)
    receipt["bytes_saved"] = len(body)
    receipt["body_sha256"] = sha(HERE / "september_statistics.body")
    receipt["completed_utc"] = datetime.now(timezone.utc).isoformat()
    save("REQUEST_RECEIPT.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
