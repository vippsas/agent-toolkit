# Report API entry types

Every entry on a ledger carries an `entryType`. Read this with `../SKILL.md`.

**New entry types can be added without notice, and that is not an API change.** Never reject an unknown type. What
always holds is that `amount` is signed and describes the effect on the balance of that account, so an unrecognized
type can still be booked correctly.

## How the accounts fit together

Three accounts, two of which have endpoints:

- **funds** (`topic=funds`): what we owe the merchant. Captures push it up, refunds pull it down, and a payout empties
  it.
- **fees** (`topic=fees`): what the merchant owes us. Settled either by retaining it from funds (net settlement) or by
  invoice (gross settlement).
- **payouts**: money on its way to the bank. **No endpoint reports on this**, which is why a `payout-scheduled` entry
  is not proof the money arrived.

A quiet day on `funds`:

| `ledgerDate` | `entryType` | `amount` | `reference` | `pspReference` | `balanceBefore` | `balanceAfter` |
| --- | --- | ---: | --- | --- | ---: | ---: |
| 2022-10-01 | capture | 10000 | purchase-12 | 3343121302 | 0 | 10000 |
| 2022-10-01 | capture | 10000 | purchase-12 | 3334234112 | 10000 | 20000 |
| 2022-10-01 | capture | 20000 | purchase-14 | 3259823497 | 20000 | 40000 |
| 2022-10-01 | refund | -10000 | purchase-12 | 1154320987 | 40000 | 30000 |
| 2022-10-01 | fees-retained | -1200 | | 01H7W7Q6Y5R-3G58CTAZX0MHKV2 | 30000 | 28800 |
| 2022-10-01 | payout-scheduled | -28800 | Vipps utbet. 2000023 Vippsnr 57860 | 12345-2000023 | 28800 | 0 |

And the matching `fees`:

| `ledgerDate` | `entryType` | `amount` | `reference` | `pspReference` | `balanceBefore` | `balanceAfter` |
| --- | --- | ---: | --- | --- | ---: | ---: |
| 2022-10-01 | capture-fee | -400 | purchase-12 | 3343121302 | 0 | -400 |
| 2022-10-01 | capture-fee | -400 | purchase-12 | 3334234112 | -400 | -800 |
| 2022-10-01 | capture-fee | -400 | purchase-14 | 3259823497 | -800 | -1200 |
| 2022-10-01 | fees-retained | 1200 | | 12345-2000321 | -1200 | 0 |

Note the same `pspReference` on a capture and its fee, and `fees-retained` appearing on both ledgers with opposite
signs.

## Funds entry types

### `capture`

Money moving from the customer to the merchant. **Both payment flows land here as `capture`**: an immediate sale and
the capture half of a reserve-then-capture are not distinguished.

- `pspReference` is unique to this capture. A partially captured payment produces several captures with different
  values.
- `reference` is shared by every entry for the payment. On ePayment it is the `reference` from `createPayment`.

### `refund`

Money going back to the customer, whether initiated through an API or in the business portal.

**Refunds are always deducted from the next payout, even on a gross settlement.** Refunds currently carry no fees.

### `fees-retained` (funds)

Money held back to cover fees, on net settlements. Negative here, positive on the fees ledger, same `pspReference`,
and `reference` is empty.

The signs invert in the rare case where large fee corrections leave us owing the merchant.

### `payout-scheduled`

A payout has been scheduled and the balance is now zero. It is always the last entry of a ledger date that pays out.

- `pspReference` is `<ledgerId>-<payoutNumber>`, the payout number increasing sequentially.
- `reference` is the text that will appear on the bank transfer, which is how you find it in the merchant's bank.
  Configurable by the merchant in Denmark and Finland. **In Norway this field is currently missing and does not match
  the actual payout reference.**

Scheduled is not paid. A blocked payout, for example while a merchant proves ownership of a new bank account, still
produces these entries; the transfers queue up and execute once the block clears.

### `payout-aborted`

A payout could not be executed despite retries, or was cancelled to cover a negative balance the next day. The money
goes back on the ledger.

### `retained-disputed-capture`

The issuer disputed a capture — suspected fraud, damaged goods — and we deducted it. `pspReference` and `reference`
are those of the disputed capture.

### `returned-disputed-capture`

The merchant won the dispute and the money came back. Same references again. The retain-and-return cycle can in
principle repeat for one capture, so do not assume it happens at most once.

### `correction` (funds)

A manual adjustment. You should normally have heard from us first; if not, ask support. Corrections are how errors are
fixed, since existing entries are never edited.

### `top-up`

The merchant transferred money in, typically after an invoice for a balance that stayed negative.

### `credit-note` (funds)

Credit against a previously issued top-up invoice.

## Fees entry types

### `capture-fee`

A fee for a capture. `pspReference` and `reference` match the capture.

Two traps:

- **`pspReference` is not unique on the fees ledger.** One capture can attract several fees.
- **The `ledgerDate` need not match the capture's.** Match on `pspReference`, never on date.

### `fees-retained` (fees)

The positive counterpart of the funds entry above.

### `fees-invoiced`

On gross settlement, fees are invoiced monthly and the fees balance is adjusted with this. Nothing appears on the
funds ledger.

### `credit-note` (fees)

Credit against a previously issued fee invoice.

### `correction` (fees)

A manual adjustment, for example fixing a `capture-fee` with the wrong amount.

## Timing effects to expect

**Fee delay.** The fee pipeline is deliberately decoupled from funds and payouts, so a fee problem never holds up a
payout. A delayed fee lands on the next ledger date instead — likeliest for captures near the business day cutoff, and
usually minutes or hours. On net settlement this means **the day's `fees-retained` will not equal the fees for that
day's captures**. If a fee is still missing after the next ledger date, contact customer service.

**Payout delay.** Payouts run on an agreed delay such as T+2. The report for Wednesday's payout is already available
on Tuesday morning.

**Negative balance.** Refunds and fees can exceed captures — a cancelled concert refunding months of ticket sales is
the standard example. The negative balance carries into the next day, and no payout is generated while it lasts. Left
long enough, we invoice, which shows up as a `top-up`.

**Rolling reserve.** Some agreements keep a permanent balance on the ledger to cover future refunds, so the balance
never returns to zero.

**Ledger dates.** Normally midnight to midnight in the merchant's timezone, but the cutoff is configurable to
something like 04:00 by us, on request; neither merchant nor partner can change it. Entries arriving after the cutoff
go onto the next date, which is fetchable immediately with `tryLater: true`.

## Modeling it in an accounting system

Mirror the structure:

- An account for funds held at Vipps MobilePay. Book income against this when a sale is made.
- An account for fees owed to Vipps MobilePay.
- A settlement payout is then just a transfer between two of the merchant's own accounts, not income.

Reconcile per transaction on transaction IDs rather than on daily totals.

Canonical page: <https://developer.vippsmobilepay.com/docs/APIs/report-api/api-guide/entry-types.md>. Settlement
mechanics: <https://developer.vippsmobilepay.com/docs/APIs/report-api/api-guide/settlement-process.md>.
