---
name: psp
description: >-
  Integrate Vipps MobilePay payments and subscriptions as a Payment Service Provider (PSP) doing card passthrough.
  Use when the user mentions PSP, payment service provider, card passthrough, CARD_PASSTHROUGH, cardPassthrough,
  Psp-Id, cardCallbackUrl, psp-epayment-api, psp-recurring-api, or acting on behalf of a merchant's sales unit.
---

# PSP card passthrough

For PSPs who acquire cards themselves and settle with the merchant directly, instead of a merchant taking
payments through their own Vipps MobilePay agreement.

This skill is additive. Read `../epayment/SKILL.md` first for one-time payments or `../recurring/SKILL.md` for
subscriptions: payment/agreement/charge creation, states, capture, refund, and errors are the same for a PSP and
are not repeated here. This page covers only what changes when a PSP does card passthrough.

## What changes for a PSP

Vipps MobilePay hands the customer's card data to the PSP instead of authorizing the card itself. The customer
still picks Vipps or MobilePay and confirms in the app; the PSP then processes the card with its own acquirer and
tells Vipps MobilePay the outcome. Settlement is between the PSP and the merchant, not through Vipps MobilePay.

## Credentials and headers

- PSP keys are their own credential set, not interchangeable with regular merchant or partner keys. Get them
  from your PSP Partner Manager, who also issues your `Psp-Id`.
- Send `Psp-Id` on every request, in addition to the usual headers from `../best-practices/SKILL.md`.
- `Merchant-Serial-Number` is the *merchant's* MSN, the sales unit being acted on behalf of, never the PSP's own.
  This is the easiest header to get wrong.
- Onboarding a merchant and getting their MSN is a separate job, the PSP Merchant API, not covered by this skill.
  See <https://developer.vippsmobilepay.com/docs/APIs/psp-merchant-api/README.md>.

## ePayment PSP: create a payment

Same `POST /epayment/v1/payments` as a direct integration, with `Psp-Id` added and
`paymentMethod.type: CARD_PASSTHROUGH` plus a required `cardPassthrough` object:

```json
{
  "amount": { "currency": "NOK", "value": 6000 },
  "customer": { "phoneNumber": "4712345678" },
  "paymentMethod": { "type": "CARD_PASSTHROUGH" },
  "cardPassthrough": {
    "pspReference": "payment-ref-123456",
    "cardCallbackUrl": "https://example.com/psp-callback",
    "allowedCardTypes": ["VISA_DEBIT", "VISA_CREDIT", "DANKORT", "MC_CREDIT", "MC_DEBIT"],
    "publicEncryptionKeyId": "3f1c2e90-7a4b-4c9d-8f21-6b3e2d7a91c4"
  },
  "reference": "acme-shop-123-order123abc",
  "userFlow": "WEB_REDIRECT",
  "returnUrl": "https://example.com/redirect?orderId=1512202",
  "paymentDescription": "Purchase of socks"
}
```

`cardPassthrough` fields:

| Field | Required | Notes |
| ----- | -------- | ----- |
| `pspReference` | Yes | Your own reference for this payment |
| `cardCallbackUrl` | Yes | Where the card token or encrypted PAN is sent. See Card callback below |
| `allowedCardTypes` | Yes | `VISA_DEBIT`, `VISA_CREDIT`, `MC_CREDIT`, `MC_DEBIT`, `DANKORT` |
| `preferVisaPartOfVisaDankort` | No | Route a co-branded Visa/Dankort card through Visa. Default `false` |
| `publicEncryptionKeyId` | No | GUID of your registered public key. Without it, standalone Dankort cards fail |

PSPs are not currency-restricted to the sales unit's registered market: `NOK`, `DKK`, `EUR`, `SEK`, `USD`, `GBP`
are all allowed, cross-border, as long as the commercial agreement covers them.

After the card callback, use the normal ePayment capture, refund, and cancel calls (`../epayment/SKILL.md`,
`Psp-Id` header added) to report the outcome and keep Vipps MobilePay's view of the payment in sync.

### Express for PSPs

Same as direct Express (`../epayment/references/features.md`), delivered through card passthrough: add
`profile.scope: "name address email phoneNumber"` and `shipping` to the `CARD_PASSTHROUGH` create request above.
The merchant's sales unit must be approved for Express first. Retrieve `shippingDetails` and `userDetails` from
`GET /epayment/v1/payments/{reference}` (with `Psp-Id`) or the webhook, same shape as direct Express.

## Recurring PSP: agreement sign-up

Same `POST /recurring/v3/agreements` as a direct integration, with the merchant's `Merchant-Serial-Number` and a
`cardPassthrough` object added:

```json
{
  "pricing": { "type": "LEGACY", "currency": "NOK", "amount": 10000 },
  "interval": { "unit": "MONTH", "count": 1 },
  "initialCharge": { "amount": 10000, "description": "First payment", "transactionType": "RESERVE_CAPTURE" },
  "merchantRedirectUrl": "https://example.com/redirect",
  "merchantAgreementUrl": "https://example.com/agreement",
  "productName": "Streaming subscription",
  "cardPassthrough": {
    "pspReference": "subscription-product-123",
    "cardCallbackUrl": "https://example.com/psp-callback",
    "allowedCardTypes": ["VISA_DEBIT", "VISA_CREDIT", "ELEC_DEBIT", "MC_CREDIT", "MC_DEBIT", "DANKORT"],
    "preferVisaPartOfVisaDankort": true
  }
}
```

