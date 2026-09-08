# Recurring agreements

Base path `/recurring/v3`. Every request that creates or changes something needs `Idempotency-Key`.

| Operation | Method and path |
| --------- | --------------- |
| List agreements | `GET /agreements` |
| Draft an agreement | `POST /agreements` |
| Get an agreement | `GET /agreements/{agreementId}` |
| Update or stop an agreement | `PATCH /agreements/{agreementId}` |
| Force accept, test only | `PATCH /agreements/{agreementId}/accept` |

`GET /agreements` supports `pageNumber` and `pageSize`.

## Draft request fields

| Field | Required | Notes |
| ----- | -------- | ----- |
| `pricing` | Yes | `{ type, amount \| suggestedMaxAmount, currency }` |
| `interval` | Usually | `{ unit: DAY\|WEEK\|MONTH\|YEAR, count: 1-31 }`. Omit for pay-per-use |
| `merchantRedirectUrl` | Yes | Where the customer lands after approving or rejecting |
| `merchantAgreementUrl` | Yes | Your agreement management page for this agreement |
| `productName` | Yes | The agreement name in the app |
| `productDescription` | No | Detail line in the app |
| `phoneNumber` | No | Prefills the landing page. MSISDN |
| `initialCharge` | No | Bills at activation. See below |
| `campaign` | No | Introductory price. See below |
| `scope` | No | Userinfo scopes to request at the same time. See below |
| `isApp` | No | Forces a `vipps://` URL. Strongly discouraged |

Response: `agreementId` and `vippsConfirmationUrl`.

## Agreement statuses

`PENDING` for 10 minutes, then `ACTIVE`, `STOPPED`, or `EXPIRED`. `EXPIRED` also happens when a `DIRECT_CAPTURE`
initial charge fails to process. `STOPPED` is permanent.

Example `GET` response:

```json
{
  "id": "agr_ADbq4JK",
  "created": "2026-08-22T12:59:56Z",
  "start": "2026-08-22T13:00:00Z",
  "stop": null,
  "status": "ACTIVE",
  "productName": "Premier League subscription",
  "pricing": { "type": "LEGACY", "amount": 49900, "currency": "NOK" },
  "interval": { "unit": "MONTH", "count": 2, "text": "every 2 months" },
  "campaign": null,
  "merchantAgreementUrl": "https://example.com/subscriptions/1234/",
  "uuid": "6080c099-d7f2-43ef-a82b-2991ccc3a239",
  "countryCode": "NO"
}
```

## Pricing in detail

### LEGACY

The default. `pricing.amount` is what the customer is told they pay each interval.

An individual charge may differ from that amount, but charges inside one interval may total at most **5 times** the
agreement price. Hitting that ceiling means the agreement price is wrong; update it rather than working around it, and
tell the customer about the change.

### VARIABLE

No fixed price. You send `suggestedMaxAmount`, which is preselected for the customer along with generated alternatives.
The customer confirms their own `maxAmount`, visible in the `GET` response, and can change it any time.

- The charge ceiling is the **higher** of `suggestedMaxAmount` and the customer's `maxAmount`.
- A charge above the customer's `maxAmount` but at or below `suggestedMaxAmount` goes `DUE`, and the customer is
  prompted to raise their maximum. If they do not, it ends `FAILED` with `charge_amount_too_high`.
- `suggestedMaxAmount` can be updated with `PATCH`, but the customer is **not** notified of that change.
- Campaigns are not available.
- The app labels the agreement "Variable".

Set a realistic `suggestedMaxAmount`. An inflated number scares customers off at the consent screen.

### FLEXIBLE

No amount at all in `pricing`, no ceiling on charges, no campaigns. Right for electricity and similar genuinely
unbounded billing. The customer gets no price context, so lean on `productDescription` and clear communication.

```json
{ "pricing": { "type": "FLEXIBLE", "currency": "DKK" } }
```

### Pay per use

Omit `interval` entirely. Suits scooter rental and similar, where there is no periodicity, usually with `VARIABLE`
pricing.

## Initial charge

Bills something the moment the agreement is approved.

```json
{
  "initialCharge": {
    "amount": 49900,
    "description": "Premier League subscription",
    "transactionType": "DIRECT_CAPTURE"
  }
}
```

