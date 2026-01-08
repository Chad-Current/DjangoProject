from django.contrib import admin

from .models import (
    Profile,
    AccountCategory,
    DigitalAccount,
    AccountRelevanceReview,
    Contact,
    DelegationScope,
    DelegationGrant,
    Device,
    DigitalEstateDocument,
    FamilyNeedsToKnowSection,
    AccountDirectoryEntry,
    EmergencyNote,
    CheckupType,
    Checkup,
    CareRelationship,
    RecoveryRequest,
    DocumentCategory,
    ImportantDocument,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "primary_email", "phone_number", "has_digital_executor", "created_at")
    search_fields = ("full_name", "primary_email", "phone_number")
    list_filter = ("has_digital_executor",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(AccountCategory)
class AccountCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order")
    ordering = ("sort_order", "name")


@admin.register(DigitalAccount)
class DigitalAccountAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "provider",
        "profile",
        "category",
        "is_critical",
        "keep_or_close_instruction",
        "created_at",
    )
    list_filter = ("category", "is_critical", "keep_or_close_instruction")
    search_fields = ("name", "provider", "username_or_email", "profile__full_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AccountRelevanceReview)
class AccountRelevanceReviewAdmin(admin.ModelAdmin):
    list_display = ("account", "matters", "reviewer", "created_at", "next_review_due")
    list_filter = ("matters", "next_review_due")
    search_fields = ("account__name", "reviewer__username", "reviewer__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "relationship",
        "profile",
        "email",
        "phone",
        "is_emergency_contact",
        "is_digital_executor",
        "is_caregiver",
    )
    list_filter = ("is_emergency_contact", "is_digital_executor", "is_caregiver", "relationship")
    search_fields = ("full_name", "email", "phone", "profile__full_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DelegationScope)
class DelegationScopeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(DelegationGrant)
class DelegationGrantAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "contact",
        "scope",
        "applies_on_death",
        "applies_on_incapacity",
        "applies_immediately",
        "created_at",
    )
    list_filter = ("applies_on_death", "applies_on_incapacity", "applies_immediately", "scope")
    search_fields = ("profile__full_name", "contact__full_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "device_type",
        "profile",
        "operating_system",
        "used_for_2fa",
        "has_full_disk_encryption",
        "created_at",
    )
    list_filter = ("device_type", "used_for_2fa", "has_full_disk_encryption")
    search_fields = ("name", "profile__full_name", "operating_system")
    readonly_fields = ("created_at", "updated_at")


class FamilyNeedsToKnowSectionInline(admin.TabularInline):
    model = FamilyNeedsToKnowSection
    extra = 1


@admin.register(DigitalEstateDocument)
class DigitalEstateDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "profile", "version", "is_active", "created_at")
    list_filter = ("is_active", "version")
    search_fields = ("title", "profile__full_name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [FamilyNeedsToKnowSectionInline]


@admin.register(AccountDirectoryEntry)
class AccountDirectoryEntryAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "profile",
        "category_label",
        "criticality",
        "action_after_death",
        "created_at",
    )
    list_filter = ("criticality", "action_after_death", "category_label")
    search_fields = ("label", "profile__full_name", "username_hint")
    readonly_fields = ("created_at", "updated_at")


@admin.register(EmergencyNote)
class EmergencyNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "profile", "contact", "created_at")
    search_fields = ("title", "profile__full_name", "contact__full_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CheckupType)
class CheckupTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "frequency")
    list_filter = ("frequency",)
    search_fields = ("name",)


@admin.register(Checkup)
class CheckupAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "checkup_type",
        "due_date",
        "completed_at",
        "all_accounts_reviewed",
        "all_devices_reviewed",
        "contacts_up_to_date",
        "documents_up_to_date",
    )
    list_filter = (
        "checkup_type",
        "all_accounts_reviewed",
        "all_devices_reviewed",
        "contacts_up_to_date",
        "documents_up_to_date",
    )
    search_fields = ("profile__full_name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(CareRelationship)
class CareRelationshipAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "contact",
        "relationship_type",
        "has_portal_access",
        "portal_role",
        "created_at",
    )
    list_filter = ("relationship_type", "has_portal_access")
    search_fields = ("profile__full_name", "contact__full_name", "portal_role")
    readonly_fields = ("created_at", "updated_at")


@admin.register(RecoveryRequest)
class RecoveryRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "profile",
        "requested_by",
        "target_account",
        "status",
        "provider_ticket_number",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = (
        "profile__full_name",
        "requested_by__full_name",
        "target_account__name",
        "provider_ticket_number",
        "target_description",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order")
    ordering = ("sort_order", "name")
    search_fields = ("name",)


@admin.register(ImportantDocument)
class ImportantDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "profile",
        "category",
        "physical_location",
        "digital_location",
        "requires_legal_review",
        "created_at",
    )
    list_filter = ("category", "requires_legal_review")
    search_fields = (
        "title",
        "profile__full_name",
        "physical_location",
        "digital_location",
    )
    readonly_fields = ("created_at", "updated_at")
