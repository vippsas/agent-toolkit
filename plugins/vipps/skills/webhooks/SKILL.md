---
name: webhooks
description: >-
  Register and verify Vipps MobilePay webhooks so a system learns about payment, agreement, charge, and login events in
  real time. Use when work involves /webhooks/v1/webhooks, epayments.payment.*.v1, recurring.charge-*.v1, HMAC-SHA256
  signature verification, x-ms-content-sha256, callback URLs, or a missing or duplicated event notification.
---

# Webhooks API

One registration endpoint for events from ePayment, Recurring, Login, QR, and Donations. Base path `/webhooks/v1`.

Read `../best-practices/SKILL.md` first for servers, keys, and access tokens.

**Webhooks are half of a status integration, never the whole of it.** Register them and poll as a fallback. A checklist
review will fail an integration that has only one of the two.

## 1. Register the webhook

```bash
curl -X POST https://apitest.vipps.no/webhooks/v1/webhooks \
-H "Authorization: Bearer YOUR-ACCESS-TOKEN" \
-H "Ocp-Apim-Subscription-Key: YOUR-SUBSCRIPTION-KEY" \
-H "Merchant-Serial-Number: YOUR-MSN" \
--data '{
    "url": "https://example.com/hooks/vipps",
    "events": ["epayments.payment.authorized.v1", "epayments.payment.captured.v1"]
}'
```

```json
{ "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08", "secret": "090a478d-37ff-4e77-970e-d457aeb26a3a" }
```

**Store the `secret` now.** It is shown once, and it is the only way to verify that a delivery is genuine. If it is
lost, delete the registration and create a new one.

Registration is a one-off setup step, not something to do per payment. Do it from a deployment script or an admin
action, and keep the `id` so you can delete it later.

| Operation | Call |
| --------- | ---- |
| List registrations | `GET /webhooks/v1/webhooks` |
| Delete a registration | `DELETE /webhooks/v1/webhooks/{id}` |

Limits: 25 registrations per event type per MSN, except QR, which allows 1. Partners can register with partner keys and
no `Merchant-Serial-Number` to cover every sales unit they manage, including future ones, against an independent quota.

## 2. Verify every delivery

A delivery is an HTTP POST to your URL with these headers:

```text
x-ms-date: Thu, 30 Mar 2023 08:38:32 GMT
x-ms-content-sha256: lNlsp1XA03N34HrQsVzPgJKtC+r7l/RBF4V3JQUWMj4=
Authorization: HMAC-SHA256 SignedHeaders=x-ms-date;host;x-ms-content-sha256&Signature=agAiSyogQbDHpeuc...
```

Two checks, in this order, before you touch the body as data:

1. SHA-256 the raw request body, base64 encode it, and compare with `x-ms-content-sha256`.
2. Build the string to sign and HMAC-SHA256 it with your `secret`, base64 encode, and compare with the `Signature` part
   of the `Authorization` header.

The string to sign is:

```text
POST\n{pathAndQuery}\n{x-ms-date};{host};{x-ms-content-sha256}
```

`\n`, not `\r\n`. `pathAndQuery` and `host` come from the URL you registered.

```js
const crypto = require('crypto');

function verify(secret, method, pathAndQuery, headers, rawBody) {
  const contentHash = crypto.createHash('sha256').update(rawBody).digest('base64');
  if (contentHash !== headers['x-ms-content-sha256']) return false;

  const stringToSign =
    `${method}\n` +
    `${pathAndQuery}\n` +
    `${headers['x-ms-date']};${headers['host']};${headers['x-ms-content-sha256']}`;

  const signature = crypto.createHmac('sha256', secret).update(stringToSign).digest('base64');
  const expected = `HMAC-SHA256 SignedHeaders=x-ms-date;host;x-ms-content-sha256&Signature=${signature}`;

  return expected === headers['authorization'];
}
```

Use the **raw** body bytes. A framework that parses and re-serializes JSON for you will change the hash and every
verification will fail. Compare with a constant-time comparison where your language offers one.

## 3. Answer correctly

Respond `HTTP 200 OK` as soon as the event is stored. Do the work afterwards, out of band.

What happens otherwise:

- Any 4xx or 5xx response, or no response within **10 seconds**, counts as a failure and is retried.
- Retries back off for up to 7 days: about every 2 seconds for the first four attempts, then 60 seconds, then 120
  seconds, then hourly through attempt 29, then daily. Do not build logic that depends on this timing.
