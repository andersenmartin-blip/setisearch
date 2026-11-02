#!/usr/bin/env python3
"""Verify actual saved primary cards and relevant failure boundaries offline."""
import copy
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fetch_headers import request_header
from header_tools import HeaderError, check_identity, parse_header_response, MJD_EPOCH
from make_plan import select

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def main():
    source = REPO / "work_harps_20261101/v2/extension02/data/main/ADP.2023-07-07T01_08_58.252.fits"
    old_receipt = REPO / "work_harps_20261101/v2/extension02/acquisition/receipts/ADP.2023-07-07T01_08_58.252.json"
    previous = json.loads(old_receipt.read_text())
    cards, primary_blocks, done = [], [], False
    with source.open("rb") as handle:
        for _ in range(512):
            block = handle.read(2880)
            assert len(block) == 2880
            primary_blocks.append(block)
            for index in range(0, 2880, 80):
                card = block[index:index + 80].decode("ascii")
                cards.append(card)
                if card[:8].strip() == "END":
                    done = True
                    break
            if done:
                break
    assert done
    body = ("\n".join(cards) + "\n").encode()
    header, evidence = parse_header_response(body, "text/plain; charset=UTF-8")
    before = previous["primary_header"]
    job = {"dp_id": previous["dp_id"], "target": previous["canonical_target"], "source_file_ids": previous["raw_progenitor_ids"], "metadata": {"t_min": before["MJD-OBS"], "t_exptime": before["EXPTIME"], "s_ra": before["RA"], "s_dec": before["DEC"]}}
    records = []

    def record(name, condition):
        assert condition, name
        records.append({"case": name, "passed": True})

    result = check_identity(header, job)
    record("existing_primary_plaintext_all_identity_checks", result["status"] == "PASS_RECORDED_BERV")
    record("existing_recorded_berv_matches_saved_receipt", result["berv_km_s"] == before["HIERARCH ESO DRS BERV"])
    record("existing_harps_nirps_mode_retained", result["primary_header"]["HIERARCH ESO INS MODE"] == "HARPS+NIRPS")
    wrapped = ("<html><body><pre>" + html.escape(body.decode()) + "</pre></body></html>").encode()
    parsed, _ = parse_header_response(wrapped, "text/html")
    record("html_pre_equivalent_to_saved_primary", parsed == header)

    for name, damaged in [("missing_end_rejected", body.rsplit(b"END", 1)[0]), ("duplicate_berv_rejected", body.replace(b"END", b"HIERARCH ESO DRS BERV = 1.0\nEND", 1)), ("binary_control_rejected", body + b"\x00")]:
        rejected = False
        try:
            parse_header_response(damaged, "text/plain")
        except HeaderError:
            rejected = True
        record(name, rejected)
    mutations = [
        ("wrong_adp_rejected", "ARCFILE", "ADP.2000-01-01T00:00:00.000.fits", "EXCLUDED_HEADER_VALIDATION"),
        ("coadd_rejected", "NCOMBINE", 2, "EXCLUDED_HEADER_VALIDATION"),
        ("wrong_resolution_rejected", "SPEC_RES", 80000, "EXCLUDED_HEADER_VALIDATION"),
        ("eggs_state_rejected", "HIERARCH ESO INS HEFS ST", True, "EXCLUDED_HEADER_VALIDATION"),
        ("unknown_mode_stays_pending", "HIERARCH ESO INS HEFS ST", None, "PENDING_MODE_COMPATIBILITY"),
        ("bervmx_not_substituted", "HIERARCH ESO DRS BERV", None, "EXCLUDED_HEADER_VALIDATION"),
        ("absurd_finite_berv_rejected", "HIERARCH ESO DRS BERV", 1e300, "EXCLUDED_HEADER_VALIDATION"),
        ("mixed_additional_provenance_rejected", "PROV2", "ADP.2000-01-01T00:00:00.000.fits", "EXCLUDED_HEADER_VALIDATION"),
        ("embedded_expected_raw_in_mixed_provenance_rejected", "PROV1", previous["raw_progenitor_ids"][0] + ".fits OTHER_FILE.fits", "EXCLUDED_HEADER_VALIDATION"),
        ("exptime_above_tolerance_rejected", "EXPTIME", before["EXPTIME"] + .021, "EXCLUDED_HEADER_VALIDATION"),
        ("mjd_above_tolerance_rejected", "MJD-OBS", before["MJD-OBS"] + 2e-7, "EXCLUDED_HEADER_VALIDATION"),
        ("wrong_date_rejected", "DATE-OBS", "2000-01-01T00:00:00", "EXCLUDED_HEADER_VALIDATION"),
        ("wrong_raw_progenitor_rejected", "PROV1", "HARPS.2000-01-01T00:00:00.000.fits", "EXCLUDED_HEADER_VALIDATION"),
    ]
    for name, key, value, expected in mutations:
        changed = dict(header)
        changed[key] = value
        record(name, check_identity(changed, job)["status"] == expected)

    candidates = []
    for year in (2020, 2021, 2022):
        for month in (1, 2):
            date = datetime(year, month, 1, tzinfo=timezone.utc)
            dp = f"ADP.{year}-{month:02d}-02T00:00:00.000"
            candidates.append({"status": "METADATA_CANDIDATE_PENDING_HEADER_IDENTITY_BERV", "reasons": [], "target": "HD122640", "dp_id": dp, "source_file_ids": [f"HARPS.{year}-{month:02d}-01T00:00:00.000"], "metadata": {"t_min": (date - MJD_EPOCH).total_seconds() / 86400}})
    chosen = select(candidates)
    record("month_number_across_years_not_year_month", len(chosen) == 2 and [row["month_number"] for row in chosen] == [1, 2] and all("2022-" in row["dp_id"] for row in chosen))
    tied = copy.deepcopy(candidates[-1])
    tied["dp_id"] = "ADP.2022-02-01T00:00:00.000"
    record("month_tie_lexicographically_first_dp", select(candidates + [tied])[-1]["dp_id"] == tied["dp_id"])

    class FakeResponse:
        status = 200
        headers = {"Content-Type": "text/plain"}

        def __init__(self):
            self.body = b"01234567890123456789"
            self.pos = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            block = self.body[self.pos:self.pos + size]
            self.pos += len(block)
            return block

    class FakeOpener:
        def open(self, *args, **kwargs):
            return FakeResponse()

    mock_job = {"job_index": 0, "dp_id": previous["dp_id"], "target": previous["canonical_target"], "url": "https://archive.eso.org/hdr?DpId=UNREQUESTED_TEST"}
    with patch("fetch_headers.urllib.request.build_opener", return_value=FakeOpener()):
        captured, receipt = request_header(mock_job, {"max_response_bytes": 10, "timeout_seconds": 30}, 10)
    record("byte_cap_does_not_read_overflow_and_marks_incomplete", len(captured) == 10 and receipt["bytes_saved"] == 10 and not receipt["complete"])
    result = {"status": "PASS", "created_utc": datetime.now(timezone.utc).isoformat(), "network_requests": 0, "spectral_arrays_read": False, "local_primary_source": str(source.relative_to(REPO)), "saved_receipt_sha256": hashlib.sha256(old_receipt.read_bytes()).hexdigest(), "primary_blocks_read": len(primary_blocks), "primary_fits_bytes_sha256": hashlib.sha256(b"".join(primary_blocks)).hexdigest(), "primary_card_text_bytes": len(body), "primary_card_text_sha256": hashlib.sha256(body).hexdigest(), "checks": records, "case_count": len(records), "parser_evidence": evidence, "code_hashes": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in ("header_tools.py", "make_plan.py", "fetch_headers.py", "select_extremes.py", "validate_local.py")}}
    (HERE / "LOCAL_VALIDATION.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "cases": len(records), "primary_text_bytes": len(body)}, indent=2))


if __name__ == "__main__":
    main()
