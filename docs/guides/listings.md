# Posting listings

A listing on bina.az is described by a {py:class}`~binaaz_sdk.Listing` and posted with `bina.items.create`. This page covers every field, the rules bina.az applies, and what you get back.

Posting needs a signed in company profile (an agency or a residence). See [Signing in](../getting-started/sign-in.md).

## The shortest listing

These are the fields bina.az always needs:

```python
from binaaz_sdk import Category, ContactType, Listing

listing = Listing(
    category_id=Category.APARTMENT_NEW_BUILDING,
    is_leased=False,
    price=150000,
    area={"value": 70},
    location={"address": "Yasamal", "city_id": "1", "latitude": 40.393, "longitude": 49.808},
    contact={"type": ContactType.OWNER},
    photo_ids=["p1", "p2", "p3", "p4"],
)
```

## Every field

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `category_id` | `Category` | yes | One of the categories below |
| `is_leased` | `bool` | yes | `False` for sale, `True` for rent |
| `price` | `int` | yes | Greater than 0, in AZN |
| `area` | `Area` | yes | `value` greater than 0 in m², optional `land` greater than 0 |
| `location` | `Location` | yes | See [Location](#location) |
| `contact` | `Contact` | yes | See [Contact](#contact) |
| `photo_ids` | `list[str]` | yes, 4 to 30 | Ids from `bina.photos.upload` |
| `description` | `str` | no | Up to 5000 characters |
| `rooms` | `int` | no | From 1 to 50 |
| `floor` | `Floor` | no | `value` and `total`, `value` not above `total` |
| `has_repair` | `bool` | no | The property is renovated |
| `has_mortgage` | `bool` | no | Mortgage is possible |
| `has_bill_of_sale` | `bool` | no | There is a bill of sale (kupça) |
| `paid_daily` | `bool` | no | Daily rent. Only with `is_leased=True` |
| `building_type` | `BuildingType` | no | Only for `Category.OFFICE` |

Unknown fields are refused, so a typo such as `room=3` fails loudly instead of being ignored.

The model accepts both the Python names above and the camelCase names bina.az uses (`categoryId`, `isLeased`, `photoIds`), which is handy when the data comes from JSON.

### Categories

| Name | Id | What it is |
| --- | --- | --- |
| `Category.APARTMENT` | 1 | Apartment |
| `Category.APARTMENT_NEW_BUILDING` | 2 | Apartment in a new building |
| `Category.APARTMENT_OLD_BUILDING` | 3 | Apartment in an old building |
| `Category.HOUSE` | 5 | House |
| `Category.OFFICE` | 7 | Office |
| `Category.GARAGE` | 8 | Garage |
| `Category.LAND` | 9 | Land |
| `Category.COMMERCIAL` | 10 | Commercial property |

`Category` is an `IntEnum`, so `category_id=3` works as well as `Category.APARTMENT_OLD_BUILDING`. The live category tree, with names in Azerbaijani, comes from `bina.catalog.categories()`.

### Location

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `address` | `str` | yes | 1 to 500 characters |
| `city_id` | `str` | yes | From `bina.catalog.cities()` |
| `latitude` | `float` | yes | From -90 to 90 |
| `longitude` | `float` | yes | From -180 to 180 |
| `region_id` | `str` | no | From `bina.catalog.regions(city_id)` |
| `township_id` | `str` | no | From `bina.catalog.townships(region_id)` |
| `landmark_ids` | `list[str]` | no | From `bina.catalog.landmarks(city_id, lat, lng)` |

### Contact

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `type` | `ContactType` | yes | `ContactType.OWNER` or `ContactType.AGENT` |
| `name` | `str` | no | Up to 100 characters |
| `email` | `str` | no | Up to 255 characters |

### Building type

`BuildingType.BUSINESS_CENTER`, `BuildingType.APARTMENT` or `BuildingType.VILLA`. bina.az only takes it for offices; on any other category the model raises an error.

## Rules checked before sending

The model and the client check everything they can before a request goes out:

- `price` must be positive and `area.value` must be positive.
- `floor.value` cannot be above `floor.total`.
- `paid_daily=True` needs `is_leased=True`.
- `building_type` is only valid for `Category.OFFICE`.
- `rooms` is from 1 to 50.
- `create` counts `photo_ids` and refuses fewer than 4 or more than 30.

Building a `Listing` directly raises pydantic's `ValidationError` when a rule is broken. Passing a plain dict to `create` or `update` raises `InvalidRequestError` with the same text instead, so you only need to catch the SDK's own errors:

```python
from binaaz_sdk import InvalidRequestError

try:
    bina.items.create({"category_id": 3, "is_leased": False, "price": 0})
except InvalidRequestError as exc:
    print(exc)
```

`InvalidRequestError` is also a `ValueError`.

## Posting

```python
result = bina.items.create(listing)
```

`create` takes a `Listing` or a dict with the same fields. It returns an {py:class}`~binaaz_sdk.ItemResult`:

| Field | Meaning |
| --- | --- |
| `id` | The new listing id, such as `"4123456"` |
| `state` | An `ItemState`, see below |
| `site_state` | The state exactly as bina.az wrote it |
| `path` | The path on bina.az, such as `/items/4123456` |
| `url` | The full address, such as `https://bina.az/items/4123456` |
| `status` | The status of the operation reported by bina.az |
| `locked_until` | Set when bina.az locked the listing |
| `raw` | The whole answer |

## Listing states

bina.az moves a listing through these states. The SDK maps every spelling bina.az uses onto {py:class}`~binaaz_sdk.ItemState`:

| `ItemState` | Meaning |
| --- | --- |
| `PENDING` | Waiting for moderation. Every new listing starts here |
| `PUBLISHED` | Live on bina.az |
| `REJECTED` | Moderation refused it |
| `EXPIRED` | Its time ran out; it can be prolonged |
| `AWAITING_PAYMENT` | Accepted, but shown only after payment (see [Payments](payments.md)) |
| `UNKNOWN` | A state this version of the SDK does not know yet |

`str(ItemState.PUBLISHED)` is `"published"`, which is convenient for logs and CSV files.

## When bina.az refuses a listing

A listing that passes the local checks can still be refused by bina.az. That raises {py:class}`~binaaz_sdk.ItemError` with three useful attributes:

| Attribute | Meaning |
| --- | --- |
| `status` | Why the listing was refused, see the next table |
| `errors` | A list of field problems as bina.az reported them, each with `code`, `message` and `path` |
| `locked_until` | Only for updates of a locked listing |

| `status` | Meaning | What to do |
| --- | --- | --- |
| `RESTRICTED` | The account must confirm its phone number before posting | Confirm the number on bina.az, then post again |
| `UNVERIFIED` | The account is not verified yet | Finish verification on bina.az |
| `INVALID` | bina.az rejected the data | Read `errors` and fix the fields |
| `FAILURE` | bina.az could not create the listing | Try again later |

```python
from binaaz_sdk import ItemError

try:
    bina.items.create(listing)
except ItemError as exc:
    for error in exc.errors:
        print(".".join(map(str, error["path"])), error["message"])
```

Field errors without a status still raise `ItemError`; `status` is `None` then and `errors` has the details.

## Timeouts while posting

A timeout or a dropped connection during `create` does not mean the listing was not created. bina.az may have received it and simply not answered in time. The SDK never repeats a `create` on its own for that reason. It raises {py:class}`~binaaz_sdk.OutcomeUnknownError` instead.

When that happens, look at the account before trying again:

```python
from binaaz_sdk import OutcomeUnknownError

try:
    result = bina.items.create(listing)
except OutcomeUnknownError:
    pending = bina.items.list("pending", first=20)
    print([(item.id, item.title) for item in pending.items])
```

The [safety guide](safety.md) explains the rules in full.
