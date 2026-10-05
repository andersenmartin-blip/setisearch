"""Build a NEW deterministic, tiny test archive; no package import/install."""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

from proxy_contract import ORIGINAL_PLAN_SHA256


def build():
    prefix = "proxy_fixture-1.0.dist-info/"
    files = {
        "proxy_fixture/__init__.py": b"# Inert synthetic payload; never imported.\n",
        prefix + "METADATA": b"Metadata-Version: 2.1\nName: proxy-fixture\nVersion: 1.0\n",
        prefix + "WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for name, body in sorted(files.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b"=").decode()
        writer.writerow((name, "sha256=" + digest, len(body)))
    writer.writerow((prefix + "RECORD", "", ""))
    files[prefix + "RECORD"] = record.getvalue().encode()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as output:
        for name, body in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100600 << 16
            output.writestr(entry, body)
    body = archive.getvalue()
    filename = "proxy_fixture-1.0-py3-none-any.whl"
    spec = {"name": "proxy-fixture", "version": "1.0", "filename": filename,
            "tags": ["py3-none-any"], "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
            "url": "https://files.pythonhosted.org/packages/synthetic-adapter-fixture/" + filename}
    plan = {"schema": "radio-proxy-separate-synthetic-wheel-fixture-v1",
            "evidence_domain": "SIMULATION_ONLY", "original_plan_sha256": ORIGINAL_PLAN_SHA256,
            "not_an_original_package_substitution": True, "wheels": [spec]}
    return body, spec, json.dumps(plan, sort_keys=True, separators=(",", ":")).encode() + b"\n"


if __name__ == "__main__":
    body, spec, plan = build()
    root = Path(__file__).parent
    (root / "synthetic-wheel.whl").write_bytes(body)
    (root / "synthetic-plan.json").write_bytes(plan)
