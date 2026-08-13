---
name: test-and-go-live
description: >-
  Set up the Vipps MobilePay test environment and take an integration to production: test users, the Merchant Test app,
  force approve endpoints, amounts that trigger specific failures, environment differences, and the go-live checklists.
  Use when work involves apitest.vipps.no, test users, MT app, force approve, or moving an integration live.
---

# Test environment and going live

Read `../best-practices/SKILL.md` first for servers, keys, and access tokens.

Test and production are separate systems with separate credentials. Nothing carries across: not keys, not sales units,
not registered redirect URIs, not webhook registrations.

| | Test (MT) | Production |
| --- | --- | --- |
| API host | `https://apitest.vipps.no` | `https://api.vipps.no` |
| Access token life | 1 hour | 24 hours |
| App | Merchant Test app, `vippsMT://` scheme | Real app, `vipps://` |
| Users | Generated test users only | Real people |
| Partner keys | Not available. Partners get test sales unit keys | Available, and `Merchant-Serial-Number` is required |

## What you need to test

1. **A test sales unit.** Created automatically when a merchant orders a product that includes an API. Merchants can
   create as many as they like in the business portal; they cannot be modified afterwards. A test sales unit inherits
   the merchant's country, so a Norwegian merchant gets Norwegian units only.
2. **Sales unit API keys** for that unit, from the *For developers* section of the portal. Usually available within
   minutes.
3. **A test user**, which is a generated phone number plus a national identity number. Test users cannot be created in
   the app. Merchants create them in the portal under *For developers* then *Test users*; partners receive them by
   email. The test user must be in the same market and currency as the sales unit.
4. **The Merchant Test app** on a phone or tablet. iOS through TestFlight, Android through the Vipps MobilePay MT Google
   group plus Google Play. It installs next to the production app without conflict.

Never use a test phone number against production. Those numbers may belong to real people.

Available in test: Access Token, ePayment, Recurring, Login, Userinfo, Webhooks, QR, Checkout, eCom, PSP APIs.

## Skipping the app: force approve

For automated tests, both payment APIs can be approved without a human touching a phone. Test environment only, and both
require the test user to be properly registered in the test app first.

| API | Call | Body |
| --- | ---- | ---- |
| ePayment | `POST /epayment/v1/payments/{reference}/approve` | `{ "customer": { "phoneNumber": "4712345678" } }`, or `token` from the create response |
| Recurring | `PATCH /recurring/v3/agreements/{agreementId}/accept` | `{ "phoneNumber": "4712345678" }` |

Express payments cannot be force approved. If force approve returns HTTP 500, the test user's card has probably expired:
create a new test user.

## Amounts that trigger specific failures

Use these in test to exercise the unhappy paths on purpose. Values are minor units.

| Amount | Result |
| ------ | ------ |
| 151 | Insufficient funds |
| 182 | Refused by issuer |
| 183 | Suspected fraud |
| 184 | Withdrawal limit exceeded |
| 186 | Expired card |
| 187 | Invalid card |
| 197 | 3-D Secure denied, Norway only |
| 201 | Unknown result for 1 hour |
| 202 | Strong customer authentication required, Norway only |

Refunds:

| Amount | Result |
| ------ | ------ |
| 123 | Cannot refund: user deleted or has no receiving account |
| 124 | Refund period expired |

Test at least insufficient funds, expired card, an aborted payment, and an expired payment. Those are the states real
customers produce.

## What the test environment cannot do

Design your test plan around these gaps rather than debugging them:

- **Freestanding card payments** (`paymentMethod: CARD`) are not available.
- **No settlements**, so no settlement data from the Report API. Only production shows the money flow.
- **Email addresses cannot be verified** the normal way, and **gender** is not available through profile sharing or
  Login.
- **Partner keys do not work.** Partners use test sales unit keys.
- **There is no test business portal.**
- Push notifications are unstable. In the test app, tap *Payments* and pull to refresh to find a pending request. The
  activity list is empty and old payments cannot be found.
- Contactless payments are not supported.
- Support is office hours, Central European Time.

If a feature only exists in production, you can test there with real money. Use **2 NOK** or the equivalent, not 1,
because the lowest possible amount is given low priority in some payment systems. Expect production sales units to be
harder to configure than test ones, because of regulatory requirements.

## Local development

Webhooks need a public HTTPS URL, so a tunnel or a request inspection service is required. Callbacks arrive from
`callback-mt-1.vipps.no` and `callback-mt-2.vipps.no` in test, and from `callback-1` through `callback-4.vipps.no` plus
the `callback-dr-*` disaster recovery hosts in production. Allow the hostnames, never IP addresses.

Postman collections for each API, plus a shared environment file, are at
<https://developer.vippsmobilepay.com/docs/knowledge-base/postman.md>. Do not put production keys in a cloud-synced
Postman environment.

## Moving to production

The switch itself is small: new keys, new host, and any registration that lives on the sales unit repeated for the
production unit.

1. Get production keys from the business portal, once the merchant has passed customer control (know your customer,
   politically exposed persons, anti-money laundering).
2. Change the host and the four key values through configuration, not code.
3. Re-register **webhooks** against the production sales unit.
4. Re-register **Login redirect URIs** against the production sales unit, character for character.
5. Confirm the product is active on the production sales unit. Recurring, Express, `PUSH_MESSAGE`, long-living payments,
   unscheduled charges, and national identity number access each need their own approval, and each fails with a distinct
   error if missing.
6. Verify one real end-to-end payment: authorized, captured, refunded, and cancelled, checked through the API.
7. Subscribe to <https://status.vippsmobilepay.com/> for incidents and maintenance.

Partners have extra steps: submit the filled-in checklist to developer@vippsmobilepay.com with a video of the flow and a
short description, and fill in the production sign-up form. Request examples in a submitted checklist must be less than
a month old.

## The checklists are the requirement specification

Not optional reading. An integration is reviewed against these, and partners must submit one.

- ePayment: <https://developer.vippsmobilepay.com/docs/APIs/epayment-api/checklist.md>
- Recurring: <https://developer.vippsmobilepay.com/docs/APIs/recurring-api/recurring-api-checklist.md>
- Login: <https://developer.vippsmobilepay.com/docs/APIs/login-api/login-api-checklist.md>
- Partners: <https://developer.vippsmobilepay.com/docs/partner/partner-checklist.md>

The recurring themes across all of them:

1. Integrate **every** non-optional endpoint, including cancel and refund. A cancel path that was never built becomes an
   operational problem the day it is needed.
2. Webhooks **and** polling.
3. Handle every state and every error, and show errors to customers and to staff in language they can act on.
4. Log endpoint, headers, request body, error code, and message for every failure.
5. Send the `Vipps-System-*` headers. Mandatory for partners and platforms.
6. Add order details to payments, so customers recognize the charge in the app.
7. Set `customerInteraction: CUSTOMER_PRESENT` for in-store flows.
8. Handle redirects that come back to a different browser or session, and never depend on the redirect happening.
9. Capture before the deadline, and cancel reservations you will not capture.
10. Handle customers from other Nordic countries.
11. Follow the design guidelines for buttons and branding.
12. Build support tooling into **your** system. The business portal is not a customer support tool, and support staff
    cannot inspect individual charges for you.

Canonical pages: <https://developer.vippsmobilepay.com/docs/knowledge-base/test-environment.md>,
<https://developer.vippsmobilepay.com/docs/getting-started.md>
