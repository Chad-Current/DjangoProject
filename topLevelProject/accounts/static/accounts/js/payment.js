/**
 * payment.js — Stripe subscription checkout
 *
 * Config is read from #stripe-config data attributes (injected by payment.html)
 * so that Django template tags are not needed inside a static JS file.
 */

(function () {
  'use strict';

  const configEl = document.getElementById('stripe-config');
  if (!configEl) return; // Not on the payment page

  const PUBLISHABLE_KEY = configEl.dataset.publishableKey;
  const CREATE_URL      = configEl.dataset.createUrl;
  const CONFIRM_URL     = configEl.dataset.confirmUrl;
  const USER_EMAIL      = configEl.dataset.userEmail;

  if (!PUBLISHABLE_KEY) {
    console.warn('Stripe publishable key is not configured.');
    return;
  }

  const stripe   = Stripe(PUBLISHABLE_KEY);
  const elements = stripe.elements();

  const cardElement = elements.create('card', {
    style: {
      base: {
        fontSize: '16px',
        color: '#32325d',
        '::placeholder': { color: '#aab7c4' },
      },
      invalid: { color: '#dc3545' },
    },
  });

  cardElement.mount('#card-element');

  cardElement.on('change', function (event) {
    document.getElementById('card-errors').textContent = event.error ? event.error.message : '';
  });

  // Exposed globally so the inline onclick handler in payment.html can call it
  window.handleSubscribe = async function () {
    const tier     = window.currentTier;
    const interval = window.currentBillingInterval;

    if (!tier || !interval) {
      document.getElementById('card-errors').textContent = 'Please select a plan.';
      return;
    }

    const submitBtn  = document.getElementById('submit-payment');
    const buttonText = document.getElementById('button-text');
    const spinner    = document.getElementById('loading-spinner');
    const errorEl    = document.getElementById('card-errors');

    submitBtn.disabled      = true;
    buttonText.style.display = 'none';
    spinner.style.display    = 'block';
    errorEl.textContent      = '';

    try {
      // Step 1: Create subscription on backend → get client_secret
      const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

      const createRes = await fetch(CREATE_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ tier, interval }),
      });
      const createData = await createRes.json();

      if (createData.error) throw new Error(createData.error);

      const { client_secret, subscription_id } = createData;

      // Step 2: Confirm card payment with Stripe
      const { error: stripeError, paymentIntent } = await stripe.confirmCardPayment(client_secret, {
        payment_method: {
          card: cardElement,
          billing_details: { email: USER_EMAIL },
        },
      });

      if (stripeError) throw new Error(stripeError.message);

      if (paymentIntent.status !== 'succeeded') {
        throw new Error('Payment did not complete. Please try again.');
      }

      // Step 3: Confirm activation on backend
      const confirmRes = await fetch(CONFIRM_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ subscription_id, tier, interval }),
      });
      const confirmData = await confirmRes.json();

      if (confirmData.error) throw new Error(confirmData.error);

      // Success — redirect
      window.location.href = confirmData.redirect_url || '/accounts/subscription/success/';

    } catch (err) {
      errorEl.textContent      = err.message;
      submitBtn.disabled        = false;
      buttonText.style.display  = 'inline';
      spinner.style.display     = 'none';
    }
  };
}());
