# Pricing Strategy — Digital Estate Planning SaaS

**Date:** 2026-03-24

---

## Competitive Landscape

| Competitor | Pricing |
|------------|---------|
| Everplans | ~$75/year or ~$199 lifetime |
| Clocr | ~$99/year |
| Cake | Free (ad/lead-gen model) |
| Lantern | Free basic |
| My Wonderful Life | Free (basic) |

This product (encrypted vault, recovery system, multi-category planning) is more feature-rich than the free options and competes directly with Everplans and Clocr.

---

## Recommended Price Points

| Tier | Price | Access |
|------|-------|--------|
| **Free** | $0 | Limited: view-only or ~5 accounts, no vault, no document uploads |
| **Essentials** | $39/year | Full edit access for 1 year; renew annually to maintain edit access |
| **Legacy** | $99 one-time | Lifetime full edit access |

---

## Tier Details

### Free Tier — $0
- View-only access or limited entry (e.g., up to 5 accounts)
- No encrypted vault access
- No document uploads
- No trusted contacts / recovery contacts
- Goal: drive top-of-funnel; let users feel the feature wall naturally

### Essentials — $39/year
- Full edit access for 1 year from payment date
- Access to all dashboard sections (accounts, devices, documents, funeral plan, etc.)
- Encrypted vault access (infrapps)
- Trusted contact delegation
- After expiry: drops to **read-only** — user must repurchase to edit again
- **Important:** Market this explicitly as a 1-year access purchase, not a recurring subscription, to avoid confusion

### Legacy — $99 one-time
- Lifetime full edit access — never expires
- All Essentials features included
- Best for users who want permanent peace of mind without annual renewal decisions

---

## Pricing Rationale

### Why $39/year for Essentials
- General consumers are price-sensitive; $49+ becomes a "think about it" purchase
- With paid social media ads, customer acquisition cost (CAC) is estimated at **$15–40** per paid user in this niche
- At $39, year 1 is near break-even on ad spend; **year 2 renewal is profit**
- $39 clears the psychological threshold for an impulse/low-friction annual purchase
- Positions below Everplans ($75/year) while offering comparable or better features

### Why $99 one-time for Legacy
- ~2.5x the annual price — standard lifetime deal ratio
- Signals confidence in product longevity (anything under $79 undersells it)
- With moderate cloud/storage costs, $99 covers approximately 3–4 years of per-user infrastructure
- After that breakeven point, renewals and new users fund ongoing Legacy users
- Converts the most committed users at a premium

---

## Free Tier Strategy

Make the free tier genuinely useful but let users naturally hit the feature wall:

- Store up to 3–5 accounts
- 1 document upload
- No vault access
- No trusted contacts
- Read-only forever (never lock out view access — keeps users returning)

The goal is that a user fills out the free tier, realizes the value, and upgrades to edit more or unlock the vault.

---

## Key Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Users confuse Essentials for a recurring subscription | Clearly label as "1-Year Access" in all marketing and checkout copy |
| Legacy pricing too low long-term as infra costs grow | Re-evaluate Legacy price annually; grandfather existing users |
| Low renewal rate after year 1 (Essentials) | Email reminders at 30/7/1 days before expiry; highlight data they'd lose edit access to |
| Paid ad CAC exceeds $39 breakeven | Test with small budget first; adjust bids or target older demographics (50+) who convert better |

---

## Revenue Targets (Side Income Goal)

| Monthly Goal | Required Paid Users | Notes |
|-------------|---------------------|-------|
| $500/mo | ~155 active Essentials users | Or ~40 Legacy sales/month |
| $1,000/mo | ~310 active Essentials users | Realistic with consistent paid traffic |
| $2,000/mo | ~620 active Essentials users | Requires scaling ad spend |

Note: Legacy sales are one-time; Essentials renewals build compounding MRR equivalent.

---

## Next Steps

- [ ] Research Everplans and Clocr checkout flows for UX benchmarks
- [ ] Implement Stripe for Essentials (annual) and Legacy (one-time) payments
- [ ] Define exact feature gates for the Free tier in code
- [ ] Write clear marketing copy distinguishing "1-Year Access" vs "Lifetime Access"
- [ ] Set up renewal reminder email sequences for Essentials users
- [ ] A/B test $39 vs $29 Essentials after first 50 paid users

---

*Strategy based on: general consumer target market, paid social media acquisition, moderate infrastructure costs, side-income revenue goal.*



<!-- Full Stripe Implemenation -->
What was changed
New pricing (subscriptions replace one-time payments)
Plan	Annual	Monthly
Essentials	$39.99/yr	$3.99/mo
Legacy	$59.99/yr	$5.99/mo
Files modified
File	Change
requirements.txt	Added stripe==11.3.0
settings.py	Added STRIPE_PUBLISHABLE_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, and 4 Price ID settings
accounts/models.py	Added 6 Stripe fields; new activate_subscription(), update_subscription_status(), deactivate_subscription() methods; updated can_modify_data() / can_view_data() for subscription-based access; backward compat with old one-time users preserved
accounts/views.py	Added CreateSubscriptionView, ConfirmSubscriptionView, SubscriptionSuccessView, ManageSubscriptionView, CancelSubscriptionView, StripeWebhookView
accounts/urls.py	Added 6 new URL patterns
accounts/templates/accounts/payment.html	Annual/Monthly billing toggle, new prices, #stripe-config data div for JS config
accounts/static/accounts/js/payment.js	Full rewrite — reads config from data attributes (fixes broken Django template tags in static file), implements 3-step subscription flow
accounts/static/accounts/css/payment.css	Added billing toggle styles
accounts/admin.py	Stripe fields added to admin
accounts/apps.py	Added ready() to register signals
accounts/signals.py	Updated for subscription model (activation + cancellation emails)
Files created
accounts/templates/accounts/subscription_success.html — Post-payment confirmation page
accounts/templates/accounts/subscription_manage.html — Manage/cancel subscription page
accounts/migrations/0004_customuser_stripe_customer_id_and_more.py — DB migration for new fields
Before going live, you need to
Install Stripe: pip install stripe==11.3.0

Run the migration: python manage.py migrate

Create 4 Price IDs in your Stripe Dashboard:

Essentials Annual — $39.99/year recurring
Essentials Monthly — $3.99/month recurring
Legacy Annual — $59.99/year recurring
Legacy Monthly — $5.99/month recurring
Add to your .env file:


STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_ESSENTIALS_ANNUAL_PRICE_ID=price_...
STRIPE_ESSENTIALS_MONTHLY_PRICE_ID=price_...
STRIPE_LEGACY_ANNUAL_PRICE_ID=price_...
STRIPE_LEGACY_MONTHLY_PRICE_ID=price_...
Register the webhook in Stripe Dashboard: Point it to https://yourdomain.com/accounts/webhook/stripe/ and subscribe to customer.subscription.updated, customer.subscription.deleted, invoice.payment_succeeded, invoice.payment_failed.