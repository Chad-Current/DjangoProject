# accounts/views.py
import json
import stripe
import logging
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.views import View
from django.views.generic import TemplateView
from django.contrib import messages
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from datetime import timedelta
from .forms import UserRegistrationForm, UserLoginForm, CustomPasswordResetForm, CustomSetPasswordForm

User = get_user_model()
logger = logging.getLogger(__name__)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


# ── Pricing constants ─────────────────────────────────────────────────────────
PRICES = {
    'essentials': {'annual': 59.99, 'monthly': 5.99},
    'legacy':     {'annual': 99.99, 'monthly': 9.99},
}


def _get_price_id(tier, interval):
    """Return the Stripe Price ID for the given tier and billing interval."""
    mapping = {
        ('essentials', 'annual'):  settings.STRIPE_ESSENTIALS_ANNUAL_PRICE_ID,
        ('essentials', 'monthly'): settings.STRIPE_ESSENTIALS_MONTHLY_PRICE_ID,
        ('legacy',     'annual'):  settings.STRIPE_LEGACY_ANNUAL_PRICE_ID,
        ('legacy',     'monthly'): settings.STRIPE_LEGACY_MONTHLY_PRICE_ID,
    }
    return mapping.get((tier, interval), '')


# ── Auth views ────────────────────────────────────────────────────────────────

