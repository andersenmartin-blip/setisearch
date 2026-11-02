"""Bounded text-header parsing and HARPS product identity checks; no arrays."""
import math
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

ADP_RE = re.compile(r"ADP\.\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}")
RAW_RE = re.compile(r"HARPS\.\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}")
MJD_EPOCH = datetime(1858, 11, 17, tzinfo=timezone.utc)


class HeaderError(ValueError):
    pass


class PreCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.blocks = []
        self.current = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "pre":
            if self.depth:
                raise HeaderError("Nested PRE blocks")
            self.depth = 1
            self.current = []
        elif self.depth and tag.lower() == "br":
            self.current.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() == "pre" and self.depth:
            self.blocks.append("".join(self.current))
            self.depth = 0

    def handle_data(self, data):
        if self.depth:
            self.current.append(data)


def fits_value(text):
    text = text.strip()
    if text.startswith("'"):
        result, index = "", 1
        while index < len(text):
            if text[index] == "'":
                if index + 1 < len(text) and text[index + 1] == "'":
                    result += "'"
                    index += 2
                    continue
                rest = text[index + 1:].strip()
                if rest and not rest.startswith("/"):
                    raise HeaderError("Unexpected content after string value")
                return result.rstrip()
            result += text[index]
            index += 1
        raise HeaderError("Unterminated FITS string")
    value = text.split("/", 1)[0].strip()
    if value in ("T", "F"):
        return value == "T"
    try:
        result = float(value.replace("D", "E")) if any(x in value for x in ".EeDd") else int(value)
    except ValueError as error:
        raise HeaderError("Unsupported FITS value") from error
    if isinstance(result, float) and not math.isfinite(result):
        raise HeaderError("Nonfinite FITS value")
    return result


def parse_header_response(body, content_type):
    """Return first primary HDU only; do not infer fields from extension HDUs."""
    mime = content_type.split(";", 1)[0].strip().lower()
    if mime not in {"text/html", "application/xhtml+xml", "text/plain"}:
        raise HeaderError("Unexpected content type: " + mime)
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HeaderError("Response is not UTF-8 text") from error
    if any(ord(char) < 32 and char not in "\n\r\t" for char in text):
        raise HeaderError("Binary/control characters in response")
    if mime in {"text/html", "application/xhtml+xml"}:
        parser = PreCollector()
        parser.feed(text)
        parser.close()
        if parser.depth:
            raise HeaderError("Unclosed PRE block")
        candidates = parser.blocks
        rendering = "HTML_PRE"
    else:
        candidates = [text]
        rendering = "FITS_CARD_PLAINTEXT"
    matches = []
    for block in candidates:
        if "\n" not in block and "\r" not in block and len(block) % 80 == 0:
            lines = [block[i:i + 80] for i in range(0, len(block), 80)]
        else:
            lines = block.splitlines()
        for index, line in enumerate(lines):
            if re.match(r"^SIMPLE\s*=", line):
                matches.append((lines, index))
    if len(matches) != 1:
        raise HeaderError("Expected exactly one primary SIMPLE block")
    lines, start = matches[0]
    header, cards, ended = {}, [], False
    for line in lines[start:]:
        if not line.strip():
            continue
        if line.strip() == "END":
            cards.append(line)
            ended = True
            break
        if len(line) < 8:
            raise HeaderError("Short non-card within primary header")
        key = line[:8].strip()
        cards.append(line)
        if key in {"COMMENT", "HISTORY", ""}:
            continue
        if key == "HIERARCH":
            if "=" not in line:
                raise HeaderError("Malformed HIERARCH card")
            key, value = line.split("=", 1)
            key = " ".join(key.split())
        elif line[8:10] == "= " and re.fullmatch(r"[A-Z0-9_-]{1,8}", key):
            value = line[10:]
        else:
            raise HeaderError("Malformed FITS card")
        if key in header:
            raise HeaderError("Duplicate keyword in primary: " + key)
        header[key] = fits_value(value)
    if not ended:
        raise HeaderError("Primary END card missing")
    if header.get("SIMPLE") is not True:
        raise HeaderError("SIMPLE is not true")
    evidence_prefixes = ("SPEC_RES", "PROCSOFT", "PIPEVERS", "OBSTECH", "HIERARCH ESO INS HEFS ST", "HIERARCH ESO INS MODE", "HIERARCH ESO DRS BERV")
    return header, {"rendering": rendering, "primary_cards": len(cards), "primary_only": True, "compatibility_card_evidence": [card for card in cards if card.startswith(evidence_prefixes)]}


def canonical_name(value):
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def number(header, key):
    value = header.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise HeaderError("Missing/invalid number: " + key)
    return float(value)


def mjd_to_datetime(value):
    return MJD_EPOCH + timedelta(days=float(value))


