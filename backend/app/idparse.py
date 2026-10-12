"""Parses the Qatar ID's MRZ (Machine Readable Zone) on the back of the card.

Format: ICAO Doc 9303 Part 5, "TD1" — three lines of 30 characters, the same standard used
by most ID-1 sized national ID cards worldwide. Most USB MRZ readers and camera-based ID
scanning SDKs hand back exactly this: three 30-character lines (sometimes newline-separated,
sometimes concatenated into one 90-character string). Both are accepted here.

  Line 1 (30): DDCCCNNNNNNNNNCOOOOOOOOOOOOOOO
               DD   = document code (starts with 'I' for an identity card)
               CCC  = issuing state, 3 letters (expected "QAT" for a Qatar-issued ID)
               NNNNNNNNN = document (card) number, 9 chars
               C    = check digit over the document number
               O... = optional data, 15 chars — see ASSUMPTION below

  Line 2 (30): BBBBBBCSEEEEEEC NNNOOOOOOOOOOOC
               BBBBBB = date of birth, YYMMDD
               C      = check digit over date of birth
               S      = sex: M / F / <
               EEEEEE = date of expiry, YYMMDD
               C      = check digit over date of expiry
               NNN    = nationality, 3 letters
               O...   = optional data, 11 chars
               C      = composite check digit over most of the above

  Line 3 (30): SURNAME<<GIVEN<NAMES<<<<<<<<<<<<<<<<<<<<  (padded with '<')

ASSUMPTION — please verify against a real card:
  The standard 9-character "document number" field (line 1) is too short for Qatar's
  11-digit QID number, so this parser reads the QID from line 1's 15-character optional
  data field instead, which is the common placement for a national personal number on
  TD1-format cards. If a real Qatar ID turns out to encode the QID differently, only
  `_extract_qid()` below needs to change — everything else (dates, name, nationality,
  check-digit validation) follows the public ICAO standard and does not need to change.
"""
import re
from dataclasses import dataclass
from datetime import date, datetime

ISSUING_STATE = "QAT"
TODAY_FOR_CENTURY = lambda: date.today()  # overridable in tests

