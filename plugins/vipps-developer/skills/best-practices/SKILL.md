---
name: best-practices
description: >-
  Pick the right Vipps MobilePay API and add it to an existing system. Use when the user mentions Vipps, MobilePay,
  vippsmobilepay, apitest.vipps.no, ePayment, Recurring, Login, agreements, charges, MSN, sales unit,
  Ocp-Apim-Subscription-Key, or asks how to take payments, run subscriptions, log users in, show QR codes, collect
  donations, or pull settlement and sales reports with Vipps or MobilePay.
---

# Vipps MobilePay integrations

Vipps MobilePay is the wallet used by Vipps in Norway and MobilePay in Denmark and Finland. One API platform serves
both brands: same keys, same authentication, same error format.

This skill is the entry point. It answers "which API?" and gives the platform facts every integration needs. Then go
to the skill for the API you picked.

Payments and identity:

| Skill | Read it for |
| ----- | ----------- |
| `epayment` | One-time payments: web, app, in-store, QR, Express, capture, refund |
| `recurring` | Subscriptions and metered billing: agreements and charges, capture, refund |
| `login` | Identifying users, sign-up, profile data, customer club, point-of-sale login |
| `webhooks` | Real-time events and how to verify them. Needed by all three above |
| `widget-sdk` | The web front end for a payment or a sign-up: payment button, desktop dialog, app-switch |
| `payment-lifecycle` | Capture deadlines, cancel, refund, timeouts, and `orderId`/`reference` rules shared by ePayment and Recurring |
| `test-and-go-live` | Test environment, test users, force approve, checklists for production |
| `psp` | Card passthrough for Payment Service Providers acting on behalf of merchants, for payments and subscriptions |

Used alongside a payment:

| Skill | Read it for |
| ----- | ----------- |
| `access-token` | Both token flows, which keys use which, caching, and the HTTP 401 that starts every integration |
| `qr` | QR at a physical point of sale: which of the four flows to use, and the printed redirect and callback codes |
| `userinfo` | The customer's full profile, when the payment or agreement response does not already carry enough |
| `order-management` | Putting a receipt, order lines, and a link into the customer's app after they paid |

Money out and administration:

| Skill | Read it for |
| ----- | ----------- |
| `settlement` | How captured payments become a bank transfer: frequency, timing, net versus gross, and what to match on |
| `report` | The API behind it: ledgers, entry types, feeds and paging, and pulling the settlement data |
| `sales` | Order lines and VAT for Vippsnummer and mPOS, for accounting partners. Pairs with `report` |
| `donations` | Donation payment reports, recurring donation agreements, donation links and QR codes |
| `management` | Looking up merchants and sales units, and prefilling a product order to onboard a merchant |

Each is a sibling directory under `skills/` in this plugin, with deeper material in its `references/` folder. Read the
file, do not guess the contents.

## Important! Keep generated code secure

You do not automatically know which parts of the code you write end up in a customer's browser or in a public
repository. Apply these rules so a quick prototype does not turn into a leaked credential:

- Never put Vipps MobilePay secrets in frontend or browser code.
- Never write production credentials into a prompt, file, or tool call.
- Never commit `.env` files or credentials to GitHub.
- Authenticate and authorize the backend endpoints you write.
- Be careful what you log. Debug code can log full API requests or responses. Those logs can accidentally contain
  access tokens, authorization headers, or customer data, and may end up stored in hosting or monitoring tools.
