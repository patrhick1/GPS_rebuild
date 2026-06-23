# Implementation Observations

Date reviewed: 2026-06-23

This document captures the read-only verification pass of the latest GPS / Impact Dashboard implementations. No code changes were made during the investigation.

## Executive Summary

Most of the latest feature work appears to be implemented: notifications, CRM/Zapier webhooks, Spanish content, PDF downloads, assessment soft-delete, MyImpact comparison, Impact Dashboard branding, and church registration links.

The remaining concerns are mostly production-hardening and configuration details rather than missing core product features. In plain terms, the app looks feature-complete for the recent work, but there are a few places where the user could be sent to the wrong page, a billing event could need manual cleanup, or production domain/email settings could still point at older values.

## Confirmed Applied

- Notification system is present and wired into the FastAPI app.
- Admin CRM/Zapier webhook support is present, including webhook configs, delivery logs, test delivery, retry processing, and master-admin read-only visibility.
- Spanish/i18n database migrations and translated data migrations are present.
- GPS and MyImpact PDF download endpoints are implemented.
- Assessment soft-delete is implemented with `deleted_at`, and dashboard/history views filter deleted assessments.
- MyImpact comparison support exists in the backend and frontend dashboard.
- Impact Dashboard branding is broadly applied across frontend title/assets and API metadata.
- Unique church registration links are implemented with `/register?org=...`.
- Church-link registration appears to create an active membership.
- Personal dashboard export UI appears removed, while the backend export endpoint remains available.
- Several P0 security fixes appear applied:
  - `SECRET_KEY` is required and validated.
  - CORS origin parsing is stricter.
  - Master-role checks use role membership rather than trusting stale role text.
  - CSV export sanitization is present.
  - Access tokens are no longer stored in localStorage.
  - Cookie fallback is limited to safe methods.

## Stripe Notes

Stripe subscription fixes are mostly present:

- Subscription period extraction handles newer Stripe subscription shapes.
- Upcoming invoice preview uses `Invoice.create_preview`.
- Customer creation uses an idempotency key.
- Billing portal session creation exists.
- Stripe webhook event deduplication exists.

### Billing Portal Return URL Concern

Status: verified.

The backend creates Stripe Billing Portal sessions with:

```text
return_url = ${FRONTEND_URL}/billing
```

The frontend billing page is currently registered at:

```text
/admin/billing
```

Layman explanation: when a church admin clicks "Manage Billing in Stripe," they leave Impact Dashboard and go to Stripe's own billing page. When they are done, Stripe asks, "Where should I send this person back?" The app currently appears to answer, "Send them to `/billing`." But the real billing page inside the frontend is `/admin/billing`.

Risk level: low to medium, mostly user experience.

What could happen: payment updates should still happen because Stripe payment events use a separate webhook. The likely problem is that after finishing in Stripe, the church admin may land on a missing page, blank page, or fallback redirect instead of returning cleanly to the billing dashboard.

This is not the same as the Stripe webhook endpoint. The webhook endpoint shown in Stripe should be:

```text
https://api.disciplesmade.com/billing/webhook
```

That endpoint is for Stripe-to-server payment events. The billing portal return URL is for user browser navigation after a Stripe-hosted billing session.

Suggested fix when code changes are allowed: change the return URL from `/billing` to `/admin/billing`.

**Resolved 2026-06-23 — commit `ec87061`.** `api/app/routers/billing.py:567`
now passes `return_url=f"{settings.FRONTEND_URL}/admin/billing"`. Admins
returning from the Stripe Billing Portal will land cleanly on the
in-app billing dashboard once Render redeploys.

### Stripe Webhook Deduplication Concern

Status: verified.

The Stripe webhook route inserts and commits a "we have seen this Stripe event" marker before it finishes handling the actual billing event.

Layman explanation: Stripe sends the app a message like, "This subscription was updated." The app first writes down, "I received message 123." Then it tries to process message 123. If processing fails after the app wrote down that it received the message, Stripe may send message 123 again. But because the app already wrote down that message 123 was received, the retry can be skipped as a duplicate.

Risk level: medium for billing data accuracy, but only when a webhook handler fails.

What could happen: most normal Stripe events should work. But if the app has a temporary error while processing a Stripe event, that event may not automatically fix itself through Stripe retry. Someone may need to manually reconcile the subscription/payment state.

Important nuance: the code comments already describe this as an intentional tradeoff. The current implementation avoids double-processing Stripe events, but the tradeoff is that some failed events may require manual cleanup.

