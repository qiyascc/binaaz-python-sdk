# A daily prolong job

Listings expire after a while and drop off the site. This job runs once a day, finds listings that expire within the next few days or have just expired, and prolongs them.

```python
import logging
import sys
from datetime import datetime, timedelta, timezone

from binaaz_sdk import BinaAzError, ItemError, ItemTab, OutcomeUnknownError

DAYS_AHEAD = 2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("prolong")


def due(item, now):
    return item.expires_at is not None and item.expires_at <= now + timedelta(days=DAYS_AHEAD)


def main() -> int:
    from session_file import signed_in_client

    now = datetime.now(timezone.utc)
    failures = 0
    with signed_in_client() as bina:
        candidates = [item for item in bina.items.all(ItemTab.PUBLISHED) if due(item, now)]
        candidates += list(bina.items.all(ItemTab.EXPIRED))
        log.info("%d listings to prolong", len(candidates))
        for item in candidates:
            try:
                result = bina.items.prolong(item.id)
                log.info("prolonged %s %s -> %s", item.id, item.title, result.state)
            except ItemError as exc:
                log.warning("bina.az refused %s: %s", item.id, exc)
                failures += 1
            except OutcomeUnknownError:
                log.warning("no answer for %s, it will be checked again tomorrow", item.id)
            except BinaAzError as exc:
                log.error("could not prolong %s: %s", item.id, exc)
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

The job exits with status 1 when something failed, so a scheduler or a monitoring tool can notice. An unknown outcome is not counted as a failure: the listing is read again the next day, and if the prolong did go through it will no longer be due.

Whether a listing can be prolonged, and on what terms, is decided by bina.az. A refusal comes back as `ItemError` with the reason.

## Run it every day

::::{tab-set}

:::{tab-item} Linux cron
Edit the crontab with `crontab -e` and add a line that runs the job at 09:00 every day:

```text
0 9 * * * cd /home/agency/binaaz && .venv/bin/python prolong.py >> prolong.log 2>&1
```
:::

:::{tab-item} systemd timer
`/etc/systemd/system/binaaz-prolong.service`:

```ini
[Unit]
Description=Prolong bina.az listings

[Service]
Type=oneshot
User=agency
WorkingDirectory=/home/agency/binaaz
ExecStart=/home/agency/binaaz/.venv/bin/python prolong.py
```

`/etc/systemd/system/binaaz-prolong.timer`:

```ini
[Unit]
Description=Prolong bina.az listings every morning

[Timer]
OnCalendar=*-*-* 09:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Then `systemctl enable --now binaaz-prolong.timer`.
:::

:::{tab-item} Windows Task Scheduler
In CMD:

```bat
schtasks /Create /SC DAILY /ST 09:00 /TN "binaaz prolong" /TR "C:\binaaz\.venv\Scripts\python.exe C:\binaaz\prolong.py"
```

The task runs with the working directory of Task Scheduler, so keep the session file path absolute (set `BINAAZ_SESSION_FILE`) or change directory in the script.
:::

::::
