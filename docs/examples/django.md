# Django

This example keeps listings in a Django model, posts them with a management command and stores the bina.az session in the database, so every worker and every server uses the same one.

## Settings

```python
BINAAZ_EMAIL = env("BINAAZ_EMAIL")
BINAAZ_PASSWORD = env("BINAAZ_PASSWORD")
```

Use whatever your project uses to read the environment; the point is to keep the credentials out of the code.

## Models

`listings/models.py`:

```python
from django.db import models


class BinaAzSession(models.Model):
    cookie = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)


class Property(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft"
        POSTING = "posting"
        POSTED = "posted"
        UNKNOWN = "unknown"
        REFUSED = "refused"

    title = models.CharField(max_length=200)
    data = models.JSONField()
    photos = models.JSONField(default=list)
    state = models.CharField(max_length=10, choices=State.choices, default=State.DRAFT)
    binaaz_id = models.CharField(max_length=32, blank=True)
    binaaz_url = models.URLField(blank=True)
    error = models.TextField(blank=True)
```

`data` holds the fields of a `Listing` without `photo_ids`, and `photos` a list of file paths under `MEDIA_ROOT`.

## A client that keeps its session in the database

`listings/binaaz.py`:

```python
from django.conf import settings

from binaaz_sdk import AuthenticationError, BinaAz

from .models import BinaAzSession


def client() -> BinaAz:
    row = BinaAzSession.objects.first()
    bina = BinaAz(row.cookie if row else None)
    try:
        if row:
            bina.profile()
            return bina
    except AuthenticationError:
        pass
    bina.auth.login(settings.BINAAZ_EMAIL, settings.BINAAZ_PASSWORD)
    save(bina)
    return bina


def save(bina: BinaAz) -> None:
    BinaAzSession.objects.update_or_create(pk=1, defaults={"cookie": bina.cookie})
```

## The management command

`listings/management/commands/post_to_binaaz.py`:

```python
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from binaaz_sdk import BinaAzError, ItemError, OutcomeUnknownError

from listings.binaaz import client, save
from listings.models import Property


class Command(BaseCommand):
    help = "Post draft properties to bina.az"

    def handle(self, *args, **options):
        drafts = Property.objects.filter(state=Property.State.DRAFT)
        if not drafts.exists():
            return
        with client() as bina:
            for prop in drafts:
                self.post(bina, prop)
            save(bina)

    def post(self, bina, prop):
        prop.state = Property.State.POSTING
        prop.save(update_fields=["state"])
        try:
            photos = bina.photos.upload_many([Path(settings.MEDIA_ROOT) / name for name in prop.photos])
            result = bina.items.create({**prop.data, "photo_ids": [p.id for p in photos]})
        except ItemError as exc:
            prop.state, prop.error = Property.State.REFUSED, f"{exc.status}: {exc.errors}"
        except OutcomeUnknownError as exc:
            prop.state, prop.error = Property.State.UNKNOWN, str(exc)
        except BinaAzError as exc:
            prop.state, prop.error = Property.State.DRAFT, str(exc)
        else:
            prop.state, prop.binaaz_id, prop.binaaz_url = Property.State.POSTED, result.id, result.url or ""
            prop.error = ""
        prop.save()
        self.stdout.write(f"{prop.pk} {prop.title}: {prop.state} {prop.binaaz_url or prop.error}")
```

Run it with `python manage.py post_to_binaaz`, by hand or from cron.

Why the states:

- `POSTING` is saved before anything is sent. If the process dies in the middle, the row stays in `POSTING` and the next run does not pick it up again, so a crash can never post the same property twice.
- `UNKNOWN` marks an `OutcomeUnknownError`. Someone looks at the pending tab on bina.az and moves the row to `POSTED` or back to `DRAFT`.
- Network errors that are known not to have created anything (such as `NotSentError`) put the row back to `DRAFT` for the next run.
- `save(bina)` stores the cookie again at the end, since bina.az may have renewed it.

## In a view

For a request handler use the async client inside an async view, or keep the sync client and move posting to a background task (Celery, Django Q, RQ). Posting uploads several photos and can take a while; it should not run inside a web request.
