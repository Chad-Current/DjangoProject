#V49
 
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
            "full_name",
            "date_of_birth",
            "primary_email",
            "phone_number",
            "notes",
            "has_digital_executor",
            "digital_executor_name",
            "digital_executor_contact",
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }


class AccountCategoryForm(forms.ModelForm):
    class Meta:
        model = AccountCategory
        fields = ["name", "description", "sort_order"]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class DigitalAccountForm(forms.ModelForm):
    class Meta:
        model = DigitalAccount
        fields = [
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
        widgets = {
            'notes_for_family': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['category'].queryset = AccountCategory.objects.filter(user=self.user)


class AccountRelevanceReviewForm(forms.ModelForm):
    class Meta:
        model = AccountRelevanceReview
        fields = [
            "account",
            "matters",
            "reasoning",
            "next_review_due",
        ]
        widgets = {
            'reasoning': forms.Textarea(attrs={'rows': 3}),
            'next_review_due': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['account'].queryset = DigitalAccount.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['account'].queryset = DigitalAccount.objects.none()


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = [
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
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class DelegationScopeForm(forms.ModelForm):
    class Meta:
        model = DelegationScope
        fields = ["name", "description"]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class DelegationGrantForm(forms.ModelForm):
    class Meta:
        model = DelegationGrant
        fields = [
            "contact",
            "scope",
            "applies_on_death",
            "applies_on_incapacity",
            "applies_immediately",
            "notes_for_contact",
        ]
        widgets = {
            'notes_for_contact': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['contact'].queryset = Contact.objects.filter(profile=profile)
                if hasattr(DelegationScope, 'user'):
                    self.fields['scope'].queryset = DelegationScope.objects.filter(user=self.user)
            except Profile.DoesNotExist:
                self.fields['contact'].queryset = Contact.objects.none()


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
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
        widgets = {
            'unlock_method_description': forms.Textarea(attrs={'rows': 2}),
            'decommission_instruction': forms.Textarea(attrs={'rows': 3}),
        }


class DigitalEstateDocumentForm(forms.ModelForm):
    class Meta:
        model = DigitalEstateDocument
        fields = [
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
        widgets = {
            'overall_instructions': forms.Textarea(attrs={'rows': 4}),
            'wishes_for_social_media': forms.Textarea(attrs={'rows': 3}),
            'wishes_for_photos_and_files': forms.Textarea(attrs={'rows': 3}),
            'data_retention_preferences': forms.Textarea(attrs={'rows': 3}),
        }


class FamilyNeedsToKnowSectionForm(forms.ModelForm):
    class Meta:
        model = FamilyNeedsToKnowSection
        fields = [
            "heading",
            "sort_order",
            "content",
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
        }


class AccountDirectoryEntryForm(forms.ModelForm):
    class Meta:
        model = AccountDirectoryEntry
        fields = [
            "label",
            "category_label",
            "website_url",
            "username_hint",
            "criticality",
            "action_after_death",
            "notes",
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class EmergencyNoteForm(forms.ModelForm):
    class Meta:
        model = EmergencyNote
        fields = [
            "contact",
            "title",
            "body",
        ]
        widgets = {
            'body': forms.Textarea(attrs={'rows': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['contact'].queryset = Contact.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['contact'].queryset = Contact.objects.none()


class CheckupTypeForm(forms.ModelForm):
    class Meta:
        model = CheckupType
        fields = [
            "name",
            "frequency",
            "description",
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class CheckupForm(forms.ModelForm):
    class Meta:
        model = Checkup
        fields = [
            "checkup_type",
            "due_date",
            "completed_at",
            "summary",
            "all_accounts_reviewed",
            "all_devices_reviewed",
            "contacts_up_to_date",
            "documents_up_to_date",
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'completed_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'summary': forms.Textarea(attrs={'rows': 4}),
        }


class CareRelationshipForm(forms.ModelForm):
    class Meta:
        model = CareRelationship
        fields = [
            "contact",
            "relationship_type",
            "has_portal_access",
            "portal_role",
            "notes",
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['contact'].queryset = Contact.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['contact'].queryset = Contact.objects.none()


class RecoveryRequestForm(forms.ModelForm):
    class Meta:
        model = RecoveryRequest
        fields = [
            "target_account",
            "target_description",
            "status",
            "provider_ticket_number",
            "steps_taken",
            "outcome_notes",
        ]
        widgets = {
            'target_description': forms.Textarea(attrs={'rows': 2}),
            'steps_taken': forms.Textarea(attrs={'rows': 4}),
            'outcome_notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['target_account'].queryset = DigitalAccount.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['target_account'].queryset = DigitalAccount.objects.none()


class DocumentCategoryForm(forms.ModelForm):
    class Meta:
        model = DocumentCategory
        fields = [
            "name",
            "description",
            "sort_order",
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class ImportantDocumentForm(forms.ModelForm):
    class Meta:
        model = ImportantDocument
        fields = [
            "category",
            "title",
            "description",
            "physical_location",
            "digital_location",
            "file",
            "requires_legal_review",
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'physical_location': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and hasattr(DocumentCategory, 'user'):
            self.fields['category'].queryset = DocumentCategory.objects.filter(user=self.user)