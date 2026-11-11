from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import IO, Any, Mapping, Optional, Union

from . import queries
from ._core import CodeReply, Flow, Op
from .enums import PHOTO_ANGLES, PHOTOS_MAX, PHOTOS_MIN, ItemTab
from .errors import (
    AuthenticationError,
    BadRequestError,
    CodeRejectedError,
    InvalidRequestError,
    ItemError,
    NotFoundError,
    NotSupportedError,
    RateLimitError,
    ServerError,
)
from .messages import text
from .models import (
    CategoryNode,
    CodeSent,
    Item,
    ItemPage,
    ItemResult,
    Listing,
    PaidService,
    Payment,
    Photo,
    Place,
    Profile,
)

OPERATORS = ("10", "50", "51", "55", "60", "70", "77", "99")
PAGE_MAX = 100

ListingLike = Union[Listing, Mapping[str, Any]]
PhotoLike = Union[bytes, bytearray, str, "os.PathLike[str]", IO[bytes]]
TabLike = Union[ItemTab, str, None]

CREATE_STATUS = {
    "RESTRICTED": "error.status_restricted",
    "UNVERIFIED": "error.status_unverified",
    "INVALID": "error.status_invalid",
    "FAILURE": "error.status_failure",
}
UPDATE_STATUS = {
    "LOCKED": "error.status_locked",
    "FORBIDDEN": "error.status_forbidden",
    "NOT_FOUND": "error.status_not_found",
    "INVALID": "error.status_invalid",
}


def required(value: Any, name: str, limit: int = 255) -> str:
    result = str(value if value is not None else "").strip()
    if not result:
        raise InvalidRequestError(text("value.empty", field=name))
    if len(result) > limit:
        raise InvalidRequestError(text("value.too_long", field=name, limit=limit))
    return result


def site_id(value: Any, name: str) -> str:
    result = required(value, name, 64)
    if any(ch in result for ch in "/?#& "):
        raise InvalidRequestError(text("value.id", field=name, value=value))
    return result


