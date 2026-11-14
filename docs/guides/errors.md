# Errors

Every exception the SDK raises inherits from {py:class}`~binaaz_sdk.BinaAzError`, so one `except BinaAzError` catches them all. Below that there are three families: problems found before sending, problems on the way, and answers from bina.az.

## The hierarchy

```text
BinaAzError
├── ConfigurationError          settings that cannot work
├── InvalidRequestError         a bad argument, found before sending (also a ValueError)
├── NotSupportedError           the profile cannot do this (not a company profile)
├── TransportError              the request did not get a usable answer
│   ├── NotSentError            the connection failed, nothing was sent
│   └── OutcomeUnknownError     a write may or may not have gone through
└── APIError                    bina.az answered with an error
    ├── BlockedError            a Cloudflare challenge page
    ├── AuthenticationError     the session is missing or expired
    ├── NotFoundError           404, or a listing that does not exist
    ├── RateLimitError          429 after the retries
    ├── ServerError             5xx after the retries, or a broken answer
    └── BadRequestError         any other 4xx, or a refusal
        ├── GraphQLError        bina.az refused the GraphQL request
        ├── ItemError           bina.az refused a listing
        └── CodeRejectedError   the SMS code was not accepted
```

## Attributes

Every exception has `message`, the text without decoration.

| Exception | Extra attributes |
| --- | --- |
| `TransportError`, `NotSentError` | `path`: the path that was called |
| `OutcomeUnknownError` | `path`, `status_code` (when there was an answer, such as a 502) |
| `APIError` and all below | `status_code`, `body` (the parsed answer or the first 200 characters of it), `path` |
| `RateLimitError` | `retry_after`: seconds bina.az asked to wait, when it said |
| `GraphQLError` | `errors`: the list of GraphQL errors |
| `ItemError` | `status`, `errors`, `locked_until`; see [Posting listings](listings.md#when-bina-az-refuses-a-listing) |

`str(error)` on an `APIError` puts the status code in front, such as `[404] bina.az item 1 was not found for this account`.

## Which one to catch

| You want to | Catch |
| --- | --- |
| Show a form error to a user | `InvalidRequestError`, `ItemError` |
| Ask the user to sign in again | `AuthenticationError` |
| Ask for a new SMS code | `CodeRejectedError` |
| Wait and try again later | `RateLimitError`, `ServerError`, `NotSentError`, `TransportError` |
| Check the account before retrying | `OutcomeUnknownError` |
| Stop and alert someone | `BlockedError`, `ConfigurationError`, `NotSupportedError` |

A typical job:

```python
from binaaz_sdk import (
    AuthenticationError,
    BinaAzError,
    BlockedError,
    InvalidRequestError,
    ItemError,
    OutcomeUnknownError,
)

try:
    result = bina.items.create(listing)
except (InvalidRequestError, ItemError) as exc:
    report_to_user(exc)
except AuthenticationError:
    sign_in_again()
except OutcomeUnknownError:
    check_pending_listings_before_retrying()
except BlockedError:
    alert_admin("bina.az is showing a challenge page to this server")
except BinaAzError as exc:
    log_and_retry_later(exc)
```

## Errors in detail

### `InvalidRequestError`

Raised before any request when an argument cannot be right: an empty field, an id with a slash, a phone number that is not Azerbaijani, a photo count outside 4 to 30, a tab name that does not exist, a paid call without `confirm=True`, or a listing that breaks a rule. It is also a `ValueError`.

### `AuthenticationError`

The session is missing, expired or refused. bina.az says this in several ways (HTTP 401 or 419, GraphQL errors with codes such as `unauthorized`, or messages such as "daxil olun"), and all of them become this one exception. Sign in again.

### `BlockedError`

bina.az, through Cloudflare, answered with a challenge page instead of the API. The SDK does not solve challenges and does not retry them. It usually means the server's IP address looks suspicious to Cloudflare; running from another network is the fix.

### `ItemError`

bina.az refused a listing or a change to one. See [Posting listings](listings.md#when-bina-az-refuses-a-listing) and [Managing listings](managing.md#when-an-update-is-refused).

### `CodeRejectedError`

The SMS code was wrong or already used. When the check had to be repeated, the message says the code may have been used by the first attempt; ask for a new code.

### `OutcomeUnknownError`

A write was sent, but no usable answer came back: a timeout, a dropped connection, a 5xx or an answer that is not JSON. The write may have happened. See [Safety and retries](safety.md).

### `NotSupportedError`

Listing management (`items.list`, `items.all`) needs a company profile, and the session belongs to another kind of profile.

## Messages

Every message comes from `messages.yaml` inside the package and can be replaced, for example to show them in Azerbaijani. See [Messages](messages.md).
