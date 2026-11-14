# Alert on rejected listings

Moderation can reject a listing hours after it was posted. This script reads the rejected tab, remembers which rejections it has already reported, and sends a Telegram message for every new one. Run it every 15 minutes from cron or Task Scheduler (see [the prolong job](prolong-job.md#run-it-every-day) for how).

You need a Telegram bot token from [@BotFather](https://t.me/BotFather) and the chat id to write to.

```python
import json
import os
from pathlib import Path

import httpx

from binaaz_sdk import ItemTab

SEEN = Path("rejected-seen.json")
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT = os.environ["TELEGRAM_CHAT_ID"]


def notify(text: str) -> None:
    httpx.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT, "text": text, "disable_web_page_preview": True},
        timeout=15,
    ).raise_for_status()


def main() -> None:
    from session_file import signed_in_client

    seen = set(json.loads(SEEN.read_text())) if SEEN.exists() else set()
    with signed_in_client() as bina:
        rejected = bina.items.all(ItemTab.REJECTED)
    for item in rejected:
        if item.id in seen:
            continue
        notify(f"bina.az rejected listing {item.id}\n{item.title or ''}\n{item.url or ''}")
        seen.add(item.id)
    SEEN.write_text(json.dumps(sorted(seen)))


if __name__ == "__main__":
    main()
```

httpx is already installed with the SDK, so the script needs nothing else.

The reason for a rejection is shown on the bina.az account page. To include it in the message, read `item.raw` for the fields bina.az sends, or fetch more with [`bina.graphql`](../guides/advanced.md#any-graphql-query).
