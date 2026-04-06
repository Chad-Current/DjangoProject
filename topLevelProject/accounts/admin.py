from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = [
        'email', 'username', 'subscription_tier', 'subscription_status',
        'subscription_interval', 'is_staff', 'is_active', 'date_joined',
    ]
    list_filter = [
        'subscription_tier', 'subscription_status', 'subscription_interval',
        'is_staff', 'is_superuser', 'is_active', 'email_verified', 'has_paid', 'date_joined',
    ]
    search_fields = ['email', 'username', 'first_name', 'last_name', 'stripe_customer_id']
    ordering = ['-date_joined']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'email_verified')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Stripe Subscription', {
            'fields': (
                'stripe_customer_id',
                'stripe_subscription_id',
                'subscription_tier',
                'subscription_status',
                'subscription_interval',
                'subscription_current_period_end',
                'subscription_cancel_at_period_end',
                'has_paid',
                'payment_date',
            ),
        }),
        ('Security', {
            'fields': ('last_login_ip', 'failed_login_attempts', 'account_locked_until'),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )

    readonly_fields = ['date_joined', 'last_login']
