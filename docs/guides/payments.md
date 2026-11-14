# Payments and paid services

Some listings are accepted by bina.az but only shown after a payment, and any listing can be promoted with paid services such as raising it to the top. The SDK can read the services on offer, buy one and pay for a listing. Every call that costs money needs an explicit `confirm=True`.

## The confirm rule

```python
bina.items.pay("4123456")
```

raises `InvalidRequestError` with the message "Paying for a listing costs money. Pass confirm=True to go ahead", and nothing is sent. The same applies to `buy_service`. The flag exists so a call copied from an example, or a default argument in your own wrapper, can never spend money by accident.

## Pay for a listing

A listing in the `awaiting_payment` state was accepted but is only published after payment:

```python
for item in bina.items.all("awaiting_payment"):
    print(item.id, item.title)

result = bina.items.pay("4123456", confirm=True)
print(result.state)
```

`pay` returns an {py:class}`~binaaz_sdk.ItemResult`, the same as `create`. The payment is taken from the account on the terms bina.az has for it.

## Paid services

### See what is on offer

```python
for service in bina.items.paid_services("4123456"):
    print(service.id, service.title)
    for option in service.options:
        print("   option", option.id, option.name, option.price, option.price_with_discount)
    for method in service.payment_methods:
        print("   pay with", method.id, method.name, method.balance)
```

`paid_services` returns a tuple of {py:class}`~binaaz_sdk.PaidService`. It reads the list of services for the listing and then the details of each service, so it makes one request per service plus one.

| `PaidService` field | Meaning |
| --- | --- |
| `id` | Service id, for `buy_service` |
| `title` | Service name as bina.az shows it |
| `options` | Tuple of `ServiceOption`: `id`, `name`, `price`, `price_with_discount` (both `Decimal` or `None`) |
| `payment_methods` | Tuple of `PaymentMethod`: `id`, `name`, `balance` (a `Decimal` for wallet style methods) |

### Buy a service

```python
services = bina.items.paid_services("4123456")
service = services[0]
payment = bina.items.buy_service(
    "4123456",
    service.id,
    service.payment_methods[0].id,
    option_id=service.options[0].id,
    confirm=True,
)
print(payment.status, payment.redirect_url)
```

| Argument | Meaning |
| --- | --- |
| `item_id` | The listing |
| `service_id` | `PaidService.id` |
| `payment_method_id` | `PaymentMethod.id` |
| `option_id` | `ServiceOption.id`, for services that come in options such as a number of days |
| `amount` | An amount, for services that take one |
| `confirm` | Must be `True` |

The result is a {py:class}`~binaaz_sdk.Payment`:

| Field | Meaning |
| --- | --- |
| `status` | The payment status bina.az reports |
| `redirect_url` | For card payments, the page where the payment is finished |
| `payment_id` | The payment id |
| `raw` | The whole answer |

### Card payments

When the payment method needs a payment page, as card payments do, bina.az answers with `redirect_url`: the page where the card details are entered and the payment is finished. Open it in a browser, or send it to whoever pays. The SDK never sees or handles card details.

```python
if payment.redirect_url:
    print("Finish the payment here:", payment.redirect_url)
```

## Never retried

Payments are writes. A timeout or a dropped connection during `pay` or `buy_service` raises `OutcomeUnknownError` and the call is not repeated. Check the listing and the account balance on bina.az before paying again, or you may pay twice.
