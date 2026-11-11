# binaaz-python-sdk

[![Python](https://img.shields.io/badge/python-3.10%20to%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![bina.az](https://img.shields.io/badge/site-bina.az-E4402F)](https://bina.az)
[![Typed](https://img.shields.io/badge/typing-mypy-2A6DB2)](https://mypy-lang.org)
[![Async](https://img.shields.io/badge/sync%20%2B%20async-httpx-5A45FF)](https://www.python-httpx.org)
[![Ruff](https://img.shields.io/badge/lint-ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/qiyascc/binaaz-python-sdk/blob/main/LICENSE)

Typed Python client for bina.az, the Azerbaijani real estate site. Sign in with email and password or with an SMS code, post, edit, prolong and delete listings, upload and rotate photos, read the catalog of cities, districts and metro stations. Sync and async, with retry rules built so a listing or a payment is never sent twice.

```bash
pip install binaaz-python-sdk
```

This is not an official bina.az product. It talks to the same endpoints the bina.az website uses, with its own User-Agent. It does not solve captchas or Cloudflare challenges: if bina.az answers with a challenge page you get `BlockedError`.

## Sign in

```python
from binaaz_sdk import BinaAz

with BinaAz() as bina:
    bina.auth.login("agency@example.az", "password")
    saved = bina.cookie
```

Phone accounts sign in with a code that bina.az sends by SMS:

```python
sent = bina.auth.send_code("050 123 45 67")
profile = bina.auth.verify_code("050 123 45 67", "1234")
```

`bina.cookie` is the signed in session. Keep it somewhere safe and pass it back later, so you do not sign in on every run:

```python
bina = BinaAz(cookie=saved)
bina.profile()
```

A cookie copied from a browser works too, as a header value, a `{"name": "value"}` mapping or a cookie export list. Cloudflare cookies are dropped, they are never stored or sent. Cookies that bina.az renews are picked up from every answer.

## Post a listing

```python
from binaaz_sdk import BinaAz, Category, ContactType, Listing

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
    description="Renovated three room flat near the metro.",
))
result.id, result.url, result.state
```

bina.az takes 4 to 30 photos on a listing. A new listing starts as `pending` and moves to `published`, `rejected` or `awaiting_payment`. When bina.az refuses it, `ItemError.status` tells why: `RESTRICTED` (confirm the phone number first), `UNVERIFIED`, `INVALID` or `FAILURE`. Field problems are in `ItemError.errors`.

## Manage listings

```python
page = bina.items.list("published", first=50)
everything = bina.items.all()
item = bina.items.get("4123456")

bina.items.update("4123456", listing)
bina.items.prolong("4123456")
bina.items.delete("4123456")
```

`list` follows bina.az cursors (`page.next_cursor`), `all` reads every page. Tabs are `pending`, `published`, `rejected`, `expired` and `awaiting_payment`. An update of a listing under moderation raises `ItemError` with `status="LOCKED"` and `locked_until`. Listing management needs a company profile (agencies and residences); other profiles get `NotSupportedError`.

## Paid services

```python
for service in bina.items.paid_services("4123456"):
    service.title, service.options, service.payment_methods

payment = bina.items.buy_service("4123456", service.id, "wallet", option_id=service.options[0].id, confirm=True)
payment.redirect_url
bina.items.pay("4123456", confirm=True)
```

Anything that costs money needs `confirm=True`, otherwise `InvalidRequestError` is raised before a request is made. A card payment comes back with `redirect_url`, the page where the payment is finished.

## Photos and catalog

```python
photo = bina.photos.upload(open("cover.jpg", "rb"))
photo = bina.photos.rotate(photo.id, 90)

bina.catalog.categories()
bina.catalog.cities()
bina.catalog.regions("1")
bina.catalog.townships("4")
bina.catalog.landmarks("1", 40.379, 49.846)
```

Uploads take bytes, a path or a file object. Rotating returns a new photo id; use that one in the listing. Catalog calls need no session.

## Safety

| Situation | What the client does |
| --- | --- |
| Connection refused, nothing sent | Retries, then `NotSentError` |
| Timeout, cut connection or 5xx on create, update, delete, prolong, payment, sign in or photo upload | No retry, `OutcomeUnknownError`. Check the account before trying again |
| Same failure on a read | Retries with backoff, then `TransportError` or `ServerError` |
| 429 | Waits `Retry-After` and retries, the request was not processed |
| SMS login service answers with an error page instead of a known error | Retried up to `code_attempts` (3), the login service drops some answers |
| SMS code sent only on a retry | `CodeSent.retried` is `True`: more than one SMS may arrive, use the latest code |
| SMS code rejected after a retry | `CodeRejectedError` says the code may have been used by the earlier attempt |
| Timeout on the SMS login service | Not resent, `OutcomeUnknownError` |
| Cloudflare challenge page | `BlockedError`, never solved or retried |
| Paid service or paying for a listing without `confirm=True` | `InvalidRequestError`, nothing is sent |
| Fewer than 4 or more than 30 photos | `InvalidRequestError` before anything is sent |
| A failed sign in | The previous session is kept |
| Plain http address outside localhost | `ConfigurationError`, unless `allow_insecure_http` |

## Endpoints

| Namespace | Methods |
| --- | --- |
| `auth` | `login` `send_code` `verify_code` `profile` |
| `items` | `create` `update` `delete` `prolong` `get` `list` `all` `paid_services` `buy_service` `pay` |
| `photos` | `upload` `upload_many` `rotate` |
| `catalog` | `categories` `cities` `regions` `townships` `landmarks` |
| client | `profile` `cookie` `set_cookie` `clear_session` `graphql` |

`AsyncBinaAz` has the same methods, awaited. `graphql(query, variables)` sends any other query with the session.

## Errors

`BinaAzError` is the base. Answers raise `APIError` subclasses: `BadRequestError`, `AuthenticationError` (the session is not signed in), `NotFoundError`, `RateLimitError`, `ServerError` and `BlockedError`. GraphQL errors raise `GraphQLError` with `errors`, refused listings raise `ItemError` with `status`, `errors` and `locked_until`, a wrong SMS code raises `CodeRejectedError`. Each carries `status_code`, `message` and the raw `body`.

## Config

Pass values in code, or set `BINAAZ_COOKIE`, `BINAAZ_TIMEOUT`, `BINAAZ_MAX_RETRIES`, `BINAAZ_CODE_ATTEMPTS`, `BINAAZ_USER_AGENT` and the rest, or put them in `binaaz.toml` ([example](https://github.com/qiyascc/binaaz-python-sdk/blob/main/examples/binaaz.toml)). Every path is a setting (`BINAAZ_ENDPOINTS__GRAPHQL=...`). Messages live in `messages.yaml` and can be replaced with `messages.use(...)`.

## Develop

```bash
pip install -e ".[dev]" && pytest && ruff check . && mypy src
```

## Links

- Source code: [github.com/qiyascc/binaaz-python-sdk](https://github.com/qiyascc/binaaz-python-sdk)
- PyPI: [pypi.org/project/binaaz-python-sdk](https://pypi.org/project/binaaz-python-sdk/)
- Project page: [theqiyas.cc/projects/binaaz-sdk](https://theqiyas.cc/projects/binaaz-sdk/)
- Author: [Qiyas Sadıqov](https://theqiyas.cc), more projects at [theqiyas.cc](https://theqiyas.cc)

## License

MIT
