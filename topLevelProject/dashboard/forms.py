from django import forms

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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "user",
            "full_name",
            "date_of_birth",
            "primary_email",
            "phone_number",
            "notes",
            "has_digital_executor",
            "digital_executor_name",
            "digital_executor_contact",
        ]


class AccountCategoryForm(forms.ModelForm):
    class Meta:
        model = AccountCategory
        fields = ["name", "description", "sort_order"]


class DigitalAccountForm(forms.ModelForm):
    class Meta:
        model = DigitalAccount
        fields = [
            "profile",
            "category",
            "name",
            "provider",
            "website_url",
            "username_or_email",
            "credential_storage_location",
            "is_critical",
            "keep_or_close_instruction",
            "notes_for_family",
        ]


class AccountRelevanceReviewForm(forms.ModelForm):
    class Meta:
        model = AccountRelevanceReview
        fields = [
            "account",
            "reviewer",
            "matters",
            "reasoning",
            "next_review_due",
        ]


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = [
            "profile",
            "full_name",
            "relationship",
            "email",
            "phone",
            "address",
            "is_emergency_contact",
            "is_digital_executor",
            "is_caregiver",
            "notes",
        ]


class DelegationScopeForm(forms.ModelForm):
    class Meta:
        model = DelegationScope
        fields = ["name", "description"]


class DelegationGrantForm(forms.ModelForm):
    class Meta:
        model = DelegationGrant
        fields = [
            "profile",
            "contact",
            "scope",
            "applies_on_death",
            "applies_on_incapacity",
            "applies_immediately",
            "notes_for_contact",
        ]


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            "profile",
            "device_type",
            "name",
            "operating_system",
            "owner_label",
            "location_description",
            "unlock_method_description",
            "has_full_disk_encryption",
            "used_for_2fa",
            "decommission_instruction",
        ]


class DigitalEstateDocumentForm(forms.ModelForm):
    class Meta:
        model = DigitalEstateDocument
        fields = [
            "profile",
            "title",
            "version",
            "is_active",
            "overall_instructions",
            "location_of_legal_will",
            "location_of_password_manager_instructions",
            "wishes_for_social_media",
            "wishes_for_photos_and_files",
            "data_retention_preferences",
        ]


class FamilyNeedsToKnowSectionForm(forms.ModelForm):
    class Meta:
        model = FamilyNeedsToKnowSection
        fields = [
            "document",
            "heading",
            "sort_order",
            "content",
        ]


class AccountDirectoryEntryForm(forms.ModelForm):
    class Meta:
        model = AccountDirectoryEntry
        fields = [
            "profile",
            "label",
            "category_label",
            "website_url",
            "username_hint",
            "criticality",
            "action_after_death",
            "notes",
        ]


class EmergencyNoteForm(forms.ModelForm):
    class Meta:
        model = EmergencyNote
        fields = [
            "profile",
            "contact",
            "title",
            "body",
        ]


class CheckupTypeForm(forms.ModelForm):
    class Meta:
        model = CheckupType
        fields = [
            "name",
            "frequency",
            "description",
        ]


class CheckupForm(forms.ModelForm):
    class Meta:
        model = Checkup
        fields = [
            "profile",
            "checkup_type",
            "due_date",
            "completed_at",
            "completed_by",
            "summary",
            "all_accounts_reviewed",
            "all_devices_reviewed",
            "contacts_up_to_date",
            "documents_up_to_date",
        ]


class CareRelationshipForm(forms.ModelForm):
    class Meta:
        model = CareRelationship
        fields = [
            "profile",
            "contact",
            "relationship_type",
            "has_portal_access",
            "portal_role",
            "notes",
        ]


class RecoveryRequestForm(forms.ModelForm):
    class Meta:
        model = RecoveryRequest
        fields = [
            "profile",
            "requested_by",
            "target_account",
            "target_description",
            "status",
            "provider_ticket_number",
            "steps_taken",
            "outcome_notes",
        ]


class DocumentCategoryForm(forms.ModelForm):
    class Meta:
        model = DocumentCategory
        fields = [
            "name",
            "description",
            "sort_order",
        ]


class ImportantDocumentForm(forms.ModelForm):
    class Meta:
        model = ImportantDocument
        fields = [
            "profile",
            "category",
            "title",
            "description",
            "physical_location",
            "digital_location",
            "file",
            "requires_legal_review",
        ]
