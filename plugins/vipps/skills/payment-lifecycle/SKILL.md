---
name: payment-lifecycle
description: >-
  Capture, cancel, refund, timeout, and transaction-ID rules shared by every Vipps MobilePay payment API. Use when
  work involves capture deadlines, reservation windows, cancelling a payment or charge, refunding, payment or
  agreement timeouts, or designing an orderId or reference value. Read together with epayment or recurring.
---

# Payment lifecycle: capture, cancel, refund, timeouts, IDs

These rules come from the underlying card and wallet mechanics, not from one API's implementation, so they apply the
same way to the ePayment API and the Recurring API (and to the legacy eCom API). Read `epayment/SKILL.md` or
`recurring/SKILL.md` for the endpoints; read this for the deadlines and behavior around them.

## Capture attempt deadlines

A reservation that is not captured in time is automatically cancelled.

| Market | Deadline |
| ------ | -------- |
| Norway | 180 days |
| Denmark, Finland | 14 days by default, unless [late capture](#late-capture-for-mobilepay-sales-units) is activated (up to 180 days) |

Attempting to capture a payment after its deadline returns HTTP 400 with the relevant error details.

Within that deadline, the card network's or payment method's own guarantee is usually shorter:

- **Visa**: reservations usually last 5-7 days (5 days for Visa Electron); banks may release after 4-7 days. Capture
  within 7 days and Visa guarantees the capture succeeds.
- **Mastercard**: reservations are valid for 30 days, but banks may release earlier. Mastercard guarantees a capture
  within that window.
- **BankAxept** (Norway): 7 days, a hard limit.

### Late capture for MobilePay sales units

This feature must be approved for the sales unit on a case-by-case basis, and requires a legitimate business need,
typically online retail where goods are delivered later and capture must happen later too. Contact the KAM or
customer service to request it. Captures between 15 and 180 days after reservation are not guaranteed to succeed.

**These deadlines are outer limits, not guarantees.** The customer's bank, card issuer, Klarna, or other payment
provider can release the reservation earlier, so capturing after the card network's window has passed is not "the
same payment, later." The bank has released the hold, so the capture becomes a new charge attempt. If the customer's
account no longer has the funds, it fails. If it does, the charge can, in rare cases, succeed and put the account
negative. This is the most common cause of failed captures for merchants shipping physical goods: capture
immediately before dispatch, verify `capturedAmount` in the response, and only then hand the goods to the carrier.
The ePayment API also exposes a `captureGuaranteedUntil` field on the payment resource and in the `authorized`
webhook, giving the exact date a successful capture is guaranteed for that payment.

Capture must never happen before the product or service is delivered. That is a regulatory requirement, not a style
choice.

## Capture amount versus reserved amount

You can never capture more than was reserved. If shipping is added at capture time, the reserved amount must already
cover it: reserving 1200 for a 1000 cart leaves 200 for shipping; a 300 shipping cost on top makes the 1300 capture
fail. Reserve for the full expected total, including shipping, up front.

## Cancel

Cancel releases whatever part of the reservation you will not capture. Do this as soon as you know you will not use
it, for the customer's sake and because carrying an unresolved reservation past its natural point causes support
contacts. It is also a compliance point, see [Payment rules](#terms-and-conditions-acceptance) below.

Cancel is subject to the same [capture deadlines](#capture-attempt-deadlines): a cancel attempt on a payment or charge past
its deadline returns HTTP 400, because the reservation is already gone.

## Refund

Refund reverses a captured amount, up to 365 days after the capture, and never more than was captured. It typically
reaches the customer in 2-3 bank days, but can take up to 10 depending on the bank. Where the money goes depends on
the market:

| Market | Refund destination |
| ------ | ------------------- |
| Norway, Sweden | The same card used for the payment. If that card is no longer valid, contact the customer to arrange another way to pay them back |
| Denmark, Finland | The receiving account configured in the customer's MobilePay app, which can differ from the account or card originally charged |

Partial refunds are allowed, repeated, until the captured amount is used up.

## Timeouts

By default a customer has 10 minutes to act on a payment or agreement request. After that it expires (`EXPIRED` on a
payment, `EXPIRED` on an agreement still `PENDING`).

**Do not cancel the order in your own system before that window has closed, or before you have an `EXPIRED` webhook
or poll result.** Cancelling early creates a race: the customer approves in the app moments after your system already
told them the order was cancelled. Wait for the full timeout, or for the terminal status, whichever comes first.

## Terms and conditions acceptance

The customer must actively accept your terms and conditions before a payment is initiated. Sending them straight to a
payment deeplink, with no acceptance step in between, does not satisfy this and makes the integration non-compliant.
Build the acceptance step into whatever triggers payment creation, not as an afterthought on a confirmation screen.

## `orderId` / `reference`

The same concept has two names: `reference` in the ePayment API, `orderId` in the Recurring, eCom, and Order
Management APIs. Rules, common to both:

- Unique per sales unit (MSN) within that API. Uniqueness across APIs for the same MSN is not enforced, but keeping
  the ePayment `reference` and the Recurring `orderId` distinct from each other is strongly recommended to avoid
  reconciliation mix-ups.
- Case-sensitive, 8-64 characters, `a-z`, `A-Z`, `0-9`, and `-` only.
- Avoid leading zeros: spreadsheet tools like Excel strip them, which breaks reconciliation.
- Avoid purely numeric IDs: they are slower to look up and easy to confuse with unrelated numbers in logs. Mix letters
  and numbers, and make the ID recognizable, since it is shown to the customer in the app.
- If a customer retries a failed attempt for the same order, append an incrementing suffix (`...-1`, `...-2`) rather
  than reusing the ID; each attempt needs its own value.
- If you have several sales units or several stores behind one sales unit, prefix the ID with the MSN or a store code,
  so a settlement report shows which store an order belongs to directly, without looking up the order in your own
  database first.

## Where the authoritative documentation lives

- Capture: <https://developer.vippsmobilepay.com/docs/knowledge-base/reserve-and-capture.md>
- Cancel: <https://developer.vippsmobilepay.com/docs/knowledge-base/cancel.md>
- Refund: <https://developer.vippsmobilepay.com/docs/knowledge-base/refund.md>
- Timeouts: <https://developer.vippsmobilepay.com/docs/knowledge-base/timeouts.md>
- Payment rules (T&C acceptance, sales unit setup): <https://developer.vippsmobilepay.com/docs/knowledge-base/payment-rules.md>
- `orderId` / `reference`: <https://developer.vippsmobilepay.com/docs/knowledge-base/orderid.md>
- Polling: <https://developer.vippsmobilepay.com/docs/knowledge-base/polling-guidelines.md>
