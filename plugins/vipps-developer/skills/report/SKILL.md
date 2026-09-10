---
name: report
description: >-
  Pull Vipps MobilePay settlement data for accounting and reconciliation: captures, refunds, fees, and payouts from a
  merchant's ledger. Use when work involves /settlement/v1/ledgers, /report/v2/ledgers, ledgerId, funds and fees
  topics, entryType, payout-scheduled, fees-retained, tryLater, cursor paging, or matching a bank transfer to the
  payments behind it.
---

# Report API

Answers *what happened to the money*: every capture, refund, fee, and payout on a merchant's ledger, so a bank
transfer can be explained line by line in an accounting system.

Read `../best-practices/SKILL.md` first for platform basics, and `../access-token/SKILL.md`, because **which token
flow you use depends on who you are**. Read `../settlement/SKILL.md` for what the data means: settlement frequency and
timing, net versus gross, why a report can be missing entirely, and which identifier to reconcile on.

**Production only.** `https://api.vipps.no`. There is no Report API in the test environment, so reconciliation logic
cannot be tested end to end before it meets real data. Write it defensively.

## Who can call it, and with which keys

| Caller | Keys | Token flow | Reaches |
| ------ | ---- | ---------- | ------- |
| ePayment or Recurring merchant | Sales unit keys | Standard | That one MSN |
| Accounting partner | **Accounting keys** | **Specialized** (`/miami/v1/token`) | Every merchant who granted access |
| Donations organization | Merchant-level keys | Specialized | Their Donations data |

Only accounting partners get partner access here. Other partner types do not, and an accounting partner may **not**
use a merchant's own keys.

**A merchant must grant access in the business portal before a partner sees anything.** Under *Reports*, then
*Accounting partners*, and they choose which ledgers each partner gets. This is a GDPR consent step and cannot be done
by the partner or by us. When an expected ledger is missing, this is nearly always why.

VM number merchants cannot use the API directly at all. They designate an accounting partner, or download reports from
the portal.

## Ledgers

Everything is scoped to a `ledgerId`. **One ledger, one sales unit** — a ledger never mixes MSNs. The ID is stable, so
store it in configuration next to the MSN.

`GET /settlement/v1/ledgers` is always the first call:

```json
{
  "items": [
    {
      "ledgerId": "302321",
      "currency": "NOK",
      "payoutBankAccount": { "scheme": "BBAN:NO", "id": "86011117947" },
      "owner": { "scheme": "business:NO:ORG", "id": "987654321" },
      "settlesForRecipientHandles": ["api:123455", "api:123456"],
      "salesUnits": [{ "name": "ACME Fitness Oslo", "recipientHandle": "api:123455" }]
    }
  ],
  "cursor": "eyJhZnRlckxlZGdlcklkIjoie"
}
```

Go the other way with `GET /settlement/v1/ledgers?settlesForRecipientHandles=DK:123456`. Handles are prefixed `api:`
for API sales units and by country for VM numbers: `NO:`, `DK:`, `FI:`.

An accounting partner should **re-poll this endpoint regularly**, not once at setup. New ledgers appear as merchants
grant access.

The ledger ID is not shown in the business portal; this endpoint is the only way to get it.

## Fetching entries

Two endpoints, one `{topic}` that is `funds` or `fees`:

| Endpoint | For |
| -------- | --- |
| `GET /report/v2/ledgers/{ledgerId}/{topic}/dates/{ledgerDate}` | A complete report for one ledger date |
| `GET /report/v2/ledgers/{ledgerId}/{topic}/feed` | A continuous stream, to mirror into your own database |

**Prefer the feed** for a new integration. It needs slightly more logic but never leaves you guessing which dates you
have already taken. Use the date endpoint when the accounting system genuinely thinks in daily reports.

An entry:

```json
{
  "pspReference": "3343121302",
  "time": "2020-10-05T00:00:00.000000Z",
  "ledgerDate": "2020-10-05",
  "entryType": "capture",
  "reference": "acme-shop-123-order123abc",
  "currency": "NOK",
  "amount": 49900,
  "balanceBefore": 49900,
  "balanceAfter": 49900,
  "recipientHandle": "NO:123455"
}
```

- Amounts are minor units, and signed: refunds and fees are negative.
- `reference` groups every entry for one payment. On ePayment it is the `reference` you sent to `createPayment`.
- `pspReference` identifies one movement. Correlate a fee to its capture on `pspReference`.
- `recipientHandle` can be `null`: some entry types never have one, and data from before 2022 may be missing it.

