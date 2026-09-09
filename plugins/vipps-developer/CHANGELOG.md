# Changelog

Notable changes to the `vipps-developer` plugin.

The plugin was called `vipps` up to and including 1.12.0 and kept its version series through the rename, so the
entries below cover both names. The deprecated `vipps` plugin has its own
[changelog](../vipps/CHANGELOG.md).

The skills restate the Vipps MobilePay developer documentation at
<https://developer.vippsmobilepay.com>, and an automated workflow syncs them whenever that documentation changes.
Most releases are therefore a minor bump carrying a documentation correction. Entries up to and including 1.13.0
were reconstructed from git history when this file was added, so they are shorter than later ones will be.

## 1.13.0 - 2026-09-09

- PSP: the `description` field on a recurring charge is optional, and falls back to the agreement's `productName`.

## 1.12.0 - 2026-09-08

- Renamed the plugin from `vipps` to `vipps-developer`. The skills are unchanged. The old name stays installable and
  tells an agent to switch.

## 1.11.0 - 2026-09-07

- Test and go live: which APIs are available in the test environment.

## 1.10.0 - 2026-09-03

- ePayment: Express `profile.scope` and the `userDetails` fields it returns.

## 1.9.0 - 2026-08-27

- ePayment and PSP: when `profile.scope` is required for Express.

## 1.8.0 - 2026-08-21

- Payment lifecycle and ePayment: what the capture attempt deadline is anchored to, and per payment method limits.

## 1.7.0 - 2026-08-19

- Payment lifecycle and ePayment: capture deadline details, and new ePayment error codes.

## 1.6.0 - 2026-08-14

- Webhooks, PSP, and best practices corrections.

## 1.5.0 - 2026-08-14

- Added the `psp` skill, for payment service providers doing card passthrough.
- Best practices, ePayment, and Recurring corrections.

## 1.4.0 - 2026-08-14

- Best practices and the ePayment operations reference.

## 1.3.0 - 2026-08-14

- Widget SDK: security and consent changes.

## 1.2.0 - 2026-08-13

- ePayment, payment lifecycle, and test and go live: corrected the force approve path and simplified the timeout
  wording.

## 1.1.0 - 2026-08-13

- Added the `payment-lifecycle` skill, for the capture, cancel, refund, and timeout rules shared by every payment
  API.
- Corrections across best practices, ePayment, Login, Recurring, and test and go live.

## 1.0.0 - 2026-08-12

- First stable release.
- Added the `widget-sdk` skill after 0.2.0, without a version of its own, because the automated version bump did not
  exist yet.

## 0.2.0 - 2026-08-06

- Split the single skill into one skill per API: `epayment`, `recurring`, `login`, `webhooks`, and
  `test-and-go-live`, each with its own `references/` files.

## 0.1.0 - 2026-08-05

- First release, as the `vipps` plugin, with a single `best-practices` skill.
