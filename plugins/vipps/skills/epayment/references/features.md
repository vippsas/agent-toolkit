# ePayment API features

Everything here is switched on by adding fields to the `POST /epayment/v1/payments` request. Nothing needs a different
endpoint.

## Profile sharing

Get the customer's profile data with consent, as part of paying. Cheaper than bolting a Login flow onto a checkout.

```json
"profile": { "scope": "name phoneNumber email address" }
```

Scope values: `address`, `birthDate`, `email`, `name`, `phoneNumber`. Space separated.

The customer sees a consent screen before the payment screen and must complete both. **If they refuse consent, the
payment fails**, so ask for the fewest scopes the feature needs. The data comes back as `userDetails` and `profile.sub`
on `GET /epayment/v1/payments/{reference}` and in the `epayments.payment.authorized.v1` webhook payload.

Comply with the privacy terms, and do not keep the data longer than the purchase requires.

## Express

Address and delivery choice happen inside the app, so the customer can buy from a product page in a few taps.

Three things are required together:

1. `paymentMethod.type` set to `WALLET`.
2. `profile.scope` set to exactly `"name address email phoneNumber"`. Not fewer values, not more. Anything else fails.
3. `shipping` with either `fixedOptions` or `dynamicOptions`, never both.

### Fixed options

Use these whenever the delivery options are known up front. Faster, and nothing can time out.

```json
"shipping": {
  "fixedOptions": [
    {
      "brand": "POSTNORD",
      "type": "HOME_DELIVERY",
      "isDefault": true,
      "priority": 0,
      "options": [
        {
          "id": "postnord-home-1",
          "amount": { "currency": "NOK", "value": 9900 },
          "name": "Posten home standard",
          "meta": "Henrik Ibsens Gate 1, 0000 Oslo",
          "estimatedDelivery": "3-5 business days",
          "isDefault": true,
          "priority": 0
        }
      ]
    }
  ]
}
```

- `type`: `HOME_DELIVERY`, `PICKUP_POINT`, `MAILBOX`, `IN_STORE`, `OTHER`.
- `brand`: `BRING`, `DHL`, `FEDEX`, `GLS`, `HELTHJEM`, `INSTABOX`, `MATKAHUOLTO`, `PORTERBUDDY`, `POSTEN`, `POSTI`,
  `POSTNORD`, `OTHER`. The app draws the carrier logo from this.
- One shipping group per unique brand and type combination. Variants such as pickup points or time slots go in
  `options`.
- `amount` on each option is the shipping cost in minor units, and it is added to the payment total. The customer
  confirms the total including shipping.
- For time slots: `name` carries the date, `estimatedDelivery` the window, `priority` orders them from 0.

### Dynamic options

Only when the address is unknown and shipping depends on it.

```json
"shipping": {
  "dynamicOptions": {
    "callbackUrl": "https://example.com/shipping",
    "callbackAuthorizationToken": "Bearer eyJhbGciOi..."
  }
}
```

Your endpoint receives `Reference`, `AddressLine1`, `AddressLine2`, `City`, `PostCode`, `Country` and must answer
`{ "groups": [ ...shipping groups... ] }`. Return HTTP 400 when you cannot ship to that address, and the app tells the
customer. Verify `callbackAuthorizationToken` on every call. Callbacks arrive from `callback-*.vipps.no`.

### Getting the result

`GET /epayment/v1/payments/{reference}` returns `shippingDetails` with `address`, `shippingCost`, `shippingOptionId`,
`shippingOptionName`, plus `userDetails` with `email`, `firstName`, `lastName`, `mobileNumber`, `addresses`. Capture the
full amount including shipping.

### Limits and branding

- The shipping address must be in the same country as the sales unit, and the currency must match that country.
- Express payments cannot use the test-environment force approve endpoint.
- Button text must be one of "Buy now with Vipps/MobilePay" (preferred), "Vipps/MobilePay Express", or icon plus
  "Express", translated for the market.

## QR payments

`userFlow: "QR"` plus `qrFormat`, for example `{ "format": "IMAGE/SVG+XML", "size": 1024 }`. Show the returned QR on a
screen facing the customer and set `customerInteraction: "CUSTOMER_PRESENT"`. For static merchant QR codes and personal
QR, see the QR API instead.

## Long-living payments

`expiresAt` extends the 10-minute default, up to 60 days ahead, with a 10-minute minimum. `receipt` is then mandatory
(error 6130). The sales unit must be approved for this (error 5050). Useful for invoices and payment links.

## Order details in the app

`receipt` on the create request puts order lines into the customer's payment history in the app. Recommended for every
integration, mandatory for merchants using content monitoring. The Order Management API can add or update details, and
a tracking link, after the payment.

## Minimum user age

`minimumUserAge` restricts a payment to customers above an age. Underage customers come back as error 7010, the same
code as an unknown phone number, so do not tell the customer their number is wrong.

## Metadata

Free-form key-value data stored with the payment and returned by `GET /epayment/v1/payments/{reference}`.

```json
"metadata": { "location": "Q-Park Magasin du Nord", "date": "2026-01-05 12:00 - 14:34" }
```

There are limits on the number of entries and on key and value length, reported as errors 4100 to 4130. Duplicate keys
are rejected. It is not a place for personal data.

## Block payment sources

`blockedSources` restricts which sources may pay, for `WALLET` payments on Danish and Finnish sales units only.
Norwegian sales units get error 5010.

## Customer present payments

At a physical point of sale, always send `"customerInteraction": "CUSTOMER_PRESENT"`. It changes risk handling and is a
requirement for in-store integrations, not an optimization.

Full pages: <https://developer.vippsmobilepay.com/docs/APIs/epayment-api/api-guide/features/>
