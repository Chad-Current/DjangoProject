# ============================================================================
# PART 5: DASHBOARD APP - ADMIN
# ============================================================================

# ============================================================================
# dashboard/admin.py
# ============================================================================
from django.contrib import admin
from .models import (
    Profile,
    Account,
    AccountRelevanceReview,
    Contact,
    DelegationScope,
    DelegationGrant,
    Device,
    DigitalEstateDocument,
    FamilyNeedsToKnowSection,
    AccountDirectoryEntry,
    EmergencyContact,
    CheckupType,
    Checkup,
    CareRelationship,
    RecoveryRequest,
    DocumentCategory,
    ImportantDocument,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'primary_email', 'phone_number', 'has_digital_executor']
    list_filter = ['has_digital_executor']
    search_fields = ['user__username', 'full_name', 'primary_email', 'phone_number']
    readonly_fields = ['user']
    
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Personal Information', {
            'fields': ('full_name', 'date_of_birth', 'primary_email', 'phone_number')
        }),
        ('Digital Executor', {
            'fields': ('has_digital_executor', 'digital_executor_name', 'digital_executor_contact')
        }),
        ('Notes', {'fields': ('notes',)}),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)
    
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return obj.user == request.user or request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        return obj.user == request.user or request.user.is_superuser


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['account_name', 'provider', 'profile', 'account_category', 'is_critical', 'created_at']
    list_filter = ['is_critical', 'account_category', 'created_at']
    search_fields = ['account_name', 'provider', 'username_or_email', 'profile__user__username']
    readonly_fields = ['profile', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Account Info', {
            'fields': ('profile', 'account_name', 'account_category', 'provider', 'website_url')
        }),
        ('Credentials', {
            'fields': ('username_or_email', 'credential_storage_location')
        }),
        ('Instructions', {
            'fields': ('is_critical', 'keep_or_close_instruction', 'notes_for_family')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(profile__user=request.user)
    
    def save_model(self, request, obj, form, change):
        if not change:
            from .models import Profile
            profile, created = Profile.objects.get_or_create(user=request.user)
            obj.profile = profile
        super().save_model(request, obj, form, change)


@admin.register(AccountRelevanceReview)
class AccountRelevanceReviewAdmin(admin.ModelAdmin):
    list_display = ['account_relevance', 'reviewer', 'matters', 'review_date', 'next_review_due']
    list_filter = ['matters', 'review_date', 'next_review_due']
    search_fields = ['account__name', 'reviewer__username', 'reasoning']
    readonly_fields = ['reviewer', 'review_date']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(reviewer=request.user)
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.reviewer = request.user
        super().save_model(request, obj, form, change)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'relationship', 'email', 'phone', 'profile', 'is_emergency_contact']
    list_filter = ['is_emergency_contact', 'is_digital_executor', 'is_caregiver']
    search_fields = ['full_name', 'email', 'phone', 'profile__user__username']
    readonly_fields = ['profile']
    
    fieldsets = (
        ('Contact Info', {
            'fields': ('profile', 'full_name', 'relationship', 'email', 'phone', 'address')
        }),
        ('Roles', {
            'fields': ('is_emergency_contact', 'is_digital_executor', 'is_caregiver')
        }),
        ('Notes', {'fields': ('notes',)}),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(profile__user=request.user)


@admin.register(DelegationScope)
class DelegationScopeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name', 'description']


@admin.register(DelegationGrant)
class DelegationGrantAdmin(admin.ModelAdmin):
    list_display = ['profile', 'contact', 'scope', 'applies_on_death', 'applies_on_incapacity', 'applies_immediately']
    list_filter = ['applies_on_death', 'applies_on_incapacity', 'applies_immediately', 'scope']
    search_fields = ['profile__user__username', 'contact__full_name']
    readonly_fields = ['profile']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(profile__user=request.user)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'device_type', 'profile', 'used_for_2fa']
    list_filter = ['device_type', 'used_for_2fa']
    search_fields = ['name', 'owner_label', 'profile__user__username']
    readonly_fields = ['profile']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(profile__user=request.user)


@admin.register(DigitalEstateDocument)
class DigitalEstateDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'version', 'profile', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'profile__user__username']
    readonly_fields = ['profile', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(profile__user=request.user)


@admin.register(FamilyNeedsToKnowSection)
class FamilyNeedsToKnowSectionAdmin(admin.ModelAdmin):
    list_display = ['heading', 'document', 'sort_order']
    list_filter = ['document']
    search_fields = ['heading', 'content']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(document__profile__user=request.user)


@admin.register(AccountDirectoryEntry)
class AccountDirectoryEntryAdmin(admin.ModelAdmin):
    list_display = ['label', 'category_label', 'criticality', 'profile', 'created_at']
    list_filter = ['criticality', 'action_after_death', 'created_at']
    search_fields = ['label', 'category_label', 'profile__user__username']
    readonly_fields = ['profile']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(profile__user=request.user)


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ['contact_name', 'profile', 'contact_relation', 'created_at']
    list_filter = ['created_at']
    search_fields = ['contact_name', 'body', 'profile__user__username']
    readonly_fields = ['profile', 'created_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(profile__user=request.user)


@admin.register(CheckupType)
class CheckupTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'frequency', 'description']
    search_fields = ['name', 'description']


@admin.register(Checkup)
class CheckupAdmin(admin.ModelAdmin):
    list_display = ['profile', 'checkup_type', 'due_date', 'completed_at', 'completed_by']
    list_filter = ['checkup_type', 'due_date', 'all_accounts_reviewed', 'all_devices_reviewed']
    search_fields = ['profile__user__username', 'summary']
    readonly_fields = ['profile', 'completed_by']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(profile__user=request.user)
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.completed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CareRelationship)
class CareRelationshipAdmin(admin.ModelAdmin):
    list_display = ['profile', 'contact', 'relationship_type', 'has_portal_access', 'portal_role']
    list_filter = ['relationship_type', 'has_portal_access', 'portal_role']
    search_fields = ['profile__user__username', 'contact__full_name']
    readonly_fields = ['profile']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(profile__user=request.user)


@admin.register(RecoveryRequest)
class RecoveryRequestAdmin(admin.ModelAdmin):
    list_display = ['profile', 'target_account', 'status', 'requested_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['profile__user__username', 'target_description', 'provider_ticket_number']
    readonly_fields = ['profile', 'requested_by', 'created_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(profile__user=request.user)
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.requested_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order', 'description']
    search_fields = ['name', 'description']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(self.model, 'user'):
            return qs.filter(user=request.user)
        return qs


@admin.register(ImportantDocument)
class ImportantDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'profile', 'requires_legal_review', 'created_at']
    list_filter = ['requires_legal_review', 'category', 'created_at']
    search_fields = ['title', 'description', 'profile__user__username']
    readonly_fields = ['profile', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Document Info', {
            'fields': ('profile', 'category', 'title', 'description')
        }),
        ('Location', {
            'fields': ('physical_location', 'digital_location', 'file')
        }),
        ('Review', {
            'fields': ('requires_legal_review',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(profile__user=request.user)

