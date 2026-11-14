# Advanced use

## Any GraphQL query

bina.az runs its website on a GraphQL API. The SDK wraps the parts that matter for listing management, and `graphql` sends anything else with the same session, headers and error handling:

```python
data = bina.graphql(
    "query Profile { profile { __typename ... on CompanyProfile { id name } } }",
    operation_name="Profile",
    safe=True,
)
print(data["profile"])
```

| Argument | Default | Meaning |
| --- | --- | --- |
| `query` | | The GraphQL document |
| `variables` | `None` | A mapping of variables |
| `operation_name` | `None` | Sent as `operationName` when set |
| `safe` | `False` | `True` for a query that can be repeated (a read). It is then retried like other reads. Leave it `False` for mutations |

The return value is the `data` part of the answer as a plain dict. GraphQL errors raise `GraphQLError` with the list in `.errors`, and authorisation errors raise `AuthenticationError`, exactly like the built in calls.

## The client object

`repr(bina)` shows the address and whether a session is set, never the cookie:

```text
BinaAz(base_url='https://bina.az', signed_in=True)
```

`bina.settings` is the loaded {py:class}`~binaaz_sdk.Settings`. Change settings by creating a new client, not by assigning to the object: the HTTP client and its timeouts are built when the client is created.

## Your own httpx client

Pass `http_client=` to control the transport: proxies, certificates, connection limits, event hooks for logging.

```python
import logging

import httpx

from binaaz_sdk import BinaAz

log = logging.getLogger("binaaz")


def show(response: httpx.Response) -> None:
    log.info("%s %s -> %s", response.request.method, response.request.url.path, response.status_code)


http = httpx.Client(
    timeout=httpx.Timeout(30, connect=10),
    limits=httpx.Limits(max_connections=5),
    event_hooks={"response": [show]},
)
bina = BinaAz(http_client=http)
```

Log only the method, the path and the status. Request headers carry the session cookie.

The SDK clears the httpx cookie jar after every answer and keeps the session in its own store. That way a cookie set by one service can never be sent to another, and Cloudflare cookies are never kept.

## Several accounts

One client holds one session. For several accounts, create one client per account. They share nothing, so they can run side by side in threads (sync) or tasks (async).

```python
clients = {name: BinaAz(cookie) for name, cookie in saved_cookies.items()}
```

## Threads

A sync client can be shared between threads for reads. Signing in changes the session of the client, so do not sign in on a client that other threads are using at the same time; give each worker its own client if they sign in separately.

## Changing addresses

`base_url`, `photos_url` and `login_url` point at the real services by default. Changing them is useful for a recording proxy or a local mock server in tests:

```python
bina = BinaAz(base_url="http://localhost:8080", photos_url="http://localhost:8080", login_url="http://localhost:8080")
```

`localhost` is allowed over plain http. See [Configuration](../getting-started/configuration.md#plain-http).
