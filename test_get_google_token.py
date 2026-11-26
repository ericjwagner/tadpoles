import base64
import hashlib
import urllib.parse

import pytest

from get_google_token import build_auth_url, make_pkce_pair, parse_redirect


def test_parse_redirect_returns_code():
    url = "http://127.0.0.1:8765/?state=abc&code=4%2F0AbCd&scope=x"
    assert parse_redirect(url, "abc") == "4/0AbCd"


def test_parse_redirect_strips_whitespace():
    url = "  http://127.0.0.1:8765/?state=abc&code=xyz \n"
    assert parse_redirect(url, "abc") == "xyz"


def test_parse_redirect_rejects_wrong_state():
    with pytest.raises(ValueError, match="state"):
        parse_redirect("http://127.0.0.1:8765/?state=old&code=xyz", "new")


def test_parse_redirect_reports_google_error():
    with pytest.raises(ValueError, match="access_denied"):
        parse_redirect("http://127.0.0.1:8765/?error=access_denied&state=abc", "abc")


def test_parse_redirect_requires_code():
    with pytest.raises(ValueError, match="No code"):
        parse_redirect("http://127.0.0.1:8765/?state=abc", "abc")


def test_pkce_challenge_matches_verifier():
    verifier, challenge = make_pkce_pair()
    assert 43 <= len(verifier) <= 128
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    assert challenge == expected.decode()


def test_auth_url_uses_loopback_and_pkce():
    url = build_auth_url("cid", "http://127.0.0.1:8765/", "st", "ch")
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert q["redirect_uri"] == ["http://127.0.0.1:8765/"]
    assert q["access_type"] == ["offline"]
    assert q["code_challenge_method"] == ["S256"]
    assert q["state"] == ["st"]
    assert "oob" not in url