Same fields as the ePayment `cardPassthrough` object, plus `ELEC_DEBIT` in `allowedCardTypes`. The agreement
sign-up is a Customer-Initiated Transaction (CIT) the PSP itself processes through the card callback, to verify
the payment source and confirm the agreement — Vipps MobilePay does not do this for you. `initialCharge` sets
the CIT amount; omit it and a zero-amount verification runs instead.

A user changing their card on an existing agreement triggers the same card callback with a zero-amount CIT.
Nothing to build beyond handling that callback.

### Recurring PSP: charges

Charges are PSP-initiated, batched, and use dedicated v4 endpoints, not the v3 ones in `../recurring/SKILL.md`:

| Step | Call |
| ---- | ---- |
| Create a batch (1–50 charges) | `POST /recurring/v4/agreements/charges` |
| Get card data for a due `RECURRING` charge | `GET /recurring/v4/agreements/{agreementId}/charges/{chargeId}/payment-info` |
| Report the outcome | `POST /recurring/v4/agreements/{agreementId}/charges/{chargeId}/result` |

The batch request is a plain array of charge items (same `type`, `amount`, `description`, `chargeId`,
`agreementId`, `transactionType` fields as `../recurring/references/charges.md`, plus `due` and `retryDays` for
`RECURRING` items). The response splits into `successfulCharges`, `failedCharges`, and `retryableCharges`; retry
only the last one, with the same `agreementId` and `chargeId`.

Card data delivery differs by charge type:

- **`UNSCHEDULED`**: `cardInfo` comes back directly in `successfulCharges` at creation. No `payment-info` call.
- **`RECURRING`**: created `DUE` with no card data. Call `payment-info` on or after the `due` date to fetch it,
  before reporting a result — reporting first returns `409 Conflict`.

Process the payment yourself with the returned `networkToken` or `encryptedPan`, then always report the result:

```json
{ "status": "SUCCESS" }
```

or

```json
{ "status": "FAILED", "error": { "code": 300, "retry": true, "message": "Refused by Issuer" } }
```

`error.retry: true` keeps the charge `DUE` and retryable within its window (the `due` date plus `retryDays`);
`retry: false` settles it to `FAILED`. Reporting `SUCCESS` with `transactionType: RESERVE_CAPTURE` reserves the
charge for a later `POST .../capture`; `DIRECT_CAPTURE` captures it in full immediately. Skipping the result
report leaves the charge stuck and the customer sees it as unresolved in the app.

Everything after a successful charge — capture, refund, cancel — uses the same v3 endpoints as
`../recurring/SKILL.md`.

## Card callback

Shared by ePayment PSP (payment creation) and Recurring PSP (agreement sign-up, payment source updates). Vipps
MobilePay `POST`s to your `cardCallbackUrl` synchronously; you must respond within 20 seconds or the operation
fails and cannot be retried by the user.

Request carries `pspReference`, `authorizationAttemptId`, `merchantSerialNumber`, `amount`, and `cardInfo`
(`maskedCardNumber`, `cardType`, `cardIssuedInCountryCode`, `cardDataType: TOKEN | PAN`, and either `networkToken`
or `encryptedPan`). Verify it with HMAC-SHA256 over `x-ms-date`, `Host`, and `x-ms-content-sha256`, signed with
your PSP client secret — same scheme as `../webhooks/SKILL.md`, but signed with your client secret instead of a
webhook `secret`.

Respond with:

```json
{ "status": "RESERVE", "networkTransactionReference": "123456789" }
```

or `{ "status": "FAIL", "errorCode": 300, "errorMessage": "Refused by Issuer" }`, or `{ "status": "SOFT_DECLINE",
"softDeclineUrl": "https://example.com" }` when the issuer needs a 3-D Secure step-up.

On `SOFT_DECLINE`: host the 3-D Secure session yourself, redirect the user to
`softDeclineCompletedRedirectUrl` from the original callback once it completes, and expect a **second** card
callback with the same `authorizationAttemptId` and a fresh cryptogram. Respond to that one with `RESERVE` or
`FAIL` to finish.

Always process the card using the `cardType` from the callback, never assume it from `allowedCardTypes` — this
matters for co-branded Visa/Dankort cards and PSD2 strong customer authentication.

## Don't use these

The Vipps PSP API and MobilePay Online are legacy, maintenance-only, and closed to new integrations: build
against ePayment PSP and Recurring PSP instead. This mirrors the "eCom API and Checkout API are legacy" rule for
direct merchants in `../best-practices/SKILL.md`.

## Deeper reference

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/psp-epayment-api/epayment-psp-api-guide.md>,
<https://developer.vippsmobilepay.com/docs/APIs/psp-epayment-api/epayment-psp-checklist.md>,
<https://developer.vippsmobilepay.com/docs/APIs/psp-recurring-api/recurring-psp-api-guide.md>,
<https://developer.vippsmobilepay.com/docs/APIs/psp-recurring-api/recurring-psp-api-checklist.md>.
