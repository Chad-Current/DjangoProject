from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta


class CustomUser(AbstractUser):
    """
    Custom user model for the Stripe recurring subscription model.

    Subscription tiers:
        none        — No active subscription (read-only or no access)
        essentials  — Full edit access while subscription is active ($39.99/yr or $3.99/mo)
        legacy      — Full edit access while subscription is active ($59.99/yr or $5.99/mo)
    """

    TIER_CHOICES = [
        ('none', 'No Subscription'),
        ('essentials', 'Essentials'),
        ('legacy', 'Legacy'),
    ]

    SUBSCRIPTION_STATUS_CHOICES = [
        ('', 'Not Set'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('incomplete', 'Incomplete'),
        ('incomplete_expired', 'Incomplete Expired'),
        ('trialing', 'Trialing'),
        ('unpaid', 'Unpaid'),
    ]

    INTERVAL_CHOICES = [
        ('', 'Not Set'),
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ]

    FREE_TIER_LIMITS = {
        'contacts': 2,
        'accounts': 1,
        'devices': 1,
        'estate_documents': 1,
        'important_documents': 1,
        'family_awareness': 2,
    }

    ESSENTIAL_TIER_LIMITS = {
        'contacts': 3,
        'accounts': 3,
        'devices': 3,
        'estate_documents': 3,
        'important_documents': 5,
        'family_awareness': 5,
    }
    
    # ── Basic fields ──────────────────────────────────────────────────────────
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)

    # ── Subscription tier ─────────────────────────────────────────────────────
    subscription_tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default='none',
        help_text="User's subscription tier",
    )

    # ── Payment tracking (kept for backward compat with legacy one-time users) ─
    has_paid = models.BooleanField(
        default=False,
        help_text="User has completed at least one payment (used for view-only access after cancellation)",
    )
    payment_date = models.DateTimeField(
        null=True, blank=True,
        help_text="Date of most recent payment or subscription start",
    )

    # ── Stripe subscription fields ────────────────────────────────────────────
    stripe_customer_id = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Stripe customer ID (cus_...)",
    )
    stripe_subscription_id = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Stripe subscription ID (sub_...)",
    )
    subscription_status = models.CharField(
        max_length=30, blank=True, default='',
        choices=SUBSCRIPTION_STATUS_CHOICES,
        help_text="Current Stripe subscription status",
    )
    subscription_interval = models.CharField(
        max_length=10, blank=True, default='',
        choices=INTERVAL_CHOICES,
        help_text="Billing interval: monthly or annual",
    )
    subscription_current_period_end = models.DateTimeField(
        null=True, blank=True,
        help_text="End of current Stripe billing period",
    )
    subscription_cancel_at_period_end = models.BooleanField(
        default=False,
        help_text="Subscription is set to cancel at end of current billing period",
    )

    # ── Add-on subscription ───────────────────────────────────────────────────
    addon_active = models.BooleanField(
        default=False,
        help_text="User has an active add-on subscription",
    )
    addon_payment_date = models.DateTimeField(
        null=True, blank=True,
        help_text="Date the add-on was purchased",
    )
    addon_expires = models.DateTimeField(
        null=True, blank=True,
        help_text="When the add-on subscription expires (1 year from purchase, renewable)",
    )

    # ── Fix for reverse accessor clashes ─────────────────────────────────────
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='customuser_set',
        related_query_name='customuser',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='customuser_set',
        related_query_name='customuser',
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    # ── Account locking ───────────────────────────────────────────────────────

    def is_account_locked(self):
        """Check if account is temporarily locked due to failed login attempts."""
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False

    # ── Access control ────────────────────────────────────────────────────────

    def can_view_data(self):
        """
        Returns True if the user may VIEW their data.

        • Active subscription → can view
        • Previously paid (subscription lapsed/canceled) → view-only forever
        • Free tier (no subscription, not demo) → can view their limited items
        • Never paid and not free tier → cannot view
        """
        if not self.is_active:
            return False
        return self.has_paid or self.is_free_tier()

    def can_modify_data(self):
        """
        Returns True if the user may ADD / CHANGE / DELETE data.

        New subscription users:
            Active subscription → can modify
            Canceled / lapsed   → cannot modify (view-only)

        Legacy one-time users (no stripe_subscription_id):
            Essentials: within 1 year of payment
            Legacy:     forever
        """
        if not self.is_active:
            return False

        # ── Stripe subscription users ─────────────────────────────────────────
        if self.stripe_subscription_id:
            return self.subscription_status == 'active'

        return False

    def is_free_tier(self):
        """Active user with no subscription — real saves allowed up to per-category limits."""
        return self.is_active and not self.has_paid

    def is_lapsed_subscriber(self):
        """True for users who have previously paid but whose subscription is no longer active."""
        return bool(self.has_paid and not self.can_modify_data())

    # ── Subscription helpers ──────────────────────────────────────────────────

    def is_subscription_active(self):
        """True when the Stripe subscription is currently active."""
        return self.stripe_subscription_id != '' and self.subscription_status == 'active'

    def days_until_renewal(self):
        """Days until the next billing date (0 if not on a subscription)."""
        if not self.subscription_current_period_end:
            return 0
        delta = self.subscription_current_period_end - timezone.now()
        return max(0, delta.days)

    def get_tier_display_name(self):
        """Human-readable tier name with status."""
        if self.stripe_subscription_id:
            tier = self.subscription_tier.capitalize()
            interval = self.subscription_interval.capitalize() if self.subscription_interval else ''
            if self.subscription_status == 'active':
                cancel_note = ' — Cancels at period end' if self.subscription_cancel_at_period_end else ''
                return f"{tier} ({interval} subscription{cancel_note})"
            return f"{tier} (Subscription {self.subscription_status})"
        if self.subscription_tier == 'essentials':
            return "Essentials (View-only)"
        if self.subscription_tier == 'legacy':
            return "Legacy (View-only)"
        return "No Subscription"

    # ── Stripe activation / deactivation ─────────────────────────────────────

    def activate_subscription(self, tier, stripe_customer_id, stripe_subscription_id,
                              interval, current_period_end, cancel_at_period_end=False):
        """
        Called after a Stripe subscription becomes active (initial payment or renewal).
        Sets all subscription fields and grants modify access.
        """
        self.subscription_tier = tier
        self.stripe_customer_id = stripe_customer_id
        self.stripe_subscription_id = stripe_subscription_id
        self.subscription_status = 'active'
        self.subscription_interval = interval
        self.subscription_current_period_end = current_period_end
        self.subscription_cancel_at_period_end = cancel_at_period_end
        self.has_paid = True
        self.payment_date = timezone.now()
        self.save()

    def update_subscription_status(self, status, current_period_end=None, cancel_at_period_end=False):
        """
        Called by the Stripe webhook to keep subscription state in sync.
        """
        self.subscription_status = status
        self.subscription_cancel_at_period_end = cancel_at_period_end
        if current_period_end:
            self.subscription_current_period_end = current_period_end
        self.save()

    def deactivate_subscription(self):
        """Mark the subscription as canceled (user loses modify access)."""
        self.subscription_status = 'canceled'
        self.subscription_cancel_at_period_end = False
        self.save()

    # ── Add-on subscription ───────────────────────────────────────────────────

    def can_access_addon(self):
        """Check if user has an active add-on."""
        if not self.has_paid or not self.addon_active:
            return False
        if self.addon_expires and timezone.now() > self.addon_expires:
            return False
        return True

    def is_eligible_for_addon(self):
        """Only paying users (essentials or legacy) may purchase the add-on."""
        return self.has_paid and self.subscription_tier in ('essentials', 'legacy')

    def days_until_addon_expires(self):
        """Days remaining on the add-on subscription."""
        if not self.addon_expires:
            return 0
        delta = self.addon_expires - timezone.now()
        return max(0, delta.days)

    def activate_addon(self):
        """Purchase / renew the add-on for 1 year."""
        if not self.is_eligible_for_addon():
            raise PermissionError("User is not eligible for the add-on subscription.")
        self.addon_active = True
        self.addon_payment_date = timezone.now()
        self.addon_expires = timezone.now() + timedelta(days=365)
        self.save()

    def deactivate_addon(self):
        """Administratively remove add-on access."""
        self.addon_active = False
        self.save()

    class Meta:
        db_table = 'users'
        permissions = [
            ("can_modify_models", "Can add, change, and delete model data"),
            ("can_view_models", "Can view model data"),
        ]
