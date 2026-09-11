---
name: management
description: >-
  Look up Vipps MobilePay merchants and sales units, and onboard merchants by prefilling a product order form for
  them. Use when work involves /management/v1/sales-units, /management/v1/merchants, /management/v1/product-orders,
  pricePackageId, businessIdentifier, MSN lookup, merchant agreement, product order status, or a partner onboarding
  merchants programmatically.
---

# Management API

Self-service administration: find out which sales units a merchant has, read a sales unit's configuration, and start a
merchant's signup by handing them a prefilled product order.

**Who this is for: partners who onboard merchants, and merchants large enough to have many sales units.** Everything
here is also available in the business portal, and for a merchant with one or two sales units the portal is the
answer. Do not reach for this API just because a task sounds administrative; check first that the user is a partner or
is managing sales units at a scale that makes clicking impractical.

Read `../best-practices/SKILL.md` first for servers, keys, and access tokens.

Three constraints that decide whether this API is usable for the job at all:

- **Production only.** `https://api.vipps.no`. There is nothing to test against, so the first real call is against
  real merchant data. Write it carefully.
- **Read and create, not update.** There is no endpoint to change an existing sales unit. Anything already live is
  changed in the business portal or by us.
- **Only sales units that have their own API keys.** Vippsnummer and MobilePay-nummer sales units have none, so they
  are invisible here.

Partners authenticate with partner keys, merchants with their normal sales unit keys. Both use the standard access
token flow; see `../access-token/SKILL.md`.

## Looking things up

| Want | Call |
| ---- | ---- |
| Every sales unit you can reach | `GET /management/v1/sales-units` |
| One sales unit's details and configuration | `GET /management/v1/sales-units/{msn}` |
| A merchant's sales units, from their org number | `GET /management/v1/merchants/{scheme}/{id}/sales-units` |
| A merchant's name, status, and addresses | `GET /management/v1/merchants/{scheme}/{id}` |

`{scheme}` and `{id}` are the business identifier, for example `business:NO:ORG` and `9876543221`.

The list endpoints return only `msn` and `name`. Fetch each MSN individually for the detail, including the
`businessIdentifier` that tells you which merchant owns it, which is the way to go from an unfamiliar MSN back to a
company.

`GET /management/v1/sales-units/{msn}` is the useful one, because `configuration` is the answer to "will this call
work before I make it":

```json
{
  "msn": "123456",
  "name": "ACME Fantastic Fitness",
  "businessIdentifier": { "scheme": "business:NO:ORG", "id": "9876543221" },
  "settlementBankAccount": { "scheme": "BBAN:NO", "id": "86011117947" },
  "configuration": {
    "paymentAllowed": true,
    "captureType": "ReserveCapture",
    "skipLandingPageAllowed": false,
    "recurringAllowed": false,
    "partialCaptureAllowed": true,
    "lateCaptureAllowed": true,
    "landingPagePhoneNumberLocked": false,
    "longLivingPaymentAllowed": false,
    "creditCardPaymentAllowed": true
  }
}
```

Check `recurringAllowed` before writing Recurring code against a sales unit, and `captureType` before assuming direct
capture. This is cheaper than discovering the answer from a rejected payment.

**HTTP 404 means "not active", not only "not found".** The endpoint returns 404 when the merchant is inactive, when
the sales unit is inactive, and, for a partner, when the merchant has no active sales unit connected to that partner.
Do not report it to a user as a typo in the MSN.

## Prefilling a product order

A partner fills in what they know about the merchant, and the merchant gets a link to a signup form that is already
complete and only needs checking and submitting. Prefilled orders are processed faster because they arrive correct.

`POST /management/v1/product-orders`:

```json
{
  "businessIdentifier": { "scheme": "business:NO:ORG", "id": "9876543221" },
  "salesUnitName": "ACME Fantastic Fitness",
  "salesUnitLogo": "VGhlIGltYWdlIGdvZXMgaGVyZQ== (base64, truncated)",
  "settlementBankAccount": { "scheme": "BBAN:NO", "id": "86011117947" },
  "pricePackageId": "8a11afb7-c223-48ed-8ca6-4722b97261aa",
  "productType": "PAYMENT_INTEGRATION",
  "productUseCase": "WebsiteWithTest",
  "annualTurnover": 100000,
  "annualTurnoverPercentage": "50",
  "intendedPurpose": "Gym membership for accessing the gym's facilities. Guests will not be physically present when buying the subscription, it's done on the gym's website.",
  "website": {
    "url": "https://example.com",
    "termsUrl": "https://example.com/terms-and-conditions",
    "testWebsiteUrl": "https://example.com/test",
    "testWebsiteUsername": "test-user",
    "testWebsitePassword": "test-password"
  },
  "hasRecurring": true,
  "merchantCategoryCode": 5942
}
```

```json
{
  "prefilledOrderId": "81b83246-5c19-7b94-875b-ea6d1114f099",
  "prefillUrl": "https://portal.vippsmobilepay.com/register/vippspanett/81b83246-5c19-7b94-875b-ea6d1114f099"
}
```

- **Send every field you can.** Missing information is the usual cause of a delayed signup, and most fields being
  technically optional does not make leaving them out a good idea.
- **The `prefillUrl` expires after 14 days**, for regulatory reasons. Do not email it and forget about it; track the
  status and re-issue if it lapses.
- The merchant can edit everything in the form except the partner and, if you supplied one, the price package.
  Correcting a wrong `pricePackageId` means the partner submits a new prefill.
- `merchantCategoryCode` is the four-digit MCC and feeds our risk assessment. Only MCCs in the form's own selector get
  pre-selected; anything else is silently ignored and the merchant picks one.
- Get `pricePackageId` values from `GET /management/v1/partners/price-packages`. If the partner has only one package,
  or you supply one, the price is hidden from the merchant's form.

**A merchant with no Merchant Agreement is sent to sign one first**, with BankID, by a person with signing rights for
the company. That is not something a partner can fill in on their behalf, and it is why the link sometimes appears to
lead somewhere unexpected. After signing, they land back on the prefilled order.

An invalid request usually returns an error, but not always: some fields cannot be validated up front, and a request
that succeeded can still produce a link to an empty form. If a merchant reports a blank form, suspect the prefill
payload rather than the portal.

## Tracking product orders

`GET /management/v2/product-orders/{productOrderId}/details` and `GET /management/v2/product-orders` cover every order
naming the partner, whether it came from a prefill, from a product order template, or from the merchant filling in the
form themselves. Only prefilled ones carry the full detail.

| Status | Means |
| ------ | ----- |
| `RECEIVED` | Created, merchant has not opened it |
| `MERCHANT_VIEWED` | Merchant has opened the link |
| `ORDER_SUBMITTED` | Submitted, waiting for us to process |
| `COMPLETED` | Approved. The response now also carries `salesUnit` with the new MSN |
| `REJECTED` | Declined. **We may not tell a partner why**, for legal reasons; ask the merchant |
| `EXPIRED` | 14 days elapsed before submission |

`COMPLETED`, `REJECTED`, and `EXPIRED` are terminal. The list endpoint hides `EXPIRED` unless you pass
`includeExpired=true`.

`DELETE /management/v1/product-orders/{productOrderId}` removes a prefilled order that was wrong, but only
before the merchant submits it.

Both parties also get an email when an order finishes processing, carrying the business identifier, the merchant name,
and the new MSN and sales unit name. Poll the status endpoint rather than depending on somebody reading that mail.

## Product order and merchant agreement

Worth keeping straight, because merchants confuse them and partners get asked:

- **MA, Merchant Agreement.** Between the merchant and Vipps MobilePay, signed with BankID, covering ownership and
  politically exposed persons. One per merchant.
- **PO, Product Order.** An order for one specific product, not signed with BankID. A merchant can have several.

Both must be in place before the merchant can use anything. A PO can be submitted before the MA exists; it just will
not complete until the MA does.

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/management-api/management-api-guide.md>,
<https://developer.vippsmobilepay.com/docs/APIs/management-api/management-api-quick-start.md>,
<https://developer.vippsmobilepay.com/docs/APIs/management-api/management-api-faq.md>, spec at `/api/management`.
Partner keys and onboarding: <https://developer.vippsmobilepay.com/docs/partner/README.md>.