See `references/entry-types.md` for what each `entryType` means.

## Paging, `hasMore`, and `tryLater`

Up to 1000 items per response, and the two endpoints signal continuation **differently**. Getting this wrong is the
classic Report API bug.

**Date endpoint.** `hasMore` is always present. Continue only while `hasMore` is `true`, passing the returned
`cursor` as a query parameter. When `hasMore` is `false` there is no `cursor` in the body. A `hasMore: true` page can
be followed by an empty one, so treat empty as normal rather than as an error.

**Feed endpoint.** No `hasMore`. The `cursor` is **always** present and never becomes empty. Persist it after every
successful batch and send it on the next poll, even when nothing came back. It is your entire position in the stream;
lose it and you re-read from the start.

`tryLater: true` means "not yet, ask again with the same request". On the date endpoint it means the ledger date is
still open. On the feed it means you have caught up.

**`tryLater` can stay true for a very long time**, and that is not a fault:

- Monthly settlement: every day of the month, until the month ends.
- A negative balance: possibly 60 days or more, until we invoice.
- A merchant with no traffic: until they have some.

So do not build "wait for `tryLater: false`" into a blocking loop. Track a `lastLedgerDate` per `ledgerId`, walk
forward from `lastLedgerDate + 1` to today each run, and shrug at every `tryLater` on the way.

If you use `includeGDPRSensitiveData=true`, repeat it on every paged request.

## Scheduling the job

**Run hourly, every hour of every day, and fetch whatever is new.** Not once at 08:00. An hourly job that asks for
everything outstanding absorbs delays, downtime, and late data without anyone being paged.

Pick a random minute in the hour and **avoid :00 to :10**, where everyone else's cron already is.

Do not poll the feed every few seconds either. Below very high volume you will fetch entries one at a time, which is
wasteful for both sides. Once a minute is plenty when latency matters; once an hour is fine otherwise.

**Data is immutable.** A report fetched again always returns the same entries. Mistakes are fixed by adding
`correction` entries, never by editing history. New JSON fields can appear over time, and new `entryType` values can
appear **without notice** — treat an unknown type by its `amount`'s effect on the balance rather than rejecting it.

## Matching a payout to its payments

Each bank transfer covers a whole number of ledger dates, and `payout-scheduled` is always the last entry of a date
where a payout happened. So: fetch the oldest unreported date, and if its `funds` report does not end with
`payout-scheduled`, roll the next date into the same report and continue.

The `reference` on a `payout-scheduled` entry is the text on the merchant's bank statement. See
`../settlement/SKILL.md` for the per-market format and for reconciling without this API.

There is no per-payout endpoint, and we do not recommend building around the idea of one: a stretch with no payouts
looks like the API has gone silent.

## What it will not tell you

- **No sums or totals.** Add the `amount` values yourself.
- **No order lines or VAT breakdown.** That is the Sales API. Join on `reference` or `pspReference`. See
  `../sales/SKILL.md`.
- **No payments detail.** Go back to the API that made the payment: `GET /epayment/v1/payments/{reference}`, or the
  charge endpoint on Recurring.
- **No payouts topic.** Only `funds` and `fees` exist today.
- **Nothing for a sales unit that cannot move money.** A Login-only sales unit has no settlements and no ledger.
- VM number shopping basket contents, per-product VAT rates, and donor tax deductions are portal-only.

Near real time on the feed is 5 to 30 seconds in the good case, but can stretch to hours under load. This is an
accounting API; do not put it behind a live fundraising display.

**HTTP 404 on a ledger means "not yours".** We do not reveal that a ledger exists to someone without access, so a
real ledger returns `No such ledgerId`. Check the keys and the MSN. An empty list means the same thing more quietly.

## GDPR data

`?includeGDPRSensitiveData=true` adds `message`, `name`, and `maskedPhoneNo` to each entry. **Only VM number merchants
have this data at all**; for API payments there is nothing to return, and the way to get customer details is consent
at payment time. See `../userinfo/SKILL.md`.

Only ask for it when the accounting process actually needs it, and treat what comes back as personal data.

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/report-api/api-guide/fetching-report-data.md>,
<https://developer.vippsmobilepay.com/docs/APIs/report-api/api-guide/settlement-process.md>,
<https://developer.vippsmobilepay.com/docs/APIs/report-api/api-guide/overview.md>,
<https://developer.vippsmobilepay.com/docs/APIs/report-api/report-api-faq.md>, spec at `/api/report`.
