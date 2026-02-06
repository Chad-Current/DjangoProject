# dashboard/admin.py
from django.contrib import admin
from .models import (
    Profile,
    Account,
    AccountRelevanceReview,
    Device,
    DigitalEstateDocument,
    Contact,
    FamilyNeedsToKnowSection,
    Checkup,
    CareRelationship,
    RecoveryRequest,
    ImportantDocument,
    DelegationGrant,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'primary_email', 'has_digital_executor', 'created_at')
    list_filter = ('has_digital_executor', 'created_at')
    search_fields = ('full_name', 'user__username', 'primary_email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'full_name', 'date_of_birth', 'primary_email', 'phone_number')
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


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_name', 'provider', 'profile', 'account_category', 'is_critical', 'created_at')
    list_filter = ('account_category', 'is_critical', 'keep_or_close_instruction', 'created_at')
    search_fields = ('account_name', 'provider', 'username_or_email', 'profile__full_name')
    readonly_fields = ('created_at', 'updated_at')
    
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


@admin.register(AccountRelevanceReview)
class AccountRelevanceReviewAdmin(admin.ModelAdmin):
    list_display = ('account', 'reviewer', 'matters', 'review_date', 'next_review_due')
    list_filter = ('matters', 'review_date', 'next_review_due')
    search_fields = ('account__account_name', 'reviewer__username', 'reasoning')
    readonly_fields = ('review_date', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Review Information', {
            'fields': ('account', 'reviewer', 'matters', 'review_date', 'next_review_due')
        }),
        ('Details', {
            'fields': ('reasoning',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'device_type', 'profile', 'owner_label', 'used_for_2fa', 'created_at')
    list_filter = ('device_type', 'used_for_2fa', 'created_at')
    search_fields = ('name', 'owner_label', 'profile__full_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Device Information', {
            'fields': ('profile', 'device_type', 'name', 'owner_label', 'location_description')
        }),
        ('Security', {
            'fields': ('unlock_method_description', 'used_for_2fa', 'decommission_instruction')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DigitalEstateDocument)
class DigitalEstateDocumentAdmin(admin.ModelAdmin):
    list_display = ('estate_document', 'profile', 'is_active', 'created_at')
    list_filter = ('is_active', 'estate_document', 'created_at')
    search_fields = ('estate_document', 'profile__full_name', 'overall_instructions')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Document Information', {
            'fields': ('profile', 'estate_document', 'is_active')
        }),
        ('Instructions', {
            'fields': ('overall_instructions',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('contact_name', 'contact_relation', 'profile', 'email', 'phone', 'is_emergency_contact', 'is_digital_executor')
    list_filter = ('contact_relation', 'is_emergency_contact', 'is_digital_executor', 'is_caregiver', 'created_at')
    search_fields = ('contact_name', 'email', 'phone', 'profile__full_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('profile', 'contact_name', 'contact_relation', 'email', 'phone', 'address')
        }),
        ('Roles', {
            'fields': ('is_emergency_contact', 'is_digital_executor', 'is_caregiver')
        }),
        ('Message', {
            'fields': ('body',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FamilyNeedsToKnowSection)
class FamilyNeedsToKnowSectionAdmin(admin.ModelAdmin):
    list_display = ('relation', 'content_preview', 'is_location_of_legal_will', 'is_password_manager', 'created_at')
    list_filter = (
        'is_location_of_legal_will',
        'is_password_manager',
        'is_social_media',
        'is_photos_or_files',
        'is_data_retention_preferences',
        'created_at'
    )
    search_fields = ('relation__contact_name', 'content')
    readonly_fields = ('created_at', 'updated_at')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
    
    fieldsets = (
        ('Family Information', {
            'fields': ('relation', 'content')
        }),
        ('Categories', {
            'fields': (
                'is_location_of_legal_will',
                'is_password_manager',
                'is_social_media',
                'is_photos_or_files',
                'is_data_retention_preferences'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Checkup)
class CheckupAdmin(admin.ModelAdmin):
    list_display = ('profile', 'due_date', 'frequency', 'completed_at', 'completed_by', 'is_overdue')
    list_filter = ('frequency', 'due_date', 'completed_at', 'created_at')
    search_fields = ('profile__full_name', 'summary')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Checkup Information', {
            'fields': ('profile', 'due_date', 'frequency', 'completed_at', 'completed_by')
        }),
        ('Summary', {
            'fields': ('summary',)
        }),
        ('Checklist', {
            'fields': (
                'all_accounts_reviewed',
                'all_devices_reviewed',
                'contacts_up_to_date',
                'documents_up_to_date'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CareRelationship)
class CareRelationshipAdmin(admin.ModelAdmin):
    list_display = ('contact_name', 'profile', 'relationship_type', 'has_portal_access', 'portal_role', 'created_at')
    list_filter = ('relationship_type', 'has_portal_access', 'portal_role', 'created_at')
    search_fields = ('contact_name__contact_name', 'profile__full_name', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    
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


@admin.register(RecoveryRequest)
class RecoveryRequestAdmin(admin.ModelAdmin):
    list_display = ('target_description', 'profile', 'requested_by', 'status', 'provider_ticket_number', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('target_description', 'profile__full_name', 'requested_by__username', 'provider_ticket_number')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Request Information', {
            'fields': ('profile', 'requested_by', 'target_account', 'target_description', 'status')
        }),
        ('Provider Information', {
            'fields': ('provider_ticket_number',)
        }),
        ('Details', {
            'fields': ('steps_taken', 'outcome_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ImportantDocument)
class ImportantDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_category', 'profile', 'requires_legal_review', 'created_at')
    list_filter = ('document_category', 'requires_legal_review', 'created_at')
    search_fields = ('document_category', 'description', 'profile__full_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Document Information', {
            'fields': ('profile', 'document_category', 'description', 'requires_legal_review')
        }),
        ('Locations', {
            'fields': ('physical_location', 'digital_location', 'file')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DelegationGrant)
class DelegationGrantAdmin(admin.ModelAdmin):
    list_display = (
        'delegate_to',
        'delegation_category',
        'estate_docs_count',
        'important_docs_count',
        'applies_on_death',
        'applies_on_incapacity',
        'applies_immediately',
        'created_at'
    )
    list_filter = (
        'delegation_category',
        'applies_on_death',
        'applies_on_incapacity',
        'applies_immediately',
        'created_at',
        'updated_at'
    )
    search_fields = (
        'delegate_to__contact_name',
        'profile__full_name',
        'notes_for_contact'
    )
    readonly_fields = ('created_at', 'updated_at', 'profile')
    
    # Use filter_horizontal for better M2M widget
    filter_horizontal = ('delegate_estate_documents', 'delegate_important_documents')
    
    fieldsets = (
        ('Delegation Information', {
            'fields': ('profile', 'delegate_to', 'delegation_category')
        }),
        ('Estate Documents', {
            'fields': ('delegate_estate_documents',),
            'description': 'Select which estate documents this delegation covers.'
        }),
        ('Important Documents', {
            'fields': ('delegate_important_documents',),
            'description': 'Select which important documents this delegation covers (optional).'
        }),
        ('Application Conditions', {
            'fields': ('applies_on_death', 'applies_on_incapacity', 'applies_immediately'),
            'description': 'Specify when this delegation becomes active.'
        }),
        ('Notes', {
            'fields': ('notes_for_contact',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def estate_docs_count(self, obj):
        """Display count of estate documents"""
        count = obj.delegate_estate_documents.count()
        return f"{count} document{'s' if count != 1 else ''}"
    estate_docs_count.short_description = 'Estate Docs'
    
    def important_docs_count(self, obj):
        """Display count of important documents"""
        count = obj.delegate_important_documents.count()
        return f"{count} document{'s' if count != 1 else ''}"
    important_docs_count.short_description = 'Important Docs'
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch_related"""
        queryset = super().get_queryset(request)
        return queryset.select_related(
            'profile',
            'delegate_to'
        ).prefetch_related(
            'delegate_estate_documents',
            'delegate_important_documents'
        )


# Optional: Customize admin site header
admin.site.site_header = "Digital Estate Planning Administration"
admin.site.site_title = "Digital Estate Admin"
admin.site.index_title = "Welcome to Digital Estate Planning Administration"