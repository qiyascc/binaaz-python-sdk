from __future__ import annotations

import base64

import httpx
import pytest

from binaaz_sdk import (
    AuthenticationError,
    BadRequestError,
    BinaAz,
    CodeRejectedError,
    InvalidRequestError,
    OutcomeUnknownError,
    RateLimitError,
    ServerError,
)

from .conftest import COOKIE, company, data

SIGNED_IN = data(signIn={"profile": {"__typename": "CompanyProfile", "id": "35339", "name": "Agency"}, "errors": []})
SESSION_HEADERS = [("set-cookie", "_binaaz_session=fresh; path=/; secure; HttpOnly"),
                   ("set-cookie", "remember_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"),
                   ("set-cookie", "__cf_bm=edge; path=/")]


def test_password_login_keeps_the_session_cookie(gw, guest):
    gw.reply(SIGNED_IN, headers=SESSION_HEADERS).reply(data(profile=company()))
    profile = guest.auth.login("agency@example.az", "secret")
    assert profile.is_company and profile.name == "Agency" and profile.agency == "Agency"
    assert guest.cookie == "_binaaz_session=fresh"
    assert gw.body(0)["variables"] == {"input": {"emailAndPassword": {"email": "agency@example.az",
                                                                      "password": "secret"}}}
    assert gw.header("cookie", 0) == "" and gw.header("cookie", 1) == "_binaaz_session=fresh"


def test_wrong_password_keeps_the_previous_session(gw, bina):
    gw.reply(data(signIn={"profile": None, "errors": [{"message": "Email or password is not valid",
                                                       "path": ["emailAndPassword"]}]}))
    with pytest.raises(BadRequestError) as info:
        bina.auth.login("agency@example.az", "wrong")
    assert "not valid" in str(info.value)
    assert bina.cookie == COOKIE


def test_login_without_a_cookie_is_an_error(gw, guest):
    gw.reply(SIGNED_IN)
    with pytest.raises(ServerError):
        guest.auth.login("agency@example.az", "secret")


def test_send_code_normalises_the_phone(gw, guest):
    gw.reply({"code_requests_left": 2})
    sent = guest.auth.send_code("+994 50 123 45 67")
    assert sent.phone == "0501234567" and sent.code_requests_left == 2 and not sent.retried
    request = gw.requests[0]
    assert request.url == "https://api.digit-u.id/auth"
    assert gw.body() == {"phone": "0501234567"}
    assert gw.header("accept-language") == "az" and gw.header("cookie") == ""


@pytest.mark.parametrize("phone", ["12345", "012 345 67 89", ""])
def test_a_bad_phone_is_refused_before_sending(gw, guest, phone):
    with pytest.raises(InvalidRequestError):
        guest.auth.send_code(phone)
    assert not gw.requests


def test_flaky_login_service_answers_are_retried(gw, guest):
    gw.reply(b"<html>oops</html>", status=403).reply({"message": "x"}, status=401).reply({"code_requests_left": 1})
    sent = guest.auth.send_code("0501234567")
    assert sent.retried and sent.more_than_one_sms and len(gw.requests) == 3


def test_the_login_service_is_given_up_after_three_answers(gw, guest):
    for _ in range(3):
        gw.reply(b"", status=500)
    with pytest.raises(ServerError) as info:
        guest.auth.send_code("0501234567")
    assert "3 attempts" in str(info.value) and len(gw.requests) == 3


def test_a_timeout_on_the_login_service_is_not_resent(gw, guest):
    gw.fail(httpx.ReadTimeout("slow"))
    with pytest.raises(OutcomeUnknownError):
        guest.auth.send_code("0501234567")
    assert len(gw.requests) == 1


def test_too_many_codes(gw, guest):
    gw.reply({"error": "code_requests", "message": "Limit"}, status=422)
    with pytest.raises(RateLimitError):
        guest.auth.send_code("0501234567")
    assert len(gw.requests) == 1


def test_verify_code_signs_in_with_the_access_token(gw, guest):
    gw.reply({"access_token": "tok", "redirect_url": "https://bina.az/"})
    gw.reply(SIGNED_IN, headers=SESSION_HEADERS).reply(data(profile=company()))
    profile = guest.auth.verify_code("050 123 45 67", "1234")
    assert profile.id == "35339" and guest.cookie == "_binaaz_session=fresh"
    verify = gw.body(0)
    assert verify["phone"] == "0501234567" and verify["code"] == "1234"
    assert base64.b64decode(verify["return_to"]) == b"https://bina.az/"
    assert gw.body(1)["variables"] == {"input": {"accessToken": "tok"}}
    assert gw.hosts == ["api.digit-u.id", "bina.az", "bina.az"]


def test_a_wrong_code(gw, guest):
    gw.reply({"error": "code", "message": "Kod yanlisdir"}, status=422)
    with pytest.raises(CodeRejectedError) as info:
        guest.auth.verify_code("0501234567", "0000")
    assert "earlier attempt" not in str(info.value)


def test_a_code_rejected_after_a_retry_may_be_used_up(gw, guest):
    gw.reply(b"", status=502).reply({"error": "code", "message": "Kod yanlisdir"}, status=422)
    with pytest.raises(CodeRejectedError) as info:
        guest.auth.verify_code("0501234567", "1234")
    assert "earlier attempt" in str(info.value)


def test_profile_without_a_session(gw, guest):
    gw.reply(data(profile=None))
    with pytest.raises(AuthenticationError):
        guest.profile()


@pytest.mark.parametrize("cookie", [
    "_binaaz_session=good",
    "Cookie: _binaaz_session=good; cf_clearance=x",
    {"_binaaz_session": "good", "__cf_bm": "x"},
    [{"name": "_binaaz_session", "value": "good", "domain": ".bina.az"}],
    '[{"name": "_binaaz_session", "value": "good"}]',
])
def test_cookie_formats(cookie):
    assert BinaAz(cookie).cookie == COOKIE


def test_an_unreadable_cookie_is_refused():
    with pytest.raises(InvalidRequestError):
        BinaAz("nothing here")


def test_clear_session(bina):
    bina.clear_session()
    assert bina.cookie == ""
