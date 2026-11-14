# bina.az Python SDK

A typed Python client for [bina.az](https://bina.az), the Azerbaijani real estate site. It signs in with an email and password or with an SMS code, posts, edits, prolongs and deletes listings, uploads and rotates photos, pays for listings and paid services, and reads the catalog of categories, cities, districts, townships and landmarks. There is a sync client, `BinaAz`, and an async one, `AsyncBinaAz`, with the same methods.

```python
from binaaz_sdk import BinaAz, Category, ContactType, Listing

with BinaAz() as bina:
    bina.auth.login("agency@example.az", "password")
    photos = bina.photos.upload_many(["1.jpg", "2.jpg", "3.jpg", "4.jpg"])
    result = bina.items.create(Listing(
        category_id=Category.APARTMENT_OLD_BUILDING,
        is_leased=False,
        price=120000,
        rooms=3,
        area={"value": 85},
        floor={"value": 4, "total": 9},
        location={"address": "Nizami street 10", "city_id": "1", "latitude": 40.379, "longitude": 49.846},
        contact={"type": ContactType.AGENT, "name": "Agency"},
        photo_ids=[p.id for p in photos],
    ))
    print(result.id, result.state, result.url)
```

:::{important}
This is not an official bina.az product. It talks to the same endpoints the bina.az website uses, with its own User-Agent. It does not solve captchas or Cloudflare challenges: when bina.az answers with a challenge page you get `BlockedError`.
:::

## Where to go next

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Installation
:link: getting-started/installation
:link-type: doc

Python versions, a virtual environment step by step, pip, uv and Poetry, extras.
:::

:::{grid-item-card} Signing in
:link: getting-started/sign-in
:link-type: doc

Email and password, SMS codes, saving the session cookie and loading it back.
:::

:::{grid-item-card} Quickstart
:link: getting-started/quickstart
:link-type: doc

From an empty folder to a posted listing, one line at a time.
:::

:::{grid-item-card} Configuration
:link: getting-started/configuration
:link-type: doc

Every setting, environment variable and config file option.
:::

:::{grid-item-card} Posting listings
:link: guides/listings
:link-type: doc

The `Listing` model, the bina.az rules and what happens after you post.
:::

:::{grid-item-card} Safety and retries
:link: guides/safety
:link-type: doc

Which calls are retried, which never are, and what to do when the outcome is unknown.
:::

:::{grid-item-card} Examples
:link: examples/index
:link-type: doc

Complete scripts: a session file, posting from a folder, CSV export, a daily prolong job, Django.
:::

:::{grid-item-card} API reference
:link: reference/api
:link-type: doc

Every class, method and field.
:::

::::

## What the SDK takes care of

- **Sessions.** The session is a plain cookie string. Save it once, pass it back later, and you do not sign in on every run. Cookies bina.az renews are picked up from every answer, and Cloudflare cookies are never stored or sent.
- **Checks before sending.** Photo counts, phone numbers, ids, listing rules and paid actions without `confirm=True` are refused locally, before a request leaves your machine.
- **Writes are never repeated by accident.** A timeout on a create, an update, a payment or a photo upload raises `OutcomeUnknownError` instead of trying again, so a listing or a payment is never sent twice.
- **Reads ride over hiccups.** Catalog calls, listing pages and profile reads are retried with backoff, and a 429 waits for `Retry-After`.
- **Typed results.** Every answer comes back as a frozen dataclass with plain Python types, `Decimal` for money and `datetime` for dates. The raw answer is still there in `.raw`.
- **Everything is configurable.** Addresses, paths, timeouts, retry counts, the User-Agent and every message can be changed from code, the environment or a config file.

```{toctree}
:hidden:
:caption: Getting started

getting-started/installation
getting-started/sign-in
getting-started/quickstart
getting-started/configuration
```

```{toctree}
:hidden:
:caption: Guides

guides/listings
guides/managing
guides/photos
guides/catalog
guides/payments
guides/async
guides/errors
guides/safety
guides/messages
guides/advanced
guides/testing
```

```{toctree}
:hidden:
:caption: Examples

examples/index
examples/session-file
examples/post-from-folder
examples/export-csv
examples/prolong-job
examples/rejected-alert
examples/django
```

```{toctree}
:hidden:
:caption: Reference

reference/api
reference/models
reference/changelog
reference/faq
```

```{toctree}
:hidden:
:caption: Project

project/development
project/about
```
