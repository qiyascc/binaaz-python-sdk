from __future__ import annotations

import httpx
import pytest

from binaaz_sdk import (
    AuthenticationError,
    BlockedError,
    GraphQLError,
    NotSentError,
    OutcomeUnknownError,
    RateLimitError,
    TransportError,
)

from .conftest import LISTING, data, item

CHALLENGE = {"server": "cloudflare", "content-type": "text/html", "cf-mitigated": "challenge"}


@pytest.mark.parametrize("exc", [httpx.ReadTimeout("slow"), httpx.RemoteProtocolError("cut"), httpx.ReadError("x")])
def test_a_listing_is_never_resent_after_an_ambiguous_failure(gw, bina, exc):
    gw.fail(exc)
    with pytest.raises(OutcomeUnknownError):
        bina.items.create(LISTING)
    assert len(gw.requests) == 1


def test_server_error_on_a_write_is_unknown(gw, bina):
    gw.reply({"message": "boom"}, status=502)
    with pytest.raises(OutcomeUnknownError) as info:
        bina.items.delete("4123456")
    assert info.value.status_code == 502 and len(gw.requests) == 1


def test_garbage_success_on_a_write_is_unknown(gw, bina):
    gw.reply(b"<html>ok</html>")
    with pytest.raises(OutcomeUnknownError):
        bina.items.prolong("4123456")


def test_a_photo_upload_is_not_resent(gw, bina):
    gw.fail(httpx.ReadTimeout("slow"))
    with pytest.raises(OutcomeUnknownError):
        bina.photos.upload(b"\xff\xd8jpeg")
    assert len(gw.requests) == 1


def test_connection_refused_is_retried_because_nothing_was_sent(gw, bina):
    gw.fail(httpx.ConnectError("refused")).reply(data(createItem={"status": "SUCCESS", "item": {"id": "1"},
                                                                  "errors": []}))
    assert bina.items.create(LISTING).id == "1"
    assert len(gw.requests) == 2


def test_connection_refused_every_time(gw, bina):
    for _ in range(3):
        gw.fail(httpx.ConnectError("refused"))
    with pytest.raises(NotSentError):
        bina.items.create(LISTING)


def test_reads_retry(gw, bina):
    gw.reply(b"", status=503).fail(httpx.ReadTimeout("slow")).reply(data(itemEdit={"item": item()}))
    assert bina.items.get("4123456").id == "4123456"
    assert len(gw.requests) == 3


def test_reads_give_up(gw, bina):
    for _ in range(3):
        gw.fail(httpx.ReadTimeout("slow"))
    with pytest.raises(TransportError):
        bina.catalog.cities()


def test_rate_limit_waits_and_retries(gw, bina):
    gw.reply({}, status=429, headers={"retry-after": "1"}).reply(data(cities=[{"id": "1", "name": "Baku"}]))
    assert bina.catalog.cities()[0].name == "Baku"
    for _ in range(3):
        gw.reply({}, status=429)
    with pytest.raises(RateLimitError):
        bina.catalog.cities()


def test_cloudflare_challenge_is_not_solved(gw, bina):
    gw.reply(b"<html>challenge</html>", status=403, headers=CHALLENGE)
    with pytest.raises(BlockedError) as info:
        bina.items.get("4123456")
    assert "bina.az" in str(info.value) and len(gw.requests) == 1


def test_rejected_session(gw, bina):
    gw.reply({"error": "unauthorized"}, status=401)
    with pytest.raises(AuthenticationError):
        bina.items.get("4123456")
    gw.reply({"data": {"itemEdit": None}, "errors": [{"message": "Server refuses to authorize request",
                                                      "extensions": {"code": "FORBIDDEN"}}]})
    with pytest.raises(AuthenticationError):
        bina.items.get("4123456")


def test_other_graphql_errors(gw, bina):
    gw.reply({"errors": [{"message": "Field 'x' doesn't exist", "path": ["query"]}]})
    with pytest.raises(GraphQLError) as info:
        bina.graphql("{ x }")
    assert info.value.errors[0]["message"].startswith("Field")


def test_renewed_cookies_are_kept(gw, bina):
    gw.reply(data(cities=[]), headers=[("set-cookie", "_binaaz_session=renewed; path=/"),
                                       ("set-cookie", "cf_clearance=x; path=/")])
    bina.catalog.cities()
    assert bina.cookie == "_binaaz_session=renewed"
