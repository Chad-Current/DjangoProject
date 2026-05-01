Stripe Payment Integration Plan
Context
The project has a payment UI already built (pricing cards, Stripe modal, partial JS) but the backend payment processing was never wired up. Currently PaymentView.post() and AddonView.post() directly call upgrade_to_essentials() / upgrade_to_legacy() / activate_addon() without any real payment. The payment.js static file also references Django template tags ({{ STRIPE_PUBLISHABLE_KEY }}, {% url ... %}) which don't work in static files.

This plan wires up real Stripe card payments for all three purchase paths:

Essentials — $297 one-time
Legacy — $597 one-time
Add-On — $99.99/year
The project stays in Stripe test mode until the user explicitly switches to live keys.

Step 0 — Create Stripe Account & Get Test Keys (User Action Required)
Go to https://stripe.com and create a free account
After confirming your email, go to Developers → API keys in the dashboard
Copy the Publishable key (starts with pk_test_)
Copy the Secret key (starts with sk_test_) — click "Reveal test key"
Create a file named .env at topLevelProject/ (same folder as manage.py) with:
STRIPE_PUBLISHABLE_KEY=pk_test_REPLACE_WITH_YOUR_KEY
STRIPE_SECRET_KEY=sk_test_REPLACE_WITH_YOUR_KEY
For test card numbers during testing, use 4242 4242 4242 4242, expiry 12/34, CVC 123
Files to Create or Modify
1. requirements.txt
Add stripe package after the cryptography entry:

stripe==11.3.0
2. topLevelProject/topLevelProject/settings.py
Add at the top, after existing imports:

from decouple import config
Add at the bottom:

# Stripe (test mode — swap to live keys in production)
STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY', default='')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
3. accounts/views.py — Add 4 new views, update existing 2
Add imports:

import stripe
import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
New view: CreatePaymentIntentView

POST only, LoginRequiredMixin
Reads tier from JSON body (essentials → 29700 cents, legacy → 59700 cents)
Sets stripe.api_key = settings.STRIPE_SECRET_KEY
Creates stripe.PaymentIntent.create(amount=..., currency='usd', metadata={'user_id': ..., 'tier': ...})
Returns JsonResponse({'client_secret': intent.client_secret})
On stripe.error.StripeError: returns JsonResponse({'error': str(e)}, status=400)
New view: ConfirmPaymentView

POST only, LoginRequiredMixin
Reads payment_intent_id and tier from JSON body
Retrieves stripe.PaymentIntent.retrieve(payment_intent_id)
Verifies intent.status == 'succeeded' AND intent.metadata['user_id'] == str(request.user.id)
If valid: calls upgrade_to_essentials() or upgrade_to_legacy(), returns JsonResponse({'success': True})
On failure: returns JsonResponse({'error': '...'}, status=400)
New view: CreateAddonPaymentIntentView

Same pattern, fixed amount 9999 cents ($99.99)
Checks request.user.is_eligible_for_addon() first
New view: ConfirmAddonPaymentView

Same verification pattern
On success: calls request.user.activate_addon()
Update PaymentView.get():

Fix prices: essentials_price: 297, legacy_price: 597
Add 'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY to context
Update PaymentView.post():

Remove the direct tier upgrade logic (this is now handled by ConfirmPaymentView)
Return JsonResponse({'error': 'Use the payment form'}, status=400) as fallback
Update AddonView.get():

Add 'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY to context
Update AddonView.post():

Remove direct activate_addon() call (now handled by ConfirmAddonPaymentView)
4. accounts/urls.py
Add 4 new URL patterns:

path('create-payment-intent/', views.create_payment_intent_view, name='create_payment_intent'),
path('confirm-payment/', views.confirm_payment_view, name='confirm_payment'),
path('create-addon-payment-intent/', views.create_addon_payment_intent_view, name='create_addon_payment_intent'),
path('confirm-addon-payment/', views.confirm_addon_payment_view, name='confirm_addon_payment'),
5. accounts/templates/accounts/payment.html
Fix the template tag issue — static JS files are not processed by Django's template engine, so {{ STRIPE_PUBLISHABLE_KEY }} doesn't render. Solution: pass values through data attributes on a hidden config div.

Replace the inline <script> block with a data-* config div:

<div id="payment-config" hidden
     data-stripe-key="{{ stripe_publishable_key }}"
     data-create-url="{% url 'accounts:create_payment_intent' %}"
     data-confirm-url="{% url 'accounts:confirm_payment' %}"
     data-redirect-url="{% url 'dashboard:dashboard_home' %}"
     data-user-email="{{ user.email }}">
</div>
Remove the duplicate openPaymentModal / closePaymentModal inline JS (these already exist in payment.js).

6. accounts/static/accounts/js/payment.js
Rewrite to read values from data attributes instead of Django template tags:

const cfg = document.getElementById('payment-config').dataset;
const stripe = Stripe(cfg.stripeKey);
// fetch(cfg.createUrl, ...) instead of {% url ... %}
// billing_details email: cfg.userEmail
// redirect: window.location.href = cfg.redirectUrl
7. accounts/templates/accounts/addon.html
Add Stripe.js script tag: <script src="https://js.stripe.com/v3/"></script>
Add a config div with data attributes (addon payment intent URL, confirm URL)
Add a Stripe card element <div id="addon-card-element"> to the payment form
Add <div id="addon-card-errors"> for inline errors
Replace the form submit button with a Stripe-backed one
8. accounts/static/accounts/js/addon_payment.js (new file)
Same pattern as payment.js but for addon:

Reads config from #addon-payment-config data attributes
Creates card element on #addon-card-element
On submit: creates addon payment intent → confirms card → confirms with backend → redirects
Price Reference (Stripe uses cents)
Product	Display	Stripe cents
Essentials	$297.00	29700
Legacy	$597.00	59700
Add-On	$99.99	9999
Security Notes
Never expose STRIPE_SECRET_KEY in templates or JS
Always re-verify PaymentIntent status server-side — never trust client-only confirmation
Verify metadata['user_id'] matches request.user.id to prevent users confirming others' payments
.env file must be in .gitignore (add if not already present)
Verification
pip install stripe (or pip install -r requirements.txt after updating)
Create .env with test keys from Stripe dashboard
python manage.py runserver
Register a new demo account, go to /accounts/payment/
Click "Get Essentials", enter test card 4242 4242 4242 4242 | 12/34 | 123
Verify payment succeeds in Stripe test dashboard under Payments
Verify user's subscription_tier changed to essentials and has_paid=True in Django admin
Repeat for Legacy tier and Add-On
Test card decline with 4000 0000 0000 0002 — verify error message shown
Production Checklist (before going live)
Replace pk_test_ / sk_test_ keys with live keys in production environment
Add Stripe webhook endpoint (/accounts/stripe-webhook/) for payment event reliability
Set SESSION_COOKIE_SECURE = True, SECURE_SSL_REDIRECT = True