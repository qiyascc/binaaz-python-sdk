from __future__ import annotations

from enum import Enum, IntEnum


class Category(IntEnum):
    APARTMENT = 1
    APARTMENT_NEW_BUILDING = 2
    APARTMENT_OLD_BUILDING = 3
    HOUSE = 5
    OFFICE = 7
    GARAGE = 8
    LAND = 9
    COMMERCIAL = 10


class ContactType(str, Enum):
    OWNER = "OWNER"
    AGENT = "AGENT"

    def __str__(self) -> str:
        return self.value


class BuildingType(str, Enum):
    BUSINESS_CENTER = "BUSINESS_CENTER"
    APARTMENT = "APARTMENT"
    VILLA = "VILLA"

    def __str__(self) -> str:
        return self.value


class ItemTab(str, Enum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    AWAITING_PAYMENT = "VALIDATED_AND_AWAITING_PAYMENT"

    def __str__(self) -> str:
        return self.value


class ItemState(str, Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AWAITING_PAYMENT = "awaiting_payment"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_site(cls, value: object) -> ItemState:
        return SITE_STATES.get(str(value or "").upper(), cls.UNKNOWN)


SITE_STATES = {
    "PENDING": ItemState.PENDING,
    "PUBLISHED": ItemState.PUBLISHED,
    "REJECTED": ItemState.REJECTED,
    "EXPIRED": ItemState.EXPIRED,
    "VALIDATED_AND_AWAITING_PAYMENT": ItemState.AWAITING_PAYMENT,
    "AWAITING_PAYMENT": ItemState.AWAITING_PAYMENT,
    "VALIDATED": ItemState.AWAITING_PAYMENT,
}

PHOTO_ANGLES = (90, 180, 270, -90)
PHOTOS_MIN = 4
PHOTOS_MAX = 30
