# Post from a folder

An agency keeps each property in its own folder: the photos and a small JSON file with the details. This script posts every folder that has not been posted yet and writes the result next to the photos.

```text
listings/
    nizami-10/
        listing.json
        01.jpg
        02.jpg
        03.jpg
        04.jpg
    yasamal-22/
        listing.json
        01.jpg
        ...
```

`listing.json` holds every field of a {py:class}`~binaaz_sdk.Listing` except `photo_ids`:

```json
{
  "category_id": 3,
  "is_leased": false,
  "price": 120000,
  "rooms": 3,
  "area": {"value": 85},
  "floor": {"value": 4, "total": 9},
  "location": {"address": "Nizami street 10", "city_id": "1", "latitude": 40.379, "longitude": 49.846},
  "contact": {"type": "AGENT", "name": "Agency"},
  "description": "Renovated three room flat near the metro.",
  "has_repair": true
}
```

The script:

```python
import json
import sys
from pathlib import Path

from binaaz_sdk import BinaAz, InvalidRequestError, ItemError, Listing, OutcomeUnknownError

PHOTO_TYPES = {".jpg", ".jpeg", ".png"}


def photos_in(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in PHOTO_TYPES)


def post(bina: BinaAz, folder: Path) -> None:
    done = folder / "posted.json"
    if done.exists() or (folder / "unknown.txt").exists():
        return
    data = json.loads((folder / "listing.json").read_text(encoding="utf-8"))
    files = photos_in(folder)[:30]
    try:
        Listing.model_validate({**data, "photo_ids": ["check"] * len(files)})
    except ValueError as exc:
        print(f"{folder.name}: listing.json is not valid: {exc}")
        return
    if len(files) < 4:
        print(f"{folder.name}: needs at least 4 photos, has {len(files)}")
        return
    uploaded = bina.photos.upload_many(files)
    try:
        result = bina.items.create({**data, "photo_ids": [p.id for p in uploaded]})
    except ItemError as exc:
        print(f"{folder.name}: bina.az refused it: {exc.status} {exc.errors}")
        return
    except OutcomeUnknownError:
        print(f"{folder.name}: no answer from bina.az, check the pending tab before posting again")
        (folder / "unknown.txt").write_text("check the account before retrying\n")
        return
    done.write_text(json.dumps({"id": result.id, "url": result.url, "state": str(result.state)}, indent=2))
    print(f"{folder.name}: posted as {result.id} {result.url}")


def main(root: str) -> None:
    from session_file import signed_in_client

    with signed_in_client() as bina:
        for folder in sorted(Path(root).iterdir()):
            if folder.is_dir() and (folder / "listing.json").exists():
                try:
                    post(bina, folder)
                except InvalidRequestError as exc:
                    print(f"{folder.name}: {exc}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "listings")
```

Points worth noting:

- The listing is validated before any photo is uploaded, with placeholder photo ids, so a typo in `listing.json` costs no uploads.
- `posted.json` marks a folder as done. Running the script again skips it, which makes the script safe to rerun after a crash.
- An `OutcomeUnknownError` writes `unknown.txt`, and later runs skip that folder until you look. Check the pending tab by hand, then delete `unknown.txt` to post it again or write `posted.json` yourself if the listing is there.
- Photo files are sorted by name, so `01.jpg` becomes the cover.
- `signed_in_client` comes from the [session file example](session-file.md).
