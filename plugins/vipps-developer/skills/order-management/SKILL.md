---
name: order-management
description: >-
  Enrich a Vipps MobilePay payment with receipt lines, a link category, and an image, so the customer sees them in the
  app's order history. Use when work involves /order-management/v1/images, /order-management/v2/{paymentType}/receipts,
  categories, orderLines, bottomLine, content monitoring, or showing a receipt, ticket, or tracking link in the app.
---

# Order Management API

Adds a receipt and a link to a payment the customer already made, so the app's *Activities* view shows order lines,
VAT, and a button back to your site rather than just an amount.

**On ePayment, assume you do not need this API to _write_ order details.** ePayment carries `receipt` on
`createPayment` through the pre-built Order Management integration, so the order lines and totals go out with the
payment itself: one call instead of three, and it works in the test environment. See
<https://developer.vippsmobilepay.com/docs/APIs/epayment-api/api-guide/features/pre-built-order-management-api-integration.md>
and `../epayment/SKILL.md`.

**You still need it to _read_ them back.** `GET /epayment/v1/payments/{reference}` has no `receipt` field, so order
lines sent on `createPayment` cannot be fetched from the ePayment API at all. Use
`GET /order-management/v2/ecom/{reference}` for that; it returns the order lines as stored, including any line marked
`isShipping`. This catches people out because writing worked without this API, so they assume reading will too.

Reach for the rest of the standalone API when the payment came from Recurring or the legacy eCom API, when the details
only exist after the payment, or when you want the link button and image that `createPayment` cannot set.

Read `../best-practices/SKILL.md` first for servers, keys, and access tokens.

Not available for PSP pass-through payments.

## Two independent concepts

| Concept | Endpoint | Mutable? |
| ------- | -------- | -------- |
| **Category** — one link button in the app, optionally with an image | `PUT /order-management/v2/{paymentType}/categories/{orderId}` | Yes, a new PUT overwrites |
| **Order details** — the receipt: order lines, VAT, totals | `POST /order-management/v2/{paymentType}/receipts/{orderId}` | **No, once only** |
| Image, uploaded first and referenced by a category | `POST /order-management/v1/images` | No, cannot be overwritten |
| Read both back, whichever way they were written | `GET /order-management/v2/{paymentType}/{orderId}` | |

Use either concept alone or both together.

## `paymentType` and `orderId`

`{paymentType}` is `recurring` or `ecom`. **`ecom` covers ePayment as well as the legacy eCom API.** There is no
`epayment` value. The path segment is required because the same identifier can exist as both a recurring charge and a
payment, and nothing else disambiguates them.

`{orderId}` is the value you chose when you started the payment: `orderId` in eCom and Recurring, `reference` in
ePayment. Same value, two names.

**The API does not check that the order exists.** A call against a typo'd or not-yet-created identifier succeeds and
the data sits there attached to nothing. Nothing will tell you. Send it at the same time you initiate the payment, and
assert on your own side that the identifier is one you actually used.

## Categories

Exactly one per payment. Sending a second replaces the first; only the last one shows.

`RECEIPT`, `ORDER_CONFIRMATION`, `DELIVERY`, `TICKET`, `BOOKING`, `GENERAL`. Pick by what is behind the
link, since the category decides the button's wording, icon, and how the app treats the push. `GENERAL` is the
fallback when none of the others fit.

```json
{
  "category": "GENERAL",
  "orderDetailsUrl": "https://www.example.com/2486791691483852025",
  "imageId": "socks-orange-123"
}
```

`category` and `orderDetailsUrl` are required, `imageId` is optional. Tapping the button opens the URL in the device's
normal browser, so it has to work for someone who is not logged in to your site on that device.

## Images

Upload first, then reference the returned `imageId` from the category.

```json
{ "imageId": "socks-orange-123", "src": "iVBORw0KGgoAAAANSUhEUgAAAKsAAADVCAMAAAAfHv...", "type": "base64" }
```

Base64 is the only supported type. Images exist on their own, not tied to a transaction, and one image can serve many
payments. They cannot be overwritten, so version the `imageId` rather than trying to replace one.

The app fetches them pre-authenticated, which is why a ticket or a receipt is a reasonable thing to upload here.

## Order details

```json
{
  "orderLines": [
    {
      "name": "Socks",
      "id": "line_item_1",
      "totalAmount": 1000,
      "totalAmountExcludingTax": 800,
      "totalTaxAmount": 200,
      "taxRate": 2500,
      "unitInfo": { "unitPrice": 400, "quantity": "2.5", "quantityUnit": "KG" },
      "discount": 0,
      "productUrl": "https://example.com/store/socks",
      "isReturn": false,
      "isShipping": false
    },
    {
      "name": "Home delivery",
      "id": "shipping_1",
      "totalAmount": 1000,
      "totalAmountExcludingTax": 1000,
      "totalTaxAmount": 0,
      "taxRate": 0,
      "discount": 0,
      "isReturn": false,
      "isShipping": true
    }
  ],
  "bottomLine": { "currency": "NOK", "posId": "vipps_pos_122", "receiptNumber": "123456789" }
}
```

- Amounts are minor units, as everywhere else. `taxRate` is in **hundredths of a percent**: `2500` is 25%, not 25%
  of anything else and not 2500%.
- `quantity` is a **string**, so fractional quantities like `"2.5"` with a `quantityUnit` of `"KG"` work.
- Shipping is an order line with `isShipping: true`, not a separate field.
- The totals shown in the app are computed from the lines. Get the arithmetic right on your side before sending.

**This can only be sent once.** There is no update and no overwrite; a wrong receipt stays wrong. Build the payload
from finalized order data, not from a cart that a warehouse system might still adjust.

## Content monitoring

Posting order details is **mandatory**, not optional, when there is no lasting public page describing what was sold:

- No customer-facing website.
- A temporary or short-lived one.
- Payment requests for goods or services agreed elsewhere and never listed on a site.

This is a regulatory requirement. Normally we verify what a merchant sells against their website; with no website, the
order details are the only record, so they have to be there.

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/order-management-api/order-management-api-guide.md>,
<https://developer.vippsmobilepay.com/docs/APIs/order-management-api/order-management-api-quick-start.md>,
checklist at
<https://developer.vippsmobilepay.com/docs/APIs/order-management-api/order-management-api-checklist.md>, spec at
`/api/order-management`.