- Use test credentials while building.
- If a secret has been exposed, [rotate it](https://developer.vippsmobilepay.com/docs/knowledge-base/api-keys.md#production-and-test-keys).


## Step 1: pick the API

Start from what the user wants to happen, not from the product name.

| The user wants | Use | Notes |
| -------------- | --- | ----- |
| Customer pays once, on a website or in an app | **ePayment API** | The default. `userFlow: WEB_REDIRECT` |
| Customer pays at a till, vending machine, or scans a QR | **ePayment API** | Set `customerInteraction: CUSTOMER_PRESENT` |
| Customer pays now and their name, address, email is needed | **ePayment API** with Express or profile sharing | No separate login flow needed |
| Customer is billed on a schedule: subscription, membership, rent | **Recurring API** | Agreement first, then one charge per payment |
| Customer is billed per use, amount unknown up front | **Recurring API** with `VARIABLE` or `FLEXIBLE` pricing | |
| Customer signs up or logs in with their wallet identity | **Login API** | OIDC authorization code flow |
| Staff enrolls a customer in a club from a till or call center | **Login API**, merchant-initiated (CIBA) | Not allowed in browsers or apps |
| The system needs status updates without polling hard | **Webhooks API** | Always in addition to polling, never instead |
| I am a PSP integrating card passthrough for my merchants | **ePayment PSP API** or **Recurring PSP API** | See the `psp` skill |
| Customer scans, or is scanned, at a physical point of sale | **ePayment API** | One-time payment QR and personal QR are built in. See the `qr` skill |
| A printed QR code: poster, sticker, vending machine | **QR API** | Merchant redirect and merchant callback codes. See the `qr` skill |
| A payment needs the customer's profile in more detail than `userDetails` carries | **Userinfo API** | See the `userinfo` skill. Profile sharing on the payment, not a login |
| The app should show a receipt or a tracking link after paying | **Order Management API** | See the `order-management` skill. ePayment writes receipts itself, but cannot read them back |
| Customer makes a single or recurring donation | **Donations API** | See the `donations` skill |
| Accounting needs settlements, fees, payouts | **Report API** | See the `report` skill, and `settlement` for how payouts work |
| "When do we get the money?", or a bank transfer that needs explaining | No API call | See the `settlement` skill |
| Accounting needs order lines and VAT | **Sales API** | See the `sales` skill. Vippsnummer and mPOS only |
| Onboarding merchants, or looking up their sales units | **Management API** | See the `management` skill |

Rules that decide the answer for you:

- **Check for a ready-made plugin first.** If the system is Shopify, WooCommerce, Magento, Shopware, PrestaShop,
  Drupal, Wix, WordPress, or Optimizely, an official plugin exists and no API code should be written. See
  <https://developer.vippsmobilepay.com/docs/plugins/README.md>.
- **Recurring is not ePayment repeated.** Do not build subscriptions by storing a token and re-charging through
  ePayment. That is not supported. Use the Recurring API.
- **Login is not needed to get profile data during a purchase.** Profile sharing on the payment is fewer moving parts.
  See "Getting the customer's profile" below.
- **eCom API and Checkout API are legacy.** Never pick them for new work. Migrate to ePayment.
- One-time payments and subscriptions can share a sales unit, but Recurring needs its own product activation and extra
  compliance checks. Confirm the sales unit has Recurring before writing code against it.

### Getting the customer's profile

Name, address, email, phone number, and birth date are always **consented to as part of something else**: a payment, an
agreement, or a log-in. You never ask for a profile on its own. Where you then read it depends on which of those three
the consent came from, and the three are not interchangeable:

| Consent came from | Ask with | Read the profile from | Authorized with |
| ----------------- | -------- | --------------------- | --------------- |
| An **ePayment** payment | `profile.scope` on `createPayment` | `userDetails` on `GET /epayment/v1/payments/{reference}`, and on the `epayments.payment.authorized.v1` webhook | Your merchant access token |
| A **Recurring** agreement, or a legacy **eCom** payment | `scope` on the draft agreement or payment | `GET /vipps-userinfo-api/userinfo/{sub}`, with the `sub` the agreement or payment returns | Your merchant access token |
| A **Login** session | Profile scopes on the authorize URL | `GET /vipps-userinfo-api/userinfo/`, **no `sub`** | The **user's** access token from the OIDC flow |

Two traps live in that table:

- **The last two rows are different endpoints**, despite the shared path prefix. One takes a `sub` and your merchant
  token; the other takes neither. Sending a merchant token to the Login endpoint, or a `sub` to it, does not work.
  A stray `Ocp-Apim-Subscription-Key` on either is an HTTP 401.
- **Row one needs no Userinfo call at all.** ePayment hands you `userDetails` directly. Only go to
  `GET /vipps-userinfo-api/userinfo/{sub}` from a payment when you need something `userDetails` does not carry: `nin`,
  the `email_verified` and `phone_number_verified` flags, the `formatted` address string, or `other_addresses`.

Scopes and consent rules are shared across all three, including the 7-day window and the all-or-nothing consent screen.
`gender` is Login only. See `userinfo/SKILL.md` for the fields and `login/SKILL.md` for the flow.

## Step 2: platform facts

These hold for every API here.

**Servers.** Test `https://apitest.vipps.no`. Production `https://api.vipps.no`. Same hosts for all markets and both
brands. Separate credentials per environment. HTTPS with TLS 1.2 or higher.

**Credentials, or API keys.** *API keys* is the docs' umbrella term for every credential type: sales unit keys (the
normal case, below), partner keys, and specialty keys for accounting and Donations. This section covers sales
unit keys and partner keys, the ones ePayment, Recurring, Login, and Webhooks use. If a key doesn't match the
shape below, it is one of the other types: see `access-token/SKILL.md` and
<https://developer.vippsmobilepay.com/docs/knowledge-base/api-keys.md>.

