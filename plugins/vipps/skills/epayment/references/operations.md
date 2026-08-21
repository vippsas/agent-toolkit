# ePayment API operations

Base path `/epayment/v1`. Test host `https://apitest.vipps.no`, production `https://api.vipps.no`.

All requests carry `Authorization: Bearer`, `Ocp-Apim-Subscription-Key`, `Merchant-Serial-Number`, and the four
`Vipps-System-*` headers. Requests that create or change state also carry `Idempotency-Key`.

| Operation | Method and path | Idempotency key | Rate limit per `reference` |
| --------- | --------------- | --------------- | -------------------------- |
| Create payment | `POST /payments` | Yes | 5 per minute |
| Get payment | `GET /payments/{reference}` | No | 120 per minute |
| Get event log | `GET /payments/{reference}/events` | No | 120 per minute |
| Capture | `POST /payments/{reference}/capture` | Yes | 5 per minute |
| Refund | `POST /payments/{reference}/refund` | Yes | 5 per minute |
| Cancel | `POST /payments/{reference}/cancel` | Recommended | 5 per minute |
| Force approve (test only) | `POST /test/payments/{reference}/approve` | No | |

## Create payment

Required body fields: `amount`, `paymentMethod`, `reference`, `userFlow`, and then `returnUrl` for `WEB_REDIRECT` or
`customer` for `PUSH_MESSAGE`.

```json
{
  "amount": { "currency": "NOK", "value": 49900 },
  "paymentMethod": { "type": "WALLET" },
  "customer": { "phoneNumber": "4712345678" },
  "reference": "acme-shop-123-order123abc",
  "returnUrl": "https://example.com/redirect?reference=acme-shop-123-order123abc",
  "userFlow": "WEB_REDIRECT",
  "paymentDescription": "One pair of socks"
}
```

Notes on individual fields:

- `reference` must match `^[a-zA-Z0-9-]{8,64}$` and be unique for the sales unit. It is not globally unique, so two
  sales units may use the same value. Send it in lower case, spelled exactly `reference`, or rate limiting treats every
  payment as the same one.
- `paymentMethod.type` is `WALLET` (the app, with delegated strong customer authentication and card-retry built in),
  `CARD` (freestanding card entry plus 3-D Secure, `WEB_REDIRECT` only, not available in test), or
  `CARD_PASSTHROUGH` (payment service providers only).
- `customer` can hold `phoneNumber` in MSISDN format, or a customer token from a scanned personal QR.
- `paymentDescription` is shown to the customer.
- `customerInteraction: "CUSTOMER_PRESENT"` is required when the customer is physically at the point of sale.
- `qrFormat` accompanies `userFlow: QR`, for example `{ "format": "IMAGE/SVG+XML", "size": 1024 }`.

Response:

```json
{
  "redirectUrl": "https://landing.vipps.no/...",
  "reference": "acme-shop-123-order123abc"
}
```

Open `redirectUrl` with the platform's normal URL opening, unchanged. Never in an iframe or web view.

## Get payment

```json
{
  "aggregate": {
    "authorizedAmount": { "currency": "NOK", "value": 6000 },
    "cancelledAmount": { "currency": "NOK", "value": 0 },
    "capturedAmount": { "currency": "NOK", "value": 0 },
    "refundedAmount": { "currency": "NOK", "value": 0 }
  },
  "amount": { "currency": "NOK", "value": 6000 },
  "state": "AUTHORIZED",
  "paymentMethod": { "type": "WALLET" },
  "profile": {},
  "pspReference": "37c34d8c-2649-448e-864b-060d5d93e4c4",
  "reference": "acme-shop-123-1234589",
  "captureGuaranteedUntil": "2026-09-01T07:53:44.812+00:00"
}
```

`aggregate` is the only reliable source for how much has been captured, refunded, or cancelled, because `state` stops
changing at `AUTHORIZED`. Reconcile against `aggregate`, not against your own assumption of what your last call did.

`captureGuaranteedUntil` is the date a successful capture is guaranteed for this payment. It can be earlier than the
market's [capture deadline](../../payment-lifecycle/SKILL.md#capture-attempt-deadlines) if the bank or card network releases
the reservation early; the same field is also included in the `epayments.payment.authorized.v1` webhook payload.

With Express or profile sharing and customer consent, the response also carries `userDetails`, `shippingDetails`, and
`profile.sub`. With `metadata` on the create request, it comes back here too.

## Get event log

Returns an array of events, each with its own `pspReference`, a `name` such as `CREATED`, `AUTHORIZED`, `CAPTURED`,
`REFUNDED`, `CANCELLED`, `TERMINATED`, plus amount and timestamp. Use it for support and reconciliation.

The `pspReference` in an API response matches the `CREATED` event, while a webhook carries the `pspReference` of the
event that fired. They intentionally differ.

## Capture

```json
{ "modificationAmount": { "currency": "NOK", "value": 49900 } }
```

- Partial captures are allowed, repeatedly, up to `authorizedAmount`.
- An idempotent retry must send an identical body, or you get error 4010.
- Some sales units are configured so partial capture is refused: error 6140.
- After a partial capture, cancel the rest.
- If the reservation was released early (error `6260`, `Funds unavailable`) or the capture otherwise fails
  transiently (error `6280`), do not send the goods; retry with the same idempotency key or contact the customer.
  See `../../payment-lifecycle/SKILL.md#capture-attempt-deadlines`.

## Refund

Same body as capture. Refund up to `capturedAmount`, in parts if needed, within 365 days of the reservation. Refunds
take a few days to reach the customer's account, unlike a cancel, which is immediate.

## Cancel

No body needed. Cancel releases every not-yet-captured krone or øre at once, and is irreversible.

- Before authorization the payment becomes `TERMINATED`.
- After authorization the state remains `AUTHORIZED` and `cancelledAmount` grows.
- After a partial capture, a cancel releases the whole remaining reservation, not a chosen slice.
- `cancelTransactionOnly: true` in the body cancels only if the customer has not authorized yet. Use it when a
  cancellation may race an in-progress authorization. Trying it on an authorized payment gives error 6060.
- Available within 180 days of reservation, and only inside the capture deadline.

## Force approve, test environment only

`POST /test/payments/{reference}/approve` confirms a payment without the app, for automated tests. The body takes either the
customer, or the token from the create response:

```json
{ "customer": { "phoneNumber": "4712345678" } }
```

The test user must have approved at least one payment manually in the app first. Express is not supported, and use in
production fails. An expired test card shows up as HTTP 500, which means it is time to create a new test user.
