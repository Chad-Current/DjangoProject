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
#Non Working code: The legacy branch has no {} and no args: valid

    # def tier_status(self, obj):
    #     """Display tier status with color coding"""
    #     if obj.subscription_tier == 'legacy':
    #         return format_html(
    #             '<span style="color: gold; font-weight: bold;">⭐ Legacy (Lifetime)</span>'
    #         )
    #     elif obj.subscription_tier == 'essentials':
    #         if obj.is_essentials_edit_active():
    #             days = obj.days_until_essentials_expires()
    #             return format_html(
    #                 '<span style="color: green;">✓ Essentials ({} days)</span>',
    #                 days
    #             )
    #         else:
    #             return format_html(
    #                 '<span style="color: orange;">👁 View-Only</span>'
    #             )
    #     else:
    #         return format_html(
    #             '<span style="color: red;">✗ No Subscription</span>'
    #         )
    
    tier_status.short_description = 'Tier Status'
    
    actions = ['grant_legacy_access', 'grant_essentials_access', 'extend_essentials_year']
    
    def grant_legacy_access(self, request, queryset):
        """Admin action to grant legacy access to selected users"""
        count = 0
        for user in queryset:
            user.upgrade_to_legacy()
            count += 1
        self.message_user(request, f'Successfully granted Legacy access to {count} user(s).')
    grant_legacy_access.short_description = 'Grant Legacy tier (lifetime access)'
    
    def grant_essentials_access(self, request, queryset):
        """Admin action to grant essentials access to selected users"""
        count = 0
        for user in queryset:
            user.upgrade_to_essentials()
            count += 1
        self.message_user(request, f'Successfully granted Essentials access to {count} user(s).')
    grant_essentials_access.short_description = 'Grant Essentials tier (1 year)'
    
    def extend_essentials_year(self, request, queryset):
        """Admin action to extend essentials by 1 year"""
        from datetime import timedelta
        count = 0
        for user in queryset.filter(subscription_tier='essentials'):
            if user.essentials_expires:
                user.essentials_expires += timedelta(days=365)
            else:
                user.essentials_expires = timezone.now() + timedelta(days=365)
            user.save()
            count += 1
        self.message_user(request, f'Extended Essentials tier by 1 year for {count} user(s).')
    extend_essentials_year.short_description = 'Extend Essentials by 1 year'
    
    def get_queryset(self, request):
        """Staff users only see their own account, superusers see all"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(pk=request.user.pk)



# Working Copy 
# # from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from .models import CustomUser

# @admin.register(CustomUser)
# class CustomUserAdmin(UserAdmin):
#     model = CustomUser
#     list_display = ['email', 'username', 'is_staff', 'is_active', 'email_verified', 'last_login', 'date_joined']
#     list_filter = ['is_staff', 'is_superuser', 'is_active', 'email_verified', 'date_joined']
#     search_fields = ['email', 'username', 'first_name', 'last_name']
#     ordering = ['-date_joined']
    
#     fieldsets = (
#         (None, {'fields': ('username', 'password')}),
#         ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
#         ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
#         ('Important dates', {'fields': ('last_login', 'date_joined')}),
#         ('Security Info', {'fields': ('email_verified', 'last_login_ip', 'failed_login_attempts', 'account_locked_until')}),
#     )
    
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('username', 'email', 'password1', 'password2', 'is_staff', 'is_active')}
#         ),
#     )
    
#     readonly_fields = ['date_joined', 'last_login']
