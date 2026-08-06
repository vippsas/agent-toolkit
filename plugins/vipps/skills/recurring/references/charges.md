# Recurring charges

Base path `/recurring/v3`. `Idempotency-Key` on every `POST`, `PUT`, `PATCH`, and `DELETE`.

| Operation | Method and path |
| --------- | --------------- |
| List charges for an agreement | `GET /agreements/{agreementId}/charges` |
| Create a charge | `POST /agreements/{agreementId}/charges` |
| Create up to 2 000 charges | `POST /agreements/charges` |
| Get a charge | `GET /agreements/{agreementId}/charges/{chargeId}` |
| Get a charge by ID alone | `GET /charges/{chargeId}` (support lookups, not automation) |
| Capture a reserved charge | `POST /agreements/{agreementId}/charges/{chargeId}/capture` |
| Cancel a charge | `DELETE /agreements/{agreementId}/charges/{chargeId}` |
| Refund a charge | `POST /agreements/{agreementId}/charges/{chargeId}/refund` |

## Create charge fields

```json
{
  "amount": 49900,
  "description": "October",
  "due": "2026-10-01",
  "retryDays": 2,
  "transactionType": "DIRECT_CAPTURE",
  "type": "RECURRING",
  "orderId": "acme-sub-1234-2026-10",
  "externalId": "INV-2026-10-4471",
  "processingMode": "MULTIPLE_ATTEMPTS"
}
```

| Field | Rules |
| ----- | ----- |
| `amount` | Plain integer, minor units. Not the `{currency, value}` object ePayment uses |
| `description` | Maximum 45 characters. Shown under the `productName` title in the app |
| `due` | `YYYY-MM-DD`. At least 1 day ahead, at most 2 years ahead. Required for `RECURRING` |
| `retryDays` | 0 to 14. Use at least 2. Days of retrying after the due date |
| `transactionType` | `DIRECT_CAPTURE` or `RESERVE_CAPTURE` |
| `type` | `RECURRING` (default) or `UNSCHEDULED` |
| `orderId` | Replaces the generated `chargeId`. Unique per MSN. Recommended |
| `externalId` | Settlement reports only. Does not replace `chargeId`, no strict uniqueness |
| `processingMode` | `MULTIPLE_ATTEMPTS` (default) or `SINGLE_ATTEMPT`, which requires `retryDays: 0` |

The agreement must be `ACTIVE`. For `LEGACY` pricing the charges within one interval may total at most 5 times the
agreement price; there is no limit on the *number* of charges in an interval.

If `orderId` is omitted, an ID like `chr-xxxxxxx` is generated. Supplying your own is what makes retries, support, and
settlement reconciliation tractable. Keep it unique across your other Vipps MobilePay APIs for the same MSN too, even
though only the Recurring API enforces it.

## Charge types

**`RECURRING`** is the default and the right choice for anything scheduled. You get automatic retries through
`retryDays`, push messages and in-app guidance for the customer, and therefore a much higher success rate with less
code.

**`UNSCHEDULED`** is a sporadic one-off inside an existing agreement, processed asynchronously right after creation with
no `due` date. Two conditions:

- The MSN must be on the allow list. Request it from developer@vippsmobilepay.com with the merchant serial number and a
  description of the user journey. Without it you get HTTP 400 "Cannot create a charge with type 'UNSCHEDULED'".
- **No retries.** Retrying is entirely your responsibility. `processingMode` does not apply.

Success sends `recurring.charge-reserved.v1` or `recurring.charge-captured.v1` depending on `transactionType`. Failure
sends `recurring.charge-failed.v1` and notifies the customer in the app.

## Charge states

| State | Meaning |
| ----- | ------- |
| `PENDING` | Created, not visible to the customer yet |
| `DUE` | Visible in the app, will be processed on the due date |
| `PROCESSING` | Being processed now |
| `CHARGED` | Processed and captured |
| `RESERVED` | Reserved, ready to capture |
| `PARTIALLY_CAPTURED` | Part captured. Cancel the rest to release it |
| `FAILED` | Insufficient funds, no valid card, or amount above the customer's max |
| `REFUNDED` | Fully refunded. Refunds allowed up to 365 days after capture |
| `PARTIALLY_REFUNDED` | |
| `CANCELLED` | |

A charge sits in `PENDING` until the due date is under 30 days away, then becomes `DUE` and appears in the app under
*Payments*. The customer sees one upcoming charge per agreement, so daily or weekly billing does not flood them.

