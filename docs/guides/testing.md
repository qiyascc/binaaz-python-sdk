# Testing your code

Code that posts listings should be tested without posting real listings. The SDK is built on httpx, and httpx can swap the network for a plain Python function with `httpx.MockTransport`. The SDK's own test suite works that way, and so can yours.

## The idea

1. Write a function that receives an `httpx.Request` and returns an `httpx.Response`.
2. Wrap it in `httpx.MockTransport` and an `httpx.Client`.
3. Pass that client to `BinaAz` as `http_client=`.

Every request the SDK makes now goes to your function. Nothing leaves the machine.

## A complete test

Say your code has this function:

```python
from binaaz_sdk import BinaAz, Listing


def post_flat(bina: BinaAz, listing: Listing) -> str:
    result = bina.items.create(listing)
    return result.url
```

A pytest test for it:

```python
import json

import httpx
import pytest

from binaaz_sdk import BinaAz, ItemError, Listing

LISTING = Listing(
    category_id=3,
    is_leased=False,
    price=120000,
    area={"value": 85},
    location={"address": "Nizami street 10", "city_id": "1", "latitude": 40.379, "longitude": 49.846},
    contact={"type": "AGENT", "name": "Agency"},
    photo_ids=["p1", "p2", "p3", "p4"],
)


def client(handler) -> BinaAz:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return BinaAz("_binaaz_session=test", max_retries=0, http_client=http)


def test_post_flat_returns_the_url():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"data": {"createItem": {
            "status": "SUCCESS",
            "item": {"id": "4123456", "path": "/items/4123456", "state": "PENDING"},
            "errors": [],
        }}})

    assert post_flat(client(handler), LISTING) == "https://bina.az/items/4123456"
    assert seen[0]["operationName"] == "CreateItem"
    assert seen[0]["variables"]["input"]["price"] == 120000


def test_post_flat_when_bina_az_refuses():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"createItem": {
            "status": "RESTRICTED", "item": None, "errors": [],
        }}})

    with pytest.raises(ItemError) as info:
        post_flat(client(handler), LISTING)
    assert info.value.status == "RESTRICTED"
```

`max_retries=0` keeps a failing test fast: without it the client would wait between retries for reads.

## What answers look like

GraphQL calls go to `https://bina.az/graphql` as a POST with `operationName` and `variables` in the JSON body. Answer with `{"data": {...}}` the way bina.az does. The names to answer with are the GraphQL fields: `createItem`, `updateItem`, `deleteItem`, `prolongItem`, `payForItem`, `createPayment` for writes, `profile`, `itemEdit` and `paidServices` for reads.

Route on the operation when one test makes several calls:

```python
def handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    if body.get("operationName") == "Profile":
        return httpx.Response(200, json={"data": {"profile": {"__typename": "CompanyProfile", "id": "1", "name": "Agency"}}})
    if body.get("operationName") == "CreateItem":
        return httpx.Response(200, json={"data": {"createItem": {"status": "SUCCESS", "item": {"id": "9", "path": "/items/9", "state": "PENDING"}, "errors": []}}})
    return httpx.Response(404)
```

Photo uploads go to `https://photos.bina.az/pond?lang=az` as a multipart form, and the photo service answers `{"photos": [{"id": "...", "thumbnail_url": "..."}]}`.

## Testing failures

Raise an httpx exception from the handler to simulate the network:

```python
from binaaz_sdk import OutcomeUnknownError


def test_create_times_out():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(OutcomeUnknownError):
        post_flat(client(handler), LISTING)
```

`httpx.ConnectError` simulates a connection that never opened (`NotSentError` after the retries), `httpx.ReadTimeout` one that opened and went quiet.

## Async tests

The same handler works with `httpx.AsyncClient`:

```python
import httpx
import pytest

from binaaz_sdk import AsyncBinaAz


@pytest.mark.asyncio
async def test_async_profile():
    def handler(request):
        return httpx.Response(200, json={"data": {"profile": {"__typename": "CompanyProfile", "id": "1", "name": "Agency"}}})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AsyncBinaAz("_binaaz_session=test", http_client=http) as bina:
        profile = await bina.profile()
    assert profile.is_company
```

This needs `pytest-asyncio`. The SDK's own tests in [tests/conftest.py](https://github.com/qiyascc/binaaz-python-sdk/blob/main/tests/conftest.py) have a small `Gateway` class that queues answers and records requests, which is worth copying for larger suites.
