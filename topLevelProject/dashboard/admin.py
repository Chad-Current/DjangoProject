# dashboard/admin.py
from datetime import timezone
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q, F
from .models import (
    Profile,
    Account,
    Device,
    Contact,
    DigitalEstateDocument,
    ImportantDocument,
    FamilyNeedsToKnowSection,
    RelevanceReview,
    
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'user', 'email', 'created_at')
    list_filter = ('email','created_at')
    search_fields = ('first_name', 'last_name', 'user__username', 'email')
    readonly_fields = ('user', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'first_name', 'last_name', 'date_of_birth', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address_1', 'address_2', 'city', 'state', 'zipcode')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        'first_name',
        'last_name',
        'contact_relation',
        'email',
        'phone',
        'city',
        'state',
        'is_emergency_contact',
        'is_digital_executor',
        'is_caregiver',
        'is_legal_executor',
        'is_trustee',
        'is_financial_agent',
        'is_healthcare_proxy',
        'is_guardian_for_dependents',
        'is_pet_caregiver',
        'is_memorial_contact',
        'is_legacy_contact',
        'is_professional_advisor',
        'is_notification_only',
        'is_knowledge_contact',
    )
    list_filter = ('contact_relation', 
                   'is_emergency_contact', 
                   'is_digital_executor', 
                   'is_caregiver',
                   'is_legal_executor',
                   'is_trustee',
                   'is_financial_agent',
                   'is_healthcare_proxy',
                   'is_guardian_for_dependents',
                   'is_pet_caregiver',
                   'is_memorial_contact',
                   'is_legacy_contact',
                   'is_professional_advisor',
                   'is_notification_only',
                   'is_knowledge_contact', 
                   'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone', 'address_1', 'address_2', 'city', 'state', 'profile__first_name', 'profile__last_name')
    readonly_fields = ('profile', 'created_at', 'updated_at', 'documents_count_display')
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('profile', 'first_name', 'last_name', 'contact_relation', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address_1', 'address_2', 'city', 'state', 'zipcode')
        }),
        ('Roles', {
            'fields': ('is_emergency_contact',
                       'is_digital_executor', 
                       'is_caregiver',
                       'is_legal_executor',
                       'is_trustee',
                       'is_financial_agent',
                       'is_healthcare_proxy',
                       'is_guardian_for_dependents',
                       'is_pet_caregiver',
                       'is_memorial_contact',
                       'is_legacy_contact',
                       'is_professional_advisor',
                       'is_notification_only',
                       'is_knowledge_contact',
                       )
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
            important_count=Count('delegated_important_documents'),
            device_count=Count('delegated_devices'),
            account_count=Count('delegated_accounts')
        )
    
    def documents_count(self, obj):
        """Display total document count in list view"""
        estate = getattr(obj, 'estate_count', 0)
        important = getattr(obj, 'important_count', 0)
        device = getattr(obj, 'device_count', 0)
        account = getattr(obj, 'account_count', 0)
        total = estate + important + device + account
        return f"{total} total (E:{estate} I:{important} D:{device} A:{account})"
    documents_count.short_description = 'Assigned Items'
    documents_count.admin_order_field = 'estate_count'
    
    def documents_count_display(self, obj):
        """Display document count in detail view"""
        if obj.pk:
            estate = obj.delegated_estate_documents.count()
            important = obj.delegated_important_documents.count()
            device = obj.delegated_devices.count()
            account = obj.delegated_accounts.count()
            total = estate + important + device + account
            return f"{total} total ({estate} estate docs, {important} important docs, {device} devices, {account} accounts)"
        return "Save contact first to see item counts"
    documents_count_display.short_description = 'Items Assigned'


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_name_or_provider', 'account_category', 'delegated_account_to', 'review_time', 'created_at')
    list_filter = ('account_category', 'keep_or_close_instruction', 'review_time', 'created_at')
    search_fields = ('account_name_or_provider', 'username_or_email', 'profile__first_name', 'profile__last_name', 'delegated_account_to__first_name', 'delegated_account_to__last_name')
    readonly_fields = ('profile', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('profile', 'account_name_or_provider', 'account_category', 'website_url', 'delegated_account_to')
        }),
        ('Credentials', {
            'fields': ('username_or_email', 'credential_storage_location')
        }),
        ('Status & Instructions', {
            'fields': ('review_time', 'keep_or_close_instruction', 'notes_for_family')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile', 'delegated_account_to')


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('device_name', 'device_type', 'owner_label', 'used_for_2fa', 'delegated_device_to', 'review_time', 'created_at')
    list_filter = ('device_type', 'used_for_2fa', 'review_time', 'created_at')
    search_fields = ('device_name', 'owner_label', 'profile__first_name', 'profile__last_name', 'delegated_device_to__first_name', 'delegated_device_to__last_name')
    readonly_fields = ('profile', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Device Information', {
            'fields': ('profile', 'device_type', 'device_name', 'owner_label', 'location_description', 'delegated_device_to', 'review_time')
        }),
        ('Security', {
            'fields': ('unlock_method_description', 'used_for_2fa', 'decommission_instruction')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile', 'delegated_device_to')


@admin.register(DigitalEstateDocument)
class DigitalEstateDocumentAdmin(admin.ModelAdmin):
    list_display = ('name_or_title', 'estate_category', 'delegated_estate_to', 'profile', 'review_time', 'created_at')
    list_filter = ('estate_category', 'applies_on_death', 'applies_on_incapacity', 'applies_immediately', 'review_time', 'created_at')
    search_fields = ('name_or_title', 'profile__first_name', 'profile__last_name', 'estate_overall_instructions', 'delegated_estate_to__first_name', 'delegated_estate_to__last_name')
    readonly_fields = ('profile', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Assignment', {
            'fields': ('profile', 'delegated_estate_to'),
            'description': 'Document must be assigned to a contact.'
        }),
        ('Document Information', {
            'fields': ('estate_category', 'name_or_title', 'estate_file', 'review_time')
        }),
        ('Locations', {
            'fields': ('estate_physical_location', 'estate_digital_location')
        }),
        ('Instructions', {
            'fields': ('estate_overall_instructions',)
        }),
        ('Applicability', {
            'fields': ('applies_on_death', 'applies_on_incapacity', 'applies_immediately')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile', 'delegated_estate_to')


@admin.register(ImportantDocument)
class ImportantDocumentAdmin(admin.ModelAdmin):
    list_display = ('name_or_title', 'document_category', 'delegated_important_document_to', 'requires_legal_review', 'review_time', 'created_at')
    list_filter = ('document_category', 'requires_legal_review', 'applies_on_death', 'applies_on_incapacity', 'applies_immediately', 'review_time', 'created_at')
    search_fields = ('name_or_title', 'description', 'profile__first_name', 'profile__last_name', 'delegated_important_document_to__first_name', 'delegated_important_document_to__last_name')
    readonly_fields = ('profile', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Assignment', {
            'fields': ('profile', 'delegated_important_document_to'),
            'description': 'Document must be assigned to a contact.'
        }),
        ('Document Information', {
            'fields': ('name_or_title', 'document_category', 'description', 'requires_legal_review', 'review_time')
        }),
        ('Locations', {
            'fields': ('physical_location', 'digital_location', 'important_file')
        }),
        ('Applicability', {
            'fields': ('applies_on_death', 'applies_on_incapacity', 'applies_immediately')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile', 'delegated_important_document_to')


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
    search_fields = ('relation__first_name', 'relation__last_name', 'content')
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

@admin.register(RelevanceReview)
class RelevanceReviewAdmin(admin.ModelAdmin):
    list_display = ('get_item_name', 'get_item_type', 'reviewer', 'matters', 'review_date', 'next_review_due')
    list_filter = ('matters', 'review_date', 'next_review_due')
    search_fields = (
        'account_review__account_name_or_provider',
        'device_review__device_name',
        'estate_review__name_or_title',
        'important_document_review__name_or_title',
        'reviewer__username',
        'reasoning'
    )
    readonly_fields = ('reviewer', 'review_date', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Review Target', {
            'fields': ('account_review', 'device_review', 'estate_review', 'important_document_review'),
            'description': 'Select exactly ONE item to review.'
        }),
        ('Review Information', {
            'fields': ('reviewer', 'matters', 'review_date', 'next_review_due')
        }),
        ('Details', {
            'fields': ('reasoning',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_item_name(self, obj):
        """Display the name of the item being reviewed"""
        return obj.get_item_name()
    get_item_name.short_description = 'Item'
    
    def get_item_type(self, obj):
        """Display the type of item being reviewed"""
        return obj.get_item_type()
    get_item_type.short_description = 'Type'

# Customize admin site header
admin.site.site_header = "Digital Estate Planning Administration"
admin.site.site_title = "Digital Estate Admin"
admin.site.index_title = "Welcome to Digital Estate Planning Administration"