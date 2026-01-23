const stripe = Stripe('{{ STRIPE_PUBLISHABLE_KEY }}');
const elements = stripe.elements();

// Create card element
const cardElement = elements.create('card', {
    style: {
        base: {
            fontSize: '16px',
            color: '#32325d',
            '::placeholder': {
                color: '#aab7c4'
            }
        },
        invalid: {
            color: '#dc3545'
        }
    }
});

cardElement.mount('#card-element');

// Handle card errors
cardElement.on('change', function (event) {
    const displayError = document.getElementById('card-errors');
    if (event.error) {
        displayError.textContent = event.error.message;
    } else {
        displayError.textContent = '';
    }
});

// Modal functions
function openPaymentModal(tier, price) {
    document.getElementById('paymentModal').style.display = 'block';
    document.getElementById('selected-tier').value = tier;

    const tierName = tier.charAt(0).toUpperCase() + tier.slice(1);
    document.getElementById('modal-title').textContent = `Purchase ${tierName} Plan`;
    document.getElementById('modal-description').textContent =
        `You are about to purchase the ${tierName} plan for $${price.toFixed(2)}`;
    document.getElementById('button-text').textContent = `Pay $${price.toFixed(2)}`;
}

function closePaymentModal() {
    document.getElementById('paymentModal').style.display = 'none';
    document.getElementById('card-errors').textContent = '';
}

// Close modal when clicking outside
window.onclick = function (event) {
    const modal = document.getElementById('paymentModal');
    if (event.target === modal) {
        closePaymentModal();
    }
}

// Handle form submission
const form = document.getElementById('payment-form');
form.addEventListener('submit', async function (event) {
    event.preventDefault();

    const submitButton = document.getElementById('submit-payment');
    const spinner = document.getElementById('loading-spinner');
    const buttonText = document.getElementById('button-text');

    // Disable button and show loading
    submitButton.disabled = true;
    buttonText.style.display = 'none';
    spinner.style.display = 'block';

    try {
        // Create payment intent
        const tier = document.getElementById('selected-tier').value;
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        const response = await fetch('{% url "accounts:create_payment_intent" %}', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ tier: tier })
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Confirm payment with Stripe
        const result = await stripe.confirmCardPayment(data.client_secret, {
            payment_method: {
                card: cardElement,
                billing_details: {
                    email: '{{ user.email }}'
                }
            }
        });

        if (result.error) {
            // Show error
            document.getElementById('card-errors').textContent = result.error.message;
            submitButton.disabled = false;
            buttonText.style.display = 'inline';
            spinner.style.display = 'none';
        } else {
            // Payment successful
            if (result.paymentIntent.status === 'succeeded') {
                // Confirm with backend
                const confirmResponse = await fetch('{% url "accounts:confirm_payment" %}', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        payment_intent_id: result.paymentIntent.id,
                        tier: tier
                    })
                });

                const confirmData = await confirmResponse.json();

                if (confirmData.success) {
                    // Redirect to dashboard
                    window.location.href = '{% url "accounts:account_dashboard" %}';
                } else {
                    throw new Error('Payment confirmation failed');
                }
            }
        }
    } catch (error) {
        document.getElementById('card-errors').textContent = error.message;
        submitButton.disabled = false;
        buttonText.style.display = 'inline';
        spinner.style.display = 'none';
    }
});