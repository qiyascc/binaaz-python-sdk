# Signing in

Most of what the SDK does happens on behalf of a bina.az account: posting, editing, prolonging and deleting listings, uploading photos and paying. bina.az keeps a signed in account in a session cookie, and so does the SDK. This page shows the three ways to get that cookie and how to keep it between runs.

The catalog (categories, cities, regions, townships, landmarks) is public and needs no session at all.

## Email and password

Agency and residence accounts usually sign in with an email and a password.

```python
from binaaz_sdk import BinaAz

with BinaAz() as bina:
    profile = bina.auth.login("agency@example.az", "password")
    print(profile.kind, profile.name, profile.email)
    saved = bina.cookie
```

`login` does two things. It sends the sign in request, which makes bina.az set a session cookie, and then it reads the profile of the account with that cookie, so you know straight away that the session works. The return value is a {py:class}`~binaaz_sdk.Profile`.

If bina.az refuses the email or the password, you get `BadRequestError` with the reason bina.az gave. Your previous session, if the client had one, is kept, so a failed attempt never leaves the client signed out.

## SMS code

Accounts registered with a phone number sign in with a code that bina.az sends by SMS. It takes two calls: one to send the code and one to check it.

```python
from binaaz_sdk import BinaAz

with BinaAz() as bina:
    sent = bina.auth.send_code("050 123 45 67")
    if sent.retried:
        print("More than one SMS may arrive, use the latest code")
    code = input("SMS code: ")
    profile = bina.auth.verify_code("050 123 45 67", code)
    saved = bina.cookie
```

### Phone numbers

`send_code` and `verify_code` accept an Azerbaijani mobile number written the way people write it. All of these are the same number:

```text
050 123 45 67
0501234567
+994 50 123 45 67
994501234567
501234567
```

The number must have nine digits after the country code and start with one of the mobile operator codes 10, 50, 51, 55, 60, 70, 77 or 99. Anything else raises `InvalidRequestError` before the code is requested.

### What `send_code` returns

{py:class}`~binaaz_sdk.CodeSent` has four fields:

| Field | Meaning |
| --- | --- |
| `phone` | The number in the local form the login service expects, such as `0501234567` |
| `code_requests_left` | How many more codes bina.az will send to this number for now, when it says so |
| `retried` | `True` when the first attempt got no usable answer and the request was sent again |
| `raw` | The answer of the login service as it came |

`sent.more_than_one_sms` is the same as `sent.retried` and reads better in an `if`.

### Why a code can be sent twice

bina.az uses a separate login service for SMS codes, and that service sometimes answers with an error page instead of a real answer. When that happens the SDK asks again, up to `code_attempts` times (3 by default). The earlier request may still have reached the phone, so the user can get two SMS messages. Only the latest code is valid; `retried` tells you when to say so on the screen.

The same rule applies to `verify_code`. If the check had to be repeated and the code is then refused, the error is a `CodeRejectedError` whose message says the code may have been used by the earlier attempt. Ask for a new code in that case.

A timeout on the login service is never repeated. You get `OutcomeUnknownError`, because there is no way to know whether the SMS went out.

### Limits

Too many codes or too many wrong codes for one number raise `RateLimitError`. Wait before asking again. A number the login service does not accept raises `BadRequestError`.

## A cookie you already have

If you are signed in to bina.az in a browser, you can reuse that session. Pass the cookie to the client in any of these forms:

```python
bina = BinaAz("_binaaz_session=abc123; other=value")
bina = BinaAz("Cookie: _binaaz_session=abc123")
bina = BinaAz({"_binaaz_session": "abc123"})
bina = BinaAz([{"name": "_binaaz_session", "value": "abc123", "domain": "bina.az"}])
```

The last form is what browser cookie export extensions produce, so you can paste their JSON as is, either as a list or as the JSON text. Cloudflare cookies such as `cf_clearance` and `__cf_bm` are dropped from every form; the SDK never stores or sends them.

To change the session of a client that already exists, use `set_cookie`:

```python
bina.set_cookie(saved)
```

A non empty value that contains no usable cookie raises `InvalidRequestError`, so a typo does not silently sign you out.

## Keep the session between runs

`bina.cookie` is the whole session as one `Cookie` header string. Store it somewhere safe after signing in and pass it back the next time:

```python
from pathlib import Path

from binaaz_sdk import BinaAz

SESSION = Path("binaaz.session")

bina = BinaAz(SESSION.read_text() if SESSION.exists() else None)
if not SESSION.exists():
    bina.auth.login("agency@example.az", "password")
    SESSION.write_text(bina.cookie)
print(bina.profile().name)
```

bina.az renews some cookies on its own. The SDK picks up every `Set-Cookie` from bina.az and its photo service and removes cookies bina.az expires, so `bina.cookie` is always the current state. Save it again from time to time, for example at the end of a job.

You can also put the cookie in the environment or a config file instead of code:

```bash
export BINAAZ_COOKIE="_binaaz_session=abc123"
```

```python
bina = BinaAz()
```

:::{warning}
The cookie is as good as the password while it is valid. Keep it out of version control, out of logs and out of error reports. The `cookie` setting is a pydantic `SecretStr`, so it does not show up when settings are printed.
:::

## Check and end a session

```python
profile = bina.profile()
profile.is_company
```

`bina.profile()` (the same as `bina.auth.profile()`) reads the account of the current session. It raises `AuthenticationError` when the session is missing or expired. A `CompanyProfile` (agencies and residences) can manage listings; other kinds get `NotSupportedError` from the listing management calls.

| `Profile` field | Meaning |
| --- | --- |
| `kind` | The profile type bina.az reports, such as `CompanyProfile` |
| `id`, `name`, `email`, `phone` | Account details |
| `contact_name` | The contact name shown on listings |
| `path` | The profile page path on bina.az |
| `agency` | The agency name, for agency accounts |
| `is_company` | `True` for a `CompanyProfile` |

`bina.clear_session()` forgets the session in the client. It does not sign the account out on bina.az; the cookie you saved earlier keeps working until bina.az expires it.

## When the session expires

Every call that needs a session raises `AuthenticationError` once bina.az stops accepting it. Catch it at the top of a job, sign in again and save the new cookie:

```python
from binaaz_sdk import AuthenticationError

try:
    page = bina.items.list("published")
except AuthenticationError:
    bina.auth.login("agency@example.az", "password")
    SESSION.write_text(bina.cookie)
    page = bina.items.list("published")
```
