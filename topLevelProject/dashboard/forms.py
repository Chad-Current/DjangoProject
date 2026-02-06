# dashboard/forms.py
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Field, Fieldset, Div, Row, Column, Submit, Button, ButtonHolder
from .models import (
    Profile,
    Account,
    AccountRelevanceReview,
    DelegationGrant,
    Device,
    DigitalEstateDocument,
    FamilyNeedsToKnowSection,
    Contact,
    Checkup,
    CareRelationship,
    RecoveryRequest,
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


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            "account_category",
            "account_name",
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
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Account Details',
                Row(
                    Column('account_category', css_class='form-group col-md-6 mb-0'),
                    Column('account_name', css_class='form-group col-md-6 mb-0'),
                    Column('provider', css_class='form-group col-md-6 mb-0'),
                    Column('website_url', css_class='form-group col-md-6 mb-0', placeholder="https://"),
                ),
                Row(
                    Column('username_or_email', css_class='form-group col-md-8 mb-0'),
                    Column('credential_storage_location', css_class='form-group col-md-4 mb-0'),
                    Column('is_critical', css_class='form-group col-md-4 mb-0'),
                ),                
            ),
            Fieldset(
                'Instructions for Family',
                'keep_or_close_instruction',
                'notes_for_family',
            ),
            Div(
                Submit('submit', 'Save Account', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();")
            ),
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
                self.fields['account'].queryset = Account.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['account'].queryset = Account.objects.none()
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'account',
            Row(
                Column('matters', css_class='form-group col-md-6 mb-0'),
                Column('next_review_due', css_class='form-group col-md-6 mb-0'),
            ),
            'reasoning',
            Div(
                Submit('submit', 'Save Review', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();")
            ),
        )


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            "device_type",
            "name",
            "owner_label",
            "location_description",
            "unlock_method_description",
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
                    Column('device_type', css_class='form-group col-md-6 mb-0'),
                    Column('name', css_class='form-group col-md-6 mb-2'),
                ),
                Row(
                    Column('owner_label', css_class='form-group col-md-6 mb-0'),
                    Column('location_description', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Security Information',
                Row(
                    Column('unlock_method_description', css_class='form-group col-md-12 mb-4'),
                    Column('decommission_instruction', css_class="form-group col-md-12 mb-4"),
                ),
                Row(
                    Column(
                        HTML("<label>Uses Two-Factor Authenication</label>"),
                    ), 
                    Column('used_for_2fa', css_class="form-group col-md-12 mt-0"),
                ),
            ),
            Div(
                Submit('submit', 'Save Device', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();")
            ),
        )


class DigitalEstateDocumentForm(forms.ModelForm):
    class Meta:
        model = DigitalEstateDocument
        fields = [
            "estate_document",
            "is_active",
            "overall_instructions",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Document Details',
                Row(
                    Column('estate_document', css_class='form-group col-md-8 mb-0'),
                    Column('is_active', css_class='form-group col-md-4 mb-0'),
                ),
                'overall_instructions',
            ),
            Div(
                Submit('submit', 'Save Estate Document', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();")
            ),
        )


class FamilyNeedsToKnowSectionForm(forms.ModelForm):
    class Meta:
        model = FamilyNeedsToKnowSection
        fields = [
            "relation",
            "content",
            "is_location_of_legal_will",
            "is_password_manager",
            "is_social_media",
            "is_photos_or_files",
            "is_data_retention_preferences",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter contacts by user's profile
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['relation'].queryset = Contact.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['relation'].queryset = Contact.objects.none()
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h2>Family Awareness</h2>'),
            Field('relation', placeholder='Tied to who?'),
            Field('content'),
            Row(
                Column('is_location_of_legal_will'),
                Column('is_password_manager'),
                Column('is_social_media'),
                Column('is_photos_or_files'),
                Column('is_data_retention_preferences'),                
            ),
            ButtonHolder(
                Submit('submit', 'Save', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
            ),
        )


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = [
            'contact_relation',
            'contact_name',
            'email',
            'phone',
            'address',
            'is_emergency_contact',
            'is_digital_executor',
            'is_caregiver',
            'body',
        ]
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Contact Information",
                Row(
                    Column('contact_relation', css_class='form-group col-md-6 mb-0'),
                    Column('contact_name', css_class='form-group col-md-6 mb-0'),
                ),
                Row(
                    Column('email', css_class='form-group col-md-6 mb-0'),
                    Column('phone', css_class='form-group col-md-6 mb-0'),
                ),
                'address',
                Row(
                    Column('is_emergency_contact', css_class='form-group col-md-12 mb-0'),
                    Column('is_digital_executor', css_class='form-group col-md-12 mb-0'),
                    Column('is_caregiver', css_class='form-group col-md-12 mb-0'),
                ),
                Row(
                    Column('body', css_class="form-group col-md-12 mb-0"),
                ),
            ),
            Div(
                Submit('submit', 'Save Contact', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();")
            ),
        )


class CheckupForm(forms.ModelForm):
    class Meta:
        model = Checkup
        fields = [
            "frequency",
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
            Row(
                Column('frequency', css_class='form-group col-md-4 mb-0'),
                Column('due_date', css_class='form-group col-md-4 mb-0'),
                Column('completed_at', css_class='form-group col-md-4 mb-0'),
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
            Div(
                Submit('submit', 'Save Checkup', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();")
            ),
        )


class CareRelationshipForm(forms.ModelForm):
    class Meta:
        model = CareRelationship
        fields = [
            "contact_name",
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
                self.fields['contact_name'].queryset = Contact.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['contact_name'].queryset = Contact.objects.none()
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('contact_name', css_class='form-group col-md-6 mb-0'),
                Column('relationship_type', css_class='form-group col-md-6 mb-0'),
            ),
            Row(
                Column('has_portal_access', css_class='form-group col-md-6 mb-0'),
                Column('portal_role', css_class='form-group col-md-6 mb-0'),
            ),
            'notes',
            Div(
                Submit('submit', 'Save Care Relationship', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();")
            ),
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
                self.fields['target_account'].queryset = Account.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['target_account'].queryset = Account.objects.none()
        
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
            Div(
                Submit('submit', 'Save Recovery Request', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();")
            ),
        )


class ImportantDocumentForm(forms.ModelForm):
    class Meta:
        model = ImportantDocument
        fields = [
            "document_category",
            "description",
            "physical_location",
            "digital_location",
            "file",
            "requires_legal_review",
        ]
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Document',
                Row(
                    Column('document_category', css_class="form-group col-md-8 mb-0"),
                    Column('requires_legal_review', css_class="form-group col-md-4 mb-0"),
                ),
                'description',
            ),
            Fieldset(
                'Document Location',
                Row(
                    Column('physical_location', css_class="form-group col-md-4 mb-0"),
                    Column('digital_location', css_class="form-group col-md-4 mb-0"),
                    Column('file', css_class="form-group col-md-4 mb-0"),
                ),
            ),
            Div(
                Submit('submit', 'Save Document', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();")
            ),
        )


class DelegationGrantForm(forms.ModelForm):
    class Meta:
        model = DelegationGrant
        fields = [
            'delegate_to',
            'delegation_category',
            'delegate_estate_documents',  
            'delegate_important_documents',
            "applies_on_death",
            "applies_on_incapacity",
            "applies_immediately",
            "notes_for_contact",
        ]
        widgets = {
            'delegate_estate_documents': forms.CheckboxSelectMultiple(),  
            'delegate_important_documents': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['delegate_to'].queryset = Contact.objects.filter(profile=profile)
                self.fields['delegate_estate_documents'].queryset = DigitalEstateDocument.objects.filter(profile=profile) 
                self.fields['delegate_important_documents'].queryset = ImportantDocument.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['delegate_to'].queryset = Contact.objects.none()
                self.fields['delegate_estate_documents'].queryset = DigitalEstateDocument.objects.none()  
                self.fields['delegate_important_documents'].queryset = ImportantDocument.objects.none()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Delegation Details',
                Row(
                    Column('delegate_to', css_class='form-group col-md-6 mb-0'),
                    Column('delegation_category', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Estate Documents',
                HTML('<p class="text-muted small">Select which estate documents this delegation covers:</p>'),
                'delegate_estate_documents',
            ),
            Fieldset(
                'Important Documents',
                HTML('<p class="text-muted small">Select which important documents this delegation covers (optional):</p>'),
                'delegate_important_documents',
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
            Div(
                Submit('submit', 'Save Delegation Grant', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();")
            ),
        )