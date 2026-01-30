# dashboard/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Profile,
    Account,
    AccountRelevanceReview,
    Device,
    DigitalEstateDocument,
    FamilyNeedsToKnowSection,
    Contact,
    DelegationGrant,
    Checkup,
    CareRelationship,
    RecoveryRequest,
    ImportantDocument,
)


# ============================================================================
# PROFILE ADMIN
# ============================================================================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'user',
        'primary_email',
        'phone_number',
        'has_digital_executor',
        'digital_executor_name',
        'created_at',
        'updated_at',
    ]
    list_filter = [
        'has_digital_executor',
        'created_at',
        'updated_at',
    ]
    search_fields = [
        'full_name',
        'user__username',
        'user__email',
        'primary_email',
        'digital_executor_name',
    ]
    readonly_fields = ['user', 'created_at', 'updated_at']
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'full_name', 'date_of_birth')
        }),
        ('Contact Information', {
            'fields': ('primary_email', 'phone_number')
        }),
        ('Digital Executor', {
            'fields': ('has_digital_executor', 'digital_executor_name', 'digital_executor_contact')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'


# ============================================================================
# ACCOUNT ADMIN
# ============================================================================
@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = [
        'account_name',
        'provider',
        'profile',
        'account_category',
        'is_critical',
        'keep_or_close_instruction',
        'created_at',
    ]
    list_filter = [
        'is_critical',
        'account_category',
        'keep_or_close_instruction',
        'created_at',
        'updated_at',
    ]
    search_fields = [
        'account_name',
        'provider',
        'username_or_email',
        'profile__full_name',
        'profile__user__username',
    ]
    readonly_fields = ['profile', 'created_at', 'updated_at']
    fieldsets = (
        ('Account Information', {
            'fields': ('profile', 'account_name', 'account_category', 'provider', 'website_url')
        }),
        ('Credentials', {
            'fields': ('username_or_email', 'credential_storage_location')
        }),
        ('Status & Instructions', {
            'fields': ('is_critical', 'keep_or_close_instruction', 'notes_for_family')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    
    def is_critical_badge(self, obj):
        if obj.is_critical:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">Critical</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">Standard</span>'
        )
    is_critical_badge.short_description = 'Priority'


# ============================================================================
# ACCOUNT RELEVANCE REVIEW ADMIN
# ============================================================================
@admin.register(AccountRelevanceReview)
class AccountRelevanceReviewAdmin(admin.ModelAdmin):
    list_display = [
        'account',
        'reviewer',
        'matters_badge',
        'review_date',
        'next_review_due',
    ]
    list_filter = [
        'matters',
        'review_date',
        'next_review_due',
    ]
    search_fields = [
        'account__account_name',
        'account__provider',
        'reviewer__username',
        'reasoning',
    ]
    readonly_fields = ['reviewer', 'review_date', 'created_at', 'updated_at']
    fieldsets = (
        ('Review Information', {
            'fields': ('account', 'reviewer', 'review_date')
        }),
        ('Review Assessment', {
            'fields': ('matters', 'reasoning', 'next_review_due')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'review_date'
    
    def matters_badge(self, obj):
        if obj.matters:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Still Matters</span>'
            )
        return format_html(
            '<span style="background-color: #ffc107; color: black; padding: 3px 10px; border-radius: 3px;">No Longer Matters</span>'
        )
    matters_badge.short_description = 'Status'


# ============================================================================
# DEVICE ADMIN
# ============================================================================
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'device_type',
        'profile',
        'owner_label',
        'used_for_2fa_badge',
        'created_at',
    ]
    list_filter = [
        'device_type',
        'used_for_2fa',
        'created_at',
    ]
    search_fields = [
        'name',
        'owner_label',
        'location_description',
        'profile__full_name',
    ]
    readonly_fields = ['profile', 'created_at', 'updated_at']
    fieldsets = (
        ('Device Information', {
            'fields': ('profile', 'device_type', 'name', 'owner_label')
        }),
        ('Location & Security', {
            'fields': ('location_description', 'unlock_method_description', 'used_for_2fa')
        }),
        ('Decommission Instructions', {
            'fields': ('decommission_instruction',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    
    def used_for_2fa_badge(self, obj):
        if obj.used_for_2fa:
            return format_html(
                '<span style="background-color: #007bff; color: white; padding: 3px 10px; border-radius: 3px;">2FA Enabled</span>'
            )
        return '-'
    used_for_2fa_badge.short_description = '2FA'


# ============================================================================
# DIGITAL ESTATE DOCUMENT ADMIN
# ============================================================================
class FamilyNeedsToKnowSectionInline(admin.TabularInline):
    model = FamilyNeedsToKnowSection
    extra = 0
    fields = ['heading', 'sort_order', 'content']
    ordering = ['sort_order', 'heading']


@admin.register(DigitalEstateDocument)
class DigitalEstateDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'version',
        'profile',
        'is_active_badge',
        'created_at',
        'updated_at',
    ]
    list_filter = [
        'is_active',
        'created_at',
        'updated_at',
    ]
    search_fields = [
        'title',
        'version',
        'profile__full_name',
        'overall_instructions',
    ]
    readonly_fields = ['profile', 'created_at', 'updated_at']
    fieldsets = (
        ('Document Information', {
            'fields': ('profile', 'title', 'version', 'is_active')
        }),
        ('General Instructions', {
            'fields': ('overall_instructions',)
        }),
        ('Important Locations', {
            'fields': ('location_of_legal_will', 'location_of_password_manager_instructions')
        }),
        ('Digital Wishes', {
            'fields': ('wishes_for_social_media', 'wishes_for_photos_and_files', 'data_retention_preferences')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [FamilyNeedsToKnowSectionInline]
    date_hierarchy = 'created_at'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'


# ============================================================================
# FAMILY NEEDS TO KNOW SECTION ADMIN
# ============================================================================
@admin.register(FamilyNeedsToKnowSection)
class FamilyNeedsToKnowSectionAdmin(admin.ModelAdmin):
    list_display = [
        'heading',
        'body',
        'document',
        'sort_order',
        'created_at',
    ]
    list_filter = [
        'document',
        'created_at',
    ]
    search_fields = [
        'heading',
        'body',
        'content',
        'document__title',
    ]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Section Information', {
            'fields': ('document', 'body','heading', 'sort_order')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'


# ============================================================================
# CONTACT ADMIN
# ============================================================================
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = [
        'contact_name',
        'contact_relation',
        'profile',
        'email',
        'phone',
        'roles_badge',
        'created_at',
    ]
    list_filter = [
        'contact_relation',
        'is_emergency_contact',
        'is_digital_executor',
        'is_caregiver',
        'created_at',
    ]
    search_fields = [
        'contact_name',
        'email',
        'phone',
        'profile__full_name',
    ]
    readonly_fields = ['profile', 'created_at', 'updated_at']
    fieldsets = (
        ('Contact Information', {
            'fields': ('profile', 'contact_name', 'contact_relation')
        }),
        ('Contact Details', {
            'fields': ('email', 'phone', 'address')
        }),
        ('Roles', {
            'fields': ('is_emergency_contact', 'is_digital_executor', 'is_caregiver')
        }),
        ('Emergency Message', {
            'fields': ('body',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    
    def roles_badge(self, obj):
        roles = []
        if obj.is_emergency_contact:
            roles.append('<span style="background-color: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; margin-right: 3px;">Emergency</span>')
        if obj.is_digital_executor:
            roles.append('<span style="background-color: #007bff; color: white; padding: 2px 6px; border-radius: 3px; margin-right: 3px;">Executor</span>')
        if obj.is_caregiver:
            roles.append('<span style="background-color: #28a745; color: white; padding: 2px 6px; border-radius: 3px; margin-right: 3px;">Caregiver</span>')
        
        if roles:
            return mark_safe(''.join(roles))
        return '-'
    roles_badge.short_description = 'Roles'


# ============================================================================
# DELEGATION GRANT ADMIN
# ============================================================================
@admin.register(DelegationGrant)
class DelegationGrantAdmin(admin.ModelAdmin):
    list_display = [
        'contact',
        'profile',
        'applies_on_death',
        'applies_on_incapacity',
        'applies_immediately',
        'created_at',
    ]
    list_filter = [
        'applies_on_death',
        'applies_on_incapacity',
        'applies_immediately',
        'created_at',
    ]
    search_fields = [
        'contact__contact_name',
        'profile__full_name',
        'notes_for_contact',
    ]
    readonly_fields = ['profile', 'created_at', 'updated_at']
    fieldsets = (
        ('Delegation Information', {
            'fields': ('profile', 'contact')
        }),
        ('When This Applies', {
            'fields': ('applies_on_death', 'applies_on_incapacity', 'applies_immediately')
        }),
        ('Notes', {
            'fields': ('notes_for_contact',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'


# ============================================================================
# CHECKUP ADMIN
# ============================================================================
@admin.register(Checkup)
class CheckupAdmin(admin.ModelAdmin):
    list_display = [
        'profile',
        'frequency',
        'due_date',
        'status_badge',
        'completed_at',
        'completed_by',
    ]
    list_filter = [
        'frequency',
        'due_date',
        'completed_at',
        'all_accounts_reviewed',
        'all_devices_reviewed',
        'contacts_up_to_date',
        'documents_up_to_date',
    ]
    search_fields = [
        'profile__full_name',
        'summary',
    ]
    readonly_fields = ['profile', 'completed_by', 'created_at', 'updated_at']
    fieldsets = (
        ('Checkup Information', {
            'fields': ('profile', 'frequency', 'due_date')
        }),
        ('Completion Status', {
            'fields': ('completed_at', 'completed_by', 'summary')
        }),
        ('Review Items', {
            'fields': ('all_accounts_reviewed', 'all_devices_reviewed', 'contacts_up_to_date', 'documents_up_to_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'due_date'
    
    def status_badge(self, obj):
        if obj.completed_at:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Completed</span>'
            )
        elif obj.is_overdue():
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">Overdue</span>'
            )
        return format_html(
            '<span style="background-color: #ffc107; color: black; padding: 3px 10px; border-radius: 3px;">Pending</span>'
        )
    status_badge.short_description = 'Status'


# ============================================================================
# CARE RELATIONSHIP ADMIN
# ============================================================================
@admin.register(CareRelationship)
class CareRelationshipAdmin(admin.ModelAdmin):
    list_display = [
        'contact_name',
        'profile',
        'relationship_type',
        'has_portal_access',
        'portal_role',
        'created_at',
    ]
    list_filter = [
        'relationship_type',
        'has_portal_access',
        'portal_role',
        'created_at',
    ]
    search_fields = [
        'contact_name__contact_name',
        'profile__full_name',
        'notes',
    ]
    readonly_fields = ['profile', 'created_at', 'updated_at']
    fieldsets = (
        ('Relationship Information', {
            'fields': ('profile', 'contact_name', 'relationship_type')
        }),
        ('Portal Access', {
            'fields': ('has_portal_access', 'portal_role')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'


# ============================================================================
# RECOVERY REQUEST ADMIN
# ============================================================================
@admin.register(RecoveryRequest)
class RecoveryRequestAdmin(admin.ModelAdmin):
    list_display = [
        'target_description',
        'profile',
        'requested_by',
        'status_badge',
        'provider_ticket_number',
        'created_at',
    ]
    list_filter = [
        'status',
        'created_at',
        'updated_at',
    ]
    search_fields = [
        'target_description',
        'profile__full_name',
        'requested_by__username',
        'provider_ticket_number',
        'steps_taken',
        'outcome_notes',
    ]
    readonly_fields = ['profile', 'requested_by', 'created_at', 'updated_at']
    fieldsets = (
        ('Request Information', {
            'fields': ('profile', 'requested_by', 'target_account', 'target_description')
        }),
        ('Status', {
            'fields': ('status', 'provider_ticket_number')
        }),
        ('Progress', {
            'fields': ('steps_taken', 'outcome_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'in-progress': '#007bff',
            'completed': '#28a745',
            'denied': '#dc3545',
            'cancelled': '#6c757d',
        }
        text_colors = {
            'pending': 'black',
            'in-progress': 'white',
            'completed': 'white',
            'denied': 'white',
            'cancelled': 'white',
        }
        color = colors.get(obj.status, '#6c757d')
        text_color = text_colors.get(obj.status, 'white')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            text_color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ============================================================================
# IMPORTANT DOCUMENT ADMIN
# ============================================================================
@admin.register(ImportantDocument)
class ImportantDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'document_category',
        'profile',
        'requires_legal_review_badge',
        'has_file',
        'created_at',
    ]
    list_filter = [
        'document_category',
        'requires_legal_review',
        'created_at',
        'updated_at',
    ]
    search_fields = [
        'title',
        'description',
        'profile__full_name',
        'physical_location',
        'digital_location',
    ]
    readonly_fields = ['profile', 'created_at', 'updated_at']
    fieldsets = (
        ('Document Information', {
            'fields': ('profile', 'title', 'document_category', 'description')
        }),
        ('Location', {
            'fields': ('physical_location', 'digital_location', 'file')
        }),
        ('Legal Review', {
            'fields': ('requires_legal_review',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    
    def requires_legal_review_badge(self, obj):
        if obj.requires_legal_review:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 3px 10px; border-radius: 3px;">Legal Review Needed</span>'
            )
        return '-'
    requires_legal_review_badge.short_description = 'Legal Review'
    
    def has_file(self, obj):
        if obj.file:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">✓ File Uploaded</span>'
            )
        return '-'
    has_file.short_description = 'File Status'


# ============================================================================
# ADMIN SITE CUSTOMIZATION
# ============================================================================
admin.site.site_header = "Digital Estate Planning Administration"
admin.site.site_title = "Digital Estate Admin"
admin.site.index_title = "Welcome to Digital Estate Planning Administration"