- **Delivery order is preserved per registration.** A failure blocks later events for the same payment. Reject the
  `AUTHORIZED` event and the `CAPTURED` event will not arrive until a retry of `AUTHORIZED` succeeds. Slow or flaky
  handlers therefore stall your own pipeline.
- A registration whose endpoint is unresponsive for **2 weeks** is deleted automatically. Re-register after an outage.

Handlers must be **idempotent**. Retries and overlapping registrations mean the same event can arrive more than once.
Key on `reference` plus `name` for payments, or on the charge and agreement identifiers, and make repeats no-ops.

## 4. Read the payload

ePayment, and the same shape for every ePayment event with only `name` changing:

```json
{
  "msn": "123456",
  "reference": "acme-shop-123-order123abc",
  "pspReference": "dd8e0a8e-2b26-40ed-98f1-1d5832fc129f",
  "name": "AUTHORIZED",
  "amount": { "currency": "NOK", "value": 49900 },
  "timestamp": "2026-01-19T16:26:32.099Z",
  "idempotencyKey": "7c8b81e7-b08b-46e4-9729-191cb801c132",
  "success": true
}
```

- Check `success`. A delivered event is not automatically a successful operation.
- `idempotencyKey` is not always present, for example on `CANCELLED`.
- `pspReference` here is the event's, which differs from the one in API responses. That is by design.
- With profile sharing, `userDetails` and `profile.sub` ride along on `epayments.payment.authorized.v1`.
- Each API sets its own payload shape. Check the event page for Recurring, Login, and QR rather than assuming this one.

Treat the payload as a signal, not as the truth. For anything that moves money, read the resource back:
`GET /epayment/v1/payments/{reference}` or the charge endpoint.

## Event types

**ePayment**: `epayments.payment.created.v1`, `.aborted.v1`, `.expired.v1`, `.cancelled.v1`, `.captured.v1`,
`.refunded.v1`, `.authorized.v1`, `.terminated.v1`. Only for payments created through the ePayment API.

**Recurring**: `recurring.agreement-activated.v1`, `-rejected.v1`, `-stopped.v1`, `-expired.v1`,
`recurring.charge-reserved.v1`, `-captured.v1`, `-canceled.v1`, `-refunded.v1`, `-failed.v1`,
`-creation-failed.v1`. Note the single "l" in `charge-canceled`.

**Login**: `login.merchant-initiated.ping.v1`, carrying `auth_req_id`. Plus revoke consent webhooks, which report a
`sub` whose consent was withdrawn.

**QR**: `user.checked-in.v1`, one registration only.

Full list: <https://developer.vippsmobilepay.com/docs/APIs/webhooks-api/events.md>

## Which events to subscribe to

Minimum useful sets:

- Checkout: `authorized`, `aborted`, `expired`, plus `captured` and `refunded` if a back office needs them.
- Subscriptions: `agreement-activated`, `agreement-stopped` (mandatory: customers cancel in the app),
  `charge-captured` or `charge-reserved`, `charge-failed`, and `charge-creation-failed` if you create charges in bulk.
- Point-of-sale login: `login.merchant-initiated.ping.v1` instead of polling the token endpoint.

## Practical requirements for the endpoint

- Public HTTPS, reachable from the internet. `localhost` will not work. In development, use a tunnel or a request
  inspection service.
- Allow the source hosts in your firewall: `callback-1.vipps.no` through `callback-4.vipps.no`,
  `callback-dr-1.vipps.no` through `callback-dr-4.vipps.no` (disaster recovery, as important as production), and
  `callback-mt-1.vipps.no` and `callback-mt-2.vipps.no` for test. Use the hostnames, not IP addresses.
- One path per environment, and separate registrations per environment. Test and production are separate systems.
- No authentication of your own on the path that would reject our POST. The HMAC is the authentication.

## Debugging a missing event

1. `GET /webhooks/v1/webhooks` — is the registration still there, or was it auto-deleted after an outage?
2. The business portal, *For developers* then *Webhooks* and *Webhook errors*, shows the status codes we got from your
   endpoint. That is the fastest answer to "did it even try?".
3. Is an earlier event for the same payment stuck failing and blocking the queue?
4. Is your handler returning 200 within 10 seconds?
5. Are you verifying against the raw body, and against the right secret for that registration?
6. Meanwhile, poll. A payment status is never unknowable.

## Switching endpoints without losing events

Register the new webhook, verify it in production traffic, then delete the old one. Keep the overlap short and be ready
for duplicates during it. There is no way to pause deliveries.

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/webhooks-api/api-guide.md>,
<https://developer.vippsmobilepay.com/docs/APIs/webhooks-api/request-authentication.md>, spec at `/api/webhooks`.
