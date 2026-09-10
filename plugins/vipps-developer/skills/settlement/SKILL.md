---
name: settlement
description: >-
  Understand how Vipps MobilePay turns captured payments into a bank transfer, and reconcile that transfer in an
  accounting system. Use when work involves settlements, payouts, settlement frequency, when the money arrives, the
  bank reference text, net versus gross settlement, settlement reports, or matching a lump sum on a bank statement
  back to the payments behind it.
---

# Settlements

Captured payments are batched and paid out as **one lump sum per sales unit per settlement period**. A bank statement
never shows a line per payment, so reconciliation is always the job of matching one transfer to many payments.

Read `../best-practices/SKILL.md` first for servers, keys, and access tokens. This skill is the domain model. The API
that returns the data is the Report API: see `../report/SKILL.md` for ledgers, entry types, paging, and `tryLater`.

**There are no settlements in the test environment.** Nothing here can be tested on `apitest.vipps.no`, and the Report
API is production only. Write reconciliation logic defensively; its first real run is against real money.

## When the money arrives

Frequency is a per-sales-unit setting. Vipps merchants choose `daily`, `weekly`, or `monthly` in the business portal
themselves, with no approval needed unless the account carries risk factors. MobilePay is daily only.

| Frequency | Calculated |
| --------- | ---------- |
| Daily | Every day at midnight, weekends and bank holidays included |
| Weekly | Every Monday |
| Monthly | First day of the month |

The lag from capture to money in the bank differs by brand:

| | Capture | Settlement calculated | Data available | Sent to the bank |
| --- | --- | --- | --- | --- |
| **Vipps** | Day 1 | Day 1, midnight | Day 2 | Day 3 |
| **MobilePay** | Day 1 | Day 1, midnight | Day 2 | Day 2 |

So a Monday capture is a Wednesday payment on Vipps and a Tuesday payment on MobilePay. The bank may not book it until
the next banking day, and money is normally available before noon.

**Do not promise the merchant a date computed from capture time alone.** Weekends, bank holidays, and the bank's own
booking delay all move it.

## What is and is not paid out

- **One payout per settlement period per sales unit**, however many payments it covers, with one settlement file each.
- **A zero or negative balance produces no settlement and no report at all.** Refunds exceeding payments, or a day with
  no traffic, means no file and not even a directory where the file would have been. The balance simply rolls forward,
  so a later report can span several days. A persistent negative balance is invoiced to the merchant.
- Reports are generated around 01:00-03:00 and are available by 12:00 noon, later if something is delayed.

A missing report is therefore normal and not an error condition. Code that alarms on "no report today" will cry wolf.
This is the same fact the Report API expresses as `tryLater: true`, which can stay true for a month on monthly
settlement or for 60 days on a negative balance.

## Net and gross

**Net settlement is the default.** Fees are deducted before the transfer, so the merchant receives payments minus fees
and there is no fee invoice to match.

**Gross settlement is rare and requires approval**, because it means extending credit to the merchant while fees are
outstanding. The merchant receives the full amount and is invoiced for fees monthly, by EHF if their organization
number is registered as an EHF recipient and by email otherwise.

Which one is in force changes what the ledger looks like: on net settlement the fees show up as `fees-retained`
entries against the funds ledger. See `../report/references/entry-types.md`. Refunds are deducted from the next payout
either way.

## Matching a bank transfer to its payments

The bank reference text is the join key between the bank statement and the settlement data.

| Market | Format | Example |
| ------ | ------ | ------- |
| Norway | `Utb. {Recipient} Vippsnr {PayoutNumber}`, not configurable | `Utb. 2000810 Vippsnr 117703` |
| Denmark, Finland | `02{Recipient:08}001{DD}{MM}{YY}{C}`, configurable in the business portal | |

We hand that text to the bank; how the bank displays it is out of our hands, so do not build a strict parser around
what the merchant sees in online banking.

From there:

- **With the Report API.** The `reference` field on a `payout-scheduled` entry in the `funds` feed matches the bank
  reference text. `payout-scheduled` is always the last entry of a ledger date where a payout happened, so a payout
  covers a whole number of ledger dates: fetch the oldest unreported date and keep rolling the next date in until you
  hit one. See `../report/SKILL.md`.
- **Without it.** Download the settlement report from the business portal under *Reports*. `Payout scheduled` rows
  carry a *Payout number* column, and the payment rows around such a row belong to that payout.

## The identifiers, and which one to design around

Three different IDs turn up in a reconciliation conversation and only one of them is yours:

| ID | Set by | What it identifies |
| -- | ------ | ------------------ |
| `reference` (ePayment) or `orderId` (Recurring, eCom) | **You** | The payment, in your own system |
| `transactionId` | Vipps MobilePay | The transaction |
| `settlementId` | Vipps MobilePay and the bank | The settlement |

**The merchant's own `reference` is the one that makes reconciliation work**, because it is the only one that already
means something in their order system. Design it before writing payment code, not afterwards. See
`../payment-lifecycle/SKILL.md`.

**Multiple stores on one MSN: prefix the reference per store**, for example `oslo-654321-123abc-11` and
`bergen-654321-345def-11`. Settlement data has no store dimension of its own, so a prefix is the only way to split a
shared sales unit's payouts per store afterwards. Retrofitting this is expensive; raise it while the MSN structure is
still being decided.

**On Recurring, `orderId` on a charge is optional**, and when it is left out the settlement report shows the generated
`chargeId` instead. `orderId` must be unique per MSN within Recurring; making it unique across your other APIs for the
same MSN is recommended but not enforced. `externalId` is an alternative that appears in settlement reports without
changing how the charge is identified.

## Personal data

Settlement reports generally hold no personal information. Payments made with *Vippsnummer* and *MobilePay-nummer* are
the exception and can contain it, so treat those reports as personal data under GDPR. The business portal's download
dialog has a `Personal information` option that adds it; the Report API equivalent is
`?includeGDPRSensitiveData=true`. Only ask for it when the accounting process genuinely needs it.

For API payments there is nothing personal to return in the first place. The way to get customer details is consent at
payment time; see `../userinfo/SKILL.md`.

Canonical page: <https://developer.vippsmobilepay.com/docs/knowledge-base/settlements.md>. API detail:
<https://developer.vippsmobilepay.com/docs/APIs/report-api/api-guide/settlement-process.md> and
<https://developer.vippsmobilepay.com/docs/APIs/report-api/report-api-faq.md>.
