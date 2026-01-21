#1V-New Claude Chat
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Fieldset, Row, Column, HTML, Div
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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Personal Information',
                Row(
                    Column('full_name', css_class='form-group col-md-6 mb-0'),
                    Column('date_of_birth', css_class='form-group col-md-6 mb-0'),
                ),
                Row(
                    Column('primary_email', css_class='form-group col-md-6 mb-0'),
                    Column('phone_number', css_class='form-group col-md-6 mb-0'),
                ),
                'notes',
            ),
            Fieldset(
                'Digital Executor Information',
                'has_digital_executor',
                Row(
                    Column('digital_executor_name', css_class='form-group col-md-6 mb-0'),
                    Column('digital_executor_contact', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Submit('submit', 'Save Profile', css_class='btn btn-primary')
        )


class AccountCategoryForm(forms.ModelForm):
    class Meta:
        model = AccountCategory
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-8 mb-0'),
            ),

            Submit('submit', 'Save Category', css_class='btn btn-primary')
        )


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
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['category'].queryset = AccountCategory.objects.filter(user=self.user)
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Account Details',
                'category',
                Row(
                    Column('name', css_class='form-group col-md-6 mb-0'),
                    Column('provider', css_class='form-group col-md-6 mb-0'),
                ),
                'website_url',
                Row(
                    Column('username_or_email', css_class='form-group col-md-8 mb-0'),
                    Column('is_critical', css_class='form-group col-md-4 mb-0'),
                ),
                'credential_storage_location',
            ),
            Fieldset(
                'Instructions for Family',
                'keep_or_close_instruction',
                'notes_for_family',
            ),
            Submit('submit', 'Save Account', css_class='btn btn-primary')
        )


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
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'account',
            Row(
                Column('matters', css_class='form-group col-md-6 mb-0'),
                Column('next_review_due', css_class='form-group col-md-6 mb-0'),
            ),
            'reasoning',
            Submit('submit', 'Save Review', css_class='btn btn-primary')
        )


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Contact Information',
                Row(
                    Column('full_name', css_class='form-group col-md-6 mb-0'),
                    Column('relationship', css_class='form-group col-md-6 mb-0'),
                ),
                Row(
                    Column('email', css_class='form-group col-md-6 mb-0'),
                    Column('phone', css_class='form-group col-md-6 mb-0'),
                ),
                'address',
            ),
            Fieldset(
                'Contact Roles',
                Row(
                    Column('is_emergency_contact', css_class='form-group col-md-4 mb-0'),
                    Column('is_digital_executor', css_class='form-group col-md-4 mb-0'),
                    Column('is_caregiver', css_class='form-group col-md-4 mb-0'),
                ),
            ),
            'notes',
            Submit('submit', 'Save Contact', css_class='btn btn-primary')
        )


class DelegationScopeForm(forms.ModelForm):
    class Meta:
        model = DelegationScope
        fields = ["name", "description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'name',
            'description',
            Submit('submit', 'Save Scope', css_class='btn btn-primary')
        )


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
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('contact', css_class='form-group col-md-6 mb-0'),
                Column('scope', css_class='form-group col-md-6 mb-0'),
            ),
            Fieldset(
                'When Does This Apply?',
                Row(
                    Column('applies_on_death', css_class='form-group col-md-4 mb-0'),
                    Column('applies_on_incapacity', css_class='form-group col-md-4 mb-0'),
                    Column('applies_immediately', css_class='form-group col-md-4 mb-0'),
                ),
            ),
            'notes_for_contact',
            Submit('submit', 'Save Delegation Grant', css_class='btn btn-primary')
        )


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Device Information',
                Row(
                    Column('device_type', css_class='form-group col-md-4 mb-0'),
                    Column('name', css_class='form-group col-md-4 mb-0'),
                    Column('operating_system', css_class='form-group col-md-4 mb-0'),
                ),
                Row(
                    Column('owner_label', css_class='form-group col-md-6 mb-0'),
                    Column('location_description', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Security Information',
                'unlock_method_description',
                Row(
                    Column('has_full_disk_encryption', css_class='form-group col-md-6 mb-0'),
                    Column('used_for_2fa', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            'decommission_instruction',
            Submit('submit', 'Save Device', css_class='btn btn-primary')
        )


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Document Details',
                Row(
                    Column('title', css_class='form-group col-md-8 mb-0'),
                    Column('version', css_class='form-group col-md-2 mb-0'),
                    Column('is_active', css_class='form-group col-md-2 mb-0'),
                ),
                'overall_instructions',
            ),
            Fieldset(
                'Important Locations',
                'location_of_legal_will',
                'location_of_password_manager_instructions',
            ),
            Fieldset(
                'Your Wishes',
                'wishes_for_social_media',
                'wishes_for_photos_and_files',
                'data_retention_preferences',
            ),
            Submit('submit', 'Save Document', css_class='btn btn-primary')
        )


class FamilyNeedsToKnowSectionForm(forms.ModelForm):
    class Meta:
        model = FamilyNeedsToKnowSection
        fields = [
            "heading",
            "sort_order",
            "content",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('heading', css_class='form-group col-md-9 mb-0'),
                Column('sort_order', css_class='form-group col-md-3 mb-0'),
            ),
            'content',
            Submit('submit', 'Save Section', css_class='btn btn-primary')
        )


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('label', css_class='form-group col-md-6 mb-0'),
                Column('category_label', css_class='form-group col-md-6 mb-0'),
            ),
            'website_url',
            Row(
                Column('username_hint', css_class='form-group col-md-6 mb-0'),
                Column('criticality', css_class='form-group col-md-6 mb-0'),
            ),
            'action_after_death',
            'notes',
            Submit('submit', 'Save Entry', css_class='btn btn-primary')
        )