def check_identity(header, job):
    checks, failures = {}, []
    dp_id, metadata = job["dp_id"], job["metadata"]
    arcfile = str(header.get("ARCFILE", ""))
    checks["exact_adp_identity"] = arcfile == dp_id + ".fits" or arcfile == dp_id
    checks["instrument_harps"] = header.get("INSTRUME") == "HARPS"
    checks["canonical_target"] = canonical_name(header.get("OBJECT")) == canonical_name(job["target"])
    checks["barycentric_spectral_frame"] = header.get("SPECSYS") == "BARYCENT"
    checks["single_exposure"] = header.get("NCOMBINE") == 1 and not isinstance(header.get("NCOMBINE"), bool)
    checks["resolving_power_115000"] = header.get("SPEC_RES") == 115000
    hefs = header.get("HIERARCH ESO INS HEFS ST")
    checks["not_explicit_eggs"] = hefs is not True
    mode_status = "HIGH_RESOLUTION_HEFS_CLOSED" if hefs is False else ("EXPLICIT_EGGS" if hefs is True else "PENDING_MODE_COMPATIBILITY")
    provenance = {key: value for key, value in header.items() if re.fullmatch(r"PROV\d+", key)}
    raw_ids = sorted(set(RAW_RE.findall(" ".join(map(str, provenance.values())))))
    checks["one_raw_progenitor"] = len(raw_ids) == 1
    checks["raw_progenitor_matches_metadata"] = raw_ids == sorted(job["source_file_ids"])
    # A regex match inside mixed provenance is insufficient: every provenance
    # value must be the exact sole expected raw file, with optional .fits.
    expected_provenance = {job["source_file_ids"][0], job["source_file_ids"][0] + ".fits"}
    checks["complete_provenance_exactly_one_expected_raw"] = len(provenance) == 1 and all(isinstance(value, str) and value in expected_provenance for value in provenance.values())
    try:
        observed = number(header, "MJD-OBS")
        checks["mjd_matches_within_1e_7_day"] = abs(observed - float(metadata["t_min"])) <= 1e-7
        date_obs = datetime.fromisoformat(str(header.get("DATE-OBS", "")).replace("Z", "+00:00"))
        if date_obs.tzinfo is None:
            date_obs = date_obs.replace(tzinfo=timezone.utc)
        checks["date_obs_matches_mjd_within_0p02s"] = abs((date_obs - mjd_to_datetime(observed)).total_seconds()) <= .02
        checks["exptime_matches_within_0p02s"] = abs(number(header, "EXPTIME") - float(metadata["t_exptime"])) <= .02
        ra, dec = number(header, "RA"), number(header, "DEC")
        ra_delta = ((ra - float(metadata["s_ra"]) + 180) % 360 - 180) * math.cos(math.radians(float(metadata["s_dec"])))
        separation = 3600 * math.hypot(ra_delta, dec - float(metadata["s_dec"]))
        checks["position_matches_metadata_within_1arcsec"] = separation <= 1
    except (HeaderError, ValueError, TypeError, OverflowError) as error:
        failures.append(str(error))
        separation = None
    for key, passed in checks.items():
        if not passed:
            failures.append(key)
    try:
        berv = number(header, "HIERARCH ESO DRS BERV")
        checks["berv_within_inherited_100km_s_sanity_gate"] = abs(berv) <= 100
        if not checks["berv_within_inherited_100km_s_sanity_gate"]:
            failures.append("berv_within_inherited_100km_s_sanity_gate")
    except HeaderError as error:
        berv = None
        failures.append(str(error))
    retained = {key: header[key] for key in ["ARCFILE", "OBJECT", "INSTRUME", "RA", "DEC", "DATE-OBS", "MJD-OBS", "EXPTIME", "NCOMBINE", "SPECSYS", "HIERARCH ESO DRS BERV", "SPEC_RES", "PROCSOFT", "PIPEVERS", "OBSTECH", "ORIGFILE", "WAVELMIN", "WAVELMAX", "SPEC_BIN", "WAVECAL", "FLUXCAL", "SSYSOBS", "SSYSSRC", "HIERARCH ESO INS OPTI1 NAME", "HIERARCH ESO INS OPTI2 NAME", "HIERARCH ESO INS HEFS ST", "HIERARCH ESO INS MODE", "HIERARCH ESO DRS VERSION", "HIERARCH ESO PRO REC1 PIPE ID"] if key in header}
    retained.update(provenance)
    status = "EXCLUDED_HEADER_VALIDATION" if failures else ("PASS_RECORDED_BERV" if hefs is False else "PENDING_MODE_COMPATIBILITY")
    return {"checks": checks, "failures": failures, "status": status, "mode_status": mode_status, "berv_km_s": berv, "primary_header": retained, "raw_progenitor_ids": raw_ids, "position_difference_arcsec": separation, "table_units_air_wavelength_compatibility": "PROVISIONAL_REQUIRE_PAYLOAD_HEADERS_BEFORE_ARRAY_ACCESS"}
