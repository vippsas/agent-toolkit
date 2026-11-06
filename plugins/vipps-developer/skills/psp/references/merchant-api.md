# PSP Merchant API

Creates and manages the merchants a PSP processes for. Each merchant gets a Merchant Serial Number (MSN), which goes in
the `Merchant-Serial-Number` header of every ePayment and Recurring call made on its behalf. For ePayment PSP,
Recurring PSP, and the Vipps PSP API. MobilePay Online PSPs onboard differently and must not use this API.

Base path `/merchant-management/psp/v1`. Test host `https://apitest.vipps.no`.

## Credentials

Signing up as a PSP partner, done outside the API, gives you `client_id`, `client_secret`,
`Ocp-Apim-Subscription-Key`, and your PSP ID. Get a token with the standard flow (`POST /accesstoken/get`, see
`../../access-token/SKILL.md`). Every request carries `Authorization`, `Ocp-Apim-Subscription-Key`, and your PSP ID
in the `PSP-ID` header, and should carry the `Vipps-System-*` headers.

## Operations

| Operation | Method and path |
| --------- | --------------- |
| List your merchants | `GET /merchants` (no logos in the response) |
| Get one merchant | `GET /merchants/{merchantSerialNumber}` (only your own merchants) |
| Create a merchant | `POST /merchants`, with `Idempotency-Key` |
| Update or deactivate | `PATCH /merchants/{merchantSerialNumber}` |

Errors are RFC 7807 bodies with `type`, `title`, `status`, `detail`, and `instance`.

## Creating a merchant

Required fields: `name`, `companyName`, `organizationNumber`, `mccCode`, `address`, and `logo`.
Optional: `companyEmail` (a valid nonempty email when sent, never `""`; omit it rather than invent one, and expect
`null` back in GET responses), `email`, `website`, `termsOfServiceAccepted`, and `marketPlaceId`. The response carries the new
`merchantSerialNumber`; store it. Retry a failed or timed-out create with the same `Idempotency-Key` to avoid a
duplicate merchant.

- `name` is shown to the customer on the landing page, payment screen, and receipt. Make it the name they recognize.
- `companyName` is the legal name, also shown on the payment screen. Changing it changes it for every merchant with
  the same organization number.
- `organizationNumber` is validated against the national registry in NO, SE, DK, and FI. In Norway: 9 digits, no
  spaces, an active main entity ("hovedenhet"), not a sub-entity.
- `mccCode` is the four-digit ISO 18245 merchant category code, leading zeros included.
- `logo` is a base64-encoded PNG, at least 100 × 100 pixels, at most 1000 pixels on the longest side, ideally square.
  It is shown on the landing page, payment screen, and receipt.
- `address.country` accepts any ISO 3166 country code.
- `termsOfServiceAccepted: true` records that the merchant accepted the terms for sharing user information. It is
  required for profile sharing (userinfo), Login, and Express. Reads return `false` when nothing is recorded.
- `marketPlaceId` is for invoicing and needs a special contract.

## Updating and deactivating

`PATCH` accepts any of `name`, `logo`, `email`, `website`, `address`, `mccCode`, `companyName`,
`termsOfServiceAccepted`, and `marketPlaceId`, several at once. The MSN and organization number cannot change.

`{ "deactivate": true }` sets `status` to `DEACTIVATED`. **This is permanent**: a deactivated merchant cannot be
reactivated or updated. To change an organization number, deactivate the merchant and create a new one with a new
MSN.

Full pages: <https://developer.vippsmobilepay.com/docs/APIs/psp-merchant-api/psp-merchant-api-guide.md>, spec at
`/api/psp-merchant`.
