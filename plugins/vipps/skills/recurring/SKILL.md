---
name: recurring
description: >-
  Implement subscriptions, memberships, and metered billing with the Vipps MobilePay Recurring API: draft an agreement,
  activate it, then create charges. Use when work involves recurring or repeat payments, subscriptions, direct debit
  style billing, /recurring/v3/agreements, charges, agreementId, chargeId, due, retryDays, DIRECT_CAPTURE, or
  RESERVE_CAPTURE.
---

# Recurring API

Subscriptions and repeat billing for Vipps and MobilePay. Base path `/recurring/v3`.

Read `../best-practices/SKILL.md` first for servers, keys, access tokens, headers, and minor units.

## Two things exist: agreements and charges

An **agreement** is the customer's standing consent, approved once in the app. A **charge** is one payment inside it.

**Charges are never created automatically.** Nothing is billed unless your system creates a charge for it, at least one
day before it is due. This is the single most common misunderstanding about this API. Your system owns the billing
schedule; the `interval` on the agreement is what the customer is told, plus a cap on how much you may charge.

```text
POST agreement (draft) -> customer approves in app -> ACTIVE
                                                       |
                              your scheduler, once per period:
                              POST charge (due >= tomorrow) -> DUE on due date -> CHARGED
                                                                              -> RESERVED -> capture
                                                                              -> FAILED
```

## Before writing code

Recurring needs its own product activation and extra compliance checks beyond ePayment. Check that the sales unit
actually has it: merchants in the business portal, partners through the partner portal or the Management API. If it is
missing, that is an order to place, not a bug to debug.

Decide `transactionType` up front, because it changes the flow:

- **`DIRECT_CAPTURE`** — money is taken on the due date. Correct for digital access granted immediately. Requires the
  sales unit to be configured for direct capture.
- **`RESERVE_CAPTURE`** — money is reserved on the due date and you capture when you ship. Required for physical goods,
  and whenever access is granted later.

## 1. Draft the agreement

`POST /recurring/v3/agreements` with `Idempotency-Key`.

```bash
curl -X POST https://apitest.vipps.no/recurring/v3/agreements \
-H "Content-Type: application/json" \
-H "Authorization: Bearer YOUR-ACCESS-TOKEN" \
-H "Ocp-Apim-Subscription-Key: YOUR-SUBSCRIPTION-KEY" \
-H "Merchant-Serial-Number: YOUR-MSN" \
-H "Idempotency-Key: YOUR-IDEMPOTENCY-KEY" \
-d '{
  "phoneNumber": "4712345678",
  "interval": { "unit": "MONTH", "count": 1 },
  "pricing": { "type": "LEGACY", "amount": 49900, "currency": "NOK" },
  "productName": "Premier League subscription",
  "productDescription": "Access to all games of English top football",
  "merchantRedirectUrl": "https://example.com/confirmation",
  "merchantAgreementUrl": "https://example.com/account/subscriptions/1234"
}'
```

Response:

```json
{ "agreementId": "agr_TGSuPyV", "vippsConfirmationUrl": "https://api.vipps.no/dwo-api-application/..." }
```

Send the customer to `vippsConfirmationUrl` unchanged. Store `agreementId` immediately, before the redirect.

Field notes:

- `productName` becomes the agreement's name in the app. `productDescription` is the detail line, optional.
- `merchantAgreementUrl` must open the page on your site where the customer manages *this* agreement. Not your home
  page. You are required to build that page. The app opens the URL in the normal browser.
- `interval` is `{ unit: DAY | WEEK | MONTH | YEAR, count: 1-31 }`. Omit `interval` entirely for pay-per-use.
- `initialCharge` bills something at activation. See `references/agreements.md`.
- `campaign` presents a discounted introductory price with the normal price shown for comparison. Use it for
  introductory offers instead of abusing `initialCharge`.

### Pricing types

| `pricing.type` | Amount set by | Charge ceiling | Campaigns |
| -------------- | ------------- | -------------- | --------- |
| `LEGACY` (default) | You, fixed per interval | 5 times the agreement price, cumulative per interval | Yes |
| `VARIABLE` | You suggest `suggestedMaxAmount`, the customer confirms a `maxAmount` | The higher of the two | No |
| `FLEXIBLE` | You, freely per charge | None | No |

The type cannot be changed later. Pick it correctly the first time. `VARIABLE` is the honest choice for usage-based
billing: the customer sees a ceiling. `FLEXIBLE` gives you no limit and the customer no context, so use it only when
the amount genuinely cannot be bounded, such as electricity.

Maximum amounts: NOK 20 000, DKK 300 000, EUR 2 000.

## 2. Wait for activation

A draft is `PENDING` for 10 minutes, then expires. Poll and listen for webhooks. Do not trust `merchantRedirectUrl`:
activation may not have finished when the customer lands there, and the customer may never land there.

```bash
curl -X GET https://apitest.vipps.no/recurring/v3/agreements/AGREEMENT-ID \
-H "Authorization: Bearer YOUR-ACCESS-TOKEN" \
-H "Ocp-Apim-Subscription-Key: YOUR-SUBSCRIPTION-KEY" \
-H "Merchant-Serial-Number: YOUR-MSN"
```

| Status | Meaning |
| ------ | ------- |
| `PENDING` | Created, not yet approved |
| `ACTIVE` | Approved. Charges may be created |
| `STOPPED` | Stopped by you or by the customer. **Cannot be reactivated** |
| `EXPIRED` | Not approved in time, or a `DIRECT_CAPTURE` initial charge failed |

Keep polling until the status is `ACTIVE`, `STOPPED`, or `EXPIRED`. For `VARIABLE` pricing, read the customer's chosen
`pricing.maxAmount` from this response.

## 3. Create charges

