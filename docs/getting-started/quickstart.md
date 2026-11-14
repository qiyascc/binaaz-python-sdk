# Quickstart

This walk through posts one apartment listing on bina.az from a short script. It assumes the SDK is installed ([Installation](installation.md)) and that you have a bina.az company account (an agency or a residence) with an email and a password. Phone accounts work the same way, only the sign in differs; see [Signing in](sign-in.md).

## 1. Prepare a folder

```text
my-project/
    post.py
    photos/
        1.jpg
        2.jpg
        3.jpg
        4.jpg
```

bina.az wants at least 4 and at most 30 photos on a listing. JPEG and PNG both work.

## 2. Sign in and keep the session

Put this at the top of `post.py`:

```python
from pathlib import Path

from binaaz_sdk import BinaAz, Category, ContactType, Listing

SESSION = Path("binaaz.session")

bina = BinaAz(SESSION.read_text() if SESSION.exists() else None)
if not SESSION.exists():
    bina.auth.login("agency@example.az", "password")
    SESSION.write_text(bina.cookie)
```

The first run signs in and writes the session cookie to `binaaz.session`. Later runs read it back and skip the sign in. Add `binaaz.session` to `.gitignore`.

## 3. Find the city id

Listings point at a city by id. The catalog is public, so this works with any client:

```python
for city in bina.catalog.cities():
    print(city.id, city.name)
```

The examples in these docs use city `"1"` with coordinates in Baku; look up the id of your own city in that list. For a district or a township use `bina.catalog.regions(city_id)` and `bina.catalog.townships(region_id)`; the [catalog guide](../guides/catalog.md) has the details.

## 4. Upload the photos

```python
photos = bina.photos.upload_many(sorted(Path("photos").glob("*.jpg")))
photo_ids = [photo.id for photo in photos]
```

Each upload returns a {py:class}`~binaaz_sdk.Photo` with the id bina.az gave it. The ids are what the listing needs.

## 5. Describe the listing

```python
listing = Listing(
    category_id=Category.APARTMENT_OLD_BUILDING,
    is_leased=False,
    price=120000,
    rooms=3,
    area={"value": 85},
    floor={"value": 4, "total": 9},
    location={
        "address": "Nizami street 10",
        "city_id": "1",
        "latitude": 40.379,
        "longitude": 49.846,
    },
    contact={"type": ContactType.AGENT, "name": "Agency"},
    photo_ids=photo_ids,
    description="Renovated three room flat near the metro.",
    has_repair=True,
    has_bill_of_sale=True,
)
```

Line by line:

- `category_id` is the kind of property. `Category.APARTMENT_OLD_BUILDING` is a flat in an old building; the [listings guide](../guides/listings.md) lists every category.
- `is_leased=False` means the flat is for sale. `True` means rent.
- `price` is a whole number in AZN.
- `area` is in square metres. Houses and land can add `"land"` for the plot size.
- `floor` is the floor of the flat and the number of floors in the building. The model refuses a floor above the top floor.
- `location` needs a street address, the city id and the coordinates of the pin on the map.
- `contact` says whether the listing is from the owner or an agent, and the name to show.
- `photo_ids` are the ids from step 4.

If a value breaks a rule, `Listing(...)` raises a pydantic `ValidationError` right here, before anything is sent.

## 6. Post it

```python
result = bina.items.create(listing)
print(result.id, result.state, result.url)
```

A new listing starts as `pending` while bina.az moderates it. `result.url` is the public address of the listing once it is published.

## 7. Handle a refusal

bina.az can refuse a listing for reasons that only it knows about, such as an account whose phone number is not confirmed. Those come back as {py:class}`~binaaz_sdk.ItemError`:

```python
from binaaz_sdk import ItemError

try:
    result = bina.items.create(listing)
except ItemError as exc:
    print(exc.status, exc.errors)
    raise
```

`exc.status` is one of `RESTRICTED`, `UNVERIFIED`, `INVALID` or `FAILURE`, and `exc.errors` lists the fields bina.az did not like.

## 8. Close the client

The client holds an HTTP connection pool. Close it when you are done, or use it as a context manager so it closes itself:

```python
bina.close()
```

## The whole script

```python
from pathlib import Path

from binaaz_sdk import BinaAz, Category, ContactType, ItemError, Listing

SESSION = Path("binaaz.session")


def main() -> None:
    with BinaAz(SESSION.read_text() if SESSION.exists() else None) as bina:
        if not SESSION.exists():
            bina.auth.login("agency@example.az", "password")
            SESSION.write_text(bina.cookie)

        photos = bina.photos.upload_many(sorted(Path("photos").glob("*.jpg")))
        listing = Listing(
            category_id=Category.APARTMENT_OLD_BUILDING,
            is_leased=False,
            price=120000,
            rooms=3,
            area={"value": 85},
            floor={"value": 4, "total": 9},
            location={"address": "Nizami street 10", "city_id": "1", "latitude": 40.379, "longitude": 49.846},
            contact={"type": ContactType.AGENT, "name": "Agency"},
            photo_ids=[photo.id for photo in photos],
            description="Renovated three room flat near the metro.",
        )
        try:
            result = bina.items.create(listing)
        except ItemError as exc:
            print("bina.az refused the listing:", exc.status, exc.errors)
            raise
        print(result.id, result.state, result.url)


if __name__ == "__main__":
    main()
```

## The same thing with async

```python
import asyncio
from pathlib import Path

from binaaz_sdk import AsyncBinaAz


async def main() -> None:
    async with AsyncBinaAz(Path("binaaz.session").read_text()) as bina:
        profile = await bina.profile()
        page = await bina.items.list("published", first=10)
        print(profile.name, [item.title for item in page.items])


asyncio.run(main())
```

Every method of `BinaAz` exists on `AsyncBinaAz` with the same arguments; you only add `await`. More in [Async](../guides/async.md).

## Next steps

- [Configuration](configuration.md): timeouts, retries, the User-Agent and config files.
- [Managing listings](../guides/managing.md): list, read, update, prolong and delete.
- [Safety and retries](../guides/safety.md): what to do when a call fails halfway.
