from __future__ import annotations

import io
from typing import Any

import pytest

from binaaz_sdk import BadRequestError, InvalidRequestError, ServerError

from .conftest import COOKIE, data

UPLOADED = {"photos": [{"id": "2026/11/11/abc.jpg", "thumbnail_url": "https://img.test/t/abc.jpg"}]}


def test_upload_bytes(gw, bina):
    gw.reply(UPLOADED)
    photo = bina.photos.upload(b"\xff\xd8jpeg", filename="cover.jpg")
    assert photo.id == "2026/11/11/abc.jpg" and photo.thumbnail_url == "https://img.test/t/abc.jpg"
    request = gw.requests[0]
    assert request.url.host == "photos.bina.az" and request.url.path == "/pond"
    assert request.url.params["lang"] == "az"
    assert b'name="images[]"; filename="cover.jpg"' in request.content
    assert gw.header("cookie") == COOKIE and gw.header("referer") == "https://bina.az/items/new"


def test_upload_path_and_file(gw, bina, tmp_path):
    picture = tmp_path / "room.png"
    picture.write_bytes(b"\x89PNG")
    gw.reply(UPLOADED).reply(UPLOADED)
    bina.photos.upload(picture)
    assert b'filename="room.png"' in gw.requests[0].content and b"image/png" in gw.requests[0].content
    bina.photos.upload(io.BytesIO(b"\xff\xd8"))
    assert b'filename="photo.jpg"' in gw.requests[1].content


def test_upload_many(gw, bina):
    gw.reply(UPLOADED).reply({"photos": [{"id": "two"}]})
    assert [p.id for p in bina.photos.upload_many([b"a", b"b"])] == ["2026/11/11/abc.jpg", "two"]


def test_upload_problems(gw, bina):
    with pytest.raises(InvalidRequestError):
        bina.photos.upload(b"")
    not_a_photo: Any = 42
    with pytest.raises(InvalidRequestError):
        bina.photos.upload(not_a_photo)
    gw.reply({"photos": []})
    with pytest.raises(ServerError):
        bina.photos.upload(b"x")
    gw.reply(b"", status=413)
    with pytest.raises(BadRequestError):
        bina.photos.upload(b"x")


def test_rotate(gw, bina):
    gw.reply({"id": "rotated.jpg", "thumbnail_url": "https://img.test/r.jpg"})
    assert bina.photos.rotate("2026/11/11/abc.jpg", 90).id == "rotated.jpg"
    params = gw.requests[0].url.params
    assert gw.requests[0].url.path == "/pond/rotate" and params["id"] == "2026/11/11/abc.jpg"
    assert params["angle"] == "90" and gw.requests[0].content == b""
    with pytest.raises(InvalidRequestError):
        bina.photos.rotate("x", 45)


def test_catalog(gw, bina):
    gw.reply(data(categories=[{"id": "1", "name": "Apartments", "children": [{"id": "2", "name": "New"}]}]))
    gw.reply(data(regions=[{"id": "4", "name": "Yasamal"}]))
    gw.reply(data(landmarks=[{"id": "m1", "name": "Nizami"}]))
    assert bina.catalog.categories()[0].children[0].name == "New"
    assert bina.catalog.regions("1")[0].name == "Yasamal"
    assert bina.catalog.landmarks("1", 40.379, 49.846)[0].id == "m1"
    assert gw.body(1)["variables"] == {"c": "1"}
    assert gw.body(2)["variables"] == {"c": "1", "lat": 40.379, "lng": 49.846}
    assert gw.header("cookie", 0) == ""
