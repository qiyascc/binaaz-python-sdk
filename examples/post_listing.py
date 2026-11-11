from __future__ import annotations

import os
import sys
from pathlib import Path

from binaaz_sdk import BinaAz, Category, ContactType, ItemError, Listing

SESSION = Path("binaaz.session")


def signed_in(bina: BinaAz) -> None:
    if SESSION.exists():
        bina.set_cookie(SESSION.read_text())
        return
    phone = os.environ["BINAAZ_PHONE"]
    sent = bina.auth.send_code(phone)
    if sent.retried:
        print("More than one SMS may arrive, use the latest code")
    bina.auth.verify_code(phone, input("SMS code: "))
    SESSION.write_text(bina.cookie)


def main(folder: str) -> None:
    with BinaAz() as bina:
        signed_in(bina)
        photos = bina.photos.upload_many(sorted(Path(folder).glob("*.jpg"))[:30])
        listing = Listing(
            category_id=Category.APARTMENT_NEW_BUILDING,
            is_leased=False,
            price=150000,
            rooms=2,
            area={"value": 70},
            floor={"value": 8, "total": 16},
            location={"address": "Yasamal", "city_id": "1", "latitude": 40.393, "longitude": 49.808},
            contact={"type": ContactType.OWNER, "name": "Owner"},
            photo_ids=[p.id for p in photos],
        )
        try:
            result = bina.items.create(listing)
        except ItemError as exc:
            print(exc.status, exc.errors)
            raise
        print(result.id, result.state, result.url)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
