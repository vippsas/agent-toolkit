---
name: widget-sdk
description: >-
  Render Vipps MobilePay payment buttons and start payments from the browser with the Widget SDK, a JavaScript library
  that app-switches on mobile and opens a payment dialog on desktop. Use when adding a pay or subscribe button to a
  website, and when working with vipps.trigger, vipps.host, vipps.button, vipps-widget.js, or vipps-mobilepay-button.
---

# Widget SDK

A small JavaScript library embedded directly in the website. It provides builders for rendering a payment button that
opens the Vipps MobilePay app on mobile devices and a payment dialog on desktop devices.

**Prefer it over a hand-built button and redirect.** The button's appearance is served by the SDK, so it always reflects
the current design guidelines and the correct brand for the market, and the SDK already implements the app-switch and
redirect behavior a manual integration has to get right. The documentation says so on every page that describes the
alternative: the button generator at
<https://developer.vippsmobilepay.com/docs/knowledge-base/buttons.md> renders a button only, while the Widget SDK
renders the same button and connects it to a payment, and both
<https://developer.vippsmobilepay.com/docs/knowledge-base/initiate-payment.md> and
<https://developer.vippsmobilepay.com/docs/knowledge-base/app-flow.md> point at it instead of their manual guides.

The resolver is handed the payment URL from the create call, which for the ePayment API is the `redirectUrl` from
`POST /epayment/v1/payments`. See `../epayment/SKILL.md`.

## Installation

The SDK exposes a global `window.vipps` object.

```html
<script src="https://cdn.vippsmobilepay.com/js/widget-sdk/vipps-widget.js" data-vipps-widget-sdk></script>
```

The `data-vipps-widget-sdk` attribute is recommended. It helps the SDK find its own script tag later, when it needs
to inject styles or load the button component.

## Quick start

Start a desktop host on the top-level page, then add a payment trigger:

```javascript
vipps.host().start();

vipps
  .trigger(async () => {
    const { paymentUrl } = await fetch("/api/create-session").then((r) => r.json());
    return paymentUrl;
  })
  .button()
  .mount("#pay-button");
```

`.button()` on the trigger returns a pre-wired payment button. Clicking it asks the top-level host to open a desktop
payment dialog; if no host accepts the request, it falls back to a full-page redirect. On mobile and tablet it redirects
directly. On success or cancel the SDK closes the dialog and redirects the page by itself, so a working integration
needs no event code.

The session is still created by your own server, which is what holds the API keys.

## Trigger API

The trigger builder starts a payment flow. On desktop it asks the top-level host to open a modal dialog; on mobile and
tablet it redirects directly to the payment page.

The builder accepts a resolver function that returns, or resolves to, the payment URL. The resolver is called each time
`.open()` is invoked, so a fresh session URL is fetched on every attempt.

| Method / Property | Description |
| ----------------- | ----------- |
| `.on(event, callback)` | Override the callback for `"success"` or `"cancel"`, or react to `"close"` when `cancelPaymentOnClose` is `false` |
| `.button()` | Return a `VippsButtonBuilder` pre-wired to this trigger. Clicking the button calls `.open()` |
| `.open()` | Start the trigger: call the resolver, then ask the host to show the modal, or redirect on mobile and tablet |
| `.close()` | Close the trigger programmatically |
| `.isOpen` | Read-only boolean, whether the trigger is currently open |

### Desktop behavior

The top-level host renders a modal `<dialog>` with an embedded `<iframe>` pointing at the payment URL. The dialog has a
close button in the top-right corner and resizes dynamically to messages from the iframe content.

### Mobile behavior

On mobile and tablet the trigger redirects the current page to the payment URL instead of opening a modal, and
**callbacks registered with `.on()` do not fire** — the customer is redirected to the URL provided at session
creation. Anything that has to happen on both device classes belongs on that page, not in an event handler.

## Host API

Use the Host API on the top-level page that should display desktop payment dialogs.

```javascript
const host = vipps.host();
host.start();
```

| Method / Property | Description |
| ----------------- | ----------- |
| `vipps.host()` | Create a desktop host |
| `host.start()` | Start listening for child-frame trigger requests |
| `host.stop()` | Stop listening for child-frame trigger requests |

Without a host, desktop triggers fall back to a full-page redirect. This applies to hosted desktop triggers, including
triggers running inside embedded iframes. The host opens payment URLs in the same desktop dialog used by normal
triggers, and forwards success, cancel, close, or error responses back to the requesting frame.

The host owns desktop dialog hosting only. Mobile and tablet payment launch stays in the user's click flow and is not
delegated through `postMessage`.

## Modal close behavior

By default the desktop modal's close button cancels the payment, which is the recommended behavior for most
integrations. To let customers close only the modal and keep the payment active, pass `cancelPaymentOnClose: false`:

```javascript
vipps
  .trigger(createSession, {
    cancelPaymentOnClose: false,
  })
  .on("close", () => {
    // The modal has been closed. Add custom cleanup, analytics, or UI updates here.
  })
  .button()
  .mount("#pay-button");
```