def whole(value: Any, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise InvalidRequestError(text("value.range", field=name, low=low, high=high, value=value))
    return value


def local_phone(raw: Any) -> str:
    digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if digits.startswith("994"):
        digits = digits[3:]
    if digits.startswith("0"):
        digits = digits[1:]
    if len(digits) != 9 or not digits.startswith(OPERATORS):
        raise InvalidRequestError(text("value.phone", value=raw))
    return "0" + digits


def listing(value: ListingLike) -> Listing:
    if isinstance(value, Listing):
        return value
    try:
        return Listing.model_validate(dict(value))
    except ValueError as exc:
        raise InvalidRequestError(str(exc)) from None


def item_tab(value: TabLike) -> Optional[str]:
    if value is None or value == "":
        return None
    try:
        return ItemTab(str(value).upper()).value
    except ValueError:
        named = {t.name: t.value for t in ItemTab}
        if str(value).upper() in named:
            return named[str(value).upper()]
        raise InvalidRequestError(text("value.choice", field="tab", choices=tuple(named), value=value)) from None


def _detail(errors: list[Any]) -> str:
    parts = []
    for error in errors:
        if isinstance(error, Mapping):
            where = ".".join(str(p) for p in error.get("path") or []) or "item"
            parts.append(f"{where}: {error.get('message')}")
    return "; ".join(parts)


def unwrap(data: Mapping[str, Any], name: str, statuses: Optional[Mapping[str, str]] = None) -> Mapping[str, Any]:
    payload = data.get(name)
    if not isinstance(payload, Mapping):
        raise AuthenticationError(text("error.session"))
    errors = [e for e in payload.get("errors") or [] if isinstance(e, Mapping)]
    status = payload.get("status")
    detail = _detail(errors)
    if statuses and status in statuses:
        until = payload.get("lockedUntil")
        params = {"until": f" until {until}" if until else ""} if status == "LOCKED" else {}
        message = text(statuses[str(status)], **params) + (f": {detail}" if detail else "")
        kind = NotFoundError if status == "NOT_FOUND" else ItemError
        if kind is ItemError:
            raise ItemError(message, status=str(status), errors=errors, locked_until=until, body=payload)
        raise NotFoundError(message, body=payload)
    if errors:
        raise ItemError(text("error.validation", detail=detail), errors=errors, body=payload)
    return payload


def read_photo(photo: PhotoLike, filename: Optional[str], content_type: Optional[str]) -> tuple[str, bytes, str]:
    if isinstance(photo, (bytes, bytearray)):
        content, name = bytes(photo), filename or "photo.jpg"
    elif isinstance(photo, (str, os.PathLike)):
        path = Path(photo)
        content, name = path.read_bytes(), filename or path.name
    elif hasattr(photo, "read"):
        content = photo.read()
        if not isinstance(content, (bytes, bytearray)):
            raise InvalidRequestError(text("value.photo_file", value=photo))
        content = bytes(content)
        name = filename or os.path.basename(str(getattr(photo, "name", "") or "")) or "photo.jpg"
    else:
        raise InvalidRequestError(text("value.photo_file", value=photo))
    if not content:
        raise InvalidRequestError(text("value.empty", field="photo"))
    kind = content_type or mimetypes.guess_type(name)[0] or "image/jpeg"
    return name, content, kind


def _graphql(query: str, parse: Any, variables: Optional[Mapping[str, Any]] = None, *, name: str = "",
             safe: bool = False, session: bool = True, action: str = "The request") -> Op:
    body: dict[str, Any] = {"query": query, "variables": dict(variables or {})}
    if name:
        body["operationName"] = name
    return Op("POST", "base_url", "graphql", parse, body=body, safe=safe, session=session, action=action)


class _Resource:
    def __init__(self, client: Any) -> None:
        self._client = client

    @property
    def _settings(self) -> Any:
        return self._client.settings

    def _run(self, op: Op) -> Any:
        return self._client._run(op)

    def _flow(self, flow: Flow[Any]) -> Any:
        return self._client._flow(flow)


def _profile(data: Mapping[str, Any]) -> Profile:
    body = data.get("profile")
    if not isinstance(body, Mapping) or not body:
        raise AuthenticationError(text("error.no_profile"))
    return Profile.from_api(body)


def _company(data: Mapping[str, Any]) -> Mapping[str, Any]:
    body = data.get("profile")
    if not isinstance(body, Mapping) or not body:
        raise AuthenticationError(text("error.no_profile"))
    if body.get("__typename") != "CompanyProfile":
        raise NotSupportedError(text("error.not_company", kind=body.get("__typename")))
    return body


def _sign_in_payload(data: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = data.get("signIn")
    payload = payload if isinstance(payload, Mapping) else {}
    errors = [e for e in payload.get("errors") or [] if isinstance(e, Mapping)]
    if errors or not payload.get("profile"):
        raise BadRequestError(text("error.login", detail=_detail(errors) or "no profile"), body=payload)
    return payload


def _code_error(reply: CodeReply, retried_message: bool = False) -> Exception:
    kind = str(reply.body.get("error") or "")
    detail = str(reply.body.get("message") or kind)
    if kind in ("code_requests", "failed_attempts"):
        return RateLimitError(text("error.code_limit", detail=detail), status_code=reply.status, body=reply.body)
    if kind == "phone":
        return BadRequestError(text("error.code_phone", detail=detail), status_code=reply.status, body=reply.body)
    key = "error.code_reused" if retried_message and reply.attempts > 1 else "error.code_rejected"
    return CodeRejectedError(text(key, detail=detail), status_code=reply.status, body=reply.body)


class Auth(_Resource):
    def profile(self) -> Any:
        return self._run(_graphql(queries.PROFILE, _profile, name="Profile", safe=True))

    def login(self, email: str, password: str) -> Any:
        variables = {"input": {"emailAndPassword": {"email": required(email, "email"),
                                                    "password": required(password, "password", 200)}}}
        return self._flow(self._sign_in(variables))

    def send_code(self, phone: str) -> Any:
        number = local_phone(phone)

        def parse(reply: CodeReply) -> CodeSent:
            if reply.status >= 400:
                raise _code_error(reply)
            left = reply.body.get("code_requests_left")
            return CodeSent(number, left if isinstance(left, int) and not isinstance(left, bool) else None,
                            reply.attempts > 1, dict(reply.body))

        return self._run(Op("POST", "login_url", "code_send", parse, body={"phone": number}, flaky=True,
                            session=False, action="Sending the SMS code"))

    def verify_code(self, phone: str, code: str) -> Any:
        return self._flow(self._verify(local_phone(phone), required(code, "code", 12)))

    def _verify(self, number: str, code: str) -> Flow[Profile]:
        def parse(reply: CodeReply) -> str:
            if reply.status >= 400:
                raise _code_error(reply, retried_message=True)
            token = reply.body.get("access_token")
            if not token:
                raise ServerError(text("error.no_token"), status_code=reply.status, body=reply.body)
            return str(token)

        return_to = base64.b64encode(self._settings.return_to.encode()).decode()
        token: str = yield Op("POST", "login_url", "code_verify", parse,
                              body={"phone": number, "code": code, "return_to": return_to}, flaky=True,
                              session=False, action="Checking the SMS code")
        profile: Profile = yield from self._sign_in({"input": {"accessToken": token}})
        return profile

    def _sign_in(self, variables: Mapping[str, Any]) -> Flow[Profile]:
        previous = dict(self._client._jar)
        self._client._jar = {}
        signed = False
        try:
            yield _graphql(queries.SIGN_IN, _sign_in_payload, variables, name="SignIn", session=False,
                           action="Signing in")
            if not self._client._jar:
                raise ServerError(text("error.no_cookie"))
            signed = True
            profile: Profile = yield _graphql(queries.PROFILE, _profile, name="Profile", safe=True)
        except Exception:
            if not signed:
                self._client._jar = previous
            raise
        return profile


class Items(_Resource):
    def create(self, item: ListingLike) -> Any:
        data = listing(item)
        count = len(data.photo_ids)
        if not PHOTOS_MIN <= count <= PHOTOS_MAX:
            raise InvalidRequestError(text("value.photos", low=PHOTOS_MIN, high=PHOTOS_MAX, count=count))
        parse = lambda body: ItemResult.from_api(unwrap(body, "createItem", CREATE_STATUS))
        return self._run(_graphql(queries.CREATE_ITEM, parse, {"input": data.to_create_input()}, name="CreateItem",
                                  action="Creating the listing"))

    def update(self, item_id: str, item: ListingLike) -> Any:
        given = site_id(item_id, "item_id")
        data = listing(item)
        parse = lambda body: ItemResult.from_api(unwrap(body, "updateItem", UPDATE_STATUS))
        return self._run(_graphql(queries.UPDATE_ITEM, parse, {"input": data.to_update_input(given)},
                                  name="UpdateItem", action="Updating the listing"))

    def delete(self, item_id: str) -> Any:
        given = site_id(item_id, "item_id")
        parse = lambda body: ItemResult.from_api(unwrap(body, "deleteItem"))
        return self._run(_graphql(queries.DELETE_ITEM, parse, {"input": {"itemId": given}}, name="DeleteItem",
                                  action="Deleting the listing"))

    def prolong(self, item_id: str) -> Any:
        given = site_id(item_id, "item_id")
        parse = lambda body: ItemResult.from_api(unwrap(body, "prolongItem"))
        return self._run(_graphql(queries.PROLONG_ITEM, parse, {"input": {"itemId": given}}, name="ProlongItem",
                                  action="Prolonging the listing"))

    def get(self, item_id: str) -> Any:
        given = site_id(item_id, "item_id")

        def parse(body: Mapping[str, Any]) -> Item:
            edit = body.get("itemEdit")
            found = edit.get("item") if isinstance(edit, Mapping) else None
            if not isinstance(found, Mapping) or not found:
                raise NotFoundError(text("error.not_found", item_id=given), status_code=404)
            return Item.from_api(found)

        return self._run(_graphql(queries.ITEM_EDIT, parse, {"id": given}, name="ItemEdit", safe=True))

    def list(self, tab: TabLike = None, first: int = 20, after: Optional[str] = None) -> Any:
        variables = {"state": item_tab(tab), "first": whole(first, "first", 1, PAGE_MAX), "after": after or None}
        return self._run(self._page_op(variables))

    def all(self, tab: TabLike = None, max_pages: int = 50) -> Any:
        return self._flow(self._every(item_tab(tab), whole(max_pages, "max_pages", 1, 10**4)))

    def _page_op(self, variables: Mapping[str, Any]) -> Op:
        parse = lambda body: ItemPage.from_api(_company(body).get("items") or {})
        return _graphql(queries.MY_ITEMS, parse, variables, name="MyItems", safe=True)

    def _every(self, state: Optional[str], max_pages: int) -> Flow[tuple[Item, ...]]:
        items: list[Item] = []
        cursor: Optional[str] = None
        for _ in range(max_pages):
            page: ItemPage = yield self._page_op({"state": state, "first": PAGE_MAX, "after": cursor})
            items.extend(page.items)
            cursor = page.next_cursor
            if not cursor:
                break
        return tuple(items)

    def pay(self, item_id: str, *, confirm: bool = False) -> Any:
        given = site_id(item_id, "item_id")
        if confirm is not True:
            raise InvalidRequestError(text("value.confirm", action="Paying for a listing"))
        parse = lambda body: ItemResult.from_api(unwrap(body, "payForItem"))
        return self._run(_graphql(queries.PAY_FOR_ITEM, parse, {"input": {"itemId": given}}, name="PayForItem",
                                  action="Paying for the listing"))

    def paid_services(self, item_id: str) -> Any:
        return self._flow(self._services(site_id(item_id, "item_id")))

    def _services(self, item_id: str) -> Flow[tuple[PaidService, ...]]:
        ids = [item_id]
        data: Mapping[str, Any] = yield _graphql(queries.PAID_SERVICES, lambda body: body, {"ids": ids},
                                                 name="PaidServices", safe=True)
        out = []
        for service in data.get("paidServices") or []:
            if not isinstance(service, Mapping):
                continue
            details: Mapping[str, Any] = yield _graphql(queries.PAID_SERVICE_DETAILS, lambda body: body,
                                                        {"sid": service.get("id"), "ids": ids},
                                                        name="PaidServiceDetails", safe=True)
            out.append(PaidService.from_api(service, details))
        return tuple(out)

    def buy_service(self, item_id: str, service_id: str, payment_method_id: str, *, option_id: Optional[str] = None,
                    amount: Optional[float] = None, confirm: bool = False) -> Any:
        given = site_id(item_id, "item_id")
        if confirm is not True:
            raise InvalidRequestError(text("value.confirm", action="A paid service"))
        data: dict[str, Any] = {"paidServiceId": required(service_id, "service_id", 64),
                                "paymentMethodId": required(payment_method_id, "payment_method_id", 64),
                                "targetId": [given], "platform": "DESKTOP"}
        if option_id is not None:
            data["paidServiceOptionId"] = required(option_id, "option_id", 64)
        if amount is not None:
            data["amount"] = amount
        parse = lambda body: Payment.from_api(unwrap(body, "createPayment"))
        return self._run(_graphql(queries.CREATE_PAYMENT, parse, {"input": data}, name="CreatePayment",
                                  action="The payment"))


def _photo(body: Mapping[str, Any]) -> Photo:
    photos = body.get("photos") or []
    first = photos[0] if isinstance(photos, list) and photos else None
    if not isinstance(first, Mapping) or first.get("id") in (None, ""):
        raise ServerError(text("error.photo_id"), body=body)
    return Photo.from_api(first)


def _rotated(body: Mapping[str, Any]) -> Photo:
    if not isinstance(body, Mapping) or body.get("id") in (None, ""):
        raise ServerError(text("error.photo_id"), body=body)
    return Photo.from_api(body)


class Photos(_Resource):
    def upload(self, photo: PhotoLike, *, filename: Optional[str] = None, content_type: Optional[str] = None) -> Any:
        return self._run(self._upload_op(photo, filename, content_type))

    def upload_many(self, photos: Any) -> Any:
        ops = [self._upload_op(photo, None, None) for photo in photos]
        return self._flow(self._many(ops))

    def _many(self, ops: list[Op]) -> Flow[tuple[Photo, ...]]:
        out = []
        for op in ops:
            uploaded: Photo = yield op
            out.append(uploaded)
        return tuple(out)

    def _upload_op(self, photo: PhotoLike, filename: Optional[str], content_type: Optional[str]) -> Op:
        name, content, kind = read_photo(photo, filename, content_type)
        return Op("POST", "photos_url", "photo_upload", _photo, query={"lang": "az"},
                  files=[("images[]", (name, content, kind))], action="The photo upload")

    def rotate(self, photo_id: str, angle: int) -> Any:
        if angle not in PHOTO_ANGLES or isinstance(angle, bool):
            raise InvalidRequestError(text("value.choice", field="angle", choices=PHOTO_ANGLES, value=angle))
        query = {"id": required(photo_id, "photo_id", 300), "angle": str(angle), "lang": "az"}
        return self._run(Op("POST", "photos_url", "photo_rotate", _rotated, query=query,
                            action="Rotating the photo"))


def _places(name: str) -> Any:
    return lambda body: tuple(Place.from_api(p) for p in body.get(name) or [] if isinstance(p, Mapping))


class Catalog(_Resource):
    def categories(self) -> Any:
        parse = lambda body: tuple(CategoryNode.from_api(c) for c in body.get("categories") or []
                                   if isinstance(c, Mapping))
        return self._run(_graphql(queries.CATEGORIES, parse, safe=True, session=False))

    def cities(self) -> Any:
        return self._run(_graphql(queries.CITIES, _places("cities"), safe=True, session=False))

    def regions(self, city_id: str) -> Any:
        return self._run(_graphql(queries.REGIONS, _places("regions"), {"c": site_id(city_id, "city_id")},
                                  safe=True, session=False))

    def townships(self, region_id: str) -> Any:
        return self._run(_graphql(queries.TOWNSHIPS, _places("townships"), {"r": site_id(region_id, "region_id")},
                                  safe=True, session=False))

    def landmarks(self, city_id: str, latitude: float, longitude: float) -> Any:
        variables = {"c": site_id(city_id, "city_id"), "lat": float(latitude), "lng": float(longitude)}
        return self._run(_graphql(queries.LANDMARKS, _places("landmarks"), variables, safe=True, session=False))
