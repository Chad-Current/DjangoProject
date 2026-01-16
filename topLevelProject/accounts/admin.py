from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils import timezone
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    # list_display = [
    #     'email', 'username', 'subscription_tier', 'tier_status',
    #     'is_staff', 'is_active', 'last_login', 'date_joined'
    # ]
    list_filter = [
        'subscription_tier', 'is_staff', 'is_superuser',
        'is_active', 'email_verified', 'has_paid', 'date_joined'
    ]
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'email_verified')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Subscription Info', {
            'fields': (
                'subscription_tier',
                'has_paid',
                'payment_date',
                'essentials_expires',
                'legacy_granted_date',
            ),
            'classes': ('collapse',)
        }),
        ('Security Info', {
            'fields': ('last_login_ip', 'failed_login_attempts', 'account_locked_until'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_staff', 'is_active')
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']

def tier_status(self, obj):
    if obj.subscription_tier == 'legacy':
        return "Legacy (Lifetime)"
    elif obj.subscription_tier == 'essentials':
        if obj.is_essentials_edit_active():
            days = obj.days_until_essentials_expires()
            return f"Essentials ({days} days)"
        else:
            return "View-Only"
    else:
        return "No Subscription"

