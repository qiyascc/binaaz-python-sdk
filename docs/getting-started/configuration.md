# Configuration

Every setting has a sensible default, so `BinaAz()` works without any configuration at all. When you do want to change something, there are three places to do it. Settings are loaded with [goodconf](https://github.com/lincolnloop/goodconf) on top of pydantic.

## Where settings come from

From the highest priority to the lowest:

1. **Arguments in code**, such as `BinaAz(timeout=10)`.
2. **Environment variables** that start with `BINAAZ_`, such as `BINAAZ_TIMEOUT=10`.
3. **A config file**, such as `binaaz.toml`.
4. **The defaults** in the table below.

A value given in code always wins. An environment variable wins over the same value in the file. Everything you do not set keeps its default.

## In code

Any setting can be passed to the client as a keyword argument:

```python
from binaaz_sdk import BinaAz

bina = BinaAz(timeout=10, max_retries=4, user_agent="my-crm/2.0 binaaz-python-sdk/{version}")
```

The first positional argument is the session cookie, see [Signing in](sign-in.md):

```python
bina = BinaAz(saved_cookie, timeout=10)
```

If you build the settings yourself, for example to share them between several clients, pass them as `settings=`. Keyword arguments next to `settings=` are applied on top:

```python
from binaaz_sdk import BinaAz, load_settings

settings = load_settings("/etc/my-crm/binaaz.toml", timeout=15)
bina = BinaAz(settings=settings)
patient = BinaAz(settings=settings, max_retries=6)
```

`load_settings(config_file=None, **overrides)` reads the environment and the config file and applies the overrides. Overrides that are `None` are ignored, so you can pass optional values straight through.

## Environment variables

Every setting has an environment variable: the setting name in capitals with a `BINAAZ_` prefix.

```bash
export BINAAZ_COOKIE="_binaaz_session=abc123"
export BINAAZ_TIMEOUT=15
export BINAAZ_MAX_RETRIES=3
```

On Windows CMD:

```bat
set BINAAZ_COOKIE=_binaaz_session=abc123
set BINAAZ_TIMEOUT=15
```

Nested settings use a double underscore between the parts:

```bash
export BINAAZ_ENDPOINTS__GRAPHQL=/graphql
```

## Config file

With no `config_file` argument, the client looks in the working directory for the first of these files:

```text
binaaz.toml
binaaz.yaml
binaaz.yml
binaaz.json
```

To load a file from somewhere else, set `BINAAZ_CONFIG=/path/to/file` or pass `config_file=`:

```python
bina = BinaAz(config_file="/etc/my-crm/binaaz.toml")
```

The same settings in each format:

::::{tab-set}

:::{tab-item} TOML
```toml
timeout = 30
max_retries = 2
code_attempts = 3
user_agent = "my-agency-crm/1.0 binaaz-python-sdk/{version}"

[endpoints]
graphql = "/graphql"
```
:::

:::{tab-item} YAML
```yaml
timeout: 30
max_retries: 2
code_attempts: 3
user_agent: "my-agency-crm/1.0 binaaz-python-sdk/{version}"
endpoints:
  graphql: /graphql
```
:::

:::{tab-item} JSON
```json
{
  "timeout": 30,
  "max_retries": 2,
  "code_attempts": 3,
  "user_agent": "my-agency-crm/1.0 binaaz-python-sdk/{version}",
  "endpoints": {"graphql": "/graphql"}
}
```
:::

::::

YAML needs the `yaml` extra and TOML on Python 3.10 needs the `toml` extra, see [Installation](installation.md#optional-extras). There is a ready example in the repository: [examples/binaaz.toml](https://github.com/qiyascc/binaaz-python-sdk/blob/main/examples/binaaz.toml).

:::{tip}
Keep the session cookie out of config files that go into version control. Use the environment variable or a file that is listed in `.gitignore`.
:::

## All settings

| Setting | Environment variable | Default | What it does |
| --- | --- | --- | --- |
| `cookie` | `BINAAZ_COOKIE` | empty | The signed in session as a `Cookie` header value. Empty until you sign in or pass one |
| `base_url` | `BINAAZ_BASE_URL` | `https://bina.az` | bina.az address. The GraphQL endpoint lives under it |
| `photos_url` | `BINAAZ_PHOTOS_URL` | `https://photos.bina.az` | Address of the photo service |
| `login_url` | `BINAAZ_LOGIN_URL` | `https://api.digit-u.id` | Address of the SMS login service bina.az uses |
| `return_to` | `BINAAZ_RETURN_TO` | `https://bina.az/` | Page the SMS login service is told to return to |
| `endpoints` | `BINAAZ_ENDPOINTS__<NAME>` | see below | Path of every call, relative to its service address |
| `language` | `BINAAZ_LANGUAGE` | `az` | Language sent to the SMS login service |
| `timeout` | `BINAAZ_TIMEOUT` | `30` | Seconds to wait for an answer |
| `connect_timeout` | `BINAAZ_CONNECT_TIMEOUT` | `10` | Seconds to wait for a connection |
| `max_retries` | `BINAAZ_MAX_RETRIES` | `2` | Extra attempts for calls that are safe to repeat, from 0 to 10 |
| `code_attempts` | `BINAAZ_CODE_ATTEMPTS` | `3` | Attempts for an SMS login call whose answer has no known error, from 1 to 10 |
| `backoff_base` | `BINAAZ_BACKOFF_BASE` | `0.6` | First wait between retries, in seconds |
| `backoff_cap` | `BINAAZ_BACKOFF_CAP` | `8` | Longest wait between retries, in seconds |
| `user_agent` | `BINAAZ_USER_AGENT` | `binaaz-python-sdk/{version}` | The User-Agent header. `{version}` is replaced with the SDK version |
| `allow_insecure_http` | `BINAAZ_ALLOW_INSECURE_HTTP` | `false` | Allow plain http addresses outside localhost, for a test server on a private network only |

Values are checked when the settings load. A negative timeout, `max_retries=11` or an address without `http://` or `https://` raises a pydantic validation error at once, not on the first request.

## Endpoints

The path of every call is a setting too, so a change on the bina.az side can be followed without a new release of the SDK.

| Name | Default | Service |
| --- | --- | --- |
| `graphql` | `/graphql` | `base_url` |
| `photo_upload` | `/pond` | `photos_url` |
| `photo_rotate` | `/pond/rotate` | `photos_url` |
| `code_send` | `/auth` | `login_url` |
| `code_verify` | `/auth/verify` | `login_url` |

Change one in a file:

```toml
[endpoints]
photo_upload = "/pond"
```

or in the environment:

```bash
export BINAAZ_ENDPOINTS__PHOTO_UPLOAD=/pond
```

## The User-Agent

The SDK sends `binaaz-python-sdk/<version>` as its User-Agent and does not pretend to be a browser. If you run a product on top of it, put your own name in front so bina.az can tell your traffic apart:

```python
bina = BinaAz(user_agent="my-agency-crm/1.0 (+https://example.az) binaaz-python-sdk/{version}")
```

## Plain http

Every address must use https, because the session cookie travels with the requests. `localhost`, `127.0.0.1` and `::1` are allowed over plain http for local test servers. Any other plain http address raises `ConfigurationError` when the client is created, unless you set `allow_insecure_http=True`. Only do that for a test server on a private network.

## Proxies and a custom HTTP client

The client builds its own `httpx.Client` (or `httpx.AsyncClient`) with the configured timeouts. To use a proxy, custom certificates or a transport of your own, build the httpx client yourself and pass it as `http_client=`:

```python
import httpx

from binaaz_sdk import BinaAz

http = httpx.Client(proxy="http://proxy.internal:3128", timeout=httpx.Timeout(30, connect=10))
bina = BinaAz(http_client=http)
```

The `proxy=` argument needs httpx 0.26 or newer; older versions call it `proxies=`.

When you pass your own client, closing `BinaAz` leaves it open; close it yourself. The SDK clears the httpx cookie jar after every answer and keeps the session in its own store, so do not rely on cookies stored in the httpx client.
