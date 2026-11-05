# Changelog

Notable changes to the `vipps-developer` plugin.

The plugin was called `vipps` up to and including 1.12.0 and kept its version series through the rename, so the
entries below cover both names. The deprecated `vipps` plugin has its own
[changelog](../vipps/CHANGELOG.md).

The skills restate the Vipps MobilePay developer documentation at
<https://developer.vippsmobilepay.com>, and an automated workflow syncs them whenever that documentation changes.
Most releases are therefore a minor bump carrying a documentation correction. Entries up to and including 1.13.0
were reconstructed from git history when this file was added, so they are shorter than later ones will be.

## 1.57.0 - 2026-11-05

- Personal QR docs describe code formats by market instead of brand

## 1.56.0 - 2026-11-05

- Add ePayment error 8020 (QR generation failed) to the epayment skill

## 1.55.0 - 2026-11-05

- llms.txt, raw Markdown pages, and the AI plugin announce the move to developer.vipps.no

## 1.54.0 - 2026-11-05

- Recurring refund deadline counts from the reservation date

## 1.53.0 - 2026-11-05

- ePayment error messages match the API, and error codes and messages show as code

## 1.52.0 - 2026-11-05

- epayment: Refund deadline counts from the reservation date

## 1.51.0 - 2026-11-05

- Update partner go-live steps in test-and-go-live skill

## 1.50.0 - 2026-11-04

- Update QR image URL expiry and recurring stop guidance

## 1.49.0 - 2026-11-04

- Plugin skills cover Login partner keys, Widget SDK agreements and CSP, and other details the docs already had

## 1.48.0 - 2026-11-04

- Plugin skills cover capture, settlement, testing, QR, and webhook details the docs already had

## 1.47.0 - 2026-11-04

- Best-practices skill and AI tools page reflect all markets and everything the plugin covers

## 1.46.0 - 2026-11-04

- Plugin skills cover PSP merchant onboarding, card callback errors, and Donations details

## 1.45.0 - 2026-11-04

- Plugin skills include the docs changes from the last two weeks

## 1.44.0 - 2026-11-03

- Plugin skills give the new webhook limit of 30 registrations per event type

## 1.43.0 - 2026-11-03

- Widget SDK, Button generator, and Badge generator moved to own folder: Buttons and widgets

## 1.42.0 - 2026-10-30

- TRE-3175: Document transactionLinkId

## 1.41.0 - 2026-10-27

- Report API: correct the 1.0 spec against production

## 1.40.0 - 2026-10-27

- Remove the deprecated Optimizely plugins from the docs

## 1.39.0 - 2026-10-20

- Align management API docs with the spec

## 1.38.0 - 2026-10-16

- Plugin skills match the current docs

## 1.37.0 - 2026-10-16

- Skills no longer link to deleted pages

## 1.36.0 - 2026-10-14

- Add Donations amount change requests and update PSP card types

## 1.35.0 - 2026-10-13

- Update recurring agreement history actor and Sales API Get Paid notes

## 1.34.0 - 2026-10-09

- Update refund destination by customer country

## 1.33.0 - 2026-10-08

- Update ePayment skill for Express capture amount and limitations

## 1.32.0 - 2026-10-02

- Update Login Connect scope, Express profile scopes, and PSP charge externalId

## 1.31.0 - 2026-10-01

- TRE-3119: Recurring PSP account payment support renaming

## 1.30.0 - 2026-10-01

- Hide the PrestaShop plugin pages

## 1.29.0 - 2026-10-01

- Use the changelog entry as the agent-toolkit PR title

## 1.28.0 - 2026-09-30

- Update PSP skill for the psp object rename and remove Checkout API references

## 1.27.0 - 2026-09-30

- Update donations skill for multiple merchant-level clients

## 1.26.0 - 2026-09-30

- Add ELEC_DEBIT to ePayment PSP card types in psp skill

## 1.25.0 - 2026-09-25

- Sync report skill: recipientHandle, ledger 404 message, and credit-note entry types

## 1.24.0 - 2026-09-24

- Clarify PSP charge retry window and agreement history actor field

## 1.23.0 - 2026-09-24

- Document agreement history in Recurring skill

## 1.22.0 - 2026-09-22

- Describe the API collections without requiring Postman

## 1.21.0 - 2026-09-22

- Sync report skill with Report API page size and tryLater updates

## 1.20.0 - 2026-09-15

- Sync plugin skills: Express shipping order line, PSP initial charge description

## 1.19.0 - 2026-09-15

- Sync plugin skills: Express currency rules, NIN, PSP maintenance mode, Recurring description length

## 1.18.0 - 2026-09-11

- Update Management, Order Management, and PSP skills to match doc changes

## 1.17.0 - 2026-09-11

- Document idempotent agreement stop in recurring skill

## 1.16.0 - 2026-09-10

- New plugin logo showing both the Vipps and the MobilePay brand mark instead of the Vipps smile alone.

## 1.15.0 - 2026-09-10

- Fix stale profile.sub and blockedSources references in plugin skills

## 1.14.0 - 2026-09-10

- Add plugin skills for the remaining public APIs

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
