from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta

class CustomUser(AbstractUser):
    """
    Custom user model with two subscription tiers:
    1. ESSENTIALS - One-time payment, 1 year of edit access, then view-only forever
    2. LEGACY - Lifetime full access (add, change, delete, view)
    """
    
    TIER_CHOICES = [
        ('none', 'No Subscription'),
        ('essentials', 'Essentials'),
        ('legacy', 'Legacy'),
    ]
    
    # Basic fields
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    
    # Subscription tier
    subscription_tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default='none',
        help_text="User's subscription tier"
    )
    
    # Payment tracking
    has_paid = models.BooleanField(
        default=False,
        help_text="User has completed payment"
    )
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date of payment"
    )
    
    # Essentials tier - expires after 1 year
    essentials_expires = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When Essentials tier edit access expires (1 year from payment)"
    )
    
    # Legacy tier - lifetime access
    legacy_granted_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When legacy access was granted"
    )
    
    # Fix for reverse accessor clashes
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
    
    def is_account_locked(self):
        """Check if account is temporarily locked due to failed login attempts"""
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False
    
    def can_view_data(self):
        """
        Check if user can VIEW data.
        
        ESSENTIALS: Can view forever (even after 1 year)
        LEGACY: Can view forever
        """
        if not self.is_active:
            return False
        
        if self.subscription_tier == 'essentials':
            return self.has_paid
        elif self.subscription_tier == 'legacy':
            return True
        
        return False
    
    def can_modify_data(self):
        """
        Check if user can ADD/CHANGE/DELETE data.
        
        ESSENTIALS: Can modify for 1 year after payment, then view-only
        LEGACY: Can modify forever (lifetime access)
        """
        if not self.is_active:
            return False
        
        if self.subscription_tier == 'essentials':
            # Can modify only within 1 year of payment
            if self.essentials_expires and timezone.now() < self.essentials_expires:
                return True
            return False
        
        elif self.subscription_tier == 'legacy':
            # Legacy users have lifetime modify access
            return True
        
        return False
    
    def is_essentials_edit_active(self):
        """Check if Essentials tier still has edit access"""
        if self.subscription_tier != 'essentials':
            return False
        if self.essentials_expires:
            return timezone.now() < self.essentials_expires
        return False
    
    def days_until_essentials_expires(self):
        """Calculate days remaining for Essentials edit access"""
        if self.subscription_tier != 'essentials' or not self.essentials_expires:
            return 0
        delta = self.essentials_expires - timezone.now()
        return max(0, delta.days)
    
    def get_tier_display_name(self):
        """Get human-readable tier name with status"""
        if self.subscription_tier == 'essentials':
            if self.is_essentials_edit_active():
                days = self.days_until_essentials_expires()
                return f"Essentials (Edit access: {days} days remaining)"
            return "Essentials (View-only)"
        elif self.subscription_tier == 'legacy':
            return "Legacy (Lifetime Access)"
        return "No Subscription"
    
    def upgrade_to_essentials(self):
        """Activate Essentials tier (1 year edit access, then view-only)"""
        self.subscription_tier = 'essentials'
        self.has_paid = True
        self.payment_date = timezone.now()
        self.essentials_expires = timezone.now() + timedelta(days=365)
        self.save()
    
    def upgrade_to_legacy(self):
        """Activate Legacy tier (lifetime full access)"""
        self.subscription_tier = 'legacy'
        self.has_paid = True
        self.payment_date = timezone.now()
        self.legacy_granted_date = timezone.now()
        self.save()
    
    class Meta:
        db_table = 'users'
        permissions = [
            ("can_modify_models", "Can add, change, and delete model data"),
            ("can_view_models", "Can view model data"),
        ]




# Original Working Copy
# from django.contrib.auth.models import AbstractUser
# from django.db import models
# from django.utils import timezone

# class CustomUser(AbstractUser):
#     email = models.EmailField(unique=True)
#     email_verified = models.BooleanField(default=False)
#     last_login_ip = models.GenericIPAddressField(null=True, blank=True)
#     failed_login_attempts = models.IntegerField(default=0)
#     account_locked_until = models.DateTimeField(null=True, blank=True)
    
#     # Fix for reverse accessor clashes
#     groups = models.ManyToManyField(
#         'auth.Group',
#         verbose_name='groups',
#         blank=True,
#         help_text='The groups this user belongs to.',
#         related_name='customuser_set',
#         related_query_name='customuser',
#     )
#     user_permissions = models.ManyToManyField(
#         'auth.Permission',
#         verbose_name='user permissions',
#         blank=True,
#         help_text='Specific permissions for this user.',
#         related_name='customuser_set',
#         related_query_name='customuser',
#     )
    
#     USERNAME_FIELD = 'username'
#     REQUIRED_FIELDS = ['email']
    
#     def is_account_locked(self):
#         if self.account_locked_until:
#             return timezone.now() < self.account_locked_until
#         return False
    
#     class Meta:
#         db_table = 'users'