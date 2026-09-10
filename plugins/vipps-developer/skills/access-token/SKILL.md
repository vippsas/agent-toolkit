---
name: access-token
description: >-
  Get and reuse a Vipps MobilePay access token. Covers both flows: standard authentication at /accesstoken/get with
  sales unit or partner keys, and specialized authentication at /miami/v1/token with accounting or Donations
  merchant-level keys. Use when work involves accesstoken/get, miami/v1/token, client_credentials, Basic auth,
  Bearer tokens, token caching, HTTP 401, or invalid_client.
---

# Access Token API

Every other API here needs a Bearer token, and this is where it comes from. Nothing else in the platform works until
this call does.

Read `../best-practices/SKILL.md` first for servers, keys, and headers.

There are **two token endpoints**, and they are not interchangeable. Picking the wrong one is the usual reason a first
integration returns HTTP 401.

| Flow | Endpoint | Keys | Token life |
| ---- | -------- | ---- | ---------- |
| Standard | `POST /accesstoken/get` | Sales unit keys, partner keys | 1 hour in test, 24 hours in production |
| Specialized | `POST /miami/v1/token` | Accounting keys, Donations merchant-level keys | 15 minutes, both environments |

## Which flow do I need?

Start from the keys you were given, not from the API you are calling.

| You have | Use | Gets you |
| -------- | --- | -------- |
| Sales unit keys from the business portal | Standard | ePayment, Recurring, Login, Webhooks, QR, Userinfo, Order Management, Management, Report |
| Partner keys | Standard | The same, plus Management and Donations, on behalf of the merchants you manage |
| Accounting keys | Specialized | Report API, Sales API |
| Donations merchant-level keys | Specialized | Donations API, and the Report and Webhooks APIs for Donations |

A Donations *partner* uses partner keys and the standard flow, not the specialized one. The key type decides, not the
product.

The give-away in the request shape: standard sends the keys as three separate headers and an empty body; specialized
sends `client_id:client_secret` base64-encoded in a `Basic` header and no subscription key at all.

## Standard authentication

Keys go in headers, the body is empty:

```bash
curl -X POST https://apitest.vipps.no/accesstoken/get \
-H 'client_id: YOUR-CLIENT-ID' \
-H 'client_secret: YOUR-CLIENT-SECRET' \
-H 'Ocp-Apim-Subscription-Key: YOUR-SUBSCRIPTION-KEY' \
-H 'Merchant-Serial-Number: YOUR-MSN' \
-H 'Vipps-System-Name: acme' \
-H 'Vipps-System-Version: 3.1.2' \
--data ''
```

```json
{
  "token_type": "Bearer",
  "expires_in": "86398",
  "expires_on": "1495271273",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1Ni <truncated>"
}
```

`expires_in` is seconds. `expires_on` is a Unix timestamp in UTC. Note that both come back as **strings**, not numbers,
so parse before you do arithmetic on them.

## Specialized authentication

A textbook OAuth 2.0 client credentials flow, so use an existing OAuth library rather than writing it by hand.

```bash
curl -X POST https://api.vipps.no/miami/v1/token \
-H 'Authorization: Basic <BASE64 OF client_id:client_secret>' \
-H 'Content-Type: application/x-www-form-urlencoded; charset=utf-8' \
--data-urlencode 'grant_type=client_credentials'
```

```json
{ "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1Ni <truncated>", "token_type": "Bearer", "expires_in": 900 }
```

Two ways to get this wrong, both of which return `invalid_client`:

- Omitting `grant_type=client_credentials`.
- Sending `Ocp-Apim-Subscription-Key`. This flow has no subscription key. Leave the header off entirely.

A `scope` may be added to the same form body when an API asks for one, for example
`grant_type=client_credentials&scope=donations:read`.

## Using the token

```text
Authorization: Bearer YOUR-ACCESS-TOKEN
```

**The word `Bearer` is required.** Omitting it gives HTTP 401, and it is the single most common cause of one. See
<https://developer.vippsmobilepay.com/docs/knowledge-base/errors.md#http-401-unauthorized>.

Standard-flow requests carry `Ocp-Apim-Subscription-Key` and `Merchant-Serial-Number` alongside the token.
Specialized-flow requests carry neither.

Send the four `Vipps-System-*` headers on the token request as well as on the API calls. They are optional in test but
they are how support finds a failing request in the logs.

## Cache the token

**Fetch a token per process, not per request.** A token is valid for its full lifetime, several may be held at once,
and they can be requested in advance. Hammering the token endpoint is the fastest way to get rate limited.

A cache that works for both flows:

1. Keep the token and its expiry in memory, shared across workers where you can.
2. Refresh when less than about 10% of the lifetime remains, or on a fixed margin such as 60 seconds for the standard
   flow. The 15-minute specialized token needs a proportionally tighter margin.
3. On an unexpected HTTP 401, discard the cached token, fetch once, and retry the call exactly once. Do not loop.
4. Never persist a token to disk or log it. It is a credential.

Clock skew on your server shortens the usable window, so trust `expires_in` over your own clock arithmetic where you
can.

## When it fails

| Symptom | Cause |
| ------- | ----- |
| HTTP 401 on an API call, token looks fine | `Bearer ` prefix missing from the `Authorization` header |
| HTTP 401 from the token endpoint | Wrong environment: test keys against `api.vipps.no`, or production keys against `apitest.vipps.no` |
| `invalid_client` from `/miami/v1/token` | `grant_type` missing, or `Ocp-Apim-Subscription-Key` sent |
| HTTP 401 with correct-looking keys | Keys from a different sales unit than the MSN you are sending |

Keys are per environment and per sales unit. Read all four values from configuration so the same code runs against
both.

If keys have been exposed, a merchant regenerates sales unit keys themselves in the business portal at
<https://portal.vippsmobilepay.com>; every other key type means
[contacting the partner team](https://developer.vippsmobilepay.com/docs/contact.md). See
<https://developer.vippsmobilepay.com/docs/knowledge-base/portal.md#how-to-regenerate-api-keys>.

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/access-token-api/README.md>,
<https://developer.vippsmobilepay.com/docs/APIs/access-token-api/standard-authentication.md>,
<https://developer.vippsmobilepay.com/docs/APIs/access-token-api/specialized-authentication.md>, spec at
`/api/access-token`.