_CHAR_VALUE = {c: i for i, c in enumerate("0123456789")}
_CHAR_VALUE.update({c: i + 10 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")})
_CHAR_VALUE["<"] = 0
_WEIGHTS = (7, 3, 1)

_NATIONALITY_NAMES = {
    "QAT": "Qatari", "IND": "Indian", "PAK": "Pakistani", "BGD": "Bangladeshi",
    "NPL": "Nepali", "PHL": "Filipino", "EGY": "Egyptian", "LKA": "Sri Lankan",
    "GBR": "British", "USA": "American", "DEU": "German", "FRA": "French",
    "LBN": "Lebanese", "JOR": "Jordanian", "SYR": "Syrian", "SDN": "Sudanese",
    "SAU": "Saudi", "ARE": "Emirati", "KWT": "Kuwaiti", "BHR": "Bahraini",
    "OMN": "Omani", "YEM": "Yemeni", "TUR": "Turkish", "IDN": "Indonesian",
    "KEN": "Kenyan", "ZAF": "South African", "CAN": "Canadian", "AUS": "Australian",
}


class MrzError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedId:
    id_number: str
    full_name: str
    date_of_birth: date
    nationality: str
    id_expiry: date
    gender: str


def _checksum(s: str) -> int:
    total = 0
    for i, ch in enumerate(s):
        value = _CHAR_VALUE.get(ch)
        if value is None:
            raise MrzError(f"Invalid MRZ character: {ch!r}")
        total += value * _WEIGHTS[i % 3]
    return total % 10


def _check_digit(data: str, digit_char: str, field_name: str) -> None:
    if not digit_char.isdigit() or _checksum(data) != int(digit_char):
        raise MrzError(f"Check digit failed for {field_name} (scan may be corrupted)")


def _resolve_year(yy: int, *, reference: date, must_not_be_future: bool) -> int:
    """A 2-digit MRZ year is ambiguous between centuries (yy=29 could be 1929 or 2029).
    Dates of birth must not be in the future; an ID's expiry can be either (a card can
    already be expired, which we flag rather than reject). Either way, the right century
    is whichever candidate lands closest to today -- Qatar's MRZ-based ID program is a
    2000s-era system, so this resolves correctly across its entire realistic date range."""
    candidates = [2000 + yy, 1900 + yy, 2100 + yy]
    if must_not_be_future:
        candidates = [y for y in candidates if y <= reference.year] or candidates
    return min(candidates, key=lambda y: abs(y - reference.year))


def _parse_mrz_date(field: str, *, reference: date, must_not_be_future: bool) -> date:
    if not re.fullmatch(r"\d{6}", field):
        raise MrzError(f"Bad date field: {field!r}")
    yy, mm, dd = int(field[0:2]), int(field[2:4]), int(field[4:6])
    year = _resolve_year(yy, reference=reference, must_not_be_future=must_not_be_future)
    try:
        return date(year, mm, dd)
    except ValueError as exc:
        raise MrzError(f"Invalid calendar date in MRZ: {field!r}") from exc


def _extract_qid(line1: str) -> str:
    """See the ASSUMPTION note at the top of this file."""
    optional = line1[15:30].rstrip("<")
    if re.fullmatch(r"\d{8,11}", optional):
        return optional
    # Fall back to the standard document-number field if optional data isn't usable.
    doc_number = line1[5:14].rstrip("<")
    if doc_number:
        return doc_number
    raise MrzError("Could not find a usable ID number in the MRZ")


def _format_name(line3: str) -> str:
    primary, _, secondary = line3.rstrip("<").partition("<<")
    given = " ".join(part for part in secondary.split("<") if part)
    surname = primary.replace("<", " ").strip()
    full = f"{given} {surname}".strip()
    if not full:
        raise MrzError("Empty name in MRZ")
    return " ".join(w.capitalize() for w in full.split())  # MRZ is all caps; capitalize for display


def _split_lines(raw: str) -> list[str]:
    text = raw.strip().replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if len(lines) == 1 and len(lines[0]) == 90:
        joined = lines[0]
        lines = [joined[0:30], joined[30:60], joined[60:90]]
    if len(lines) != 3 or any(len(ln) != 30 for ln in lines):
        raise MrzError("Expected a 3-line, 30-character-per-line MRZ (TD1 format)")
    return [ln.upper() for ln in lines]


def parse_mrz_td1(raw: str) -> ParsedId:
    if len(raw) > 400:
        raise MrzError("Input too long to be an MRZ scan")
    line1, line2, line3 = _split_lines(raw)

    if not line1.startswith("I"):
        raise MrzError(f"Not an identity-card MRZ (document code {line1[0:2]!r})")
    issuing_state = line1[2:5]
    if issuing_state != ISSUING_STATE:
        raise MrzError(f"Unexpected issuing state {issuing_state!r}, expected {ISSUING_STATE!r}")

    _check_digit(line1[5:14], line1[14], "document number")
    qid = _extract_qid(line1)

    dob_field, dob_check = line2[0:6], line2[6]
    _check_digit(dob_field, dob_check, "date of birth")
    sex_char = line2[7]
    expiry_field, expiry_check = line2[8:14], line2[14]
    _check_digit(expiry_field, expiry_check, "date of expiry")
    nationality = line2[15:18]

    composite_data = line1[5:30] + line2[0:7] + line2[8:15] + line2[18:29]
    _check_digit(composite_data, line2[29], "composite")

    today = TODAY_FOR_CENTURY()
    dob = _parse_mrz_date(dob_field, reference=today, must_not_be_future=True)
    expiry = _parse_mrz_date(expiry_field, reference=today, must_not_be_future=False)

    gender = {"M": "Male", "F": "Female"}.get(sex_char, "Other")
    nationality_name = _NATIONALITY_NAMES.get(nationality, nationality)

    return ParsedId(
        id_number=qid,
        full_name=_format_name(line3),
        date_of_birth=dob,
        nationality=nationality_name,
        id_expiry=expiry,
        gender=gender,
    )


PARSERS = [parse_mrz_td1]


def parse_id(raw: str) -> ParsedId:
    errors = []
    for parser in PARSERS:
        try:
            return parser(raw)
        except MrzError as exc:
            errors.append(str(exc))
    raise ValueError("; ".join(errors) or "Unrecognised ID format")