- No price ceiling applies to an initial charge, so a bundled device can be billed with the subscription.
- `DIRECT_CAPTURE`: the agreement only becomes `ACTIVE` if this payment succeeds. Use for instant digital access.
- `RESERVE_CAPTURE`: required for physical goods. Capture it when you ship, using the charge capture endpoint.
- Capture a reserved initial charge **before** stopping the agreement, or it is cancelled with everything else.
- Do not use an initial charge as a discount mechanism. The app then makes it look as though full price starts
  immediately. Use a campaign.

## Campaigns

A period at a lower price, shown next to the normal price. Not available with `VARIABLE` or `FLEXIBLE` pricing. Added as
`campaign` on the draft.

```json
{ "campaign": { "type": "PRICE_CAMPAIGN", "price": 100, "end": "2026-12-25T00:00:00Z" } }
```

```json
{ "campaign": { "type": "PERIOD_CAMPAIGN", "price": 100, "period": { "unit": "WEEK", "count": 10 } } }
```

```json
{
  "campaign": {
    "type": "EVENT_CAMPAIGN",
    "price": 100,
    "eventDate": "2026-09-01T00:00:00Z",
    "eventText": "until Christmas"
  }
}
```

`PRICE_CAMPAIGN` runs the discounted price per interval until `end`. `PERIOD_CAMPAIGN` charges one price for a whole
duration. `EVENT_CAMPAIGN` runs until a named event; start `eventText` in lower case, since it is appended to a
sentence.

## Updating an agreement

`PATCH /agreements/{agreementId}`. All fields optional.

```json
{
  "productName": "A new name",
  "productDescription": "A new description",
  "merchantAgreementUrl": "https://example.com/subscriptions/1234/",
  "pricing": { "amount": 25000 },
  "interval": { "type": "RECURRING", "period": { "count": 1, "unit": "MONTH" } }
}
```

- `pricing.amount` is updatable for `LEGACY` only, `pricing.suggestedMaxAmount` for `VARIABLE` only.
- `pricing.type` can never change. A different pricing model means a new agreement.
- The interval can switch between `RECURRING` with a period and `FLEXIBLE`.
- Setting `status: "STOPPED"` must be sent alone. Combining it with other fields gives HTTP 400.
- For a large price change, create a new agreement so the customer consents again.

## Stopping, and the customer's side of it

- `PATCH` with `{"status": "STOPPED"}`. Irreversible.
- Stopping cancels `PENDING`, `DUE`, and `RESERVED` charges.
- When the **customer** stops the agreement in the app, `RESERVED` charges are not cancelled. Capture or cancel them.
- Subscribe to `recurring.agreement-stopped.v1`. Its `actor` field tells you whether the merchant or the customer did
  it. Also `recurring.agreement-activated.v1`, `-rejected.v1`, `-expired.v1`.
- There is no pause. Stop creating charges and describe the pause in the agreement description.
- Customers manage agreements in the app by default. Key-account merchants can apply to opt out of in-app cancellation,
  which raises the bar on `merchantAgreementUrl` and is discouraged.

## Getting profile data with the agreement

Add `scope` to the draft so sign-up and consent happen in one approval instead of a separate login flow.

```json
{ "scope": "address name email birthDate phoneNumber" }
```

1. Draft the agreement with `scope`.
2. The customer consents and approves. It is all or nothing: refusing the scopes means no agreement.
3. `GET /agreements/{agreementId}` returns `sub` and the full `userinfoUrl`.
4. Fetch the profile from `GET /vipps-userinfo-api/userinfo/{sub}`.

Two traps on step 4:

- **Do not send `Ocp-Apim-Subscription-Key`** on the Userinfo call. Userinfo belongs to Login, outside the Recurring
  subscription, and including the header gives HTTP 401.
- You have 168 hours (one week) to fetch the data, and you get the profile as it is at fetch time, not at approval time.
  Fetch it right after the agreement is active.

`sub` is stable for that sales unit. Ask for the fewest scopes you need; every extra one costs conversion.

Full pages: <https://developer.vippsmobilepay.com/docs/APIs/recurring-api/recurring-api-guide.md>
