---
name: donations
description: >-
  Pull donation payment reports, read and stop recurring donation agreements, and build donation links or QR codes for
  the Vipps MobilePay Donations product. Use when work involves /donations/v1/reports/payments,
  /donations/v1/agreements, donations.agreement.started.v1, merchant-level keys, qr.vipps.no/donations, fundraising,
  or a charity receiving single or recurring gifts.
---

# Donations API

The *Donations* product itself needs no integration: an approved organization receives donations in the app straight
away. This API is the optional reporting and agreement layer on top of it.

Read `../best-practices/SKILL.md` first, and `../access-token/SKILL.md`, because **the token flow here depends on
which keys you hold** and getting it wrong is the usual first failure.

**Production only.** `https://api.vipps.no`. Not in the test environment.

Approval for the Donations product comes first, and who can be approved varies by market. Without it there is nothing
to call.

## Keys and authentication

| Caller | Keys | Token flow |
| ------ | ---- | ---------- |
| Merchant | **Merchant-level keys** — organization level, not sales unit | **Specialized**, `/miami/v1/token`, returns `scope: donations:read` |
| Partner | Ordinary partner keys, one set for every merchant they manage | **Standard**, `/accesstoken/get` |
| Legacy merchant on a *Recurring donations* sales unit | Sales unit keys | Standard |

Merchant-level keys are unusual: they belong to the organization rather than to a sales unit, and you generate them
yourself in the business portal under *For developers*, then the *Donations* tab, which only appears once the product
is approved. **The secret is shown once.** Regenerating it invalidates the old one immediately, so deploy the new one
before you regenerate in production.

The same merchant-level keys also reach the Report API, which is where settlement data lives. See
`../report/SKILL.md`.

## Payment reports

`GET /donations/v1/reports/payments?from=...&to=...`, ISO 8601 timestamps.

```json
{
  "from": "2025-01-01T00:00:00Z",
  "to": "2025-12-31T23:59:59Z",
  "payments": [
    {
      "externalReference": "spring-promotion-2025",
      "agreementId": "79458f91-82b5-4c38-a886-56df6a6b7980",
      "payer": { "name": "Ada Lovelace", "phoneNumber": "4712345678" },
      "capturedAt": "2025-10-24T14:15:22Z",
      "pspReference": "11268125611",
      "transactionReference": "11268125611",
      "recipientHandle": "api:922061",
      "amount": "50001",
      "currency": "NOK"
    }
  ]
}
```

One entry per payment, at capture. It covers the Donations product and also the older *Recurring Donations* and
*VM number with fundraising report* solutions. `agreementId` is present only for recurring gifts.

**This is for identifying the donor in your system, not for reconciliation.** There is nothing about fees, payouts, or
settlement here. Those questions go to the Report API.

Expect a payment to appear within about 10 minutes. There is no SLA on that.

### Paging is by timestamp, not by cursor

The response is capped by payload size, so **a single request does not necessarily return the whole interval, even
when it looks complete**. Assuming it does is the standard bug in a Donations importer.

1. Request with your `from` and `to`.
2. Process the payments.
3. If any came back, repeat with `from` set to the **exact** latest `capturedAt` from the response.
4. Stop when `payments` comes back empty.

Two consequences to build for: using the exact timestamp means **the last payment of one page reappears as the first
of the next**, so deduplicate on `pspReference`; and the number of entries per page varies and may change, so never
key logic off a page size.

Polling more than once a minute gains nothing.

### As a partner

You see only the donations sales units you have been granted access to. If you pass `recipientHandles`, **every
handle must be valid and accessible or the whole call returns HTTP 403** — it does not quietly drop the ones you
cannot see.

## Agreements

| Call | Behavior |
| ---- | -------- |
| `GET /donations/v1/agreements/{agreementId}` | `200` with the agreement, `404` if it does not exist **or you cannot see it** |
| `POST /donations/v1/agreements/{agreementId}/stop` | `200` when stopped, `200` again if already stopped, so it is idempotent |

```json
{
  "id": "2518f497-bfad-43a6-8914-fd0168a6c221",
  "recipientHandle": "NO:6666",
  "startedAt": "2026-01-31T17:26:50.8789251+00:00",
  "schedule": { "interval": "MONTHLY", "withdrawalDay": 10 },
  "amount": { "currency": "NOK", "value": 2300 },
  "payer": {
    "firstName": "Ada",
    "lastName": "Lovelace",
    "phoneNumber": "4712345678",
    "address": { "country": "NO", "region": "Oslo", "postalCode": "0154", "addressLine1": "Robert Levins gate 5" },
    "email": "user@example.com",
    "emailVerified": true
  }
}
```

There is no endpoint to create or change an agreement. Donors start them in the app and change the amount or
withdrawal day themselves; you find out through webhooks.

## Webhooks

Four events, registered through the Webhooks API in the normal way. See `../webhooks/SKILL.md` for registration and
signature verification, which are identical here.

| Event | Fires when |
| ----- | ---------- |
| `donations.agreement.started.v1` | A donor starts an agreement |
| `donations.agreement.stopped.v1` | An agreement stops |
| `donations.agreement.withdrawal-day-changed.v1` | The donor moved the withdrawal day |
| `donations.agreement.amount-changed.v1` | The donor changed the amount |

**Subscribe to `stopped`, `amount-changed`, and `withdrawal-day-changed`, not just `started`.** Donors adjust and
cancel in the app, and nothing else tells you.

The payload is a notification. Follow it with `GET /donations/v1/agreements/{agreementId}` for the current state.

A partner registers `donations.*` webhooks with partner keys. Omitting the `Merchant-Serial-Number` covers every
connected sales unit, including ones added later.

## Donation links and QR codes

A plain universal link, no API call needed:

```text
https://{domain}/donations/{alias}
https://{domain}/donations/{alias}?reference={reference}
```

| Market | Domain |
| ------ | ------ |
| Norway | `qr.vipps.no` |
| Denmark | `qr.mobilepay.dk` |
| Finland | `qr.mobilepay.fi` |

- `alias` is the Donations sales unit's short number from the business portal: digits only, 1 to 6 of them.
  **Leading zeros matter** — `0011` and `11` are different sales units.
- `reference` is optional campaign tracking. Letters, digits, hyphen, underscore, and spaces; 50 characters maximum;
  URL-encode it.
- **Only these hosts and this path work.** A donation link anywhere else will not open the donation journey in the
  app.

Encode the same full URL to make a QR code, with any standard generator. Branded ones are available in the business
portal.

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/donations-api/api-guide.md>,
<https://developer.vippsmobilepay.com/docs/APIs/donations-api/quick-start.md>,
<https://developer.vippsmobilepay.com/docs/APIs/donations-api/donation-links-and-qr.md>,
<https://developer.vippsmobilepay.com/docs/APIs/donations-api/faq.md>, spec at `/api/donations`.
