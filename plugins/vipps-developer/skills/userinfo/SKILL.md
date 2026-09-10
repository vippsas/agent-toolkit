---
name: userinfo
description: >-
  Get a Vipps MobilePay user's name, address, email, phone number, or birth date as part of a payment or agreement,
  using profile sharing and the Userinfo API. Use when work involves /vipps-userinfo-api/userinfo, the profile.scope
  field on a payment or agreement, a sub identifier, consent screens, or fetching a customer's address without
  asking them to type it.
---

# Userinfo API

*Profile sharing*: the customer approves the payment and hands over their profile details on the same trip into the
app. One consent screen, no separate login, no forms to fill in.

Read `../best-practices/SKILL.md` first for servers, keys, and access tokens.

**Profile sharing is the right tool when a purchase needs customer details.** Reach for the Login API only when the
customer is signing in or signing up without paying. See `../login/SKILL.md`.

## Check whether you need this API at all

Consent is always requested on something else: a payment, an agreement, or a log-in. This API only reads the result,
and for two of those three the API you are already calling hands the details back on its own:

| You are using | Where the details arrive | Call Userinfo when |
| ------------- | ------------------------ | ------------------ |
| ePayment | `userDetails` on `GET /epayment/v1/payments/{reference}` and on the `authorized` webhook | You need `nin`, the `_verified` flags, `formatted` addresses, or more than one address |
| Recurring | Only `sub` and `userinfoUrl` on the agreement | Always, once you have the `sub` |

So on ePayment this API is for detail the payment response does not carry: `profile.scope` on the create request plus
`userDetails` on the response is usually the whole job. See `../epayment/SKILL.md`. On Recurring and the legacy eCom
API, `profile.scope` buys the consent but the details themselves always come from here.

**Login is a different endpoint, not this one.** A log-in returns profile information from
`GET /vipps-userinfo-api/userinfo/` with **no `sub`**, authorized with the *user's* access token from the OpenID
Connect flow, and documented under the Login API. This skill's `GET /vipps-userinfo-api/userinfo/{sub}` takes a `sub`
and your own merchant access token. Same path prefix, different endpoint, different authorization. See
`../login/SKILL.md`, and the profile table under "Getting the customer's profile" in `../best-practices/SKILL.md` for
all three paths side by side.

`userDetails` on an ePayment payment covers `firstName`, `lastName`, `email`, `mobileNumber`, `dateOfBirth`, and
`addresses`. It does not carry `nin`, `email_verified`, `phone_number_verified`, or the `formatted` address string.

## The flow, three calls

1. **Ask.** Add `profile.scope` to the request that starts the payment or agreement.
2. **Read the `sub`.** Fetch the payment or agreement afterwards; the response carries a `sub`.
3. **Fetch the details.** `GET /vipps-userinfo-api/userinfo/{sub}`.

Step 1, on ePayment:

```json
{
  "amount": { "currency": "NOK", "value": 49900 },
  "paymentMethod": { "type": "WALLET" },
  "customer": { "phoneNumber": "4712345678" },
  "reference": "acme-shop-123-order123abc",
  "userFlow": "WEB_REDIRECT",
  "returnUrl": "https://example.com/redirect?reference=acme-shop-123-order123abc",
  "paymentDescription": "Purchase of socks",
  "profile": { "scope": "name phoneNumber address birthDate" }
}
```

The same `profile.scope` goes on `POST /recurring/v3/agreements`.

Step 2 reads `profile.sub` back from `GET /epayment/v1/payments/{reference}` or
`GET /recurring/v3/agreements/{agreementId}`. With webhooks, `userDetails` and `sub` also ride along on
`epayments.payment.authorized.v1`, which saves you the extra fetch.

Step 3:

```bash
curl -X GET https://apitest.vipps.no/vipps-userinfo-api/userinfo/{sub} \
-H "Authorization: Bearer YOUR-ACCESS-TOKEN" \
-H "Ocp-Apim-Subscription-Key: YOUR-SUBSCRIPTION-KEY" \
-H "Merchant-Serial-Number: YOUR-MSN"
```

## Scopes

Space-separated, any order. Only these values:

| Scope | You get back | Notes |
| ----- | ------------ | ----- |
| `name` | `name`, `given_name`, `family_name` | Verified against the National Population Register |
| `address` | `address` and `other_addresses` | Up to three: home, work, other |
| `email` | `email`, `email_verified` | |
| `phoneNumber` | `phone_number`, `phone_number_verified` | The number the customer uses with Vipps MobilePay |
| `birthDate` | `birthdate`, as `YYYY-MM-DD` | Verified against the National Population Register |
| `nin` | `nin` | National Identity Number. Needs approval per sales unit, see below |

**Ask for the minimum.** The customer sees every scope on one screen and can only accept or reject the whole set. They
cannot approve name and decline address. Every extra scope is another reason to tap no, and **a declined consent fails
the payment or agreement**, it does not fall through to a payment without details.

A customer who already consented to a scope within the last 7 days is not asked for it again.

`nin` is restricted. Only a sales unit with a legal requirement or another objective need to identify the person that
precisely gets it approved. Do not design a flow around it and then discover it was never enabled.

## The response

```json
{
  "sub": "126684df-c056-4625-821d-f2905febe3f9",
  "sid": "57bccee36b19600c",
  "name": "Test User",
  "given_name": "Test",
  "family_name": "User",
  "birthdate": "1955-05-18",
  "email": "test.user@example.com",
  "email_verified": false,
  "phone_number": "4748571123",
  "phone_number_verified": true,
  "address": {
    "address_type": "home",
    "country": "NO",
    "formatted": "BOKS 6300, ETTERSTAD\n0603\nOSLO\nNO",
    "postal_code": "0603",
    "region": "OSLO",
    "street_address": "BOKS 6300, ETTERSTAD"
  },
  "other_addresses": [
    {
      "address_type": "work",
      "country": "NO",
      "formatted": "Robert Levins gate 5\n0152\nOslo\nNO",
      "postal_code": "0152",
      "region": "Oslo",
      "street_address": "Robert Levins gate 5"
    }
  ]
}
```

Only the fields covered by the granted scopes appear. Do not assume a key is present.

**Addresses.** `address` is the customer's default; `other_addresses` holds the rest. Fetch both and let the customer
pick which one to ship to rather than silently using the default. A customer with no registered address gets an
`address` object of empty strings, not a missing field or a null, so test for `""` and not for absence.

The app's *Unit, floor or other details* field is folded into `street_address` after a `\n`, for example
`Suburbia 23\nUnit B5`. Splitting on the newline gives you the two lines back if your address form needs them
separately.

## The `sub`

A UUID identifying one customer's consent to one sales unit.

- Stable across revoking and re-consenting, because it derives from the customer's national identity number.
- It changes if the customer deletes their profile and makes a new one, so treat it as a strong hint rather than a
  permanent primary key.
- **One `sub` per MSN.** The same person has a different `sub` at each of your sales units. A `sub` from one MSN with
  the API keys of another will not resolve.
- It is written **asynchronously**. A fetch within milliseconds of the approval can come back without it. Retry rather
  than treating that as an error.

## The 168-hour rule

Profile data can be fetched for **168 hours (7 days)** from the moment consent is given, and no longer.

- After that the API returns `[Expired]` in place of the values. There is no manual recovery: privacy rules mean the
  data cannot be handed over out of band either.
- The window survives revocation. A customer who withdraws consent on day two does not cut off your access for the
  remainder of the 168 hours, which is deliberate, so back-office processing can finish. Revocation does apply
  immediately to *future* payment sessions.

**Fetch immediately and store what you need.** Do not treat `/userinfo/{sub}` as a lookup you can call whenever an
order is opened. Details also drift: what you read on day six may no longer match what the customer consented to on
day one.

What you store is personal data under GDPR from the moment it lands. Keep only the fields the order actually needs,
and keep them only as long as it needs them.

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/userinfo-api/userinfo-api-guide.md>,
<https://developer.vippsmobilepay.com/docs/APIs/userinfo-api/userinfo-api-quick-start.md>, spec at `/api/userinfo`.
Per-API detail: <https://developer.vippsmobilepay.com/docs/APIs/epayment-api/api-guide/features/profile-sharing.md>
and <https://developer.vippsmobilepay.com/docs/APIs/recurring-api/recurring-api-guide.md#profile-sharing>.
