# tests/scope01/test_email_normalization_stress.py
from __future__ import annotations

import string
import unicodedata
import pytest
from server.app.security import normalize_email


def test_unicode_casefolding():
    # Turkish dotted capital I: 'İ' -> 'i\u0307' under casefold()
    turkish_email = "İ@gmail.com"
    normalized = normalize_email(turkish_email)
    assert normalized == "i\u0307@gmail.com"

    # German sharp S: 'ß' -> 'ss'
    german_email = "STRAßE@gmail.com"
    assert normalize_email(german_email) == "strasse@gmail.com"

    # Greek uppercase
    greek = "ΔΟΚΙΜΗ@gmail.com"
    assert normalize_email(greek) == "δοκιμη@gmail.com"


def test_unicode_whitespace_and_invisible_chars():
    # Various whitespace characters: non-breaking space, em-space, ideographic space
    ws_email = "\u00a0\u2003john.doe+test@gmail.com\u3000\t\n"
    assert normalize_email(ws_email) == "johndoe@gmail.com"


def test_subaddressing_and_plus_combinations():
    # Multiple pluses
    assert normalize_email("user+tag1+tag2+tag3@gmail.com") == "user@gmail.com"
    assert normalize_email("user++extra@gmail.com") == "user@gmail.com"
    assert normalize_email("user+@gmail.com") == "user@gmail.com"

    # Plus sign with non-gmail
    assert normalize_email("user+tag@custom.org") == "user@custom.org"
    assert normalize_email("user+tag1+tag2@custom.org") == "user@custom.org"


def test_dots_in_local_part():
    # Many consecutive dots in Gmail
    assert normalize_email("a.b.c.d.e.f@gmail.com") == "abcdef@gmail.com"
    assert normalize_email("a...b...c@gmail.com") == "abc@gmail.com"
    assert normalize_email("...abc...@gmail.com") == "abc@gmail.com"

    # Googlemail
    assert normalize_email("a.b.c@googlemail.com") == "abc@gmail.com"

    # Dots preserved in non-Gmail
    assert normalize_email("john.doe@enterprise.com") == "john.doe@enterprise.com"
    assert normalize_email("first.middle.last@navy.mil") == "first.middle.last@navy.mil"


def test_edge_and_malformed_inputs():
    # Empty string
    assert normalize_email("") == ""
    assert normalize_email("   ") == ""

    # No @ symbol
    assert normalize_email("admin") == "admin"
    assert normalize_email("  OPERATOR_SUPER  ") == "operator_super"

    # Only @
    assert normalize_email("@") == "@"

    # Leading @ (empty local part)
    assert normalize_email("@gmail.com") == "@gmail.com"
    assert normalize_email("@custom.org") == "@custom.org"

    # Leading plus (empty local part before plus)
    assert normalize_email("+tag@gmail.com") == "@gmail.com"

    # Trailing @ (empty domain)
    assert normalize_email("user@") == "user@"

    # Multiple @ signs
    assert normalize_email("user@sub@domain.com") == "user@sub@domain.com"


def test_domain_variations():
    # Domain case insensitivity
    assert normalize_email("user@GMAIL.COM") == "user@gmail.com"
    assert normalize_email("user@GOOGLEMAIL.COM") == "user@gmail.com"
    assert normalize_email("user@OUTLOOK.COM") == "user@outlook.com"

    # Lookalike domains
    assert normalize_email("user.name@notgmail.com") == "user.name@notgmail.com"
    assert normalize_email("user.name@gmail.com.fake.io") == "user.name@gmail.com.fake.io"
    assert normalize_email("user.name@googlemail.org") == "user.name@googlemail.org"


def test_fuzzing_random_inputs():
    import random
    rng = random.Random(42)
    chars = string.ascii_letters + string.digits + ".+@-_ "

    for _ in range(5000):
        length = rng.randint(0, 50)
        sample = "".join(rng.choice(chars) for _ in range(length))
        # normalize_email must never raise an unhandled exception
        result = normalize_email(sample)
        assert isinstance(result, str)
