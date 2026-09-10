---
name: sales
description: >-
  Retrieve what was sold — order lines, VAT breakdowns, and sales categories — for Vippsnummer and mPOS payments, as
  an accounting partner. Use when work involves /sales/report/v1/ledgers, VARIABLE_AMOUNT, SHOPPING_BASKET, MPOS,
  lineTotalGross, vatRate, salesCategory, or joining sales context to Report API money movements.
---

# Sales API

Answers *what was sold*, where the Report API answers *what happened to the money*. Order lines, VAT, and categories
for Vippsnummer and mPOS payments.

Read `../best-practices/SKILL.md` first, and `../report/SKILL.md`, because **this API is only useful next to the
Report API**: the ledger IDs come from there, and so does everything about settlement.

Constraints that rule this in or out before any code:

- **Accounting partners only**, with accounting keys and the specialized token flow at `/miami/v1/token`. See
  `../access-token/SKILL.md`. There is no merchant-keys path, because VM number sales units have no API keys at all —
  a merchant who wants this data designates an accounting partner.
- **Production and UAT only**, `https://api.vipps.no`. Not in the test environment.
- **Vippsnummer and mPOS only.** ePayment and Recurring payments are not here.
- **No customer information, ever.** The `customer` field is reserved and always `null`.

## What data exists, and from when

| Sales type | `solution` | You get |
| ---------- | ---------- | ------- |
| Open Amount | `VARIABLE_AMOUNT` | Amount and `salesCategory` when set. **No order lines** — the customer typed an amount |
| Shopping Basket | `SHOPPING_BASKET` | Order lines, names, quantities, VAT per line, as far as the merchant entered them |
| mPOS | `MPOS` | Terminal sales: card, cash, and wallet |

**There is a hard historical floor**, and asking for anything earlier returns nothing:

| Sales type | Available from |
| ---------- | -------------- |
| mPOS | 2026-03-09 12:45 UTC |
| Open Amount | 2026-03-16 09:28 UTC |
| Shopping Basket | 2026-04-22 11:04 UTC |

## Endpoints

All scoped to a `ledgerId` you got from the Report API's `GET /settlement/v1/ledgers`.

| Call | For |
| ---- | --- |
| `GET /sales/report/v1/ledgers/{ledgerId}` | The feed: continuous sync |
| `GET /sales/report/v1/ledgers/{ledgerId}/dates/{ledgerDate}` | One accounting date, `YYYY-MM-DD` |
| `GET /sales/report/v1/ledgers/{ledgerId}/references/{reference}` | Every capture and return on one order |
| `GET /sales/report/v1/ledgers/{ledgerId}/psp-references/{pspReference}` | One transaction |

```bash
curl -X GET "https://api.vipps.no/sales/report/v1/ledgers/{ledgerId}?pageSize=100" \
-H "Authorization: Bearer YOUR-ACCESS-TOKEN"
```

`pageSize` defaults to 100 and caps at 1000. Both the feed and the date endpoint page with a `cursor`; the date
endpoint also returns `hasMore`. **Persist the cursor** and resume from it rather than restarting the feed. Omitting
it starts from the very first sale on the ledger.

## An entry

One entry is **one financial transaction on an order** — a capture or a refund — with the sales context attached.

```json
{
  "entryType": "capture",
  "time": "2026-01-19T12:45:00Z",
  "pspReference": "35054310398",
  "reference": "12494299492",
  "currency": "NOK",
  "paymentType": "CARD",
  "classification": { "solution": "MPOS", "salesCategory": null },
  "amounts": { "gross": 25000, "net": 20000, "vat": 5000 },
  "lines": [
    {
      "lineId": "121772",
      "name": "Product A",
      "quantity": 2,
      "unitPriceGross": 12500,
      "unitPriceNet": 10000,
      "discountTotal": 0,
      "lineTotalGross": 25000,
      "lineTotalNet": 20000,
      "vatRate": 2500,
      "vatAmount": 5000,
      "category": "GOODS"
    }
  ],
  "customer": null,
  "completeness": { "hasLineItems": true, "hasVatBreakdown": true, "hasCustomerIdentity": false }
}
```

- Minor units throughout. **Gross includes VAT, net excludes it.**
- `vatRate` is basis points: `2500` is 25%.
- `unitPriceGross` and `unitPriceNet` are before discount; `lineTotalGross` and `lineTotalNet` are after it.
- `paymentType` is `CARD`, `CASH`, or `WALLET`.
- **`pspReference` is `null` for payment methods with no PSP**, cash being the obvious one. Do not use it as a
  required key.

Three invariants worth asserting on ingest, because a mismatch means you have misread the fields:

```text
unitPriceGross * quantity - discountTotal = lineTotalGross
sum(lines[].lineTotalGross)               = amounts.gross
sum(lines[].vatAmount)                    = amounts.vat
```

**Use `completeness` rather than inferring from empty.** It exists precisely to separate "the merchant did not provide
this" from "known to be nothing", and those book differently. Shopping Basket VAT in particular is whatever the
merchant typed: it is not mandatory per line, so partial VAT across an order is normal and must not crash the import.

## Joining to the Report API

Same field names, same values:

| Level | Field |
| ----- | ----- |
| Order | `reference` — stable across captures, refunds, and fees. Equals `orderId` in ePayment |
| Transaction | `pspReference` — one capture or one refund |

The working shape of an accounting integration:

1. `GET /settlement/v1/ledgers` on the Report API for the ledgers the partner agreement covers.
2. Sales entries from here.
3. Funds and fees entries from the Report API.
4. Join on `reference`, or on `pspReference` where you need transaction granularity.
5. Store the cursors, resume from them, repeat on a schedule.

**This API does not replace settlement reporting.** It carries no payment state, no payout, fee, balance, or refund
settlement detail, and it makes no claim that a sale settled correctly. Every one of those questions goes to the
Report API.

Canonical pages: <https://developer.vippsmobilepay.com/docs/APIs/sales-api/api-guide.md>,
<https://developer.vippsmobilepay.com/docs/APIs/sales-api/quick-start.md>,
<https://developer.vippsmobilepay.com/docs/APIs/sales-api/README.md>, spec at `/api/sales`.
