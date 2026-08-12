---
name: epayment
description: >-
  Implement one-time Vipps or MobilePay payments with the ePayment API: create a payment, get its status, capture,
  refund, cancel, Express checkout, QR and in-store flows. Use when adding a pay button, a checkout, a point-of-sale
  payment, or when working with /epayment/v1/payments, the Widget SDK, userFlow, WEB_REDIRECT, AUTHORIZED, capture, or
  refund.
---

# ePayment API

One-time payments for Vipps and MobilePay, online and in person. Base path `/epayment/v1`.

Read `../best-practices/SKILL.md` first for servers, keys, access tokens, headers, and minor units. This skill assumes them.

## The shape of the integration

Four things to build. Nothing works without all four.

1. **Create** the payment when the customer chooses Vipps or MobilePay, and send them to the returned `redirectUrl`.
2. **Learn the outcome** through a webhook and by polling the payment. Update the order from that, never from the
   browser redirect.
3. **Capture** when the goods or service are actually delivered. Uncaptured money is never paid out.
4. **Cancel or refund** for the rest: cancel what will not be captured, refund what already was.

```text
create -> user approves in app -> AUTHORIZED (funds reserved) -> capture -> [refund]
                               -> ABORTED | EXPIRED | TERMINATED
```

## 1. Create a payment

`POST /epayment/v1/payments`

```bash
curl -X POST https://apitest.vipps.no/epayment/v1/payments \
-H "Content-Type: application/json" \
-H "Authorization: Bearer YOUR-ACCESS-TOKEN" \
-H "Ocp-Apim-Subscription-Key: YOUR-SUBSCRIPTION-KEY" \
-H "Merchant-Serial-Number: YOUR-MSN" \
-H "Idempotency-Key: YOUR-IDEMPOTENCY-KEY" \
-H "Vipps-System-Name: acme" \
-H "Vipps-System-Version: 3.1.2" \
-H "Vipps-System-Plugin-Name: acme-webshop" \
-H "Vipps-System-Plugin-Version: 4.5.6" \
-d '{
  "amount": { "currency": "NOK", "value": 49900 },
  "paymentMethod": { "type": "WALLET" },
  "customer": { "phoneNumber": "4712345678" },
  "reference": "acme-shop-123-order123abc",
  "returnUrl": "https://example.com/redirect?reference=acme-shop-123-order123abc",
  "userFlow": "WEB_REDIRECT",
  "paymentDescription": "One pair of socks"
}'
```

Required fields:

| Field | Notes |
| ----- | ----- |
| `amount` | `{ currency, value }`. `value` in minor units, integer. Minimum NOK 100 øre, DKK 1 øre, EUR 1 cent |
| `paymentMethod.type` | `WALLET` for the app (normal), `CARD` for a freestanding card form |
| `reference` | Your ID for the payment. Unique per MSN. Must match `^[a-zA-Z0-9-]{8,64}$` |
| `userFlow` | `WEB_REDIRECT` unless you have a specific reason. See below |
| `returnUrl` | Required for `WEB_REDIRECT`. `https://` or a custom scheme |
| `customer` | Required for `PUSH_MESSAGE`: phone number in MSISDN format |

The response contains `redirectUrl` and your `reference`. Send the customer to `redirectUrl` unchanged. On a phone with
the app installed, the operating system app-switches straight into it. Elsewhere the landing page opens and the
customer types their phone number.

The default payment expires after 10 minutes if the customer does nothing.

**Do not** put `redirectUrl` in an iframe or web view, do not rewrite it, and do not sniff for an installed app. That
logic is handled for you and breaking it lowers conversion.

### Send the customer there with the Widget SDK

**On a website, use the Widget SDK. It is the front end of this integration, not an optional extra.** It renders the
brand-correct button, app-switches on mobile, and opens `redirectUrl` in a Vipps MobilePay hosted dialog on desktop so
the customer keeps their place in the checkout. That dialog is the one sanctioned exception to the rule above; iframes
you build yourself are still forbidden.

Hand the SDK's resolver the `redirectUrl` from the create call. Everything else — the script tag, the host, events,
button options — is in `../widget-sdk/SKILL.md`. Hand-roll a button and a redirect only when the page genuinely cannot
run JavaScript.

The SDK is front end only. The outcome still comes from the webhook and the poll below, never from its `success` event.

### Choosing `userFlow`

| Value | When | Requires |
| ----- | ---- | -------- |
| `WEB_REDIRECT` | Websites and apps. The right answer almost always | `returnUrl` |
| `QR` | Customer-facing screen the customer scans. Returns a one-time QR | `qrFormat`, `customerInteraction` |
| `PUSH_MESSAGE` | Till, vending machine, call center: a device the customer does not hold | `customer`, and the sales unit must be approved for it |
| `NATIVE_REDIRECT` | Discouraged. Only when the merchant has no web presence at all | `customer` |

`CARD` supports `WEB_REDIRECT` only, and card payments cannot be tested in the test environment.

For a physical point of sale also send `"customerInteraction": "CUSTOMER_PRESENT"`. That is required, not cosmetic.

### Optional features

Add these to the create request when asked for. Details in `references/features.md`.

| Field | Feature |
| ----- | ------- |
| `shipping` plus `profile.scope` | **Express**: address and delivery options chosen inside the app |
| `profile.scope` | **Profile sharing**: get name, address, email, phone with consent |
| `receipt` | Order details shown in the app's payment history |
| `expiresAt` | **Long-living payment**: up to 60 days. Requires `receipt` |
| `minimumUserAge` | Age-restricted goods |
| `metadata` | Your own key-value data on the payment |
| `blockedSources` | Block payment sources. Danish and Finnish sales units only |