class RegisterView(View):
    template_name = 'accounts/register.html'
    form_class = UserRegistrationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        plan = request.GET.get('plan', '').lower()
        if plan in ('free','essentials', 'legacy'): #CHANGE MADE FOR FREE TIER
            request.session['plan_intent'] = plan
        context = {
            'form': self.form_class(),
            'plan_intent': request.session.get('plan_intent', ''),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            if hasattr(user, 'last_login_ip'):
                user.last_login_ip = get_client_ip(request)
                user.save(update_fields=['last_login_ip'])
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            logger.info(f'New user registered: {user.email}')
            return redirect('dashboard:profile_create')
        return render(request, self.template_name, {
            'form': form,
            'plan_intent': request.session.get('plan_intent', ''),
        })


class LoginView(View):
    template_name = 'accounts/login.html'
    form_class = UserLoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard:dashboard_home')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {'form': self.form_class()})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data.get('username_or_email')
            password = form.cleaned_data.get('password')
            auth_user = authenticate(request, username=username_or_email, password=password)

            if auth_user is not None:
                account_locked_until = getattr(auth_user, 'account_locked_until', None)
                if account_locked_until and timezone.now() < account_locked_until:
                    messages.error(request, 'Account is temporarily locked due to multiple failed login attempts.')
                    return render(request, self.template_name, {'form': form})

                if hasattr(auth_user, 'failed_login_attempts'):
                    auth_user.failed_login_attempts = 0
                    auth_user.account_locked_until = None
                if hasattr(auth_user, 'last_login_ip'):
                    auth_user.last_login_ip = get_client_ip(request)
                auth_user.save()

                login(request, auth_user)
                request.session.set_expiry(3600)
                logger.info(f'User logged in: {auth_user.username}')

                if request.user.has_paid:
                    return redirect('dashboard:dashboard_home')
                else:
                    return redirect('accounts:payment')
            else:
                try:
                    from django.db.models import Q
                    user = User.objects.get(
                        Q(username__iexact=username_or_email) | Q(email__iexact=username_or_email)
                    )
                    if hasattr(user, 'failed_login_attempts'):
                        user.failed_login_attempts += 1
                        if user.failed_login_attempts >= 5:
                            user.account_locked_until = timezone.now() + timedelta(minutes=30)
                            messages.error(request, 'Account locked for 30 minutes due to multiple failed attempts.')
                        else:
                            messages.error(request, f'Invalid credentials. {5 - user.failed_login_attempts} attempts remaining.')
                        user.save()
                    else:
                        messages.error(request, 'Invalid credentials.')
                except User.DoesNotExist:
                    messages.error(request, 'Invalid credentials.')
                logger.warning(f'Failed login attempt for: {username_or_email}')

        return render(request, self.template_name, {'form': form})


class LogoutView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

    def get(self, request):
        user_email = request.user.email
        logout(request)
        logger.info(f'User logged out: {user_email}')
        messages.success(request, 'You have been logged out.')
        return redirect('accounts:login')

    def post(self, request):
        return self.get(request)


# ── Payment / Subscription views ──────────────────────────────────────────────

class PaymentView(LoginRequiredMixin, View):
    """Pricing page — lets users choose a subscription tier and billing interval."""
    template_name = 'accounts/payment.html'
    login_url = '/accounts/login/'

    def get(self, request):
        if request.user.is_subscription_active():
            # messages.info(request, 'You already have an active subscription.')
            return redirect('dashboard:dashboard_home')

        plan_intent = request.session.get('plan_intent', '')
        context = {
            'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
            'essentials_annual_price': PRICES['essentials']['annual'],
            'essentials_monthly_price': PRICES['essentials']['monthly'],
            'legacy_annual_price': PRICES['legacy']['annual'],
            'legacy_monthly_price': PRICES['legacy']['monthly'],
            'plan_intent': plan_intent,
        }
        return render(request, self.template_name, context)


class CreateSubscriptionView(LoginRequiredMixin, View):
    """
    AJAX endpoint: creates a Stripe Customer (if needed) and a Subscription.
    Returns the client_secret from the first invoice's PaymentIntent so the
    frontend can confirm the card payment.
    """
    login_url = '/accounts/login/'

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            data = json.loads(request.body)
            tier = data.get('tier', '').lower()
            interval = data.get('interval', '').lower()
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Invalid request body.'}, status=400)

        if tier not in ('essentials', 'legacy') or interval not in ('annual', 'monthly'):
            return JsonResponse({'error': 'Invalid tier or billing interval.'}, status=400)

        price_id = _get_price_id(tier, interval)
        if not price_id:
            return JsonResponse({'error': 'Stripe price not configured for this plan. Please contact support.'}, status=500)

        user = request.user

        try:
            # Create or retrieve Stripe customer
            if user.stripe_customer_id:
                customer = stripe.Customer.retrieve(user.stripe_customer_id)
            else:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=f"{user.first_name} {user.last_name}".strip() or user.username,
                    metadata={'user_id': user.pk, 'username': user.username},
                )
                user.stripe_customer_id = customer.id
                user.save(update_fields=['stripe_customer_id'])

            # Create subscription (incomplete until payment is confirmed)
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': price_id}],
                payment_behavior='default_incomplete',
                payment_settings={'save_default_payment_method': 'on_subscription'},
                expand=['latest_invoice.payment_intent'],
                metadata={'user_id': user.pk, 'tier': tier, 'interval': interval},
            )

            client_secret = subscription.latest_invoice.payment_intent.client_secret
            return JsonResponse({
                'client_secret': client_secret,
                'subscription_id': subscription.id,
            })

        except stripe.error.StripeError as e:
            logger.error(f'Stripe error creating subscription for {user.email}: {e}')
            return JsonResponse({'error': str(e.user_message)}, status=400)
        except Exception as e:
            logger.error(f'Unexpected error creating subscription for {user.email}: {e}')
            return JsonResponse({'error': 'An unexpected error occurred. Please try again.'}, status=500)