Keys belong to a *sales unit*, not to a company. A merchant with several sales units has several key sets. Each
set is:

- `client_id` and `client_secret`
- `Ocp-Apim-Subscription-Key` (a primary and a secondary, interchangeable, so one can be rotated without downtime)
- `merchantSerialNumber` (MSN) — not itself an API key, but required on most requests, and the sales unit's ID

Merchants find them in the business portal at <https://portal.vippsmobilepay.com>. Partners use partner keys, which
work in production only and make the `Merchant-Serial-Number` header mandatory, since one partner key set can act on
behalf of many merchants.

**Access token.** Every call needs a Bearer token, exchanged for the key values above through the Access Token
API's *standard authentication* flow (the one sales unit keys and partner keys use). The keys go in headers, the
body is empty:

```bash
curl -X POST 'https://apitest.vipps.no/accesstoken/get' \
-H 'client_id: YOUR-CLIENT-ID' \
-H 'client_secret: YOUR-CLIENT-SECRET' \
-H 'Ocp-Apim-Subscription-Key: YOUR-SUBSCRIPTION-KEY' \
-H 'Merchant-Serial-Number: YOUR-MSN' \
--data ''
```

The response carries `access_token` and `expires_in`, the validity period in seconds. The token is valid for 1 hour
in test and 24 hours in production. Cache it and reuse it for its full life. Do not fetch a token per request.
Multiple valid tokens may be held at once.

Accounting keys and Donations merchant-level keys use a different, *specialized authentication* flow with only
`client_id` and `client_secret`, no `Ocp-Apim-Subscription-Key`, and a 15-minute token. See `access-token/SKILL.md`
for both flows side by side.

**Headers.** Send these on API calls:

```text
Authorization: Bearer YOUR-ACCESS-TOKEN
Ocp-Apim-Subscription-Key: YOUR-SUBSCRIPTION-KEY
Merchant-Serial-Number: YOUR-MSN
Idempotency-Key: YOUR-IDEMPOTENCY-KEY
Content-Type: application/json
Vipps-System-Name: acme
Vipps-System-Version: 3.1.2
Vipps-System-Plugin-Name: acme-webshop
Vipps-System-Plugin-Version: 4.5.6
```

- The word `Bearer` is required. Omitting it gives HTTP 401.
- `Idempotency-Key` goes on anything that creates or changes state. Derive it from your own order or charge ID so a
  retry sends the same value. Reusing a key with a different body gives HTTP 409. A 4xx response stays 4xx for that
  key, so do not retry a rejected request with the same key.
- The four `Vipps-System-*` headers are required for partners and platform plugins, recommended for everyone, and
  capped at 30 characters each. They are how support traces a failing request.

