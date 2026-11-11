from __future__ import annotations

PROFILE = (
    "query Profile { profile { __typename "
    "... on CompanyProfile { id name email phone contactName agency { name } } "
    "... on Business { __typename ... on Agency { id name path } ... on Residence { id name path } } } }"
)

ITEM_FIELDS = "id title state path expiresAt updatedAt price { total currency } photos { thumbnail }"

ITEM_EDIT = f"query ItemEdit($id: ID!) {{ itemEdit(itemId: $id) {{ item {{ {ITEM_FIELDS} }} }} }}"

MY_ITEMS = (
    "query MyItems($state: ProfileItemTabStatesEnum, $first: Int, $after: String) { profile { __typename "
    "... on CompanyProfile { items(state: $state, first: $first, after: $after) { totalCount "
    f"pageInfo {{ hasNextPage endCursor }} nodes {{ {ITEM_FIELDS} }} }} }} }} }}"
)

_ERRORS = "errors { code message path }"
_ITEM_RESULT = f"item {{ id path state }} {_ERRORS}"

CREATE_ITEM = (f"mutation CreateItem($input: ItemCreateInput!) "
               f"{{ createItem(input: $input) {{ status {_ITEM_RESULT} }} }}")
UPDATE_ITEM = (f"mutation UpdateItem($input: ItemUpdateInput!) "
               f"{{ updateItem(input: $input) {{ status lockedUntil {_ITEM_RESULT} }} }}")
DELETE_ITEM = (f"mutation DeleteItem($input: ItemDeleteInput!) "
               f"{{ deleteItem(input: $input) {{ item {{ id state }} {_ERRORS} }} }}")
PROLONG_ITEM = (f"mutation ProlongItem($input: ItemProlongInput!) "
                f"{{ prolongItem(input: $input) {{ {_ITEM_RESULT} }} }}")
PAY_FOR_ITEM = (f"mutation PayForItem($input: ItemPayInput!) "
                f"{{ payForItem(input: $input) {{ item {{ id state }} {_ERRORS} }} }}")
CREATE_PAYMENT = (f"mutation CreatePayment($input: PaymentCreateInput!) "
                  f"{{ createPayment(input: $input) {{ status redirectUrl paymentId {_ERRORS} }} }}")

PAID_SERVICES = "query PaidServices($ids: [ID!]!) { paidServices(targetIds: $ids, targetType: ITEM) { id title } }"

PAID_SERVICE_DETAILS = (
    "query PaidServiceDetails($sid: ID!, $ids: [ID!]!) { "
    "paidServiceOptions(paidServiceId: $sid, targetIds: $ids) "
    "{ id name price priceWithDiscount(paymentMethodId: \"wallet\") } "
    "paymentMethods(paidServiceId: $sid, targetIds: $ids, targetType: ITEM) { id name balance } }"
)

SIGN_IN = (
    "mutation SignIn($input: ProfileSignInInput!) { signIn(input: $input) { "
    "profile { __typename ... on CompanyProfile { id name } } errors { message path } } }"
)

CATEGORIES = "{ categories { id name children { id name } } }"
CITIES = "{ cities { id name } }"
REGIONS = "query($c: ID!) { regions(cityId: $c) { id name } }"
TOWNSHIPS = "query($r: ID!) { townships(regionId: $r) { id name } }"
LANDMARKS = ("query($c: ID!, $lat: Float!, $lng: Float!) "
             "{ landmarks(cityId: $c, latitude: $lat, longitude: $lng) { id name } }")