## Deployment And Configuration Notes

### Database Migrations On Render

Status: not a current issue, per project owner clarification.

Render migration execution is not treated as a current concern because the project owner clarified that local and production use the same database.

Layman explanation: if the local app and production app are truly pointing at the same database, then running migrations locally updates the same database production uses. In that setup, Render does not need to run migrations again during deployment.

Future caution: if local and production ever stop using the same database, migrations should be run intentionally as part of release operations.

### Email Sender Domain

Status: verified.

`EMAIL_FROM` defaults still reference:

```text
no-reply@email.giftpassionstory.com
```

User-facing support/help email references appear updated to:

```text
info@disciplesmade.com
```

Layman explanation: when users read help/support text in the app, they mostly see the new Disciples Made email. But the technical sender address used for outgoing automated emails still defaults to the older Gift Passion Story domain unless the environment overrides it.

Risk level: low to medium, depending on email/domain setup.

What could happen: users may receive automated emails from the old domain, which can look inconsistent with the new branding. If the old sender domain is not fully configured for email delivery, messages could also be more likely to land in spam or fail authentication checks.

### Production API Domain References

Status: verified.

Frontend CSP currently allows API calls to:

```text
https://gps-api-4q4m.onrender.com
```

Render frontend env also points `VITE_API_URL` to:

```text
https://gps-api-4q4m.onrender.com
```

The Stripe screenshot shows the public API domain:

```text
https://api.disciplesmade.com
```

Layman explanation: the app may still be configured in some places to call the older Render URL instead of the cleaner `api.disciplesmade.com` domain.

Risk level: medium if production is supposed to use `api.disciplesmade.com`.

What could happen: the frontend may keep talking to the Render subdomain. That can still work, but it may create confusion, CORS/CSP issues, mixed-domain behavior, or a harder migration later. If the Render subdomain changes or is disabled, the frontend could stop reaching the API.

**Partially resolved 2026-06-23 — commit `e6ebd4f`.** Project owner
confirmed `api.disciplesmade.com` is the intended public domain and
verified live (Render screenshot shows the custom domain attached to
`gps-api`; `curl https://api.disciplesmade.com/` returns HTTP 200 with
the Impact Dashboard API welcome). Frontend CSP `connect-src` updated
to allow the new domain; `web/.env.example` updated to recommend it.
The legacy `gps-api-4q4m.onrender.com` was intentionally kept in CSP
during the transition window so the frontend doesn't break if a deploy
lands before Render's `VITE_API_URL` env var is flipped.

**Operational follow-up (not code):** flip `VITE_API_URL` in Render →
gps-web → Environment from `https://gps-api-4q4m.onrender.com` to
`https://api.disciplesmade.com`, redeploy, verify, then ship a follow-up
commit removing the legacy entry from `connect-src`.

## Testing And Tooling Notes

### Automated Tests

Status: verified.

Backend scoring tests exist under `api/tests`.

Layman explanation: there are tests for the scoring logic, which is good because scoring is one of the core parts of the product. But I did not observe broad automated coverage for login/security flows, billing, Stripe webhooks, admin flows, notifications, or CRM webhooks.

Risk level: medium over time.

What could happen: future changes could accidentally break billing, login, webhooks, or admin behavior without an automated test catching it before deployment.

### CI Workflow

Status: not observed.

No GitHub Actions / CI workflow was observed.

Layman explanation: CI is the automatic checker that usually runs tests/builds when code is pushed. Without it, the team has to remember to run checks manually.

Risk level: medium over time.

What could happen: broken builds or failing tests may be discovered later than ideal.

### Dependency Versions

Status: partially verified.

Observed dependency notes:

- `api/requirements.txt` pins `python-multipart==0.0.22`.
- `web/package.json` allows `axios ^1.7.0`.
- `web/package-lock.json` currently resolves Axios to `1.13.6`.

Layman explanation: backend Python multipart handling is pinned to an older version. Frontend Axios is declared with an older minimum, but the lockfile currently installed a newer version.

Risk level: low to medium, depending on known vulnerability requirements.

What could happen: security scanners may continue to flag older pinned minimums, especially `python-multipart`. Axios may be less concerning if production installs from the lockfile and gets `1.13.6`, but the declared dependency range still starts at `1.7.0`.

## Brand Alignment Notes

Source reviewed: `brand elements - Impact Dashboard.pdf`.

