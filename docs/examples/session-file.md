# A session file

Signing in on every run is slow, and for SMS accounts it needs a person to type the code. This script signs in once, saves the session to a file, and reuses it until bina.az stops accepting it.

```python
import os
import sys
from pathlib import Path

from binaaz_sdk import AuthenticationError, BinaAz

SESSION = Path(os.environ.get("BINAAZ_SESSION_FILE", "binaaz.session"))


def sign_in(bina: BinaAz) -> None:
    email = os.environ.get("BINAAZ_EMAIL")
    if email:
        bina.auth.login(email, os.environ["BINAAZ_PASSWORD"])
    else:
        phone = os.environ.get("BINAAZ_PHONE") or input("Phone: ")
        sent = bina.auth.send_code(phone)
        if sent.retried:
            print("More than one SMS may arrive, use the latest code")
        bina.auth.verify_code(phone, input("SMS code: "))
    SESSION.write_text(bina.cookie)
    SESSION.chmod(0o600)


def signed_in_client() -> BinaAz:
    bina = BinaAz(SESSION.read_text().strip() if SESSION.exists() else None)
    try:
        if SESSION.exists():
            bina.profile()
            return bina
    except AuthenticationError:
        print("The saved session expired, signing in again", file=sys.stderr)
    sign_in(bina)
    return bina


if __name__ == "__main__":
    with signed_in_client() as bina:
        profile = bina.profile()
        print("Signed in as", profile.name, profile.kind)
        SESSION.write_text(bina.cookie)
```

How it works:

- `signed_in_client` loads the saved cookie and checks it with `bina.profile()`, which is a cheap read.
- If there is no file, or the check raises `AuthenticationError`, it signs in. With `BINAAZ_EMAIL` and `BINAAZ_PASSWORD` set it uses email and password, otherwise it asks for a phone number and an SMS code.
- After every successful sign in, and again at the end, the current cookie is written back. bina.az renews some cookies on its own, and the client always holds the latest ones.
- `chmod(0o600)` makes the file readable by your user only on Linux and macOS. On Windows the call does little; keep the file in your user folder.

Import `signed_in_client` from your other scripts so they all share one session:

```python
from session_file import signed_in_client

with signed_in_client() as bina:
    print(len(bina.items.all("published")))
```
