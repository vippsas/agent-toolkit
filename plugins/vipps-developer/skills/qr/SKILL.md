---
name: qr
description: >-
  Pick and build the right Vipps MobilePay QR flow for a physical location: one-time payment QR on a screen, printed
  merchant redirect QR, merchant callback QR for vending machines, or scanning a customer's personal QR at a till.
  Use when work involves /qr/v1/merchant-callback, /qr/v1/merchant-redirect, /qr/v1/exchange, customerToken,
  merchantQrId, user.checked-in.v1, userFlow QR, or a QR code on a poster, kiosk, or vending machine.
---

# QR API

Four unrelated flows share this API. Choosing the wrong one costs a rebuild, so start with the hardware the merchant
already has, not with the QR code.

Read `../best-practices/SKILL.md` first for servers, keys, and access tokens. A QR code only identifies the customer
or the checkout. The payment itself is made by a payment API: ePayment for new work, but existing integrations pay with
Recurring or the legacy eCom API too. ePayment has personal QR and one-time payment QR built in, so those two flows
need no call to this API at all. See `../epayment/SKILL.md`.

| Merchant has | Use | How it works |
| ------------ | --- | ------------ |
| A QR scanner at the till | **Personal QR** | Scan the code in the customer's app, then push them a payment |
| A customer-facing screen | **One-time payment QR** | Show a QR unique to this payment |
| Neither, unmanned location | **Merchant callback QR** | Printed sticker, you get a webhook when it is scanned |
| Neither, and no payment yet | **Merchant redirect QR** | Printed code that just opens a web page |

Scanner beats screen beats sticker. Personal QR is the recommended flow where the hardware allows it.

**Do not generate these QR codes yourself.** Only codes on the `qr.vipps.no` domain are scannable inside the app, so a
home-made code will not work, quite apart from losing the branding that makes people scan it in the first place.

## Personal QR

Every customer has one in their app. Scan it, exchange it for a phone number, then create a normal push payment.

```bash
curl -X POST https://apitest.vipps.no/qr/v1/exchange \
-H "Authorization: Bearer YOUR-ACCESS-TOKEN" \
-H "Ocp-Apim-Subscription-Key: YOUR-SUBSCRIPTION-KEY" \
-H "Merchant-Serial-Number: YOUR-MSN" \
-H "Content-Type: application/json" \
-d '{ "qrCode": "https://qr.vipps.no/p/qwjhewqhueheuqwhuqwhe" }'
```

```json
{ "msisdn": "4712345678", "timestamp": 1634025600, "version": "2.0" }
```

Send the **full** scanned content as `qrCode`, URL and all, not a fragment of it. `version` `2.0` is the current
tokenized code; `1.0` is a deprecated clear-text one, and only `2.0` carries `timestamp`.

Simpler still, ePayment takes the scanned content directly: create the payment with `userFlow: PUSH_MESSAGE` and the
`personalQr` field, and skip the exchange call. Use the exchange endpoint when you genuinely need the phone number for
something else.

## One-time payment QR

One QR per payment, shown on a screen. The customer scans and the payment is waiting in their app.

With ePayment this is built in: create the payment with `userFlow: "QR"` and the response carries the QR image. That is
the whole integration, and it is what new work should use. See
<https://developer.vippsmobilepay.com/docs/APIs/epayment-api/api-guide/features/qr-payments.md>.

The standalone `POST /qr/v1/` endpoint exists for eCom and Recurring: initiate the payment, then post the returned
deep-link `url` to it and get back a QR image plus `expiresIn` in seconds.

**These expire in 10 minutes, so they cannot be printed.** They are also the one flow that uses **polling rather than
webhooks**, because the payment starts inside the app at scan time. Poll about once a second in a physical setting.
The appearance of `transactionId` in the transaction log is your signal that the code was actually scanned, and the
right moment to put "waiting for customer" on the screen.

## Merchant redirect QR

A printed code that opens a URL. No payment, no app required, any camera works, and it never expires.

