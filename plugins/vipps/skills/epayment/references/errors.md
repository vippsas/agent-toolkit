# ePayment API errors

Error bodies follow RFC 7807. Domain errors carry a numeric code inside `extraDetails`.

```json
{
  "type": "https://httpstatuses.io/400",
  "title": "Cannot capture before reservation",
  "detail": "The amount you tried to capture is not reserved. The user must accept the payment before capture can be done.",
  "instance": "/v1/payments/577531734343670112/capture",
  "status": 400,
  "extraDetails": [ { "name": "ErrorCode", "reason": "6080" } ],
  "traceId": "00-813b63975adcaaeef2b0ec7c103c40e3-706492e906541d31-01"
}
```

Log `traceId`, `instance`, and every `extraDetails` entry. Support cannot trace a request without them. A malformed
body gives HTTP 400 with `extraDetails` naming the field and the pattern it failed, and no error code.

Titles and details are reworded over time. Branch on the numeric code and the HTTP status, never on the text.

## Rate limits

| Operation | Limit | Counted per |
| --------- | ----- | ----------- |
| Create, capture, cancel, refund | 5 per minute | `reference` plus MSN |
| Get payment, get event log | 120 per minute | `reference` plus subscription key |

The limit is per unique `reference`, so the ceiling on distinct payments is far higher. If `reference` is missing or
misspelled, every payment counts as the same one and you will hit HTTP 429 immediately.

## Internal

| Code | Title | What to do |
| ---- | ----- | ---------- |
| 3010 | Internal error | Often a malformed request. Check the request, then the status page |

## Invalid request

| Code | Title | What to do |
| ---- | ----- | ---------- |
| 4010 | Capture idempotency conflict | An idempotent retry must repeat the body exactly |
| 4020 | Idempotency error | That `Idempotency-Key` already exists. Generate a new one for a new operation |
| 4040 | Invalid amount | Integers only, minor units. Usually a rounding or decimal bug |
| 4050 | Invalid CustomerToken | The token from a personal QR scan is not valid |
| 4060 | Invalid PersonalQr | |
| 4070 | Invalid phone number | MSISDN: country code plus number, no prefix, no spaces |
| 4080 | Invalid scope | Check the `profile.scope` spelling |
| 4090 | Invalid URL | `returnUrl` and callback URLs must be valid and `https://` |
| 4100 | Metadata capacity exceeded | |
| 4110 | Metadata duplicate keys not allowed | |
| 4120 | Metadata key length exceeded | |
| 4130 | Metadata value length exceeded | |
| 4140 | Missing required parameter | The named field is required for this flow |
| 4150 | Reference exists, or refund idempotency conflict | Either the `reference` is taken, or a retry body changed |

## Merchant configuration

These are account or product problems. No amount of code changes them; the merchant or partner has to act.

| Code | Title | What to do |
| ---- | ----- | ---------- |
| 5010 | Blocking sources not applicable | `blockedSources` is Danish and Finnish sales units only |
| 5020 | Express payment not allowed | The sales unit is not enabled for Express |
| 5030 | Illegal scope | Asking for national identity number or account number without permission |
| 5040 | Invalid currency for merchant | Currency must match the sales unit's registered market |
| 5050 | Long-living payment not allowed | The sales unit is not approved for `expiresAt` |
| 5060 | Merchant bank account not verified | The merchant must verify the account before receiving payments |
| 5070 | Payment cannot be created | Invalid state, missing precondition, or incorrect setup |
| 5080 | PUSH_MESSAGE not allowed | The sales unit needs approval to skip the landing page |
| 5090 | Reference not found | Wrong `reference`, or the right one against the wrong MSN |
| 5100 | Refund not possible | Configuration problem on the sales unit |

## Payment

| Code | Title | What to do |
| ---- | ----- | ---------- |
| 6010 | Amount too small | Minimum is NOK 400 øre, DKK 1 øre, EUR 1 cent |
| 6020 | Attempted refund before reservation | Check the event log |
| 6030 | Cancel period expired | Cancel is possible within 180 days of reservation, and inside the capture deadline |
| 6040 | Cannot cancel a captured payment | Refund instead |
| 6050 | Cannot cancel a non-reserved payment | |
| 6060 | Cannot cancel authorized payment | Sent with `cancelTransactionOnly: true` after the customer authorized |
| 6070 | Cannot capture a cancelled payment | |
| 6080 | Cannot capture before reservation | The customer has not approved. Wait for `AUTHORIZED` |
| 6090 | Capture amount too high | Total captures cannot exceed `authorizedAmount` |
| 6100 | Capture period expired | The reservation is gone. The money cannot be collected |
| 6110 | Expiration date is too late | `expiresAt` maximum is 60 days ahead |
| 6120 | Expiration date is too soon | Minimum is 10 minutes ahead |
| 6130 | Long living payments require a receipt | Send `receipt` with `expiresAt` |
| 6140 | Must capture full amount | Partial capture is not allowed on this payment |
| 6150 | Not enough refundable | Cannot refund more than the captured amount that is not already refunded |
| 6160 | Order processing | Another operation holds the payment. Retry shortly |
| 6170 | Payment already captured | |
| 6180 | Payment already refunded | |
| 6190 | Payment cannot be cancelled | Wrong state |
| 6200 | Payment cannot be captured | Wrong state |
| 6210 | Payment cannot be refunded | Wrong state |
| 6220 | Refund period expired | Refund is possible within 365 days of reservation |
| 6230 | Payment is already reserved | The reference has already been authorized |

## Users

| Code | Title | What to do |
| ---- | ----- | ---------- |
| 7010 | Customer not found | No user for that number, the user cannot pay this business, or `minimumUserAge` blocks them. Do not tell the customer their number is wrong |

## Test environment only

| Code | Title |
| ---- | ----- |
| 10010 | Approve failed |
| 10020 | Approve not allowed |
| 10030 | Identification required |
| 10040 | Invalid payment source |
| 10050 | No cards: the test user must add a card in the app |
| 10060 | Operation not supported |
| 10070 | Payment limit exceeded |

## HTTP statuses worth handling explicitly

| Status | Meaning | Handling |
| ------ | ------- | -------- |
| 401 | Unauthorized | Token missing, expired, or sent without the word `Bearer` |
| 403 | Forbidden | The sales unit lacks the product or permission |
| 409 | Conflict | `Idempotency-Key` reused with a different body |
| 423 | Locked | The payment is locked by a concurrent operation. Retry after a short wait |
| 429 | Too many requests | Slow down, respect any `Retry-After`, check the `reference` field |
| 500 | Internal error | Retry with the same idempotency key. In test, an expired card on force approve shows up here |

Never treat a network timeout as a failed payment. Retry the same request with the same `Idempotency-Key`, or read the
payment back with `GET /epayment/v1/payments/{reference}`, before deciding anything.

Full pages: <https://developer.vippsmobilepay.com/docs/APIs/epayment-api/api-guide/errors.md> and
<https://developer.vippsmobilepay.com/docs/knowledge-base/errors.md>
