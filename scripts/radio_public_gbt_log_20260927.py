"""One bounded public target-row read. No telescope or workbook mutation."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_radio_public_log_contact_2026-09-27" / "retrieval_01"
SCOPE = ROOT / "RADIO_PUBLIC_LOG_CONTACT_2026-09-27_SCOPE.md"
QUERY = "select A,B,C,D,E,F,G where A = 'HIP1499' limit 10"
URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1f8Gzx67_0KN2eP4whE4Qcdj8iSTRSuRZFnXthWRcVB0/gviz/tq?"
    + urlencode({"headers": 2, "tqx": "out:json", "tq": QUERY})
)
CAP = 65536


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def save(name, data):
    with (OUT / name).open("x", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False, allow_nan=False)
        file.write("\n")


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    save("source_snapshot.json", {
        "scope_sha256": hashlib.sha256(SCOPE.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope_path": SCOPE.name,
        "script_path": "scripts/" + Path(__file__).name,
        "query": QUERY, "url": URL,
        "started_utc": datetime.now(timezone.utc).isoformat(),
    })
    started = time.monotonic()
    receipt = {"url": URL, "direct_get_attempts": 1, "redirects_followed": 0,
               "credentials_used": False, "body_bytes": 0,
               "body_limit_bytes": CAP, "overflow_sentinel_bytes": 1}
    body = b""
    try:
        request = Request(URL, headers={"Accept-Encoding": "identity"})
        try:
            response = build_opener(NoRedirect()).open(request, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            receipt.update({"status": response.status,
                            "final_url": response.geturl(),
                            "response_headers": {k: response.headers.get(k)
                                for k in ("Content-Type", "Content-Length", "Date",
                                          "Location", "ETag", "Last-Modified")}})
            body = response.read(CAP + 1)
        receipt["body_bytes"] = len(body)
        receipt["body_sha256"] = hashlib.sha256(body).hexdigest()
        receipt["body_within_limit"] = len(body) <= CAP
        (OUT / "response.txt").write_bytes(body)
        if receipt["status"] != 200 or len(body) > CAP:
            raise ValueError("Response is not an admissible bounded HTTP 200 body")
        text = body.decode("utf-8")
        marker = "google.visualization.Query.setResponse("
        if marker not in text or not text.rstrip().endswith(");"):
            raise ValueError("Unrecognized query response envelope")
        payload = json.loads(text.split(marker, 1)[1].rstrip()[:-2])
        if payload.get("status") != "ok":
            raise ValueError("Query service returned a non-ok status")
        table = payload["table"]
        rows = table["rows"]
        if len(rows) > 10 or any(r["c"][0]["v"] != "HIP1499" for r in rows):
            raise ValueError("Returned rows violate target/row scope")
        save("target_rows.json", payload)
        receipt["parsed_rows"] = len(rows)
    except Exception as error:
        receipt["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        receipt["elapsed_seconds"] = time.monotonic() - started
        receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save("transport_receipt.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
