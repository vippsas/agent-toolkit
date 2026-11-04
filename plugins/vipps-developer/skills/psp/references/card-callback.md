# PSP card callback

Vipps MobilePay `POST`s card data to `psp.callbackUrl` when the user selects a card: on ePayment payment creation,
Recurring agreement sign-up, and Recurring payment source updates. Recurring charges never use it. The call is
synchronous: respond with the authorization result within 20 seconds.

If you need to allow our servers through a firewall, see
<https://developer.vippsmobilepay.com/docs/knowledge-base/servers.md>.

## Request body

| Field | Notes |
| ----- | ----- |
| `pspReference` | Your reference from the `psp` object on the payment or agreement |
| `authorizationAttemptId` | Unique per attempt. The same in the second callback after a soft decline |
| `merchantSerialNumber` | The merchant the payment is for |
| `amount` | `{ value, currency }`, minor units. For Express it includes the shipping the customer picked |
| `softDeclineCompletedRedirectUrl` | Where to send the user, unchanged, after a 3-D Secure step-up |
| `cardInfo.maskedCardNumber` | For example `47969485XXXX1234` |
| `cardInfo.cardType` | Same values as `allowedCardTypes`. Always process with this type |
| `cardInfo.cardIssuedInCountryCode` | ISO 3166-1 alpha-2 |
| `cardInfo.cardDataType` | `TOKEN` or `PAN` |
| `cardInfo.networkToken` | With `TOKEN`: `number`, `cryptogram`, `expiryMonth`, `expiryYear`, `tokenType` (for example `VISA`), `eci`, and `paymentAccountReference`, which stays stable across token renewals |
| `cardInfo.encryptedPan` | With `PAN`: see Encrypted PAN below |

The body is plain JSON. Verify it before acting on it.

## Verifying the request

The callback is signed with HMAC-SHA256 using your PSP client secret. It carries `Host`, `x-ms-date`,
`x-ms-content-sha256`, and `Authorization`, plus `X-Vipps-Authorization` with the same value as `Authorization`.

1. SHA-256 the raw body as received, base64 encode it, and compare it with `x-ms-content-sha256`. Do not re-serialize
   the JSON first: whitespace changes the hash.
2. Build `POST\n<pathAndQuery>\n<x-ms-date>;<Host>;<x-ms-content-sha256>`, with `\n` and not `\r\n`, and with the
   port if `Host` has one.
3. HMAC-SHA256 that string with the client secret, base64 encode it, and compare it with the `Signature` part of
   `Authorization`.

## Response

Always `HTTP 200 OK` with a JSON body:

- `status`: `RESERVE`, `SOFT_DECLINE`, or `FAIL`. Required.
- `networkTransactionReference`: with `RESERVE`, when you have one.
- `transactionLinkId`: with `RESERVE` on a Mastercard card in Recurring, to link later charges to this transaction.
- `softDeclineUrl`: required with `SOFT_DECLINE`.
- `errorCode` and `errorMessage`: required with `FAIL`.

`errorCode` values for `FAIL`. A retryable code lets the user try again with the same or another card:

| `errorCode` | Meaning | Retryable |
| ----------- | ------- | --------- |
| `100` | Card error | Yes |
| `200` | Insufficient funds | Yes |
| `210` | Limit exceeded | Yes |
| `300` | Issuer declined, no specific reason | Yes |
| `400` | Permanent decline | No |
| `500` | Risk declined | Yes |
| `600` | Temporary technical error | Yes |
| `700` | Merchant configuration error | No |
| `800` | Duplicate or already in progress | No |
| `900` | Unknown error | Yes |

A timeout or HTTP 500 response is never retryable for the user. A new payment is needed.

The same codes are used for `error.code` when reporting a Recurring PSP charge result.

## Encrypted PAN

The callback carries a network token by default. About 0.1% of cards cannot be tokenized, mostly standalone Dankort.
To receive an encrypted PAN for those, set `publicEncryptionKeyId` in the `psp` object. Without it, those payments
fail, so set it whenever `DANKORT` is in `allowedCardTypes`.

To get a key ID in production, send a 4096-bit RSA public key to Vipps MobilePay: `X.509 SubjectPublicKeyInfo`, DER
encoded, as a PEM file named `{integratorname}-{environment}-public`, in a ZIP file. A key unused for 6 months is
deleted, and you must then send a new one.

In test, no key is needed: send any random GUID as `publicEncryptionKeyId`, and decrypt with the sandbox private test
key from <https://developer.vippsmobilepay.com/downloads/psp/private.pem>.

`encryptedPan` uses `RSA/NONE/OAEPWithSHA256AndMGF1Padding`. Decrypted, it looks like:

```json
{ "timestampticks": 123456789123456789, "encryptedCardData": { "cardNumber": 1234567812345678, "expiryMonth": 12, "expiryYear": 28 } }
```

Most Dankort cards are co-branded Visa/Dankort. With `DANKORT` allowed and a key set, the Dankort rail is available,
and `preferVisaPartOfVisaDankort: true` routes them through Visa instead. To handle tokens only, drop `DANKORT` and
omit the key.

## Test tokens

Cards can't be added in the test app. Whatever card the user picks, the callback carries the token chosen by the
payment amount:

| Amount (minor units) | Token number | Expiry | Cryptogram |
| -------------------- | ------------ | ------ | ---------- |
| `2200` | `5226603115488031` | 05/30 | `AlhlvxmN2ZKuAAESNFZ4GoABFA==` |
| `3100` | Emulates a card that is not eligible | | |
| `3200` | `4111111111111111` | 03/30 | `uxToh3Ep6gsR8AAkvZALN19Iz34=` |
| `4200` | `4895370013193500` | 03/30 | `AlhlvxmN2ZKuAAESNFZ4GoABFA==` |
| `4300` | `5226603115488031` | 03/30 | `AlhlvxmN2ZKuAAESNFZ4GoABFA==` |
| `4400` | `4895370012792682` | 12/30 | `AgAAAAAAAIR8CQrXSohbQAAAAAA=` |
| `5100` | `4268270087302871` | 09/30 | `AgAAAAAAAIR8CQrXSohbQAAAAAA=` |
| `5200` | `5413330089010442` | 12/30 | `AgAAAAAAAIR8CQrXSohbQAAAAAA=` |
| `5300` | `4895370013193500` | 03/30 | `/wAAAAwAUkMTObMAAAAAgS0AAAA==` |
| Any other amount | `4895370013193500` | 05/30 | `AlhlvxmN2ZKuAAESNFZ4GoABFA==` |

Full pages: <https://developer.vippsmobilepay.com/docs/APIs/psp-epayment-api/epayment-psp-api-guide.md> and
<https://developer.vippsmobilepay.com/docs/APIs/psp-recurring-api/recurring-psp-api-guide.md>