class ConfirmSubscriptionView(LoginRequiredMixin, View):
    """
    AJAX endpoint: called after stripe.confirmCardPayment succeeds on the frontend.
    Retrieves the subscription from Stripe, verifies it is active, and activates
    the user's account.
    """
    login_url = '/accounts/login/'

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            data = json.loads(request.body)
            subscription_id = data.get('subscription_id', '')
            tier = data.get('tier', '').lower()
            interval = data.get('interval', '').lower()
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Invalid request body.'}, status=400)

        if not subscription_id:
            return JsonResponse({'error': 'Missing subscription ID.'}, status=400)

        user = request.user

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)

            if subscription.status != 'active':
                return JsonResponse({'error': f'Subscription is not active (status: {subscription.status}).'}, status=400)

            import datetime
            period_end = datetime.datetime.fromtimestamp(
                subscription.current_period_end, tz=datetime.timezone.utc
            )

            user.activate_subscription(
                tier=tier,
                stripe_customer_id=subscription.customer,
                stripe_subscription_id=subscription.id,
                interval=interval,
                current_period_end=period_end,
                cancel_at_period_end=subscription.cancel_at_period_end,
            )

            logger.info(f'User {user.email} activated {tier} ({interval}) subscription')
            return JsonResponse({
                'success': True,
                'redirect_url': '/accounts/subscription/success/',
            })

        except stripe.error.StripeError as e:
            logger.error(f'Stripe error confirming subscription for {user.email}: {e}')
            return JsonResponse({'error': str(e.user_message)}, status=400)
        except Exception as e:
            logger.error(f'Unexpected error confirming subscription for {user.email}: {e}')
            return JsonResponse({'error': 'An unexpected error occurred.'}, status=500)


class SubscriptionSuccessView(LoginRequiredMixin, TemplateView):
    """Shown after a successful subscription payment."""
    template_name = 'accounts/subscription_success.html'
    login_url = '/accounts/login/'


class ManageSubscriptionView(LoginRequiredMixin, View):
    """Shows current subscription details and allows cancellation."""
    template_name = 'accounts/subscription_manage.html'
    login_url = '/accounts/login/'

    def get(self, request):
        user = request.user
        stripe_sub = None
        stripe_error = None

        if user.stripe_subscription_id:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            try:
                stripe_sub = stripe.Subscription.retrieve(user.stripe_subscription_id)
            except stripe.error.StripeError as e:
                stripe_error = str(e.user_message)

        context = {
            'user': user,
            'stripe_sub': stripe_sub,
            'stripe_error': stripe_error,
            'prices': PRICES,
        }
        return render(request, self.template_name, context)


class CancelSubscriptionView(LoginRequiredMixin, View):
    """Cancels the user's subscription at the end of the current billing period."""
    login_url = '/accounts/login/'

    def post(self, request):
        user = request.user
        if not user.stripe_subscription_id:
            messages.error(request, 'No active subscription found.')
            return redirect('accounts:subscription_manage')

        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            stripe.Subscription.modify(
                user.stripe_subscription_id,
                cancel_at_period_end=True,
            )
            user.subscription_cancel_at_period_end = True
            user.save(update_fields=['subscription_cancel_at_period_end'])
            messages.success(
                request,
                'Your subscription will be canceled at the end of the current billing period. '
                'You will retain access until then.'
            )
            logger.info(f'User {user.email} scheduled subscription cancellation')
        except stripe.error.StripeError as e:
            messages.error(request, f'Could not cancel subscription: {e.user_message}')

        return redirect('accounts:subscription_manage')


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    Receives and processes Stripe webhook events.
    Keeps subscription status in sync with Stripe.
    Must NOT require login — called by Stripe servers.
    """

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)

        stripe.api_key = settings.STRIPE_SECRET_KEY
        event_type = event['type']
        data_object = event['data']['object']

        if event_type in ('customer.subscription.updated', 'customer.subscription.deleted'):
            self._handle_subscription_event(data_object)

        elif event_type == 'invoice.payment_succeeded':
            sub_id = data_object.get('subscription')
            if sub_id:
                try:
                    sub = stripe.Subscription.retrieve(sub_id)
                    self._handle_subscription_event(sub)
                except stripe.error.StripeError:
                    pass

        elif event_type == 'invoice.payment_failed':
            sub_id = data_object.get('subscription')
            if sub_id:
                try:
                    user = User.objects.get(stripe_subscription_id=sub_id)
                    user.update_subscription_status('past_due')
                    logger.warning(f'Payment failed for user {user.email}')
                except User.DoesNotExist:
                    pass

        return HttpResponse(status=200)

    def _handle_subscription_event(self, subscription):
        """Update the user's subscription status from a Stripe Subscription object."""
        sub_id = subscription.get('id') or subscription.id
        try:
            user = User.objects.get(stripe_subscription_id=sub_id)
        except User.DoesNotExist:
            logger.warning(f'Webhook: no user found for subscription {sub_id}')
            return

        import datetime
        status = subscription.get('status') or subscription.status
        cancel_at_period_end = subscription.get('cancel_at_period_end', False)
        period_end_ts = subscription.get('current_period_end') or getattr(subscription, 'current_period_end', None)
        period_end = None
        if period_end_ts:
            period_end = datetime.datetime.fromtimestamp(period_end_ts, tz=datetime.timezone.utc)

        user.update_subscription_status(status, period_end, cancel_at_period_end)
        logger.info(f'Webhook updated subscription for {user.email}: status={status}')


