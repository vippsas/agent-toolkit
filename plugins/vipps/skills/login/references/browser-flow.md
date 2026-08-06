# Login browser flow reference

OIDC authorization code flow, API version 2.0. Use a certified OpenID Connect library rather than writing this by hand.

## Endpoints

Discovery, which everything else comes from:

| Environment | URL |
| ----------- | --- |
| Test | `https://apitest.vipps.no/access-management-1.0/access/.well-known/openid-configuration` |
| Production | `https://api.vipps.no/access-management-1.0/access/.well-known/openid-configuration` |

Typical values in the response:

```json
{
  "issuer": "https://apitest.vipps.no/access-management-1.0/access/",
  "authorization_endpoint": "https://apitest.vipps.no/access-management-1.0/access/oauth2/auth",
  "token_endpoint": "https://apitest.vipps.no/access-management-1.0/access/oauth2/token",
  "userinfo_endpoint": "https://apitest.vipps.no/vipps-userinfo-api/userinfo",
  "jwks_uri": "https://apitest.vipps.no/access-management-1.0/access/.well-known/jwks.json",
  "revocation_endpoint": "https://apitest.vipps.no/access-management-1.0/access/oauth2/revoke",
  "backchannel_authentication_endpoint": "https://apitest.vipps.no/vipps-login-ciba/api/backchannel/authentication",
  "grant_types_supported": ["authorization_code", "client_credentials"],
  "code_challenge_methods_supported": ["S256"],
  "id_token_signing_alg_values_supported": ["RS256"],
  "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
  "scopes_supported": ["openid", "name", "phoneNumber", "nin", "address", "birthDate",
                       "delegatedConsents", "email", "gender"]
}
```

Cache the document. It sends `Cache-Control: max-age=3600` and rarely changes, but fetch it dynamically rather than
hardcoding paths.

## Authorize parameters

| Parameter | Required | Notes |
| --------- | -------- | ----- |
| `response_type` | Yes | Always `code` |
| `client_id` | Yes | Partners send the target sales unit's MSN instead |
| `redirect_uri` | Yes | Must match the portal entry exactly. Universal or app links preferred. A custom scheme needs a path: `myapp://path` |
| `scope` | Yes | Space separated, URL encoded. `openid` always included |
| `state` | Yes | Opaque, at least 8 characters, fresh per login. Too short and the user is bounced back with an error |
| `code_challenge`, `code_challenge_method` | No | PKCE. Set `S256`, because the default is `plain` |
| `requested_flow` | No | `app_to_app` or `app_to_app_v2` for mobile app flows |
| `app_callback_uri` | No | Where to switch back to your app. Needs `requested_flow` |
| `final_redirect_is_app` | No | `true` turns on compatibility features for returning to an app |
| `market` | No | `NO`, `DK`, `FI`, `SE`. Decides Vipps or MobilePay theming |
| `acr_values` | No | `urn:vipps:acr:app_auth` forces app confirmation even for a remembered browser. Advanced tier only, and the returned `acr` claim must be validated |

Success redirect: `?code=...&state=...&scope=...`. The `scope` returned always equals the scope requested, because the
user cannot deselect parts of it.

The code is single use and bound to the `client_id` and `redirect_uri`.

## Token call

Headers: `Content-Type: application/x-www-form-urlencoded` and `Authorization: Basic base64(client_id:client_secret)`.

Form body: `grant_type=authorization_code`, `code`, `redirect_uri`.

```json
{
  "access_token": "hel39XaKjGH5tkCvIENGPNbsSHz1DLKluOat4qP-A4...",
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6...",
  "expires_in": 3599,
  "scope": "openid",
  "token_type": "bearer"
}
```

- HTTP 401 means bad client credentials.
- The invalid-grant message covers several causes at once: a reused code, an expired code, and above all a
  `redirect_uri` that does not match. Check the URI character by character, including the trailing slash.
- No refresh tokens exist. When the token expires, run the flow again.
- `client_secret_post` can replace `client_secret_basic` per sales unit, set in the business portal.
- Validate `id_token` against `jwks_uri` with RS256, and check `iss`, `aud`, `exp`.

## Userinfo

`GET {userinfo_endpoint}` with `Authorization: Bearer {access_token}`. Nothing else. In particular, do not send
`Ocp-Apim-Subscription-Key`: userinfo sits outside that subscription and the call returns HTTP 401.

```json
{
  "sub": "126684df-c056-4625-821d-f2905febe3f9",
  "sid": "f2373816-439c-40e4-9882-afe7d79dd170",
  "name": "Test User",
  "given_name": "Test",
  "family_name": "User",
  "birthdate": "1955-05-18",
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

Address handling worth getting right:

- `address` is the user's default, `other_addresses` holds the rest, up to three in total. Fetch all of them and let the
  user pick the one that fits the context.
- Some users have no address at all. The `address` object is still returned, with empty strings in every field. Treat
  empty as absent.
- Extra unit or floor detail arrives inside `street_address` after a `\n`.

## Mobile app flows

Three options, all built on the same authorization code flow.

| Flow | Complexity | Automatic return to app | Third-party redirect URIs |
| ---- | ---------- | ----------------------- | ------------------------- |
| Simple app flow | Low | Yes | Limited |
| Website flow, used inside an app | Low | No | Yes |
| Advanced app flow | High | Yes | Yes |

Start with the simple app flow. Choose the website flow if your app cannot handle the redirect itself. Reach for the
advanced flow only when the redirect URI has to pass through a third party.

Never use a web view. Android: Custom Tabs, falling back to the external browser. iOS: `ASWebAuthenticationSession`, or
`SFAuthenticationSession` on iOS 11 and 12.

## Error handling

Errors arrive as query parameters on the redirect: `error`, `error_description`, `state`. Beyond the standard OAuth2 and
OIDC codes:

| `error_code` | Meaning |
| ------------ | ------- |
| `access_denied` | The user cancelled |
| `server_error` | Try again |
| `login_required` | Interactive login needed |
| `invalid_app_callback_uri` | Malformed app callback URI |
| `app_callback_uri_not_registered` | Not registered as a redirect URI |
| `outdated_app_version` | The user's app is too old |
| `wrong_challenge` | The user chose the wrong number in the browser confirmation step |
| `unknown_reject_reason` | Unknown rejection |

Undocumented codes will appear. Fail gracefully with a retry path instead of a stack trace. If the user cannot be
redirected at all, a branded error page is shown instead.

## Remembered users

The user can tick "Remember me in browser". Later logins then skip the app entirely, and skip the consent screen too if
consent was already given. To force app confirmation regardless, use `acr_values=urn:vipps:acr:app_auth` and
validate the `acr` claim in the returned ID token.

## Marketing consents

Add the `customFlow` scope (`delegatedConsents` is the legacy equivalent) to collect marketing consents alongside login.
Configure the texts in the business portal.

- The consent screen appears on the **first** login only, and the `delegatedConsents` object is present in userinfo only
  that first time. Persist it when you get it.
- Consents are remembered per user. Saving a new configuration in the portal can make previously consented users review
  the new terms.
- The object carries the heading, terms description, links, `timeOfConsent`, and a `consents` array of
  `{ id, accepted, required, textDisplayedToUser }`.

Full pages: <https://developer.vippsmobilepay.com/docs/APIs/login-api/api-guide/browser-flow-integration.md>,
<https://developer.vippsmobilepay.com/docs/APIs/login-api/api-guide/core-concepts.md>,
<https://developer.vippsmobilepay.com/docs/APIs/login-api/api-guide/collecting-consents.md>