`POST /recurring/v3/agreements/{agreementId}/charges` with `Idempotency-Key`.

```json
{
  "amount": 49900,
  "description": "October",
  "due": "2026-10-01",
  "retryDays": 2,
  "transactionType": "DIRECT_CAPTURE",
  "orderId": "acme-sub-1234-2026-10"
}
```

Rules that the API enforces:

- The agreement must be `ACTIVE`. Charges cannot be created against any other status.
- `due` must be at least 1 day ahead and at most 2 years ahead. A charge due the 27th must be created on the 26th or
  earlier.
- `retryDays` is capped at 14. Use at least 2. `retryDays: 0` means one attempt and then `FAILED`.
- `description` is at most 45 characters. The app shows it under the `productName` title.
- `orderId` replaces the generated `chargeId` and must be unique per MSN. Use your own stable ID so retries and
  reconciliation line up. `externalId` is a separate, looser field used only in settlement reports.
- For `LEGACY` pricing the charges inside one interval may total at most 5 times the agreement price.

To bill a batch, `POST /recurring/v3/agreements/charges` takes up to 2 000 charges in one request. Failures come back
two ways: synchronously in the response for validation errors, and asynchronously as
`recurring.charge-creation-failed.v1` webhooks.

For a one-off extra amount outside the schedule, `"type": "UNSCHEDULED"` exists but the sales unit must be allow-listed
for it, and **unscheduled charges are never retried**. Default is `"type": "RECURRING"`, which gets automatic retries
and in-app prompts to the customer, and therefore a much higher success rate.

## 4. Follow the charge

`GET /recurring/v3/agreements/{agreementId}/charges/{chargeId}`

| Status | Meaning |
| ------ | ------- |
| `PENDING` | Created, not yet visible to the customer |
| `DUE` | Visible in the app, will be processed on the due date |
| `PROCESSING` | Being processed now |
| `CHARGED` | Money captured |
| `RESERVED` | Reserved, waiting for you to capture |
| `PARTIALLY_CAPTURED` | Part captured. Cancel the rest if you will not take it |
| `FAILED` | No funds, no valid card, or the amount exceeded the customer's max |
| `REFUNDED` / `PARTIALLY_REFUNDED` | |
| `CANCELLED` | |

A charge moves from `PENDING` to `DUE` once the due date comes within about a month, which is when the customer can see
it in the app. Because you learn state by polling or webhook, a charge can appear to skip states.

Failures are handled for you: the customer gets a push message and an in-app message explaining what to fix, and the
charge is retried until `retryDays` runs out. You get `failureReason` and `failureDescription`, not per-attempt detail.
Do not build your own retry loop for `RECURRING` charges, and do not ask support to inspect charges. Ask the customer to
open the app.

`failureReason` values: `user_action_required` (funds, card, blocked or expired card), `charge_amount_too_high` (above
the customer's `maxAmount` on a `VARIABLE` agreement), `non_technical_error`, `technical_error`.

## 5. Capture, cancel, refund, stop

| Goal | Call |
| ---- | ---- |
| Capture a `RESERVED` charge | `POST /agreements/{id}/charges/{chargeId}/capture` |
| Cancel a charge before it is paid | `DELETE /agreements/{id}/charges/{chargeId}` |
| Refund a charged amount | `POST /agreements/{id}/charges/{chargeId}/refund` |
| End the subscription | `PATCH /agreements/{id}` with `{"status": "STOPPED"}` |

- Partial capture is supported. Cancel any reserved remainder you will not take.
- Refunds are allowed up to 365 days after capture.
- There is **no pause status**. To pause, simply create no charges and say so in the agreement description. Do not use
  `STOPPED` as a pause: it is irreversible.
- Stop at the end of the paid period, not the moment the customer asks. While the agreement is `ACTIVE` you can still
  bill and the customer keeps access.
- Stopping cancels `PENDING`, `DUE`, and `RESERVED` charges. If the customer stops the agreement in the app instead,
  `RESERVED` charges survive and you must capture or cancel them yourself. Capture the initial charge before stopping.
- When stopping, send only `status`. Any other field in the same `PATCH` gives HTTP 400.

## Things that will bite you

1. **Nobody creates charges but you.** A scheduler that dies means a customer who is never billed. Make it observable.
2. **`Idempotency-Key` is required on every POST, PUT, PATCH, and DELETE.** Reusing a key with a different body gives
   HTTP 409, and a 4xx response stays 4xx for that key.
3. **Listen for `recurring.agreement-stopped.v1`.** Customers cancel in the app, and your system has to notice. The
   `actor` field says whether it was you or them.
4. **Charge timing is not exact.** Batches run in the market's local time (Norway 09:00 with a 17:00 retry, Denmark and
   Finland 03:00 with several retries) and are not guaranteed. Never depend on the hour.
5. **You never touch card data.** Do not build card storage or updating. The customer maintains their own card in the
   app, and an expired card is their action, not yours.
6. **Amounts are plain integers in minor units** here, not the `{currency, value}` object that ePayment uses. `amount`
   is a number.

## Before calling it done

Both webhooks and polling. Every agreement status and charge status handled. A working agreement management page behind
`merchantAgreementUrl`. Charges created early enough. `retryDays` at least 2. Errors logged with request and response.

Full requirement list:
<https://developer.vippsmobilepay.com/docs/APIs/recurring-api/recurring-api-checklist.md>

## Deeper reference

- `references/agreements.md` — pricing types, initial charge, campaigns, intervals, updating, user cancellation
- `references/charges.md` — charge fields, states, retries, batches, webhooks, test-environment force accept

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/recurring-api/recurring-api-quick-start.md>,
<https://developer.vippsmobilepay.com/docs/APIs/recurring-api/recurring-api-guide.md>, spec at `/api/recurring`.
