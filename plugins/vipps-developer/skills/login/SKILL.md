---
name: login
description: >-
  Add Vipps or MobilePay Login to a site, app, or point of sale: OpenID Connect authorization code flow, userinfo,
  scopes, sub, account linking, and merchant-initiated CIBA login. Use when work involves logging in or signing up with
  Vipps or MobilePay, /access-management-1.0/access/oauth2, /vipps-userinfo-api/userinfo, openid scopes, id_token, or
  customer club enrollment.
---

# Login API

Sign-in and sign-up with a verified Vipps or MobilePay identity, plus consented profile data: name, phone number,
email, address, birth date, and for approved merchants the national identity number. Every user has been through Know
Your Customer checks, so the data is real and verified.

Login is **not** an electronic ID and must not be used as one.

Read `../best-practices/SKILL.md` first for servers, keys, and access tokens. Note that Login uses its own OAuth token endpoint,
not the platform Access Token API.

## Pick the flow first

| Situation | Flow | Read |
| --------- | ---- | ---- |
| Website, or a mobile app that can accept a redirect | **Browser flow**: OIDC authorization code | `references/browser-flow.md` |
| Mobile app that needs automatic return | Simple app flow, `requested_flow=app_to_app_v2` | `references/browser-flow.md` |
| Point of sale, call center, vending machine, customer club sign-up | **Merchant-initiated (CIBA)**, keyed on phone number | `references/merchant-initiated.md` |
| You only need profile data during a payment or an agreement | Not Login. Use ePayment profile sharing or the Recurring `scope` field | `../epayment/references/features.md` |

Merchant-initiated login is **not allowed** on web pages or inside apps. Use the browser flow there.

## Before writing code

1. The sales unit must be set up for Login in the business portal, including the **exact** redirect URI. A trailing
   slash or a different encoding is a different URI and the token call will fail.
2. Scope availability depends on the merchant's product plan. The basic plan covers `name`, `phoneNumber`, `email`,
   `address`. Requesting a scope outside the plan does not fail the request: the scope is silently dropped. Check the
   *Login Configuration* page in the portal before promising a field.
3. Users must be at least 15 years old to use Login.
4. **Use a certified OpenID Connect library.** Do not hand-roll this. See <https://openid.net/developers/certified/>.
   Plugins exist for Magento, WordPress, and WooCommerce.

## The browser flow in four calls

### 1. Discover the endpoints, then cache them

```bash
curl -X GET https://apitest.vipps.no/access-management-1.0/access/.well-known/openid-configuration
```

Take `authorization_endpoint`, `token_endpoint`, `userinfo_endpoint`, `jwks_uri`, and
`backchannel_authentication_endpoint` from the response. The endpoint sends `Cache-Control: max-age=3600`; respect it.
Do not hardcode the paths, and do not fetch this on every login.

### 2. Send the user to the authorize endpoint

```text
https://apitest.vipps.no/access-management-1.0/access/oauth2/auth
  ?client_id=YOUR-CLIENT-ID
  &response_type=code
  &scope=openid%20name%20phoneNumber
  &state=A-RANDOM-VALUE
  &redirect_uri=https://example.com/callback
```

- `response_type` is always `code`.
- `state` is required, must be at least 8 characters, and must be fresh and random per login. Verify it on the way back.
- `redirect_uri` must match the portal entry exactly.
- Partners send the target sales unit's **MSN** in place of `client_id`.
- Add `code_challenge` and `code_challenge_method=S256` for PKCE. The default is `plain`, so set `S256` explicitly.
- Full-page redirect in the top-level browser window. **iframes are not supported**, and a new window is discouraged.
- In a native app, use Custom Tabs on Android and `ASWebAuthenticationSession` on iOS. Never a web view.

The user comes back to `redirect_uri?code=...&state=...&scope=...`, or with `error` and `error_description` if they
cancelled. Handle both, including error codes you have never seen.

### 3. Exchange the code for tokens

```bash
curl -X POST https://apitest.vipps.no/access-management-1.0/access/oauth2/token \
-H 'Content-Type: application/x-www-form-urlencoded' \
-H 'Authorization: Basic BASE64(client_id:client_secret)' \
--data-urlencode 'grant_type=authorization_code' \
--data-urlencode 'code=THE-CODE-FROM-THE-REDIRECT' \
--data-urlencode 'redirect_uri=https://example.com/callback'
```

The `redirect_uri` here must be byte-identical to the one used in step 2 and registered in the portal. Mismatch is the
most common failure, and the error text talks about an invalid grant rather than naming the real cause.

The default client authentication is `client_secret_basic`. `client_secret_post` can be switched on per sales unit in
the portal. Partners using partner keys send `Bearer` instead of `Basic`. There are **no refresh tokens**.

You get back `access_token`, `id_token`, `expires_in`, `scope`, and `token_type`. Validate the `id_token` signature
against `jwks_uri` (RS256) and check `iss`, `aud`, and expiry. A library does this for you.