```bash
curl -X POST https://apitest.vipps.no/qr/v1/merchant-redirect \
-H "Authorization: Bearer YOUR-ACCESS-TOKEN" \
-H "Ocp-Apim-Subscription-Key: YOUR-SUBSCRIPTION-KEY" \
-H "Merchant-Serial-Number: YOUR-MSN" \
-H "Accept: image/png" \
-d '{ "id": "billboard_1", "redirectUrl": "https://example.com/myProduct" }'
```

You choose the `id`, and it is how you reach the code later: `GET`, `PUT`, and `DELETE` on
`/qr/v1/merchant-redirect/{id}`.

**The destination is editable after printing.** A `PUT` with a new `redirectUrl` takes effect immediately and the
printed image is unchanged, which is what makes these worth using on anything expensive to reprint. A `ttl` in seconds
on the original `POST` deletes the code automatically.

Deleting is permanent for that image: the `id` can be reused, but a code already out in the world will never work
again.

A merchant who does not want to write code can make one of these in the business portal instead.

## Merchant callback QR

A printed sticker at an unmanned point of sale. The customer scans it, you get a webhook, you push them a payment.

```bash
curl -X PUT https://apitest.vipps.no/qr/v1/merchant-callback/{merchantQrId} \
-H "Authorization: Bearer YOUR-ACCESS-TOKEN" \
-H "Ocp-Apim-Subscription-Key: YOUR-SUBSCRIPTION-KEY" \
-H "Merchant-Serial-Number: YOUR-MSN" \
-d '{ "locationDescription": "Kiosk", "category": "IN_STORE" }'
```

- `merchantQrId` is yours, and together with the MSN it identifies the code. Neither can be changed afterwards; only
  `locationDescription` and `category` can.
- `locationDescription` shows in the app after scanning. Maximum 36 characters.
- `category` is `IN_STORE` (default) or `VENDING`, and only changes the wording on the app's waiting screen.
- **The PUT does not return the image.** Fetch it with `GET /qr/v1/merchant-callback/{merchantQrId}`, or list every
  code for the MSN with `GET /qr/v1/merchant-callback`, which is the convenient way to print a batch.
- `qrImageUrl` can change over time for security reasons even though the code itself does not. Re-fetch rather than
  caching it forever. `qrContent` is the text embedded in the code.

**Register the `user.checked-in.v1` webhook before deploying any of this.** Without it, or if your endpoint does not
answer successfully, the customer gets the app error *Can't connect to store. Try scanning again or pay in another
way* and the sale is lost. See `../webhooks/SKILL.md`.

```json
{
  "customerToken": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
  "merchantQrId": "d8b7d76d-49aa-48b8-90c6-38779372c163",
  "msn": "12345",
  "initiatedAt": "2023-10-06T10:45:40.3061965Z"
}
```

**`customerToken` is valid for 15 minutes.** Pass it straight to ePayment to create the payment; there is no need to
resolve it to a phone number first. If you do need the number, `POST /qr/v1/exchange/customer` with
`{ "customer": { "customerToken": "..." } }` returns `msisdn` and the scan `timestamp`.

QR is limited to **one webhook registration per sales unit**, unlike the 25 other event types get. A partner
registration may exist alongside it, and when both match, the sales unit one wins.

Delete codes that go out of service. A scan of a deleted code tells the customer it is not found, which beats leaving
them watching a spinner that will never resolve.

## Image format

Set `Accept: image/png` or `Accept: image/svg+xml` on the request. Merchant callback QRs use `qrImageFormat` and
`qrImageSize` parameters instead, and default to `SVG`.

- `size`: 100 to 2000 pixels, default 1024. PNG only.
- `whiteBorder`: 0 to 100 pixels, default 8. The quiet zone scanners need, so do not set it to 0 on anything printed.
- The returned image URL needs no authentication and can be embedded anywhere. Re-`GET` the same `id` with a different
  `Accept` header to get another format of the same code.

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/qr-api/api-guide/README.md>,
<https://developer.vippsmobilepay.com/docs/APIs/qr-api/api-guide/choosing-qr-type.md>,
<https://developer.vippsmobilepay.com/docs/APIs/qr-api/qr-api-quick-start.md>, spec at `/api/qr`.