With that option the close button only closes the modal, and a cancel action from inside the payment iframe still
cancels the payment. The SDK closes the modal before calling the `"close"` handler, so the handler only reacts to the
closed modal.

## Custom event handling

Override the default success or cancel behavior by chaining `.on()` before `.button()`:

```javascript
vipps
  .trigger(async () => {
    const { paymentUrl } = await fetch("/api/create-session").then((r) => r.json());
    return paymentUrl;
  })
  .on("success", (close, redirectUrl) => {
    close();
    analytics.track("payment_success");
    window.location.href = redirectUrl ?? "/thank-you";
  })
  .on("cancel", (close) => {
    close();
  })
  .button()
  .mount("#pay-button");
```

## Button API

The button builder creates and mounts payment buttons into the DOM. Most integrations should use `trigger.button()`
rather than a standalone button.

The SDK renders a lightweight placeholder button immediately, then upgrades it to the full `<vipps-mobilepay-button>`
web component once the component definition is registered, so the button is visible before the web component scripts
finish loading.

| Method | Description |
| ------ | ----------- |
| `.brand(value)` | `"vipps"` or `"mobilepay"` |
| `.language(value)` | `"no"`, `"en"`, `"da"`, `"fi"`, `"sv"`. Defaults to the user's preferred language |
| `.verb(value)` | `"pay"`, `"login"`, `"register"`, `"continue"`, `"confirm"`, `"donate"`, `"express"`, `"buy"`. Default `"pay"` |
| `.variant(value)` | `"primary"`, `"dark"`, `"light"`. Default `"primary"` |
| `.type(value)` | `"button"` or `"submit"`. Default `"button"` |
| `.branded(value)` | Toggle the brand logo inside the label. Default `true` |
| `.compact(value)` | Compact, logo-only layout. Default `false` |
| `.rounded(value)` | Fully rounded corners. Default `true` |
| `.stretched(value)` | Full-width layout. Default `false` |
| `.continueAsFirstName(name)` | The name shown by the `"continue"` verb, as in "Continue as Ada" |
| `.mount(selector)` | Mount button(s) into all elements matching the CSS selector |
| `.triggers(target)` | Connect the button to a trigger target. Clicks call `.open()` |
| `.onclick(handler)` | Register an additional click handler, sync or async |
| `.rerender()` | Re-mount the button at the previously used selector |
| `.unmount()` | Remove the button(s) from the DOM and detach event listeners |
| `.toElement()` | Return the raw button `HTMLElement` without mounting it |

All presentation methods are chainable, before or after `.mount()`:

```javascript
vipps
  .trigger(createSession)
  .button()
  .brand("mobilepay")
  .verb("express")
  .variant("dark")
  .stretched(true)
  .mount("#pay-button");
```

On desktop the button is rendered in an iframe hosted on the Vipps domain, which currently only honors `brand`,
`language`, and `verb`. The remaining presentation methods apply to the button rendered directly on the page, which is
mobile, tablet, and `toElement()` on mobile.

A standalone button, for the rare case where the trigger is not what drives it:

```javascript
vipps
  .button()
  .brand("vipps")
  .mount("#pay-button-container")
  .triggers(async () => {
    // Handle payment initiation
  });
```

## Content security policy and cookie consent

If the embedding page uses a Content Security Policy, allowlist `https://cdn.vippsmobilepay.com` for `script-src` and
the market's payment domain (for example `https://pay.vipps.no`) for `frame-src`. Do not pin the script with a hashed
CSP source or Subresource Integrity, since the CDN script changes without notice. If CSP blocks framing, the SDK
degrades gracefully: the dialog closes and redirects to the payment URL, or the button falls back to an on-page
web component.

The SDK itself stores nothing on the visitor's device. Cross-site "remember me" personalization and analytics are
consent-relevant behaviors on the Vipps origin; call `vipps.consent({ rememberMe, analytics })` to reflect the
visitor's cookie consent choice. `rememberMe` defaults to off until explicitly enabled; `analytics` and on-page
personalization default to on until consent is set, to preserve historic behavior.

See <https://developer.vippsmobilepay.com/docs/knowledge-base/widget.md#content-security-policy> and
<https://developer.vippsmobilepay.com/docs/knowledge-base/widget.md#cookie-consent-and-gdpr> for full details.

## Before calling it done

- `vipps.host().start()` runs on the top-level page, not inside the frame that holds the button.
- The resolver calls your own server, which creates the session with the API keys. No keys in the browser.
- The order is updated from webhooks and polling, never from the `success` event.
- Both paths work: the desktop dialog, and the full-page redirect it falls back to when no host is running.
- Nothing on mobile depends on an `.on()` callback.

Everything in this skill comes from the canonical page,
<https://developer.vippsmobilepay.com/docs/knowledge-base/widget.md>. Fetch it for anything not covered here rather than
guessing, and see <https://developer.vippsmobilepay.com/docs/knowledge-base/buttons.md> for button design and the
standalone generator.
