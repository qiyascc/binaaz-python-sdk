# Safety and retries

Networks fail in the middle of requests. For a read that is a nuisance; for a write it is a real question, because a listing or a payment that bina.az received but never confirmed must not be sent a second time. The SDK sorts every call into one of a few kinds and treats each kind differently.

## The kinds of calls

| Kind | Calls | On a timeout, a dropped connection or a 5xx |
| --- | --- | --- |
| Reads | `auth.profile`, `items.get`, `items.list`, `items.all`, `items.paid_services`, every `catalog` call, `graphql(..., safe=True)` | Retried with backoff, then `TransportError` or `ServerError` |
| Writes | `auth.login`, `items.create`, `items.update`, `items.delete`, `items.prolong`, `items.pay`, `items.buy_service`, `photos.upload`, `photos.upload_many`, `photos.rotate`, `graphql(...)` | Never retried. `OutcomeUnknownError` |
| SMS login | `auth.send_code`, `auth.verify_code` | Error pages are retried up to `code_attempts`; a timeout is not retried |

## Every situation

| Situation | What the client does |
| --- | --- |
| Connection refused, DNS failure, connect timeout: nothing was sent | Retried for every kind of call, then `NotSentError` |
| Timeout, cut connection or 5xx on a write | No retry, `OutcomeUnknownError`. Check the account before trying again |
| Same failure on a read | Retried with backoff, then `TransportError` or `ServerError` |
| A write answered with something that is not JSON | `OutcomeUnknownError` |
| 429 Too Many Requests | Waits for `Retry-After` (at most `backoff_cap` seconds) and tries again. A 429 means the request was not processed, so this is safe for writes too. After the retries, `RateLimitError` |
| SMS login service answers with an error page | Asked again up to `code_attempts` times (3) |
| SMS code sent only on a retry | `CodeSent.retried` is `True`: more than one SMS may arrive, use the latest code |
| SMS code rejected after a retry | `CodeRejectedError` says the code may have been used by the earlier attempt |
| Timeout on the SMS login service | Not resent, `OutcomeUnknownError` |
| Cloudflare challenge page | `BlockedError`, never solved or retried |
| Paid service or paying for a listing without `confirm=True` | `InvalidRequestError`, nothing is sent |
| Fewer than 4 or more than 30 photos | `InvalidRequestError` before anything is sent |
| A failed sign in | The previous session is kept |
| Plain http address outside localhost | `ConfigurationError`, unless `allow_insecure_http` |

## Backoff

Between attempts the client waits

```text
min(backoff_cap, backoff_base * 2 ** attempt) + a random part of up to backoff_base / 2
```

`max_retries` (2 by default) is the number of extra attempts after the first one. With the defaults (`backoff_base=0.6`, `backoff_cap=8`) the two waits are about 0.6 and 1.2 seconds; more retries would wait 2.4, 4.8 and then 8 seconds each. The random part keeps many clients from retrying in step.

```python
bina = BinaAz(max_retries=4, backoff_base=1.0, backoff_cap=15)
```

Set `max_retries=0` to turn retries off entirely, which is useful in tests.

## Timeouts

`timeout` (30 seconds) is how long to wait for an answer, `connect_timeout` (10 seconds) how long to wait for a connection. A connect timeout means nothing was sent, so it is retried even for writes. A read timeout on a write is the classic unknown outcome.

```python
bina = BinaAz(timeout=60, connect_timeout=5)
```

## When the outcome is unknown

`OutcomeUnknownError` means: the request left, and no usable answer came back. The write may have happened, half happened or not happened. The SDK cannot know, so it does not guess.

What to do depends on the call:

| Call | How to check |
| --- | --- |
| `items.create` | Look at `items.list("pending")` for a listing with the same title or address |
| `items.update` | Read the listing with `items.get` and compare |
| `items.delete` | `items.get` raises `NotFoundError` when the delete went through |
| `items.prolong` | Read the listing and look at `expires_at` |
| `items.pay`, `items.buy_service` | Check the listing state and the account balance on bina.az |
| `photos.upload` | Upload again. An unused photo on the photo service does no harm |
| `auth.login` | Call `bina.profile()`; if it works, the sign in went through |

A careful create:

```python
from binaaz_sdk import OutcomeUnknownError

def create_once(bina, listing, address):
    try:
        return bina.items.create(listing)
    except OutcomeUnknownError:
        recent = bina.items.list("pending", first=50).items
        if any(address in (item.title or "") for item in recent):
            return None
        raise
```

## Cloudflare

bina.az sits behind Cloudflare. If Cloudflare decides to show a challenge page, the API answer is a HTML page, not JSON. The SDK recognises it (the `cf-mitigated: challenge` header, or a Cloudflare 403 or 503 HTML page) and raises `BlockedError` at once. It does not try to pass the challenge, does not retry, uses no proxies on its own and never stores Cloudflare cookies. If you see `BlockedError` often, the server's network is the problem, not the code.

## Sessions

The session cookie is sent to bina.az and its photo service only. The SMS login service never receives it, and cookies from that service are not stored. A failed sign in restores the session the client had before.
