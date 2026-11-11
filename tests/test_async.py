from __future__ import annotations

import httpx
import pytest

from binaaz_sdk import ItemState, OutcomeUnknownError

from .conftest import LISTING, company, data, item


async def test_async_code_login_and_listing(gw, abina):
    gw.reply({"code_requests_left": 2})
    gw.reply({"access_token": "tok"})
    gw.reply(data(signIn={"profile": {"__typename": "CompanyProfile", "id": "1"}, "errors": []}),
             headers=[("set-cookie", "_binaaz_session=async; path=/")])
    gw.reply(data(profile=company()))
    sent = await abina.auth.send_code("0501234567")
    profile = await abina.auth.verify_code("0501234567", "1234")
    assert sent.code_requests_left == 2 and profile.name == "Agency" and abina.cookie == "_binaaz_session=async"
    gw.reply(data(createItem={"status": "SUCCESS", "item": {"id": "9", "state": "PENDING"}, "errors": []}))
    assert (await abina.items.create(LISTING)).state is ItemState.PENDING
    page = {"totalCount": 1, "pageInfo": {"hasNextPage": False}, "nodes": [item("9")]}
    gw.reply(data(profile=company(items=page)))
    assert [i.id for i in await abina.items.all()] == ["9"]
    await abina.close()


async def test_async_write_is_not_resent(gw, abina):
    gw.fail(httpx.ReadTimeout("slow"))
    with pytest.raises(OutcomeUnknownError):
        await abina.items.delete("9")
    assert len(gw.requests) == 1


async def test_async_context_manager():
    from binaaz_sdk import AsyncBinaAz

    async with AsyncBinaAz() as client:
        assert client.cookie == ""
