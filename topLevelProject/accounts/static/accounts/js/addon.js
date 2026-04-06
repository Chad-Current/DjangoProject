/**
 * addon.js — Stripe one-time payment for the Password Vault add-on
 *
 * Config is read from #stripe-addon-config data attributes (injected by addon.html)
 * so that Django template tags are not needed inside a static JS file.
 */

(function () {
  'use strict';

  const configEl = document.getElementById('stripe-addon-config');
  if (!configEl) return; // Not on the add-on page

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

  cardElement.mount('#addon-card-element');

  cardElement.on('change', function (event) {
    document.getElementById('addon-card-errors').textContent = event.error ? event.error.message : '';
  });

  // Exposed globally so the inline onclick handler in addon.html can call it
  window.handleAddonPayment = async function () {
    const submitBtn  = document.getElementById('addon-submit-btn');
    const buttonText = document.getElementById('addon-button-text');
    const spinner    = document.getElementById('addon-spinner');
    const errorEl    = document.getElementById('addon-card-errors');
    const alertEl    = document.getElementById('addon-alert');

    submitBtn.disabled       = true;
    buttonText.style.display = 'none';
    spinner.style.display    = 'inline';
    errorEl.textContent      = '';
    alertEl.style.display    = 'none';

    try {
      // Step 1: Create PaymentIntent on backend → get client_secret
      const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

      const createRes = await fetch(CREATE_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({}),
      });
      const createData = await createRes.json();

      if (createData.error) throw new Error(createData.error);

      const { client_secret, payment_intent_id } = createData;

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
        body: JSON.stringify({ payment_intent_id }),
      });
      const confirmData = await confirmRes.json();

      if (confirmData.error) throw new Error(confirmData.error);

      // Success — redirect
      window.location.href = confirmData.redirect_url || '/dashboard/';

    } catch (err) {
      errorEl.textContent      = err.message;
      submitBtn.disabled        = false;
      buttonText.style.display  = 'inline';
      spinner.style.display     = 'none';
    }
  };
}());
