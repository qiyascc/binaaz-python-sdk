from __future__ import annotations

import json
from typing import Any, Callable, Union

import httpx
import pytest

from binaaz_sdk import AsyncBinaAz, BinaAz

COOKIE = "_binaaz_session=good"

Reply = Union[httpx.Response, Exception, Callable[[httpx.Request], httpx.Response]]


def data(**fields: Any) -> dict[str, Any]:
    return {"data": fields}


def company(**extra: Any) -> dict[str, Any]:
    return {"__typename": "CompanyProfile", "id": "35339", "name": "Agency", "email": "a@agency.test",
            "phone": "+994501234567", "contactName": "Agent", "agency": {"name": "Agency"}, **extra}


def item(item_id: str = "4123456", state: str = "PUBLISHED") -> dict[str, Any]:
    return {"id": item_id, "title": "3 room flat", "state": state, "path": f"/items/{item_id}",
            "expiresAt": "2026-12-11T10:00:00+04:00", "updatedAt": "2026-11-11T10:00:00+04:00",
            "price": {"total": 120000, "currency": "AZN"}, "photos": [{"thumbnail": "https://img.test/t.jpg"}]}


LISTING: dict[str, Any] = {
    "category_id": 3,
    "is_leased": False,
    "price": 120000,
    "rooms": 3,
    "area": {"value": 85},
    "floor": {"value": 4, "total": 9},
    "location": {"address": "Nizami street 10", "city_id": "1", "latitude": 40.379, "longitude": 49.846},
    "contact": {"type": "AGENT", "name": "Agency"},
    "photo_ids": ["p1", "p2", "p3", "p4"],
}


class Gateway:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.replies: list[Reply] = []

    def reply(self, body: Any = None, status: int = 200, headers: Any = None) -> Gateway:
        content = b"" if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        self.replies.append(httpx.Response(status, content=content, headers=headers))
        return self

    def fail(self, exc: Exception) -> Gateway:
        self.replies.append(exc)
        return self

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        reply = self.replies.pop(0) if self.replies else httpx.Response(200, json={"data": {}})
        if isinstance(reply, Exception):
            raise reply
        if callable(reply):
            return reply(request)
        return reply

    def body(self, index: int = -1) -> dict[str, Any]:
        return dict(json.loads(self.requests[index].content.decode()))

    def header(self, name: str, index: int = -1) -> str:
        return str(self.requests[index].headers.get(name, ""))

    @property
    def hosts(self) -> list[str]:
        return [r.url.host for r in self.requests]

    @property
    def operations(self) -> list[str]:
        out = []
        for r in self.requests:
            try:
                out.append(str(json.loads(r.content.decode()).get("operationName", "")))
            except (ValueError, AttributeError):
                out.append("")
        return out


@pytest.fixture
def gw() -> Gateway:
    return Gateway()


def _quiet(client: Any) -> Any:
    client._backoff = lambda attempt: 0.0
    client._sleep = (lambda seconds: None) if isinstance(client, BinaAz) else _no_wait
    return client


async def _no_wait(seconds: float) -> None:
    return None


@pytest.fixture
def bina(gw: Gateway) -> BinaAz:
    client = BinaAz(COOKIE, max_retries=2, http_client=httpx.Client(transport=httpx.MockTransport(gw)))
    return _quiet(client)


@pytest.fixture
def guest(gw: Gateway) -> BinaAz:
    client = BinaAz(max_retries=2, http_client=httpx.Client(transport=httpx.MockTransport(gw)))
    return _quiet(client)


@pytest.fixture
def abina(gw: Gateway) -> AsyncBinaAz:
    client = AsyncBinaAz(COOKIE, max_retries=2, http_client=httpx.AsyncClient(transport=httpx.MockTransport(gw)))
    return _quiet(client)
