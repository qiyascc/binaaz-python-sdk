from __future__ import annotations

import pytest

from binaaz_sdk import (
    InvalidRequestError,
    ItemError,
    ItemState,
    Listing,
    NotFoundError,
    NotSupportedError,
)

from .conftest import COOKIE, LISTING, company, data, item

CREATED = data(createItem={"status": "SUCCESS", "item": {"id": "4123456", "path": "/items/4123456",
                                                          "state": "PENDING"}, "errors": []})


def test_create_sends_the_listing(gw, bina):
    gw.reply(CREATED)
    result = bina.items.create(LISTING)
    assert result.id == "4123456" and result.state is ItemState.PENDING
    assert result.url == "https://bina.az/items/4123456" and result.status == "SUCCESS"
    body = gw.body()
    assert body["operationName"] == "CreateItem"
    sent = body["variables"]["input"]
    assert sent["categoryId"] == "3" and sent["isLeased"] is False and sent["area"] == {"value": 85.0}
    assert sent["location"]["cityId"] == "1" and sent["photoIds"] == ["p1", "p2", "p3", "p4"]
    assert gw.header("cookie") == COOKIE and gw.header("origin") == "https://bina.az"
    assert gw.header("user-agent").startswith("binaaz-python-sdk/")


@pytest.mark.parametrize("count", [0, 3, 31])
def test_photo_count_is_checked_before_sending(gw, bina, count):
    with pytest.raises(InvalidRequestError):
        bina.items.create({**LISTING, "photo_ids": [f"p{i}" for i in range(count)]})
    assert not gw.requests


@pytest.mark.parametrize("change", [{"price": 0}, {"paid_daily": True}, {"building_type": "VILLA"},
                                    {"floor": {"value": 10, "total": 9}}, {"unknown": 1}])
def test_listing_rules(change):
    with pytest.raises(ValueError):
        Listing.model_validate({**LISTING, **change})


def test_restricted_account(gw, bina):
    gw.reply(data(createItem={"status": "RESTRICTED", "item": None, "errors": []}))
    with pytest.raises(ItemError) as info:
        bina.items.create(LISTING)
    assert info.value.status == "RESTRICTED" and "phone" in str(info.value)


def test_field_errors(gw, bina):
    gw.reply(data(createItem={"status": "INVALID", "item": None,
                              "errors": [{"code": "x", "message": "is too low", "path": ["price"]}]}))
    with pytest.raises(ItemError) as info:
        bina.items.create(LISTING)
    assert info.value.errors[0]["path"] == ["price"] and "price: is too low" in str(info.value)


def test_update_of_a_locked_listing(gw, bina):
    gw.reply(data(updateItem={"status": "LOCKED", "lockedUntil": "2026-11-12T10:00:00+04:00", "item": None,
                              "errors": []}))
    with pytest.raises(ItemError) as info:
        bina.items.update("4123456", LISTING)
    assert info.value.locked_until == "2026-11-12T10:00:00+04:00" and "until" in str(info.value)
    sent = gw.body()["variables"]["input"]
    assert sent["itemId"] == "4123456" and "categoryId" not in sent and sent["contactName"] == "Agency"


def test_update_of_a_missing_listing(gw, bina):
    gw.reply(data(updateItem={"status": "NOT_FOUND", "item": None, "errors": []}))
    with pytest.raises(NotFoundError):
        bina.items.update("4123456", LISTING)


def test_delete_and_prolong(gw, bina):
    gw.reply(data(deleteItem={"item": {"id": "4123456", "state": "DELETED"}, "errors": []}))
    gw.reply(data(prolongItem={"item": {"id": "4123456", "path": "/items/4123456", "state": "PENDING"},
                               "errors": []}))
    assert bina.items.delete("4123456").site_state == "DELETED"
    assert bina.items.prolong("4123456").state is ItemState.PENDING
    assert gw.operations == ["DeleteItem", "ProlongItem"]
    assert gw.body(0)["variables"] == {"input": {"itemId": "4123456"}}


def test_ids_are_checked(gw, bina):
    with pytest.raises(InvalidRequestError):
        bina.items.delete("../profile")
    assert not gw.requests


def test_get(gw, bina):
    gw.reply(data(itemEdit={"item": item()}))
    found = bina.items.get("4123456")
    assert found.state is ItemState.PUBLISHED and found.thumbnail == "https://img.test/t.jpg"
    assert str(found.price.total) == "120000" and found.expires_at is not None
    gw.reply(data(itemEdit=None))
    with pytest.raises(NotFoundError):
        bina.items.get("1")


def test_list_and_all(gw, bina):
    page = {"totalCount": 3, "pageInfo": {"hasNextPage": True, "endCursor": "c1"}, "nodes": [item("1"), item("2")]}
    last = {"totalCount": 3, "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [item("3", "VALIDATED_AND_AWAITING_PAYMENT")]}
    gw.reply(data(profile=company(items=page)))
    first = bina.items.list("awaiting_payment", first=2)
    assert first.has_more and first.next_cursor == "c1" and first.total == 3
    assert gw.body()["variables"] == {"state": "VALIDATED_AND_AWAITING_PAYMENT", "first": 2, "after": None}
    gw.reply(data(profile=company(items=page))).reply(data(profile=company(items=last)))
    everything = bina.items.all()
    assert [i.id for i in everything] == ["1", "2", "3"]
    assert everything[2].state is ItemState.AWAITING_PAYMENT
    assert gw.body()["variables"]["after"] == "c1"


def test_list_needs_a_company_profile(gw, bina):
    gw.reply(data(profile={"__typename": "Agency", "id": "1"}))
    with pytest.raises(NotSupportedError):
        bina.items.list()


def test_unknown_tab(bina):
    with pytest.raises(InvalidRequestError):
        bina.items.list("sold")


def test_paid_services(gw, bina):
    gw.reply(data(paidServices=[{"id": "bump", "title": "Bump"}]))
    gw.reply(data(paidServiceOptions=[{"id": "o1", "name": "1 day", "price": 1.5, "priceWithDiscount": 1.2}],
                  paymentMethods=[{"id": "wallet", "name": "Wallet", "balance": 10}]))
    services = bina.items.paid_services("4123456")
    assert services[0].title == "Bump" and str(services[0].options[0].price) == "1.5"
    assert services[0].payment_methods[0].id == "wallet"
    assert gw.body()["variables"] == {"sid": "bump", "ids": ["4123456"]}


def test_money_needs_confirm(gw, bina):
    with pytest.raises(InvalidRequestError):
        bina.items.buy_service("4123456", "bump", "wallet")
    with pytest.raises(InvalidRequestError):
        bina.items.pay("4123456")
    assert not gw.requests
    gw.reply(data(createPayment={"status": "PENDING", "redirectUrl": "https://pay.test/1", "paymentId": "9",
                                 "errors": []}))
    payment = bina.items.buy_service("4123456", "bump", "card", option_id="o1", confirm=True)
    assert payment.redirect_url == "https://pay.test/1"
    assert gw.body()["variables"]["input"] == {"paidServiceId": "bump", "paymentMethodId": "card",
                                               "targetId": ["4123456"], "platform": "DESKTOP",
                                               "paidServiceOptionId": "o1"}
    gw.reply(data(payForItem={"item": {"id": "4123456", "state": "PENDING"}, "errors": []}))
    assert bina.items.pay("4123456", confirm=True).id == "4123456"
