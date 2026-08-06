# Merchant-initiated login (CIBA)

The merchant's system starts the login from the customer's phone number. The customer confirms in the Vipps or
MobilePay app. Built on the OpenID Client-Initiated Backchannel Authentication standard.

Use it for tills, call centers, vending machines, and customer club sign-up at a counter. **Not allowed on web pages or
inside apps** — use the browser flow there. Available to all Login-enabled sales units.

If the customer has push notifications turned off, they have to open the app themselves and pull to refresh before the
request appears. Say so out loud to the person at the counter.

## Variant 1: finish in the app

Everything happens on the phone. Best when the till only needs the result.

### Step 1: authenticate

```text
POST {backchannel_authentication_endpoint}
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

scope=openid name address&login_hint=urn:msisdn:4712345678&binding_message=4MZ-CQ3
```

```json
{ "auth_req_id": "VYGaaAMRkI6SyAm_uIywhxsN2K0", "expires_in": 600, "interval": 5 }
```

| Parameter | Required | Notes |
| --------- | -------- | ----- |
| `login_hint` | Yes | `urn:msisdn:{msisdn}` for a phone number, or `urn:customer-token:{token}` from a QR check-in |
| `scope` | Yes | Same scopes as the browser flow. The legacy `nnin` is not supported: use `nin` |
| `binding_message` | No | Shown on both devices so the customer knows it is the right login. `^[A-Z0-9\-]{5,8}$` |
| `requested_expiry` | No | Seconds the request stays valid. Minimum 60, maximum 900, default around 10 to 15 minutes |

`interval` is the minimum seconds between polls. Respect it.

### Step 2: get the tokens

Either poll, or wait for a webhook.

```text
POST {token_endpoint}
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

grant_type=urn%3Aopenid%3Aparams%3Agrant-type%3Aciba&auth_req_id=VYGaaAMRkI6SyAm_uIywhxsN2K0
```

While the customer has not acted:

```json
{ "error": "authorization_pending", "error_description": "The authorization request is still pending" }
```

Keep polling on `authorization_pending`, no faster than `interval`. Long polling is not supported. On success you get
`access_token`, `token_type`, `expires_in`, and `id_token`.

### Step 3: userinfo

`GET {userinfo_endpoint}` with `Authorization: Bearer {access_token}`. Nothing else, and no
`Ocp-Apim-Subscription-Key`.

## Variant 2: redirect to browser

The customer confirms in the app and their phone then opens your web page, so you can collect more information, show
offers, accept terms, or continue into a purchase or an agreement.

Same authentication request plus two parameters:

```text
requested_flow=login_to_webpage&scope=openid name address&login_hint=urn:msisdn:4712345678
&redirect_uri=https://merchant.example.com/callback
```

`redirect_uri` must be `https` in production. The customer's browser lands on `{redirect_uri}?code={code}`. Exchange it
with a **different grant type**:

```text
POST {token_endpoint}
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

code=some-valid-code&grant_type=urn:vipps:params:grant-type:ciba-redirect
```

You **must** validate that the returned `id_token` carries the same `auth_req_id` you got in step 1. That is what ties
the browser session to the login you started, and skipping it is a security hole. Validate the JWS as usual; this token
may be signed with ES256.

The token endpoint may be called only **once** per authentication. So do not combine this variant with the webhook: an
exchange triggered by the webhook consumes the one exchange the browser redirect needed.

## Webhooks instead of polling

Register `login.merchant-initiated.ping.v1` (see `../../webhooks/SKILL.md`). Payload:

```json
{ "auth_req_id": "qwieuhwqiuhdiuwqh123" }
```

Order of operations: subscribe, start the authentication, the customer confirms, you receive the ping, then you call the
token endpoint. Up to 25 registrations per event type per MSN.

Supported for the finish-in-the-app variant only, for the single-exchange reason above.

## Check whether a user exists first

Avoid starting a login for someone who cannot complete it.

```text
POST https://api.vipps.no/vipps-login-ciba/api/v1/user-exists
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

login_hint=urn:msisdn:4712345678
```

```json
{ "exists": true }
```

Useful at a counter, where a failed login is an awkward silence rather than a log line.

## Error responses

Standard CIBA errors, plus:

| Response | Meaning | Handling |
| -------- | ------- | -------- |
| HTTP 429 | Too many logins started for the same user at once | Respect the `Retry-After` header |
| `error_code=old_app` | The customer's app is too old for this flow | Ask them to update, or fall back to another method |
| `error_code=invalid_user` | No account, inactive account, or not eligible, for example under 15 | Do not retry. Offer another route |

## Texts shown to the customer

The wording in the app is configured per sales unit in the business portal, not in the API. Options:

- *Join customer club*
- *Share information*
- *Confirm information*

Pick the one that matches what actually happens, so the consent screen is honest.

## Marketing consents

Add the `delegatedConsents` scope (see also `customFlow`) to the backchannel authentication request to collect the
merchant's configured consents in the same approval. The userinfo response then carries what the customer accepted or
declined. Configure the texts in the portal first.

Full pages:
<https://developer.vippsmobilepay.com/docs/APIs/login-api/api-guide/merchant-initiated-login-integration.md>,
<https://developer.vippsmobilepay.com/docs/APIs/login-api/how-it-works/merchant-initiated-login-howitworks.md>
