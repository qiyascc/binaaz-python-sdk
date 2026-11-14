# Async

`AsyncBinaAz` is the async twin of `BinaAz`. It is built from the same resource classes, so it has exactly the same namespaces, methods, arguments and return types. The only difference is `await`.

```python
import asyncio

from binaaz_sdk import AsyncBinaAz


async def main() -> None:
    async with AsyncBinaAz() as bina:
        await bina.auth.login("agency@example.az", "password")
        page = await bina.items.list("published", first=20)
        for item in page.items:
            print(item.id, item.title)


asyncio.run(main())
```

## Creating and closing

Use `async with`, or call `await bina.close()` yourself:

```python
bina = AsyncBinaAz(cookie)
try:
    profile = await bina.profile()
finally:
    await bina.close()
```

The constructor takes the same arguments as `BinaAz`: a cookie, `settings=`, `config_file=`, any setting as a keyword, and `http_client=`, which must be an `httpx.AsyncClient` here.

`bina.cookie`, `bina.set_cookie(...)` and `bina.clear_session()` are plain attributes and methods with no `await`, the same as in the sync client.

## Running calls side by side

The point of async is doing several reads at once. Reading many listings:

```python
async def read_all(bina: AsyncBinaAz, ids: list[str]):
    return await asyncio.gather(*(bina.items.get(item_id) for item_id in ids))
```

Keep the number of parallel requests modest. bina.az answers 429 when it gets too many; the SDK then waits and retries reads, but there is no reason to provoke it. A semaphore keeps the pressure down:

```python
async def read_all(bina: AsyncBinaAz, ids: list[str], limit: int = 4):
    gate = asyncio.Semaphore(limit)

    async def one(item_id: str):
        async with gate:
            return await bina.items.get(item_id)

    return await asyncio.gather(*(one(item_id) for item_id in ids))
```

## One client, one session

A client carries one session. If you work with several bina.az accounts, create one client per account:

```python
async with AsyncBinaAz(cookie_a) as first, AsyncBinaAz(cookie_b) as second:
    a, b = await asyncio.gather(first.items.all(), second.items.all())
```

Do not sign in on a client while other calls on it are running: signing in replaces the session the other calls use.

## Retries and waits

Backoff waits use `asyncio.sleep`, so a client that is waiting for a retry does not block the event loop. The rules about which calls are retried are the same as in the sync client; see [Safety and retries](safety.md).

## In a web framework

Create the client once, when the application starts, and close it when it stops. With FastAPI:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from binaaz_sdk import AsyncBinaAz

bina = AsyncBinaAz()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await bina.close()


app = FastAPI(lifespan=lifespan)


@app.get("/cities")
async def cities():
    return [{"id": place.id, "name": place.name} for place in await bina.catalog.cities()]
```
