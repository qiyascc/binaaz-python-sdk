# Models and enums

Everything the SDK returns is an immutable dataclass with plain Python types. Money is a `decimal.Decimal`, dates are timezone aware `datetime` objects, and every model that comes from bina.az keeps the original answer in `.raw` for fields the SDK does not map. `raw` is left out of `repr()` and of equality checks.

## Returned models

| Model | Returned by | Guide |
| --- | --- | --- |
| `Profile` | `auth.login`, `auth.verify_code`, `auth.profile`, `profile()` | [Signing in](../getting-started/sign-in.md) |
| `CodeSent` | `auth.send_code` | [Signing in](../getting-started/sign-in.md#sms-code) |
| `ItemResult` | `items.create`, `update`, `delete`, `prolong`, `pay` | [Posting listings](../guides/listings.md#posting) |
| `Item`, `Price` | `items.get`, `items.all`, inside `ItemPage` | [Managing listings](../guides/managing.md) |
| `ItemPage` | `items.list` | [Managing listings](../guides/managing.md#pages-and-cursors) |
| `Photo` | `photos.upload`, `upload_many`, `rotate` | [Photos](../guides/photos.md) |
| `Place` | `catalog.cities`, `regions`, `townships`, `landmarks` | [Catalog](../guides/catalog.md) |
| `CategoryNode` | `catalog.categories` | [Catalog](../guides/catalog.md#categories) |
| `PaidService`, `ServiceOption`, `PaymentMethod` | `items.paid_services` | [Payments](../guides/payments.md) |
| `Payment` | `items.buy_service` | [Payments](../guides/payments.md#buy-a-service) |

```{eval-rst}
.. autoclass:: binaaz_sdk.Profile
   :members: is_company
   :undoc-members: false

.. autoclass:: binaaz_sdk.CodeSent
   :members: more_than_one_sms
   :undoc-members: false

.. autoclass:: binaaz_sdk.ItemResult
   :members:
   :undoc-members: false

.. autoclass:: binaaz_sdk.Item
   :members:
   :undoc-members: false

.. autoclass:: binaaz_sdk.Price
   :members:
   :undoc-members: false

.. autoclass:: binaaz_sdk.ItemPage
   :members: has_more
   :undoc-members: false

.. autoclass:: binaaz_sdk.Photo
   :members:
   :undoc-members: false

.. autoclass:: binaaz_sdk.Place
   :members:
   :undoc-members: false

.. autoclass:: binaaz_sdk.CategoryNode
   :members:
   :undoc-members: false

.. autoclass:: binaaz_sdk.PaidService
   :members:
   :undoc-members: false

.. autoclass:: binaaz_sdk.ServiceOption
   :members:
   :undoc-members: false

.. autoclass:: binaaz_sdk.PaymentMethod
   :members:
   :undoc-members: false

.. autoclass:: binaaz_sdk.Payment
   :members:
   :undoc-members: false
```

## Enums

All enums print as their value: `str(ItemState.PUBLISHED)` is `"published"`, `str(ContactType.AGENT)` is `"AGENT"`.

| Enum | Values |
| --- | --- |
| `Category` | `APARTMENT` 1, `APARTMENT_NEW_BUILDING` 2, `APARTMENT_OLD_BUILDING` 3, `HOUSE` 5, `OFFICE` 7, `GARAGE` 8, `LAND` 9, `COMMERCIAL` 10 |
| `ContactType` | `OWNER`, `AGENT` |
| `BuildingType` | `BUSINESS_CENTER`, `APARTMENT`, `VILLA` |
| `ItemTab` | `PENDING`, `PUBLISHED`, `REJECTED`, `EXPIRED`, `AWAITING_PAYMENT` |
| `ItemState` | `PENDING`, `PUBLISHED`, `REJECTED`, `EXPIRED`, `AWAITING_PAYMENT`, `UNKNOWN` |

```{eval-rst}
.. autoclass:: binaaz_sdk.Category
   :members:
   :undoc-members:
   :member-order: bysource

.. autoclass:: binaaz_sdk.ContactType
   :members:
   :undoc-members:
   :member-order: bysource

.. autoclass:: binaaz_sdk.BuildingType
   :members:
   :undoc-members:
   :member-order: bysource

.. autoclass:: binaaz_sdk.ItemTab
   :members:
   :undoc-members:
   :member-order: bysource

.. autoclass:: binaaz_sdk.ItemState
   :members:
   :undoc-members:
   :member-order: bysource
```

## Constants

| Name | Value | Meaning |
| --- | --- | --- |
| `PHOTOS_MIN` | 4 | Fewest photos on a listing |
| `PHOTOS_MAX` | 30 | Most photos on a listing |
| `PHOTO_ANGLES` | `(90, 180, 270, -90)` | Angles `photos.rotate` accepts |
