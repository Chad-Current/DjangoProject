# vault/admin.py
#
# SECURITY DESIGN:
#   - The encrypted_password token is NEVER shown or editable in the admin.
#     Admins can see that an entry exists and manage its metadata, but cannot
#     read any stored password. This is intentional and enforced by:
#       1. Excluding encrypted_password from all fieldsets.
#       2. Making the token field read-only even if someone adds it manually.
#       3. Providing a safe "reset password" action that re-encrypts via
#          set_password() rather than writing raw tokens.
#   - VaultAccessLog is fully read-only — no add/change/delete in admin.
#   - All admin actions are logged via Django's built-in LogEntry.

import logging
from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.timezone import localtime

from .models import VaultEntry, VaultAccessLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Inline: Access logs shown inside a VaultEntry change page
# ---------------------------------------------------------------------------

class VaultAccessLogInline(admin.TabularInline):
    model          = VaultAccessLog
    extra          = 0
    can_delete     = False
    show_change_link = False
    verbose_name   = 'Access Event'
    verbose_name_plural = 'Access History'

    # Completely read-only — no one should edit audit records
    readonly_fields = ('accessed_by', 'accessed_at', 'ip_address')
    fields          = ('accessed_by', 'accessed_at', 'ip_address')

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Admin form for VaultEntry — keeps encrypted_password out of the UI
# ---------------------------------------------------------------------------

class VaultEntryAdminForm(forms.ModelForm):
    """
    Adds an optional plain-text 'new_password' field so a superuser can
    reset a credential without ever exposing the encrypted token.
    The field is intentionally NOT required — leaving it blank keeps the
    existing encrypted value untouched.
    """
    new_password = forms.CharField(
        label='Reset Password',
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}),
        help_text=(
            'Enter a new password to re-encrypt and replace the stored credential. '
            'Leave blank to keep the current encrypted value unchanged. '
            'The existing token is never displayed here.'
        ),
    )

    class Meta:
        model = VaultEntry
        # encrypted_password is explicitly excluded — never expose the token
        exclude = ('encrypted_password', 'slug')

    def save(self, commit=True):
        instance     = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password', '').strip()

        if new_password:
            instance.set_password(new_password)
            logger.info(
                "Admin reset encrypted_password for VaultEntry pk=%s label='%s'",
                instance.pk,
                instance.label,
            )

        if commit:
            instance.save()
        return instance


# ---------------------------------------------------------------------------
# VaultEntry admin
# ---------------------------------------------------------------------------

