---
name: payment-lifecycle
description: >-
  Capture, cancel, refund, timeout, and transaction-ID rules shared by every Vipps MobilePay payment API. Use when
  work involves capture deadlines, reservation windows, reserve or direct capture, partial capture, cancelling a
  payment or charge, refunding, payment or agreement timeouts, polling, or designing an orderId or reference value.
  Read together with epayment or recurring.
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

If a capture keeps failing more than 30 days after the reservation, stop retrying and contact the customer to arrange
another way to pay. Some banks show both the reservation and the capture, which customers can mistake for being
charged twice; it is one payment at two stages.

## Reserve capture and direct capture

*Reserve capture* is the default: the payment is reserved until you capture it. *Direct capture* captures at once and
exists only in the Recurring API and the legacy eCom API; ePayment is always reserve capture.

- **Recurring:** choose per charge with `transactionType`. `DIRECT_CAPTURE` works only on a sales unit that Vipps
  MobilePay has configured for it. Use `RESERVE_CAPTURE` for physical goods, or whenever access is granted later.
- **eCom:** a sales unit has one capture type, which Vipps MobilePay configures; a merchant cannot switch it. Direct
  capture needs extra compliance checks and is offered only to merchants with a partner or a key account manager, who
  request it. Merchants see the capture type in the business portal's *Developer* section, partners through the
  Management API.

With reserve capture a reservation can be released at once with a cancel. After a capture, money goes back only through
a refund, which takes days. If in doubt, use reserve capture and capture right after the reservation: the customer
sees no difference.

## Partial capture

You can capture part of the reserved amount, and capture again while some remains. Merchants in Denmark and Finland
must request partial capture from customer service first. Partial captures **do not** extend the reservation, so the
deadlines above still count from the reservation. When the order is complete, cancel whatever you will not capture. A
typical case is an EV charger, taxi, or vending machine: reserve a reasonable upper amount, capture the real cost, and
cancel the rest.

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

- A payment can be cancelled through the API, or in the business portal, until it is fully captured.
- Cancelling before the customer has approved is possible, but not guaranteed, because it races the customer's action
  in the app. It is not possible while the customer is in a 3-D Secure session.
- Released funds usually reach the customer's account in 2-3 bank days, and up to 10, depending on the bank.

## Refund

Refund reverses a captured amount, up to 365 days after the reservation, and never more than was captured. It typically
reaches the customer in 2-3 bank days, but can take up to 10 depending on the bank. Where the money goes depends on
the market:

| Customer's country | Refund destination |
| ------ | ------------------- |
| Norway, Sweden | The same card used for the payment. If that card is no longer valid, contact the customer to arrange another way to pay them back |
| Denmark, Finland, Greenland | The receiving account configured in the customer's app, which can differ from the account or card originally charged |

Partial refunds are allowed, repeated, until the captured amount is used up.

- A refund past 365 days returns HTTP 400. Some refunds can also be made in the business portal.
- The refunded amount is deducted from the merchant's settlement account after two business days.
- A refund can also fail because the card is no longer valid or the customer no longer has an active account. To check
  a refund, read the payment or charge in the same API that created it. If it succeeded and the customer still has not
  seen the money, check where refunds go in their market, above.

## Timeouts

By default a customer has 10 minutes to act on a payment or agreement request. After that it expires (`EXPIRED` on a
payment, `EXPIRED` on an agreement still `PENDING`).

**Do not cancel the order in your own system before that window has closed, or before you have an `EXPIRED` webhook
or poll result.** Cancelling early creates a race: the customer approves in the app moments after your system already
told them the order was cancelled. Wait for the full timeout, or for the terminal status, whichever comes first.

`EXPIRED` is final: the payment cannot be recovered. Tell the customer, and create a new payment, with a new
`reference`, if they still want to pay.

## Polling

Poll alongside webhooks, never instead of them, because a webhook can be delayed. Start 5 seconds after the request,
then check every 2 seconds, and adapt the interval to the use case. On HTTP 429, slow down: the APIs rate-limit
polling, and each API's skill gives its limits.

## Terms and conditions acceptance

The customer must actively accept your terms and conditions before a payment is initiated. Sending them straight to a
payment deeplink, with no acceptance step in between, does not satisfy this and makes the integration non-compliant.
Build the acceptance step into whatever triggers payment creation, not as an afterthought on a confirmation screen.

Vipps MobilePay runs compliance checks and assigns the merchant category code (MCC) per sales unit. A business that
takes payments in different contexts, such as online and in person, or across different product categories, may need
a separate sales unit for each. Plan the sales units before building.

## `orderId` / `reference`

The same concept has two names: `reference` in the ePayment API, `orderId` in the Recurring, eCom, and Order
Management APIs. Rules, common to both:

- Unique per sales unit (MSN) within that API. Uniqueness across APIs for the same MSN is not enforced, but keeping
  the ePayment `reference` and the Recurring `orderId` distinct from each other is strongly recommended to avoid
  reconciliation mix-ups.
- Case-sensitive, at most 64 characters (at least 8 recommended), `a-z`, `A-Z`, `0-9`, and `-` only.
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
