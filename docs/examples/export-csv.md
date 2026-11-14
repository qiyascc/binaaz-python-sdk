# Export to CSV

A spreadsheet of every listing on the account: id, title, state, price, expiry date and link. Handy for a weekly report or for checking what is about to expire.

```python
import csv
import sys
from datetime import datetime, timezone

from binaaz_sdk import BinaAz, ItemTab

TABS = [ItemTab.PUBLISHED, ItemTab.PENDING, ItemTab.AWAITING_PAYMENT, ItemTab.EXPIRED, ItemTab.REJECTED]
FIELDS = ["id", "tab", "state", "title", "price", "currency", "expires_at", "days_left", "updated_at", "url"]


def rows(bina: BinaAz):
    now = datetime.now(timezone.utc)
    for tab in TABS:
        for item in bina.items.all(tab):
            days_left = (item.expires_at - now).days if item.expires_at else ""
            yield {
                "id": item.id,
                "tab": tab.name.lower(),
                "state": str(item.state),
                "title": item.title or "",
                "price": item.price.total if item.price else "",
                "currency": item.price.currency if item.price else "",
                "expires_at": item.expires_at.isoformat() if item.expires_at else "",
                "days_left": days_left,
                "updated_at": item.updated_at.isoformat() if item.updated_at else "",
                "url": item.url or "",
            }


def main(path: str) -> None:
    from session_file import signed_in_client

    with signed_in_client() as bina, open(path, "w", newline="", encoding="utf-8-sig") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        writer.writeheader()
        count = 0
        for row in rows(bina):
            writer.writerow(row)
            count += 1
    print(f"{count} listings written to {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "binaaz-listings.csv")
```

Notes:

- The tabs are read one by one so the CSV says which tab each listing came from.
- `utf-8-sig` writes a byte order mark, which makes Excel open Azerbaijani letters (ə, ğ, ı, ö, ş, ü, ç) correctly.
- `expires_at` from bina.az carries its time zone, so subtracting a UTC `now` gives the right number of days.
- `item.price.total` is a `Decimal`; the csv module writes it as plain text such as `120000`.

## With pandas

If you work in pandas, build a DataFrame from the same rows:

```python
import pandas as pd

with signed_in_client() as bina:
    frame = pd.DataFrame(rows(bina))

print(frame.groupby("tab")["price"].count())
frame.to_excel("binaaz-listings.xlsx", index=False)
```

`to_excel` needs `openpyxl` (`pip install pandas openpyxl`).