Typical paths:

- Everything works: `PENDING` -> `DUE` for the due day -> `CHARGED`
- No funds and `retryDays: 0`: `PENDING` -> `DUE` -> `FAILED`
- No funds, `retryDays: 10`, funds on day five: `PENDING` -> `DUE` for five days -> `CHARGED`

Because you observe state by polling or webhook, transitions can appear skipped, even `PENDING` straight to `REFUNDED`.
Write the state machine so any forward jump is safe.

## Retries and failures

The charge stays `DUE` from the due date until it succeeds or `retryDays` runs out, ending `CHARGED` or `FAILED`. Two or
more retry days are strongly recommended. `retryDays` is independent of the agreement interval, so a daily agreement can
have overlapping retrying charges.

Batches, in local market time and explicitly not guaranteed:

- Norway: 09:00 main batch, 17:00 retries
- Denmark and Finland: 03:00 main batch, retries at 13:00, 18:00, 20:00, 22:00, 23:00

Do not design around these hours.

You do not get per-attempt detail. You get, on the charge:

| `failureReason` | Meaning | Who fixes it |
| --------------- | ------- | ------------ |
| `user_action_required` | No funds, wrong number, card blocked for ecommerce, card expired | The customer, in the app |
| `charge_amount_too_high` | Above the customer's `maxAmount` on a `VARIABLE` agreement | The customer raises their maximum |
| `non_technical_error` | For example the profile was deleted | The customer |
| `technical_error` | Failure in Recurring or downstream | While not `FAILED` we are still retrying. Once `FAILED`, create a new charge with a new due date |

The customer gets a push message per failed attempt plus a message in the app explaining exactly what to change, in
their own language. So: when a charge fails, point the customer at the app. Do not write your own dunning emails that
guess the reason, and do not ask support to inspect charges unless there is clear evidence of a fault on our side.

Push messages are sent for failures whether or not the customer has payment notifications switched on. That toggle only
controls notifications for successful charges.

## Capture, cancel, refund

- Capture applies to `RESERVED` charges, in full or in part. Cancel any reserved remainder you will not take, so the
  customer gets their money back immediately instead of waiting for a refund.
- Cancel with `DELETE` before the money moves.
- Refund with `POST .../refund` and `{ "amount": ..., "description": ... }`, up to 365 days after capture, in parts if
  needed.
- Stopping the agreement cancels `PENDING`, `DUE`, and `RESERVED` charges, except that a customer-initiated stop leaves
  `RESERVED` charges for you to capture or cancel.

## Creating many charges at once

`POST /agreements/charges` accepts up to 2 000 charges. Validation happens twice: API-level failures come back in the
response body, and later asynchronous failures arrive as `recurring.charge-creation-failed.v1` webhooks. Handle both, or
some customers are silently never billed.

## Webhook events

Agreements: `recurring.agreement-activated.v1`, `recurring.agreement-rejected.v1`, `recurring.agreement-stopped.v1`,
`recurring.agreement-expired.v1`.

Charges: `recurring.charge-reserved.v1`, `recurring.charge-captured.v1`, `recurring.charge-canceled.v1`,
`recurring.charge-refunded.v1`, `recurring.charge-failed.v1`, `recurring.charge-creation-failed.v1`.

Up to 25 registrations per event type per MSN. Registration and HMAC verification are in
`../../webhooks/SKILL.md`.
`recurring.agreement-stopped.v1` carries an `actor` field saying whether the merchant or the customer stopped it.

## Test environment

`PATCH /agreements/{agreementId}/accept` with `{ "phoneNumber": "4712345678" }` force accepts an agreement without the
app, for automated tests. Test environment only, and the test user must be properly registered in the test app or it
fails.

In test, charges may be created just one day before `due`, the same minimum as production.

## Errors

RFC 7807 bodies with a `traceId`. Idempotency specifics:

- Reusing a key on a different request gives HTTP 409 Conflict.
- A 4xx response is cached against the key: the same key returns the same error, and the operation is not retried.
- Retry only true failures (network, 5xx), and always with the same key.

Full pages: <https://developer.vippsmobilepay.com/docs/APIs/recurring-api/recurring-api-guide.md> and
<https://developer.vippsmobilepay.com/docs/APIs/recurring-api/recurring-api-problems.md>