### 4. Fetch the profile

```bash
curl -X GET https://apitest.vipps.no/vipps-userinfo-api/userinfo \
-H 'Authorization: Bearer YOUR-ACCESS-TOKEN'
```

Call it right after the token exchange: the access token is short-lived, documented as 10 minutes for userinfo. If you
get an unauthorized response, start the login again rather than trying to refresh.

You only receive the claims the user consented to.

## Scopes

`openid` is required, needs no consent, and yields `sub`. Everything else needs consent and is **all or nothing**: the
user accepts the whole list or none of it, and cannot deselect individual items. So request the minimum.

| Scope | Claim |
| ----- | ----- |
| `openid` | `sub` |
| `name` | `name`, `given_name`, `family_name`, verified |
| `phoneNumber` | `phone_number`, verified |
| `email` | `email`, always verified, so `email_verified` is always `true` |
| `address` | `address` plus `other_addresses`. Up to three: home, work, other |
| `birthDate` | `birthdate`, verified |
| `gender` | `gender`. Not available in the test environment |
| `nin` | National identity number. Not available in Norway. Requires application and legal justification |
| `customFlow` / `delegatedConsents` | Marketing consents. `customFlow` is the current one |
| `paymentSourceReferences` | Login Connect |

Space separated, URL encoded as `%20` in the authorize URL.

## `sub`: the identifier to store

`sub` is the stable user ID for one sales unit. Store it on the account the first time and use it to recognize the user
afterwards.

- Different sales units get different `sub` values for the same person. Do not mix a `sub` from one MSN with keys from
  another.
- It survives consent being revoked and given again.
- It changes only in rare cases, such as the user deleting their profile and creating a new one.
- Use the same sales unit for login, payment, and agreements so the `sub` stays consistent across them.

### Linking to existing accounts

The order that avoids both duplicate accounts and account takeover:

1. Look for a stored `sub`. Match, log in, done.
2. Otherwise match on verified phone number **and** email. Exactly one hit is required.
3. Sanity check the name against the existing account, so a recycled phone number or email cannot take over an old
   account.
4. On several matches, ask the user to log in the old way once and link from there.
5. Offer linking from account settings for users who already signed in another way.
6. If no account exists and one is required, explain that and say how to get one.

## Handle consent being revoked

Users revoke sharing in the app under *Profile* then *Personal information*, and they must consent again before the next
login. Subscribe to the revoke consent webhook (`CONSENT_REVOKED`, carrying the `sub`) if you want to react: prompt for
re-consent, offer another login method, or clean up stored data.

## Merchant-initiated login, in short

For a till or call center. Full detail in `references/merchant-initiated.md`.

1. `POST` to `backchannel_authentication_endpoint` with `scope` and `login_hint=urn:msisdn:4712345678`, plus optional
   `binding_message` matching `^[A-Z0-9\-]{5,8}$` shown on both devices.
2. Get `auth_req_id`, `expires_in`, and `interval`.
3. Poll `token_endpoint` with `grant_type=urn:openid:params:grant-type:ciba` and `auth_req_id`, never faster than
   `interval` seconds. `authorization_pending` means keep waiting. Or subscribe to
   `login.merchant-initiated.ping.v1` and skip the polling.
4. Use the access token against userinfo as usual.

## Common failures

| Symptom | Cause |
| ------- | ----- |
| Invalid grant on the token call | `redirect_uri` differs from the authorize call or the portal entry, or the code was reused. A code is single use |
| A requested scope is missing from the response | Not included in the merchant's product plan |
| `access_denied` on the redirect | The user cancelled. Not an error to log loudly |
| `outdated_app_version` | The user's app is too old for the flow |
| `wrong_challenge` | The user picked the wrong number in the browser confirmation step |
| HTTP 401 on userinfo | Token expired, over 10 minutes old, or sent without `Bearer` |
| HTTP 401 on userinfo after a Recurring agreement | `Ocp-Apim-Subscription-Key` was sent. Userinfo does not take it |
| Login works in test but not production | Different keys, and a redirect URI that has to be registered separately |

## Before calling it done

`state` is verified on return. The `id_token` is validated. Only necessary scopes are requested. `sub` is stored and
used for linking. Cancellation and error redirects are handled. Buttons follow the brand guidelines at
<https://brand.vippsmobilepay.com/document/61#/branding/online/buttons>, or use the button generator at
<https://developer.vippsmobilepay.com/docs/knowledge-base/buttons.md>.

Full requirement list: <https://developer.vippsmobilepay.com/docs/APIs/login-api/login-api-checklist.md>

## Deeper reference

- `references/browser-flow.md` — every parameter, mobile app flows, error codes, marketing consents
- `references/merchant-initiated.md` — CIBA in full, including redirect-to-browser and webhook alternatives

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/login-api/login-api-quick-start.md>,
<https://developer.vippsmobilepay.com/docs/APIs/login-api/api-guide/user-info.md>, spec at `/api/login`.
