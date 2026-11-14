# API reference

This page is generated from the code. The code carries no docstrings, so the descriptions live in the guides; this page lists every public class, method, argument and type in one place. Each section links back to the guide that explains it.

Everything below can be imported from the top level package, for example `from binaaz_sdk import BinaAz, Listing, ItemError`. The resource classes (`Auth`, `Items`, `Photos`, `Catalog`) are reached through a client as `bina.auth`, `bina.items`, `bina.photos` and `bina.catalog`; you never create them yourself.

## Clients

See [Quickstart](../getting-started/quickstart.md), [Signing in](../getting-started/sign-in.md) and [Async](../guides/async.md).

```{eval-rst}
.. autoclass:: binaaz_sdk.BinaAz
   :members: profile, graphql, cookie, set_cookie, clear_session, close

.. autoclass:: binaaz_sdk.AsyncBinaAz
   :members: profile, graphql, close
```

Both clients take the same constructor arguments:

| Argument | Meaning |
| --- | --- |
| `cookie` | Optional session cookie, as a header string, a mapping, a cookie export list or its JSON text |
| `settings` | A ready `Settings` object |
| `config_file` | Path of a config file to load |
| `http_client` | Your own `httpx.Client` (sync) or `httpx.AsyncClient` (async) |
| any setting | Such as `timeout=10`, applied on top of everything else |

## `bina.auth`

See [Signing in](../getting-started/sign-in.md).

```{eval-rst}
.. autoclass:: binaaz_sdk.resources.Auth
   :members: login, send_code, verify_code, profile
```

## `bina.items`

See [Posting listings](../guides/listings.md), [Managing listings](../guides/managing.md) and [Payments](../guides/payments.md).

```{eval-rst}
.. autoclass:: binaaz_sdk.resources.Items
   :members: create, update, delete, prolong, get, list, all, paid_services, buy_service, pay
```

## `bina.photos`

See [Photos](../guides/photos.md).

```{eval-rst}
.. autoclass:: binaaz_sdk.resources.Photos
   :members: upload, upload_many, rotate
```

## `bina.catalog`

See [Catalog](../guides/catalog.md).

```{eval-rst}
.. autoclass:: binaaz_sdk.resources.Catalog
   :members: categories, cities, regions, townships, landmarks
```

## Listing input

See [Posting listings](../guides/listings.md).

The input models are pydantic models. Their fields and rules are listed in the guide; the signatures below show the types.

```{eval-rst}
.. autoclass:: binaaz_sdk.Listing
   :members: to_create_input, to_update_input
   :undoc-members: false

.. autoclass:: binaaz_sdk.Area
   :members:
   :undoc-members: false

.. autoclass:: binaaz_sdk.Floor
   :members:
   :undoc-members: false

.. autoclass:: binaaz_sdk.Location
   :members:
   :undoc-members: false

.. autoclass:: binaaz_sdk.Contact
   :members:
   :undoc-members: false
```

## Settings

See [Configuration](../getting-started/configuration.md).

```{eval-rst}
.. autofunction:: binaaz_sdk.load_settings

.. autoclass:: binaaz_sdk.Settings
   :members: url, path, resolved_user_agent, check_transport
   :undoc-members: false

.. autoclass:: binaaz_sdk.Endpoints
   :members:
   :undoc-members: false
```

## Messages

See [Messages](../guides/messages.md).

```{eval-rst}
.. autofunction:: binaaz_sdk.messages.use
.. autofunction:: binaaz_sdk.messages.reset
.. autofunction:: binaaz_sdk.messages.catalog
.. autofunction:: binaaz_sdk.messages.text
```

## Errors

See [Errors](../guides/errors.md).

```{eval-rst}
.. autoexception:: binaaz_sdk.BinaAzError
.. autoexception:: binaaz_sdk.ConfigurationError
.. autoexception:: binaaz_sdk.InvalidRequestError
.. autoexception:: binaaz_sdk.NotSupportedError
.. autoexception:: binaaz_sdk.TransportError
.. autoexception:: binaaz_sdk.NotSentError
.. autoexception:: binaaz_sdk.OutcomeUnknownError
.. autoexception:: binaaz_sdk.APIError
.. autoexception:: binaaz_sdk.BlockedError
.. autoexception:: binaaz_sdk.AuthenticationError
.. autoexception:: binaaz_sdk.NotFoundError
.. autoexception:: binaaz_sdk.RateLimitError
.. autoexception:: binaaz_sdk.ServerError
.. autoexception:: binaaz_sdk.BadRequestError
.. autoexception:: binaaz_sdk.GraphQLError
.. autoexception:: binaaz_sdk.ItemError
.. autoexception:: binaaz_sdk.CodeRejectedError
```
