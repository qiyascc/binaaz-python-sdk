from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from .enums import PHOTOS_MAX, BuildingType, Category, ContactType, ItemState

ORIGIN = "https://bina.az"


def _pick(body: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = body.get(key)
        if value is not None and value != "":
            return value
    return None


def _str(body: Mapping[str, Any], *keys: str) -> Optional[str]:
    value = _pick(body, *keys)
    return None if value is None else str(value)


def _int(body: Mapping[str, Any], *keys: str) -> Optional[int]:
    value = _pick(body, *keys)
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _money(value: Any) -> Optional[Decimal]:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _when(body: Mapping[str, Any], *keys: str) -> Optional[datetime]:
    value = _pick(body, *keys)
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def site_url(path: Optional[str], origin: str = ORIGIN) -> Optional[str]:
    if not path:
        return None
    return path if path.startswith("http") else origin.rstrip("/") + path


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Area(_Camel):
    value: float = Field(gt=0)
    land: Optional[float] = Field(default=None, gt=0)


class Floor(_Camel):
    value: float
    total: float = Field(gt=0)

    @model_validator(mode="after")
    def _check(self) -> Floor:
        if self.value > self.total:
            raise ValueError("floor.value cannot exceed floor.total")
        return self


class Location(_Camel):
    address: str = Field(min_length=1, max_length=500)
    city_id: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    region_id: Optional[str] = None
    township_id: Optional[str] = None
    landmark_ids: Optional[list[str]] = None


class Contact(_Camel):
    type: ContactType
    name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)


class Listing(_Camel):
    category_id: Category
    is_leased: bool
    price: int = Field(gt=0)
    area: Area
    location: Location
    contact: Contact
    photo_ids: list[str] = Field(default_factory=list, max_length=PHOTOS_MAX)
    description: Optional[str] = Field(default=None, max_length=5000)
    rooms: Optional[int] = Field(default=None, ge=1, le=50)
    floor: Optional[Floor] = None
    has_repair: Optional[bool] = None
    has_mortgage: Optional[bool] = None
    has_bill_of_sale: Optional[bool] = None
    paid_daily: Optional[bool] = None
    building_type: Optional[BuildingType] = None

    @model_validator(mode="after")
    def _check(self) -> Listing:
        if self.paid_daily and not self.is_leased:
            raise ValueError("paid_daily needs is_leased=True")
        if self.building_type and self.category_id != Category.OFFICE:
            raise ValueError("building_type is only valid for offices (category 7)")
        return self

    def _dump(self, **kw: Any) -> dict[str, Any]:
        data = self.model_dump(mode="json", by_alias=True, exclude_none=True, **kw)
        if "categoryId" in data:
            data["categoryId"] = str(data["categoryId"])
        return data

    def to_create_input(self) -> dict[str, Any]:
        return self._dump()

    def to_update_input(self, item_id: str) -> dict[str, Any]:
        data = self._dump(exclude={"category_id", "is_leased", "contact", "building_type"})
        if self.contact.name:
            data["contactName"] = self.contact.name
        return {"itemId": str(item_id), **data}


@dataclass(frozen=True)
class Profile:
    kind: str
    id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_name: Optional[str] = None
    path: Optional[str] = None
    agency: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def is_company(self) -> bool:
        return self.kind == "CompanyProfile"

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> Profile:
        return cls(
            kind=_str(body, "__typename") or "",
            id=_str(body, "id"),
            name=_str(body, "name"),
            email=_str(body, "email"),
            phone=_str(body, "phone"),
            contact_name=_str(body, "contactName"),
            path=_str(body, "path"),
            agency=_str(_map(body.get("agency")), "name"),
            raw=dict(body),
        )


@dataclass(frozen=True)
class Price:
    total: Optional[Decimal]
    currency: str

    @classmethod
    def from_api(cls, body: Any) -> Optional[Price]:
        data = _map(body)
        if not data:
            return None
        return cls(_money(data.get("total")), _str(data, "currency") or "AZN")


