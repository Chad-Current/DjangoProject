# dashboard/admin.py
from django.contrib import admin
from django.db.models import Count, Q, F
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
    list_display = ('account_name_or_provider', 'account_category', 'is_critical', 'created_at')
    list_filter = ('account_category', 'is_critical', 'keep_or_close_instruction', 'created_at')
    search_fields = ('account_name_or_provider', 'username_or_email', 'profile__full_name')
    readonly_fields = ('profile', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('profile', 'account_name_or_provider', 'account_category', 'website_url')
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
    search_fields = ('account__account_name_or_provider', 'reviewer__username', 'reasoning')
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
    list_display = ('name', 'device_type', 'owner_label', 'used_for_2fa', 'created_at')
    list_filter = ('device_type', 'used_for_2fa', 'created_at')
    search_fields = ('name', 'owner_label', 'profile__full_name')
    readonly_fields = ('profile', 'created_at', 'updated_at')
    
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
    list_display = ('name_or_title', 'estate_document', 'delegated_to', 'profile', 'created_at')
    list_filter = ('estate_document', 'created_at', 'delegated_to')
    search_fields = ('name_or_title', 'profile__full_name', 'overall_instructions', 'delegated_to__contact_name')
    readonly_fields = ('profile', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Assignment', {
            'fields': ('profile', 'delegated_to'),
            'description': 'Document must be assigned to a contact.'
        }),
        ('Document Information', {
            'fields': ('estate_document', 'name_or_title', 'estate_file')
        }),
        ('Instructions', {
            'fields': ('overall_instructions',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile', 'delegated_to')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        'contact_name',
        'contact_relation',
        'email',
        'phone',
        'is_emergency_contact',
        'is_digital_executor',
        'documents_count'
    )
    list_filter = ('contact_relation', 'is_emergency_contact', 'is_digital_executor', 'is_caregiver', 'created_at')
    search_fields = ('contact_name', 'email', 'phone', 'profile__full_name')
    readonly_fields = ('profile', 'created_at', 'updated_at', 'documents_count_display')
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('profile', 'contact_name', 'contact_relation', 'email', 'phone', 'address')
        }),
        ('Roles', {
            'fields': ('is_emergency_contact', 'is_digital_executor', 'is_caregiver')
        }),
        ('Document Assignment', {
            'fields': ('documents_count_display',),
            'description': 'Number of documents assigned to this contact.'
        }),
        ('Message', {
            'fields': ('body',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            estate_count=Count('delegated_estate_documents'),
            important_count=Count('delegated_important_documents')
        )
    
    def documents_count(self, obj):
        """Display total document count in list view"""
        total = obj.estate_count + obj.important_count
        return f"{total} ({obj.estate_count} estate, {obj.important_count} important)"
    documents_count.short_description = 'Documents'
    documents_count.admin_order_field = 'estate_count'
    
    def documents_count_display(self, obj):
        """Display document count in detail view"""
        if obj.pk:
            estate = obj.delegated_estate_documents.count()
            important = obj.delegated_important_documents.count()
            return f"{estate + important} total ({estate} estate, {important} important)"
        return "Save contact first to see document count"
    documents_count_display.short_description = 'Documents Assigned'


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
    list_display = ('due_date', 'frequency', 'completed_at', 'completed_by', 'is_overdue')
    list_filter = ('frequency', 'due_date', 'completed_at', 'created_at')
    search_fields = ('profile__full_name', 'summary')
    readonly_fields = ('profile', 'created_at', 'updated_at')
    
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
    list_display = ('contact_name', 'relationship_type', 'has_portal_access', 'portal_role', 'created_at')
    list_filter = ('relationship_type', 'has_portal_access', 'portal_role', 'created_at')
    search_fields = ('contact_name__contact_name', 'profile__full_name', 'notes')
    readonly_fields = ('profile', 'created_at', 'updated_at')
    
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
    list_display = ('target_description', 'requested_by', 'status', 'provider_ticket_number', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('target_description', 'profile__full_name', 'requested_by__username', 'provider_ticket_number')
    readonly_fields = ('profile', 'created_at', 'updated_at')
    
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
    list_display = ('name_or_title', 'document_category', 'delegated_to', 'requires_legal_review', 'created_at')
    list_filter = ('document_category', 'requires_legal_review', 'created_at', 'delegated_to')
    search_fields = ('name_or_title', 'description', 'profile__full_name', 'delegated_to__contact_name')
    readonly_fields = ('profile', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Assignment', {
            'fields': ('profile', 'delegated_to'),
            'description': 'Document must be assigned to a contact.'
        }),
        ('Document Information', {
            'fields': ('name_or_title', 'document_category', 'description', 'requires_legal_review')
        }),
        ('Locations', {
            'fields': ('physical_location', 'digital_location', 'important_file')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile', 'delegated_to')

# Customize admin site header
admin.site.site_header = "Digital Estate Planning Administration"
admin.site.site_title = "Digital Estate Admin"
admin.site.index_title = "Welcome to Digital Estate Planning Administration"