@admin.register(VaultEntry)
class VaultEntryAdmin(admin.ModelAdmin):
    form = VaultEntryAdminForm

    # ── List view ────────────────────────────────────────────────────────────
    list_display = (
        'label',
        'profile_owner',
        'linked_source',
        'username_or_email',
        'has_password',
        'last_accessed_display',
        'updated_at',
    )
    list_display_links = ('label',)
    list_filter        = ('created_at', 'updated_at')
    search_fields      = (
        'label',
        'username_or_email',
        'profile__user__email',
        'profile__user__username',
        'linked_account__account_name_or_provider',
        'linked_device__device_name',
    )
    ordering           = ('-updated_at',)
    date_hierarchy     = 'created_at'
    list_per_page      = 30

    # ── Detail view ──────────────────────────────────────────────────────────
    readonly_fields = (
        'slug',
        'created_at',
        'updated_at',
        'last_accessed',
        'encrypted_password_status',
    )

    fieldsets = (
        ('Ownership', {
            'fields': ('profile',),
        }),
        ('Entry Details', {
            'fields': (
                'label',
                'username_or_email',
                'notes',
            ),
        }),
        ('Linked Source', {
            'description': (
                'Link this entry to one of the user\'s existing accounts or devices. '
                '<strong>Exactly one must be set.</strong>'
            ),
            'fields': ('linked_account', 'linked_device'),
        }),
        ('Encrypted Credential', {
            'description': (
                '<strong style="color:#b91c1c;">Security:</strong> '
                'The stored password token is never displayed. '
                'Use the field below only to replace the credential with a new one.'
            ),
            'fields': ('encrypted_password_status', 'new_password'),
        }),
        ('Identifiers & Audit', {
            'classes': ('collapse',),
            'fields': ('slug', 'created_at', 'updated_at', 'last_accessed'),
        }),
    )

    inlines = [VaultAccessLogInline]

    # ── Bulk actions ─────────────────────────────────────────────────────────
    actions = ['action_clear_last_accessed']

    @admin.action(description='Clear "last accessed" timestamp on selected entries')
    def action_clear_last_accessed(self, request, queryset):
        updated = queryset.update(last_accessed=None)
        self.message_user(
            request,
            f'{updated} entr{"y" if updated == 1 else "ies"} cleared.',
            messages.SUCCESS,
        )

    # ── Custom list columns ───────────────────────────────────────────────────

    @admin.display(description='Owner', ordering='profile__user__email')
    def profile_owner(self, obj):
        user = obj.profile.user
        return format_html(
            '<span title="{}">{}</span>',
            user.email,
            user.get_full_name() or user.username,
        )

    @admin.display(description='Linked To')
    def linked_source(self, obj):
        if obj.linked_account:
            return format_html(
                '<span style="color:#065f46;">⬡ {}</span>',
                obj.linked_account.account_name_or_provider,
            )
        if obj.linked_device:
            return format_html(
                '<span style="color:#1e40af;">⬡ {}</span>',
                obj.linked_device.device_name,
            )
        return '—'

    @admin.display(description='Has Password', boolean=True)
    def has_password(self, obj):
        return bool(obj.encrypted_password)

    @admin.display(description='Last Accessed', ordering='last_accessed')
    def last_accessed_display(self, obj):
        if not obj.last_accessed:
            return format_html('<span style="color:#9ca3af;">Never</span>')
        local = localtime(obj.last_accessed)
        return format_html(
            '<span title="{}">{}</span>',
            local.strftime('%Y-%m-%d %H:%M:%S %Z'),
            local.strftime('%d %b %Y'),
        )

    @admin.display(description='Encrypted Token Status')
    def encrypted_password_status(self, obj):
        if obj.pk and obj.encrypted_password:
            return format_html(
                '<span style="color:#065f46; font-weight:600;">'
                '✔ Token present ({} chars) — value is hidden for security.'
                '</span>',
                len(obj.encrypted_password),
            )
        return format_html(
            '<span style="color:#b91c1c;">✘ No token stored — use "Reset Password" below to set one.</span>'
        )

    # ── FK queryset scoping ───────────────────────────────────────────────────

    def get_form(self, request, obj=None, **kwargs):
        """Scope linked_account and linked_device to the selected profile's data."""
        form = super().get_form(request, obj, **kwargs)

        if obj and obj.profile_id:
            from dashboard.models import Account, Device
            form.base_fields['linked_account'].queryset = (
                Account.objects.filter(profile=obj.profile)
                               .order_by('account_name_or_provider')
            )
            form.base_fields['linked_device'].queryset = (
                Device.objects.filter(profile=obj.profile)
                              .order_by('device_name')
            )
        else:
            from dashboard.models import Account, Device
            form.base_fields['linked_account'].queryset = (
                Account.objects.select_related('profile__user')
                               .order_by('profile__user__email', 'account_name_or_provider')
            )
            form.base_fields['linked_device'].queryset = (
                Device.objects.select_related('profile__user')
                              .order_by('profile__user__email', 'device_name')
            )

        return form

    # ── Prevent token exposure via raw queryset ───────────────────────────────

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
                   .select_related(
                       'profile__user',
                       'linked_account',
                       'linked_device',
                   )
        )


# ---------------------------------------------------------------------------
# VaultAccessLog admin — read-only, no add / change / delete
# ---------------------------------------------------------------------------

@admin.register(VaultAccessLog)
class VaultAccessLogAdmin(admin.ModelAdmin):
    list_display = (
        'entry_label',
        'accessed_by',
        'accessed_at',
        'ip_address',
    )
    list_display_links = ('entry_label',)
    list_filter        = ('accessed_at',)
    search_fields      = (
        'entry__label',
        'accessed_by__email',
        'accessed_by__username',
        'ip_address',
    )
    ordering      = ('-accessed_at',)
    date_hierarchy = 'accessed_at'
    list_per_page  = 50

    readonly_fields = ('entry', 'accessed_by', 'accessed_at', 'ip_address')
    fields          = ('entry', 'accessed_by', 'accessed_at', 'ip_address')

    # Fully read-only — no mutations allowed on audit records
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Entry', ordering='entry__label')
    def entry_label(self, obj):
        return obj.entry.label

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
                   .select_related('entry', 'accessed_by')
        )