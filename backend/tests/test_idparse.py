import pytest

from app.idparse import parse_id, parse_mrz_td1

# Valid vector, hand-computed and verified against the ICAO 9303 TD1 check-digit algorithm.
# Ahmed Khalid Al-Marri, QID 29850123456, DOB 1985-03-14, expires 2029-06-30 (not expired).
VALID_LINE1 = "IDQAT123456789729850123456<<<<"
VALID_LINE2 = "8503149M2906302QAT<<<<<<<<<<<5"
VALID_LINE3 = "ALMARRI<<AHMED<KHALID<<<<<<<<<"
VALID_MRZ = "\n".join([VALID_LINE1, VALID_LINE2, VALID_LINE3])

# Second vector: Mariam Yusuf, QID 29655544331, expired 2020-01-15 -- must still parse.
EXPIRED_LINE1 = "IDQAT987654321329655544331<<<<"
EXPIRED_LINE2 = "9001011F2001159QAT<<<<<<<<<<<7"
EXPIRED_LINE3 = "YUSUF<<MARIAM<<<<<<<<<<<<<<<<<"
EXPIRED_MRZ = "\n".join([EXPIRED_LINE1, EXPIRED_LINE2, EXPIRED_LINE3])


def test_valid_mrz_parses_all_fields():
    p = parse_mrz_td1(VALID_MRZ)
    assert p.id_number == "29850123456"
    assert p.full_name == "Ahmed Khalid Almarri"
    assert str(p.date_of_birth) == "1985-03-14"
    assert str(p.id_expiry) == "2029-06-30"
    assert p.nationality == "Qatari"
    assert p.gender == "Male"


def test_single_line_90_char_variant_matches():
    joined = VALID_LINE1 + VALID_LINE2 + VALID_LINE3
    assert parse_mrz_td1(joined) == parse_mrz_td1(VALID_MRZ)


def test_expired_card_still_parses_not_blocked():
    """Business rule: an expired ID is flagged by the API layer, never rejected by the parser."""
    p = parse_mrz_td1(EXPIRED_MRZ)
    assert p.id_number == "29655544331"
    assert str(p.id_expiry) == "2020-01-15"
    assert p.gender == "Female"


def test_wrong_issuing_state_rejected():
    tampered = VALID_LINE1.replace("QAT", "ARE", 1)
    bad_mrz = "\n".join([tampered, VALID_LINE2, VALID_LINE3])
    with pytest.raises(ValueError, match="issuing state"):
        parse_mrz_td1(bad_mrz)


def test_corrupted_document_number_check_digit_rejected():
    corrupted = VALID_LINE1[:10] + "9" + VALID_LINE1[11:]  # flips a digit inside the doc number
    bad_mrz = "\n".join([corrupted, VALID_LINE2, VALID_LINE3])
    with pytest.raises(ValueError, match="[Cc]heck digit"):
        parse_mrz_td1(bad_mrz)


def test_corrupted_composite_check_digit_rejected():
    corrupted_line2 = VALID_LINE2[:-1] + ("0" if VALID_LINE2[-1] != "0" else "1")
    bad_mrz = "\n".join([VALID_LINE1, corrupted_line2, VALID_LINE3])
    with pytest.raises(ValueError, match="[Cc]omposite"):
        parse_mrz_td1(bad_mrz)


@pytest.mark.parametrize("raw", [
    "not an mrz at all",
    "x" * 500,
    "",
    VALID_LINE1 + "\n" + VALID_LINE2,          # missing third line
    VALID_LINE1[:-1] + "\n" + VALID_LINE2 + "\n" + VALID_LINE3,  # wrong line length
])
def test_malformed_input_rejected(raw):
    with pytest.raises(ValueError):
        parse_id(raw)


def test_passport_mrz_td3_rejected_not_an_id_card():
    # TD3 (passport) document code starts with 'P', not 'I' -- must be rejected, not misread.
    fake_passport_line = "P<QATDOE<<JOHN<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"[:30]
    with pytest.raises(ValueError):
        parse_mrz_td1("\n".join([fake_passport_line, VALID_LINE2, VALID_LINE3]))