class UpgradeSubscriptionView(LoginRequiredMixin, View):
    """
    Upgrades an active Essentials subscription to Legacy in Stripe using
    subscription item modification + proration. No cancellation required.
    """
    login_url = '/accounts/login/'

    def post(self, request):
        user = request.user

        if user.subscription_tier != 'essentials' or not user.is_subscription_active():
            messages.error(request, 'Upgrade is only available for active Essentials subscribers.')
            return redirect('accounts:subscription_manage')

        new_price_id = _get_price_id('legacy', user.subscription_interval)
        if not new_price_id:
            messages.error(request, 'Legacy price not configured. Please contact support.')
            return redirect('accounts:subscription_manage')

        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            sub = stripe.Subscription.retrieve(user.stripe_subscription_id)
            current_item_id = sub['items']['data'][0]['id']

            updated_sub = stripe.Subscription.modify(
                user.stripe_subscription_id,
                items=[{'id': current_item_id, 'price': new_price_id}],
                proration_behavior='always_invoice',
                metadata={'user_id': user.pk, 'tier': 'legacy', 'interval': user.subscription_interval},
            )

            import datetime
            period_end = datetime.datetime.fromtimestamp(
                updated_sub.current_period_end, tz=datetime.timezone.utc
            )

            user.activate_subscription(
                tier='legacy',
                stripe_customer_id=updated_sub.customer,
                stripe_subscription_id=updated_sub.id,
                interval=user.subscription_interval,
                current_period_end=period_end,
                cancel_at_period_end=updated_sub.cancel_at_period_end,
            )

            logger.info(f'User {user.email} upgraded Essentials → Legacy ({user.subscription_interval})')
            messages.success(
                request,
                'You have been upgraded to Legacy! The prorated difference has been charged to your card.'
            )

        except stripe.error.StripeError as e:
            logger.error(f'Stripe error upgrading subscription for {user.email}: {e}')
            messages.error(request, f'Could not process upgrade: {e.user_message}')

        return redirect('accounts:subscription_manage')


# ── Password Reset views ──────────────────────────────────────────────────────

class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.txt'
    html_email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')

    def form_valid(self, form):
        messages.success(self.request, 'Password reset email has been sent.')
        return super().form_valid(form)


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('password_reset_complete')

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been reset successfully.')
        return super().form_valid(form)


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'


# ── View aliases ──────────────────────────────────────────────────────────────
register_view = RegisterView.as_view()
login_view = LoginView.as_view()
logout_view = LogoutView.as_view()
payment_view = PaymentView.as_view()
create_subscription_view = CreateSubscriptionView.as_view()
confirm_subscription_view = ConfirmSubscriptionView.as_view()
subscription_success_view = SubscriptionSuccessView.as_view()
manage_subscription_view = ManageSubscriptionView.as_view()
cancel_subscription_view = CancelSubscriptionView.as_view()
upgrade_subscription_view = UpgradeSubscriptionView.as_view()
stripe_webhook_view = StripeWebhookView.as_view()
password_reset_view = CustomPasswordResetView.as_view()
password_reset_done_view = CustomPasswordResetDoneView.as_view()
password_reset_confirm_view = CustomPasswordResetConfirmView.as_view()
password_reset_complete_view = CustomPasswordResetCompleteView.as_view()
