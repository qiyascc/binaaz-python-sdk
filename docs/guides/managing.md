# Managing listings

Once a listing exists you can read it, list it with the others, change it, prolong it and delete it. All of this lives under `bina.items` and needs a signed in company profile. Other profile kinds get {py:class}`~binaaz_sdk.NotSupportedError` from the list calls.

## Read one listing

```python
item = bina.items.get("4123456")
print(item.title, item.state, item.price.total, item.url)
```

`get` returns an {py:class}`~binaaz_sdk.Item`:

| Field | Meaning |
| --- | --- |
| `id` | Listing id |
| `state` | `ItemState` (`pending`, `published`, `rejected`, `expired`, `awaiting_payment`, `unknown`) |
| `site_state` | The state as bina.az wrote it |
| `title` | The title bina.az built for the listing |
| `path`, `url` | Path and full address on bina.az |
| `price` | A `Price` with `total` (a `Decimal`) and `currency` (`AZN` unless bina.az says otherwise), or `None` |
| `expires_at` | When the listing expires, as a `datetime` |
| `updated_at` | When it was last changed |
| `thumbnail` | Address of the first photo's thumbnail |
| `raw` | The whole answer |

A listing that does not exist, or belongs to another account, raises {py:class}`~binaaz_sdk.NotFoundError`.

Ids are strings. Numbers work too, since they are turned into text, but an id with `/`, `?`, `#`, `&` or a space is refused with `InvalidRequestError` before any request.

## List listings by tab

The bina.az account page sorts listings into tabs. `list` reads one page of one tab:

```python
page = bina.items.list("published", first=50)
for item in page.items:
    print(item.id, item.title, item.expires_at)
print(page.total, page.has_more)
```

| Argument | Default | Meaning |
| --- | --- | --- |
| `tab` | `None` | Which tab to read. `None` reads all listings |
| `first` | `20` | Page size, from 1 to 100 |
| `after` | `None` | The cursor of the previous page |

### Tabs

The tab can be given as an {py:class}`~binaaz_sdk.ItemTab` or as text, in any case:

| Text | `ItemTab` |
| --- | --- |
| `"pending"` | `ItemTab.PENDING` |
| `"published"` | `ItemTab.PUBLISHED` |
| `"rejected"` | `ItemTab.REJECTED` |
| `"expired"` | `ItemTab.EXPIRED` |
| `"awaiting_payment"` | `ItemTab.AWAITING_PAYMENT` |

Anything else raises `InvalidRequestError` with the list of valid names.

### Pages and cursors

bina.az pages with cursors, not page numbers. Each {py:class}`~binaaz_sdk.ItemPage` carries the cursor of the next page:

| Field | Meaning |
| --- | --- |
| `items` | A tuple of `Item` |
| `total` | How many listings the tab has in total, when bina.az says |
| `next_cursor` | Pass it as `after` to get the next page. `None` on the last page |
| `has_more` | `True` while `next_cursor` is set |

Walking the pages by hand:

```python
cursor = None
while True:
    page = bina.items.list("published", first=100, after=cursor)
    for item in page.items:
        print(item.id, item.title)
    if not page.has_more:
        break
    cursor = page.next_cursor
```

### Every listing at once

`all` does the same loop for you, 100 listings per request:

```python
everything = bina.items.all("published")
print(len(everything))
```

It returns a tuple of `Item` and stops after `max_pages` pages (50 by default, which is 5000 listings), so a mistake can never turn into an endless loop. Raise it for very large accounts:

```python
everything = bina.items.all(max_pages=200)
```

## Update a listing

`update` takes the listing id and a full `Listing` (or a dict), the same shape as for `create`:

```python
listing = listing.model_copy(update={"price": 115000, "description": "Price reduced."})
result = bina.items.update("4123456", listing)
```

A few fields cannot be changed after posting and are left out of the update: `category_id`, `is_leased`, the contact type and `building_type`. The contact name is sent when it is set. The model still needs those fields to be valid, so keep the original values in the object you send.

An update usually sends the listing back to moderation.

### When an update is refused

| `ItemError.status` | Meaning |
| --- | --- |
| `LOCKED` | The listing is locked, for example while it is being moderated. `locked_until` says until when, when bina.az tells |
| `FORBIDDEN` | This account cannot edit this listing |
| `INVALID` | bina.az rejected the data; see `errors` |

A listing that is not found raises `NotFoundError` instead.

```python
from binaaz_sdk import ItemError

try:
    bina.items.update("4123456", listing)
except ItemError as exc:
    if exc.status == "LOCKED":
        print("Try again after", exc.locked_until)
    else:
        raise
```

## Prolong a listing

```python
result = bina.items.prolong("4123456")
print(result.state)
```

Prolonging puts an expired listing (or one close to its end) back for another period, on the terms bina.az sets for the account. If bina.az refuses, you get `ItemError` with its reason.

## Delete a listing

```python
bina.items.delete("4123456")
```

Deleting cannot be undone from the SDK.

## Writes are never repeated

`update`, `prolong` and `delete` are writes. If the connection drops or bina.az times out while one of them is in flight, the SDK raises `OutcomeUnknownError` instead of sending it again. Read the listing with `get` to see whether the change went through before you retry. More in [Safety and retries](safety.md).