## 2. Learn the outcome

Register the webhooks (see `../webhooks/SKILL.md`) **and** poll:

```bash
curl -X GET https://apitest.vipps.no/epayment/v1/payments/YOUR-REFERENCE \
-H "Authorization: Bearer YOUR-ACCESS-TOKEN" \
-H "Ocp-Apim-Subscription-Key: YOUR-SUBSCRIPTION-KEY" \
-H "Merchant-Serial-Number: YOUR-MSN"
```

Poll from 5 seconds after creating, then every 2 seconds. The limit is 120 calls per minute per reference; create,
capture, cancel, and refund are limited to 5 per minute per reference.

### Payment states

| State | Meaning |
| ----- | ------- |
| `CREATED` | Sent, customer has not acted |
| `AUTHORIZED` | Customer approved. Funds reserved. **Final state** |
| `ABORTED` | Customer cancelled before approving. Final |
| `EXPIRED` | Customer did nothing in time. Final |
| `TERMINATED` | You cancelled it before approval. Final |

The trap: **the state stays `AUTHORIZED` after capture, refund, and cancel.** There is no `CAPTURED` state, because a
payment can be captured and refunded in parts. To know what has actually moved, read the `aggregate` object on
`GET /epayment/v1/payments/{reference}`: `authorizedAmount`, `capturedAmount`, `refundedAmount`, `cancelledAmount`.

Full history is at `GET /epayment/v1/payments/{reference}/events`. Use it for support cases, and expect a different
`pspReference` per event.

## 3. Capture the payment

`POST /epayment/v1/payments/{reference}/capture` with `Idempotency-Key`.

```json
{ "modificationAmount": { "currency": "NOK", "value": 49900 } }
```

Partial captures are allowed: call it repeatedly, up to the authorized amount.

The rules are legal, not just technical:

- Capture **as soon as** the product or service is delivered. Some banks release the reservation after a few days.
- Do **not** capture before delivery.
- Uncaptured reservations are cancelled automatically after the capture deadline, and money never reaches the merchant.
- If part of the amount will not be captured, cancel the remainder so the customer gets the funds back.

## 4. Cancel and refund

| Situation | Call |
| --------- | ---- |
| Nothing captured yet, order will not ship | `POST .../cancel` |
| Partly captured, rest will not ship | `POST .../cancel` releases the uncaptured remainder |
| Already captured | `POST .../refund` with `modificationAmount` |

Cancel works within 180 days of reservation, refund within 365 days. Refunds may be partial and repeated up to the
captured amount. A captured payment cannot be cancelled: error 6040.

## Errors

RFC 7807 bodies with a `traceId`, plus a numeric code in `extraDetails` for domain errors. The ones that show up most:

| Code | Meaning | Fix |
| ---- | ------- | --- |
| 4040 | Invalid amount | Send integers in minor units. No decimals |
| 4070 | Invalid phone number | MSISDN, no `+`, no spaces |
| 4020 / 4150 | Idempotency conflict, or reference already exists | New reference for a new payment, same key only for a true retry |
| 6010 | Amount too small | Below the market minimum |
| 6080 | Cannot capture before reservation | The customer has not approved yet. Check the state |
| 6090 | Capture amount too high | Total captures exceed the authorized amount |
| 6100 | Capture period expired | Reservation is gone. Nothing to do |
| 5040 | Invalid currency for merchant | Currency must match the sales unit's market |
| 5060 | Bank account not verified | Merchant setup, not code |
| 7010 | Customer not found | The phone number has no eligible user, or fails `minimumUserAge` |
| HTTP 423 | Resource locked | Concurrent operation on the same payment. Retry shortly |
| HTTP 429 | Too many requests | Slow the polling. Check you send `reference` in lower case |

The full table is in `references/errors.md`.

## Testing

`POST /epayment/v1/payments/{reference}/approve` approves a payment without touching the app. Test environment only.
The test user must have approved at least one payment manually in the app first, and Express is not supported.

Specific amounts trigger specific failures in test: `151` insufficient funds, `186` expired card, `187` invalid card.
See `../test-and-go-live/SKILL.md`.

## Before calling it done

- Both webhooks and polling are wired up.
- All five states are handled, plus captured, refunded, and cancelled events.
- Capture happens at delivery, and unused reservations get cancelled.
- Errors are logged with endpoint, headers, body, code, and message, and surfaced to a human.
- `Vipps-System-*` headers are sent.
- On the web, the button and the redirect go through the Widget SDK, with `vipps.host().start()` on the top-level page.
- Order details are added to the payment so the customer recognizes it in the app.
- Branding follows the design guidelines at
  <https://developer.vippsmobilepay.com/docs/knowledge-base/design-guidelines/>. The Widget SDK button follows them
  without any work from you, and keeps following them when they change.

The full requirement list is the ePayment checklist:
<https://developer.vippsmobilepay.com/docs/APIs/epayment-api/checklist.md>.

## Deeper reference

- `references/operations.md` — every endpoint with request and response shapes
- `references/features.md` — Express, profile sharing, QR, long-living payments, metadata, age limit
- `references/errors.md` — full error code table and what to do about each

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/epayment-api/quick-start.md>,
<https://developer.vippsmobilepay.com/docs/APIs/epayment-api/api-guide/concepts.md>, spec at `/api/epayment`.
