# Photos

Photos are uploaded to the bina.az photo service first. The upload returns an id, and the listing refers to its photos by those ids. A listing needs between 4 and 30 of them.

## Upload one photo

```python
photo = bina.photos.upload("cover.jpg")
print(photo.id, photo.thumbnail_url)
```

`upload` accepts the photo in three forms:

| Form | Example | File name sent |
| --- | --- | --- |
| A path, as `str` or `pathlib.Path` | `bina.photos.upload("photos/1.jpg")` | The file's name |
| A binary file object | `bina.photos.upload(open("1.jpg", "rb"))` | The file's name, or `photo.jpg` |
| Bytes | `bina.photos.upload(data)` | `photo.jpg` |

Two optional keyword arguments override what is sent:

```python
bina.photos.upload(data, filename="living-room.png", content_type="image/png")
```

Without `content_type`, the type is guessed from the file name and falls back to `image/jpeg`.

An empty file, a file opened in text mode or any other type raises `InvalidRequestError` before the upload starts. A photo that is too large for bina.az comes back as `BadRequestError` with a message saying so.

The result is a {py:class}`~binaaz_sdk.Photo`:

| Field | Meaning |
| --- | --- |
| `id` | The id to put in `Listing.photo_ids` |
| `thumbnail_url` | Address of the thumbnail, when the service returns one |
| `raw` | The whole answer |

## Upload many photos

```python
from pathlib import Path

photos = bina.photos.upload_many(sorted(Path("flat-12").glob("*.jpg")))
photo_ids = [p.id for p in photos]
```

`upload_many` uploads the photos one after another, in the order you give them, and returns a tuple of `Photo` in the same order. The first photo becomes the cover of the listing, so sort the list the way you want it shown.

If one upload fails, the error is raised and the photos uploaded before it stay on the photo service unused. That does no harm; a listing only shows the ids you give it.

## Rotate a photo

```python
turned = bina.photos.rotate(photo.id, 90)
photo_ids[0] = turned.id
```

The angle is one of `90`, `180`, `270` or `-90`. Anything else raises `InvalidRequestError`. Rotating returns a **new** photo with a new id. Use the new id in the listing; the old one still shows the photo the old way.

## Uploads are not repeated

An upload is a write. If the connection drops in the middle, the photo may or may not have reached bina.az, so the SDK raises `OutcomeUnknownError` and does not upload it again on its own. Uploading it again yourself is harmless: at worst an unused copy stays on the photo service.

```python
from binaaz_sdk import OutcomeUnknownError

def upload_with_one_retry(bina, path):
    try:
        return bina.photos.upload(path)
    except OutcomeUnknownError:
        return bina.photos.upload(path)
```

## Photo checklist

- 4 to 30 photos per listing. `items.create` checks the count before sending.
- The first id in `photo_ids` is the cover.
- Rotate before posting, and use the id that `rotate` returns.
- Keep the files: bina.az does not give the originals back.
