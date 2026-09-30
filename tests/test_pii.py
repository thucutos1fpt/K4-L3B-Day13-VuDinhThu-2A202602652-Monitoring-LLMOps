from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out

def test_scrub_labeled_passport() -> None:
    passport = "Passport: C12345678"

    out = scrub_text(passport)

    assert passport not in out
    assert "REDACTED_PASSPORT" in out


def test_scrub_labeled_address() -> None:
    address = "Address: 123 Nguyen Hue, District 1"

    out = scrub_text(address)

    assert address not in out
    assert "REDACTED_VN_ADDRESS" in out
