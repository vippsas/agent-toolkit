---
name: best-practices
description: >-
  Pick the right Vipps MobilePay API and add it to an existing system. Use when the user mentions Vipps, MobilePay,
  vippsmobilepay, apitest.vipps.no, ePayment, Recurring, Login, agreements, charges, MSN, sales unit,
  Ocp-Apim-Subscription-Key, or asks how to take payments, run subscriptions, or log users in with Vipps or MobilePay.
---

# Vipps MobilePay integrations

Vipps MobilePay is the wallet used by Vipps in Norway and MobilePay in Denmark and Finland. One API platform serves
both brands: same keys, same authentication, same error format.

This skill is the entry point. It answers "which API?" and gives the platform facts every integration needs. Then go
to the skill for the API you picked.

| Skill | Read it for |
| ----- | ----------- |
| `epayment` | One-time payments: web, app, in-store, QR, Express, capture, refund |
| `recurring` | Subscriptions and metered billing: agreements and charges, capture, refund |
| `login` | Identifying users, sign-up, profile data, customer club, point-of-sale login |
| `webhooks` | Real-time events and how to verify them. Needed by all three above |
| `test-and-go-live` | Test environment, test users, force approve, checklists for production |

Each is a sibling directory under `skills/` in this plugin, with deeper material in its `references/` folder. Read the
file, do not guess the contents.

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
| Accounting needs settlements, fees, payouts | **Report API** | Out of scope for this plugin |
| Accounting needs order lines and VAT | **Sales API** | Out of scope for this plugin |

Rules that decide the answer for you:

- **Check for a ready-made plugin first.** If the system is Shopify, WooCommerce, Magento, Shopware, PrestaShop,
  Drupal, Wix, WordPress, or Optimizely, an official plugin exists and no API code should be written. See
  <https://developer.vippsmobilepay.com/docs/plugins/>.
- **Recurring is not ePayment repeated.** Do not build subscriptions by storing a token and re-charging through
  ePayment. That is not supported. Use the Recurring API.
- **Login is not needed to get profile data during a purchase.** Profile sharing on the payment is fewer moving parts.
- **eCom API and Checkout API are legacy.** Never pick them for new work. Migrate to ePayment.
- One-time payments and subscriptions can share a sales unit, but Recurring needs its own product activation and extra
  compliance checks. Confirm the sales unit has Recurring before writing code against it.

## Step 2: platform facts

These hold for every API here.

**Servers.** Test `https://apitest.vipps.no`. Production `https://api.vipps.no`. Same hosts for all markets and both
brands. Separate credentials per environment. HTTPS with TLS 1.2 or higher.

**Credentials.** Keys belong to a *sales unit*, not to a company. A merchant with several sales units has several key
sets. Each set is:

- `client_id` and `client_secret`
- `Ocp-Apim-Subscription-Key`
- `merchantSerialNumber` (MSN), the sales unit's ID

Merchants find them in the business portal at <https://portal.vippsmobilepay.com>. Partners use partner keys, which
work in production only and make the `Merchant-Serial-Number` header mandatory.

**Access token.** Every call needs a Bearer token from the Access Token API. The keys go in headers, the body is empty:

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
   or web view, and do not try to detect whether the app is installed.
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
- Rendered API specifications: `/api/epayment`, `/api/recurring`, `/api/login`, `/api/access-token`, `/api/webhooks`
- Postman collections: <https://developer.vippsmobilepay.com/docs/knowledge-base/postman/>

When a detail is not in these skills, fetch the raw Markdown page rather than inventing a field name. The API rejects
unknown fields.

## What to ask the user before writing code

Ask only what changes the code, and ask it early:

- Which environment, and are the four key values available?
- One-time, recurring, or login? If payment: web, app, or physical point of sale?
- Which market and currency does the sales unit belong to?
- Are goods shipped later (reserve then capture) or delivered instantly (direct capture)?
- Is there a public HTTPS URL that can receive webhooks?

If the user cannot answer the environment question yet, build against test with the values read from configuration,
never hardcoded.