**Amounts.** Always integers in minor units: øre for NOK and DKK, cents for EUR. `49900` is 499.00 NOK. Decimals are
rejected. Minimum per payment is NOK 100 øre, DKK 1 øre, EUR 1 cent. The currency must match the sales unit's market;
a Danish sales unit charges DKK.

**Phone numbers.** MSISDN format, country code plus subscriber number, no `+` and no spaces: `4712345678`.

## Step 3: rules that keep the integration from breaking

Apply these without being asked. Each one maps to a real failure mode.

1. **All API calls go server side.** `client_secret` and `Ocp-Apim-Subscription-Key` never reach a browser or a mobile
   binary.
2. **Use webhooks and polling.** Webhooks are faster, polling is the fallback when one is delayed. Shipping only one
   of the two is an incomplete integration and will fail review. Poll from 5 seconds after the request, then every 2
   seconds, and back off on HTTP 429.
3. **Never trust the redirect back to your site.** The user may land in a different browser, a different session, or
   never return. Treat the API status as the truth and the redirect as a convenience.
4. **Open the returned `redirectUrl` or `vippsConfirmationUrl` as-is.** Do not modify it, do not wrap it in an iframe
   or web view, and do not try to detect whether the app is installed. On the web, hand the payment or agreement URL to
   the Widget SDK instead of writing this yourself: it renders the brand-correct button, app-switches on mobile, and
   opens a Vipps MobilePay hosted desktop dialog so the customer keeps the page. See `widget-sdk/SKILL.md`. Login
   authorization URLs are not in scope for it and always open top-level.
5. **Store your own reference.** Keep the payment `reference`, `agreementId`, and `chargeId` next to your order row.
   Every support question starts there.
6. **Handle every state, including the unhappy ones.** Aborted, expired, and failed are normal outcomes, not edge
   cases.
7. **Log endpoint, headers, request body, and the full error response.** Errors follow RFC 7807 and carry a `traceId`
   plus an `extraDetails` array. Without them nobody can help.
8. **Show errors to a human.** Both the customer and the merchant's staff need to see what went wrong.
9. **Currency, amounts, and cross-border.** Nordic users pay across borders, so a Norwegian shop will see Danish and
   Finnish customers. Do not assume the customer's country.

## Where the authoritative documentation lives

Every documentation page ships as raw Markdown for agents. Fetch these instead of guessing:

- Index of every page: <https://developer.vippsmobilepay.com/llms.txt>
- Any page as Markdown: append `.md` to the doc path, for example
  <https://developer.vippsmobilepay.com/docs/APIs/epayment-api/quick-start.md>
- Rendered API specifications: `/api/epayment`, `/api/recurring`, `/api/login`, `/api/access-token`, `/api/webhooks`,
  `/api/qr`, `/api/userinfo`, `/api/order-management`, `/api/management`, `/api/report`, `/api/sales`,
  `/api/donations`
- Full list of APIs, including ones not covered by these skills (Agentic commerce, which is still under development,
  and the legacy Checkout and eCom APIs): <https://developer.vippsmobilepay.com/docs/APIs/README.md>
- Becoming a partner, partner keys, and partner onboarding questions, which these skills do not cover:
  <https://developer.vippsmobilepay.com/docs/partner/README.md>

When a detail is not in these skills, fetch the raw Markdown page rather than inventing a field name. The API rejects
unknown fields.

These skills can be wrong or out of date. Verify anything that looks off against the pages above, and report the
mistake at <https://github.com/vippsas/agent-toolkit/issues>.

## What to ask the user before writing code

Ask only what changes the code, and ask it early:

- Which environment, and are the four key values available?
- One-time, recurring, or login? If payment: web, app, or physical point of sale?
- Which market and currency does the sales unit belong to?
- Are goods shipped later (reserve then capture) or delivered instantly (direct capture)?
- Is there a public HTTPS URL that can receive webhooks?

If the user cannot answer the environment question yet, build against test with the values read from configuration,
never hardcoded.