The brand guide says the app should feel clean, spacious, high-contrast, and restrained. The core brand palette is Deep Teal `#0B6C80`, Gold `#F7A824`, Light Teal `#88C0C3`, Charcoal `#3F4644`, Light Gray `#E3E3E3`, and White `#FFFFFF`. Headlines should use Brandon Grotesque Medium/Black, body text should use Mulish, and Gold should be used sparingly for highlights/icons only.

### What Is Aligned

Status: verified.

The app does define the main brand colors in Tailwind and CSS variables:

- `brand-teal`: `#0B6C80`
- `brand-gold`: `#F7A824`
- `brand-teal-light`: `#88C0C3`
- `brand-charcoal`: `#3F4644`
- `brand-gray-light`: `#E3E3E3`
- `brand-gray-lightest`: `#F8F8F8`

The app also loads Mulish from Google Fonts and uses many `font-body`, `font-heading`, `bg-brand-teal`, `text-brand-charcoal`, and `border-brand-gray-light` classes across the newer pages.

Layman explanation: the project has the right brand ingredients available, and many newer screens are already using them.

### Brandon Grotesque Is Referenced But Not Loaded

Status: verified.

The Tailwind config says headings should use:

```text
Brandon Grotesque
```

But the HTML only loads Mulish from Google Fonts. I did not observe a local Brandon Grotesque font file in the repo.

Layman explanation: the code asks for Brandon Grotesque, but the app does not appear to actually provide that font. If a visitor's computer does not already have Brandon installed, the browser will quietly use a fallback sans-serif font instead.

Risk level: medium for visual brand accuracy.

What could happen: headings may look slightly different from the Figma files even if the CSS class names look correct. This directly matches Sherri's note that the fonts seem slightly off.

### Old Purple/Blue Styling Is Still Active

Status: verified.

`web/src/App.tsx` still imports `web/src/App.css`. That file contains older generic SaaS colors such as:

```text
#667eea
#764ba2
#5568d3
#a5b4fc
```

These create purple/blue gradients, buttons, borders, and links that are not part of the Disciples Made brand guide.

Other legacy CSS files also contain similar non-brand colors, including:

- `AssessmentResults.css`
- `MyImpactResults.css`
- `AuditLog.css`
- `SystemExport.css`
- `AssessmentHistory.css`
- `ChurchLinking.css`

Layman explanation: even though the app now has the correct brand colors, some older style sheets are still hanging around and can still paint parts of the app in the old blue/purple look.

Risk level: medium for brand consistency.

What could happen: some screens may look like the old generic app while other screens look like the newer Impact Dashboard brand. This can make the app feel visually inconsistent and can explain why colors look slightly off compared with Figma.

**Resolved 2026-06-23 — commit `ec87061`.** `web/src/App.css` colors
were surgically remapped to brand tokens while preserving every class
name and layout rule, so the consuming pages (ForgotPassword,
ResetPassword, AssessmentHistory, ChurchLinking, AuditLog) pick up the
fix automatically:

| Was | Now | Token |
|---|---|---|
| `#667eea` | `#0B6C80` | brand-teal |
| `#764ba2` | `#88C0C3` | brand-teal-light (gradient end) |
| `#5568d3` | `#095668` | darker teal (hover) |
| `#a5b4fc` | `#88C0C3` | brand-teal-light (disabled) |
| `#333` | `#3F4644` | brand-charcoal |
| `#666` | `#797E7C` | brand-gray-med |
| `#ddd` | `#E3E3E3` | brand-gray-light |
| `#f5f7fa` | `#F8F8F8` | brand-gray-lightest |

Semantic error colors (`#fee2e2` / `#dc2626`) were intentionally kept.
The auth hero now renders a teal → light-teal gradient instead of the
old indigo → purple. The other legacy CSS files listed above
(`AssessmentResults.css`, `MyImpactResults.css`, `AuditLog.css`,
`SystemExport.css`, `AssessmentHistory.css`, `ChurchLinking.css`)
remain untouched in this pass — flag separately if Sherri's team
calls them out.

### Too Many Non-Brand Status Colors

Status: verified.

The app uses several Tailwind status colors like blue, green, yellow, amber, purple, and red across notifications, password strength, billing status, webhook delivery status, alerts, and destructive actions.

Layman explanation: some of these colors are normal for error/success/warning states, but the brand guide specifically says not to introduce off-brand blues or greens and to use Gold sparingly.

Risk level: low to medium.

What could happen: the interface can feel busier and less brand-controlled than the guide intends. This is especially noticeable when blue/purple are used as regular UI colors rather than only as semantic status colors.