class EmergencyNoteForm(forms.ModelForm):
    class Meta:
        model = EmergencyNote
        fields = [
            "contact",
            "name",
            "body",
        ]
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['name'].queryset = Contact.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['name'].queryset = Contact.objects.none()
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'contact',
            'name',
            'body',
            Submit('submit', 'Save Emergency Note', css_class='btn btn-primary')
        )


class CheckupTypeForm(forms.ModelForm):
    class Meta:
        model = CheckupType
        fields = [
            "name",
            "frequency",
            "description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-8 mb-0'),
                Column('frequency', css_class='form-group col-md-4 mb-0'),
            ),
            'description',
            Submit('submit', 'Save Checkup Type', css_class='btn btn-primary')
        )


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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'checkup_type',
            Row(
                Column('due_date', css_class='form-group col-md-6 mb-0'),
                Column('completed_at', css_class='form-group col-md-6 mb-0'),
            ),
            'summary',
            Fieldset(
                'Checkup Items',
                Row(
                    Column('all_accounts_reviewed', css_class='form-group col-md-6 mb-0'),
                    Column('all_devices_reviewed', css_class='form-group col-md-6 mb-0'),
                ),
                Row(
                    Column('contacts_up_to_date', css_class='form-group col-md-6 mb-0'),
                    Column('documents_up_to_date', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Submit('submit', 'Save Checkup', css_class='btn btn-primary')
        )


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
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['contact'].queryset = Contact.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['contact'].queryset = Contact.objects.none()
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('contact', css_class='form-group col-md-6 mb-0'),
                Column('relationship_type', css_class='form-group col-md-6 mb-0'),
            ),
            Row(
                Column('has_portal_access', css_class='form-group col-md-6 mb-0'),
                Column('portal_role', css_class='form-group col-md-6 mb-0'),
            ),
            'notes',
            Submit('submit', 'Save Care Relationship', css_class='btn btn-primary')
        )


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
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['target_account'].queryset = DigitalAccount.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['target_account'].queryset = DigitalAccount.objects.none()
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'target_account',
            'target_description',
            Row(
                Column('status', css_class='form-group col-md-6 mb-0'),
                Column('provider_ticket_number', css_class='form-group col-md-6 mb-0'),
            ),
            'steps_taken',
            'outcome_notes',
            Submit('submit', 'Save Recovery Request', css_class='btn btn-primary')
        )


class DocumentCategoryForm(forms.ModelForm):
    class Meta:
        model = DocumentCategory
        fields = [
            "name",
            "description",
            "sort_order",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-8 mb-0'),
                Column('sort_order', css_class='form-group col-md-4 mb-0'),
            ),
            'description',
            Submit('submit', 'Save Category', css_class='btn btn-primary')
        )


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
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and hasattr(DocumentCategory, 'user'):
            self.fields['category'].queryset = DocumentCategory.objects.filter(user=self.user)
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'category',
            'title',
            'description',
            Fieldset(
                'Document Location',
                'physical_location',
                'digital_location',
                'file',
            ),
            'requires_legal_review',
            Submit('submit', 'Save Document', css_class='btn btn-primary')
        )