@dataclass(frozen=True)
class Item:
    id: str
    state: ItemState
    site_state: Optional[str] = None
    title: Optional[str] = None
    path: Optional[str] = None
    url: Optional[str] = None
    price: Optional[Price] = None
    expires_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    thumbnail: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> Item:
        photos = [p for p in _list(body.get("photos")) if isinstance(p, Mapping)]
        return cls(
            id=_str(body, "id") or "",
            state=ItemState.from_site(body.get("state")),
            site_state=_str(body, "state"),
            title=_str(body, "title"),
            path=_str(body, "path"),
            url=site_url(_str(body, "path")),
            price=Price.from_api(body.get("price")),
            expires_at=_when(body, "expiresAt"),
            updated_at=_when(body, "updatedAt"),
            thumbnail=_str(photos[0], "thumbnail") if photos else None,
            raw=dict(body),
        )


@dataclass(frozen=True)
class ItemPage:
    items: tuple[Item, ...]
    total: Optional[int]
    next_cursor: Optional[str]

    @property
    def has_more(self) -> bool:
        return self.next_cursor is not None

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> ItemPage:
        info = _map(body.get("pageInfo"))
        nodes = tuple(Item.from_api(n) for n in _list(body.get("nodes")) if isinstance(n, Mapping))
        cursor = _str(info, "endCursor") if info.get("hasNextPage") else None
        return cls(nodes, _int(body, "totalCount"), cursor)


@dataclass(frozen=True)
class ItemResult:
    id: Optional[str]
    state: Optional[ItemState]
    site_state: Optional[str] = None
    path: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None
    locked_until: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> ItemResult:
        item = _map(body.get("item"))
        site_state = _str(item, "state")
        return cls(
            id=_str(item, "id"),
            state=ItemState.from_site(site_state) if site_state else None,
            site_state=site_state,
            path=_str(item, "path"),
            url=site_url(_str(item, "path")),
            status=_str(body, "status"),
            locked_until=_str(body, "lockedUntil"),
            raw=dict(body),
        )


@dataclass(frozen=True)
class Photo:
    id: str
    thumbnail_url: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> Photo:
        return cls(_str(body, "id") or "", _str(body, "thumbnail_url", "thumbnailUrl", "thumbnail"), dict(body))


@dataclass(frozen=True)
class Place:
    id: str
    name: str

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> Place:
        return cls(_str(body, "id") or "", _str(body, "name") or "")


@dataclass(frozen=True)
class CategoryNode:
    id: str
    name: str
    children: tuple[Place, ...] = ()

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> CategoryNode:
        kids = tuple(Place.from_api(c) for c in _list(body.get("children")) if isinstance(c, Mapping))
        return cls(_str(body, "id") or "", _str(body, "name") or "", kids)


@dataclass(frozen=True)
class ServiceOption:
    id: str
    name: str
    price: Optional[Decimal]
    price_with_discount: Optional[Decimal]

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> ServiceOption:
        return cls(_str(body, "id") or "", _str(body, "name") or "", _money(body.get("price")),
                   _money(body.get("priceWithDiscount")))


@dataclass(frozen=True)
class PaymentMethod:
    id: str
    name: str
    balance: Optional[Decimal]

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> PaymentMethod:
        return cls(_str(body, "id") or "", _str(body, "name") or "", _money(body.get("balance")))


@dataclass(frozen=True)
class PaidService:
    id: str
    title: str
    options: tuple[ServiceOption, ...] = ()
    payment_methods: tuple[PaymentMethod, ...] = ()

    @classmethod
    def from_api(cls, service: Mapping[str, Any], details: Mapping[str, Any]) -> PaidService:
        options = tuple(ServiceOption.from_api(o) for o in _list(details.get("paidServiceOptions"))
                        if isinstance(o, Mapping))
        methods = tuple(PaymentMethod.from_api(m) for m in _list(details.get("paymentMethods"))
                        if isinstance(m, Mapping))
        return cls(_str(service, "id") or "", _str(service, "title") or "", options, methods)


@dataclass(frozen=True)
class Payment:
    status: Optional[str]
    redirect_url: Optional[str]
    payment_id: Optional[str]
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> Payment:
        return cls(_str(body, "status"), _str(body, "redirectUrl"), _str(body, "paymentId"), dict(body))


@dataclass(frozen=True)
class CodeSent:
    phone: str
    code_requests_left: Optional[int]
    retried: bool = False
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def more_than_one_sms(self) -> bool:
        return self.retried