Suggested direction: keep red/green/yellow only where they communicate real system state, like error/success/warning. Avoid using blue/purple as decorative or default UI colors. Prefer Deep Teal, Charcoal, Light Teal, Light Gray, and White for normal interface styling.

### Gold Is Sometimes Used Like A Button Background

Status: verified.

The brand guide says Gold should be used sparingly for highlights, icons, and emphasis only. It also says an Accent Button with Gold is rare.

The app uses Gold for some full button backgrounds and labels, such as result actions and admin/master actions.

Layman explanation: Gold is supposed to be the sparkle, not the main paint. When it becomes a full button background too often, the brand starts to feel louder than the guide recommends.

Risk level: low to medium.

What could happen: important highlights may lose impact because Gold is no longer rare. Some screens may feel more colorful or promotional than the restrained brand guide intends.

### Cards And Corners Are Heavier Than The Guide Implies

Status: verified.

Many newer screens use `rounded-xl`, `rounded-2xl`, and strong shadows like:

```text
shadow-[0_4px_4px_rgba(0,0,0,0.25)]
shadow-xl
shadow-2xl
```

Layman explanation: the brand guide does not explicitly ban rounded cards or shadows, but it emphasizes white space, clean hierarchy, and restrained color. Heavy shadows and very rounded cards can make the product feel more like a generic dashboard template than a crisp brand system.

Risk level: low to medium.

What could happen: even when colors are correct, the UI may still feel slightly different from Figma because the shape language and shadows are heavier than expected.

Suggested direction: use lighter shadows, subtler borders, and less-rounded controls unless the Figma files intentionally use the larger radius.

### Tailwind Gray Is Used Alongside Brand Charcoal/Gray

Status: verified.

Some shared styles still use Tailwind default grays like `text-gray-800`, `text-gray-600`, `bg-gray-100`, `border-gray-200`, and similar values.

Layman explanation: these grays are not necessarily ugly or broken, but they are not the exact brand neutrals from the guide.

Risk level: low.

What could happen: text and UI containers may look close but not exact. This can produce the "slightly off" feeling when compared side-by-side with Figma.

Suggested direction: use `brand-charcoal`, `brand-gray-med`, `brand-gray-light`, `brand-gray-lightest`, and white for normal text, dividers, and containers.

### Overall Brand Deviation Summary

The app is not missing the brand system. It has the correct color tokens and Mulish loaded. The main deviations are:

1. Brandon Grotesque is referenced but not bundled/loaded.
2. Old purple/blue CSS is still imported and can affect screens.
3. Some pages mix brand colors with default Tailwind colors.
4. Gold is used more prominently than the guide recommends.
5. Shadows and rounded corners may be heavier than the clean, restrained guide suggests.

Plain English conclusion: the implementation is partway there. The newer app styling understands the brand, but older CSS and missing heading font support are likely why the app still feels "slightly off" compared with the Figma files.

## Suggested Follow-Up Priority

1. ~~Confirm whether Stripe Billing Portal should return to `/admin/billing`; if yes, update the backend return URL.~~ **Done 2026-06-23 — commit `ec87061`.**
2. Review Stripe webhook deduplication order so failed handlers can be retried safely. *(Project owner read this as an intentional, code-commented trade-off — leave-as-is unless a manual-reconciliation tool is wanted.)*
3. ~~Decide whether production API domain should be `https://api.disciplesmade.com`; if yes, align CSP and frontend env references.~~ **Done 2026-06-23 — commit `e6ebd4f` (CSP + .env.example).** Domain verified live (HTTP 200). Operational follow-up: flip `VITE_API_URL` in Render UI, then drop legacy `gps-api-4q4m.onrender.com` from CSP in a follow-up commit.
4. Confirm whether `EMAIL_FROM` should move from the old Gift Passion Story domain to a Disciples Made domain. *(Per project memory, `no-reply@email.giftpassionstory.com` is an intentional Resend-verified subdomain — not a misconfiguration. Reply-required flows use `info@disciplesmade.com`.)*
5. Add CI and broader regression tests when ready.

## Resolution Log

| Date | Commit | Item |
|---|---|---|
| 2026-06-23 | `ec87061` | A1 — Billing portal return URL `/billing` → `/admin/billing` |
| 2026-06-23 | `ec87061` | A2 — Replaced legacy indigo/purple in `App.css` with brand tokens |
| 2026-06-23 | `e6ebd4f` | B1 — Added `api.disciplesmade.com` to CSP `connect-src` + updated `.env.example` |
