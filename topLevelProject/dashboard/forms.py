from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Field, Fieldset, Div, Submit, Button
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
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Personal Information',
                Field('full_name', css_class='textinput'),
                Field('date_of_birth', css_class='dateinput'),
                Field('primary_email', css_class='emailinput'),
                Field('phone_number', css_class='textinput'),
                Field('notes', css_class='textarea'),
            ),
            Fieldset(
                'Digital Executor Information',
                Field('has_digital_executor', css_class='checkboxinput form-check-input'),
                Field('digital_executor_name', css_class='textinput'),
                Field('digital_executor_contact', css_class='textinput'),
            ),
            Div(
                Submit('submit', 'Save Profile', css_class='btn btn-primary'),
                css_class='button-group'
            )
        )


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            "account_category",
            "account_name_or_provider",
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
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Account Details',
                Field('account_category', css_class='select'),
                Field('account_name_or_provider', css_class='textinput'),
                Field('website_url', css_class='urlinput', placeholder="https://"),
                Field('username_or_email', css_class='textinput'),
                Field('credential_storage_location', css_class='textinput'),
                Field('is_critical', css_class='checkboxinput form-check-input'),
            ),
            Fieldset(
                'Instructions for Family',
                Field('keep_or_close_instruction', css_class='select'),
                Field('notes_for_family', css_class='textarea'),
            ),
            Div(
                Submit('submit', 'Save Account', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
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
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Field('account', css_class='select'),
            Field('matters', css_class='select'),
            Field('next_review_due', css_class='dateinput'),
            Field('reasoning', css_class='textarea'),
            Div(
                Submit('submit', 'Save Review', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
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
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Device Information',
                Field('device_type', css_class='select'),
                Field('name', css_class='textinput'),
                Field('owner_label', css_class='textinput'),
                Field('location_description', css_class='textinput'),
            ),
            Fieldset(
                'Security Information',
                Field('unlock_method_description', css_class='textarea'),
                Field('decommission_instruction', css_class='textarea'),
                Field('used_for_2fa', css_class='checkboxinput form-check-input', wrapper_class='checkbox-wrapper'),
            ),
            Div(
                Submit('submit', 'Save Device', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )


class DigitalEstateDocumentForm(forms.ModelForm):
    class Meta:
        model = DigitalEstateDocument
        fields = [
            "estate_document",
            "name_or_title",
            "overall_instructions",
            "estate_file"
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Document Details',
                Field('name_or_title', css_class='textinput'),
                Field('estate_document', css_class='select'),
                Field('estate_file', css_class='fileinput'),
                Field('overall_instructions', css_class='textarea'),
            ),
            Div(
                Submit('submit', 'Save Estate Document', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
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
        
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['relation'].queryset = Contact.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['relation'].queryset = Contact.objects.none()
        
        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            HTML('<h2 class="form-section-title">Family Awareness</h2>'),
            Field('relation', css_class='select', placeholder='Tied to who?'),
            Field('content', css_class='textarea'),
            Div(
                Field('is_location_of_legal_will', css_class='checkboxinput form-check-input'),
                Field('is_password_manager', css_class='checkboxinput form-check-input'),
                Field('is_social_media', css_class='checkboxinput form-check-input'),
                Field('is_photos_or_files', css_class='checkboxinput form-check-input'),
                Field('is_data_retention_preferences', css_class='checkboxinput form-check-input'),
                css_class='checkbox-grid'
            ),
            Div(
                Submit('submit', 'Save', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
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
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                "Contact Information",
                Field('contact_relation', css_class='select'),
                Field('contact_name', css_class='textinput'),
                Field('email', css_class='emailinput'),
                Field('phone', css_class='textinput'),
                Field('address', css_class='textarea'),
                Div(
                    Field('is_emergency_contact', css_class='checkboxinput form-check-input'),
                    Field('is_digital_executor', css_class='checkboxinput form-check-input'),
                    Field('is_caregiver', css_class='checkboxinput form-check-input'),
                    css_class='checkbox-group'
                ),
                Field('body', css_class='textarea'),
            ),
            Div(
                Submit('submit', 'Save Contact', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
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
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Field('frequency', css_class='select'),
            Field('due_date', css_class='dateinput'),
            Field('completed_at', css_class='datetimeinput'),
            Field('summary', css_class='textarea'),
            Fieldset(
                'Checkup Items',
                Div(
                    Field('all_accounts_reviewed', css_class='checkboxinput form-check-input'),
                    Field('all_devices_reviewed', css_class='checkboxinput form-check-input'),
                    Field('contacts_up_to_date', css_class='checkboxinput form-check-input'),
                    Field('documents_up_to_date', css_class='checkboxinput form-check-input'),
                    css_class='checkbox-grid'
                ),
            ),
            Div(
                Submit('submit', 'Save Checkup', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
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
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Field('contact_name', css_class='select'),
            Field('relationship_type', css_class='select'),
            Field('has_portal_access', css_class='checkboxinput form-check-input'),
            Field('portal_role', css_class='select'),
            Field('notes', css_class='textarea'),
            Div(
                Submit('submit', 'Save Care Relationship', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
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
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Field('target_account', css_class='select'),
            Field('target_description', css_class='textinput'),
            Field('status', css_class='select'),
            Field('provider_ticket_number', css_class='textinput'),
            Field('steps_taken', css_class='textarea'),
            Field('outcome_notes', css_class='textarea'),
            Div(
                Submit('submit', 'Save Recovery Request', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )


class ImportantDocumentForm(forms.ModelForm):
    class Meta:
        model = ImportantDocument
        fields = [
            "name_or_title",
            "document_category",
            "description",
            "physical_location",
            "digital_location",
            "important_file",
            "requires_legal_review",
        ]
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Document',
                Field('name_or_title', css_class='textinput'),
                Field('document_category', css_class='select'),
                Field('requires_legal_review', css_class='checkboxinput form-check-input'),
                Field('description', css_class='textarea'),
            ),
            Fieldset(
                'Document Location',
                Field('important_file', css_class='fileinput'),
                Field('physical_location', css_class='textinput'),
                Field('digital_location', css_class='textinput'),
            ),
            Div(
                Submit('submit', 'Save Document', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
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
                
                all_estate_docs = DigitalEstateDocument.objects.filter(profile=profile)
                all_important_docs = ImportantDocument.objects.filter(profile=profile)
                
                if self.instance and self.instance.pk:
                    # For editing: exclude docs delegated to OTHER contacts
                    # But include docs currently in THIS delegation
                    current_estate_ids = self.instance.delegate_estate_documents.values_list('id', flat=True)
                    current_important_ids = self.instance.delegate_important_documents.values_list('id', flat=True)
                    
                    already_delegated_estate_ids = DelegationGrant.objects.filter(
                        profile=profile
                    ).exclude(pk=self.instance.pk).values_list('delegate_estate_documents', flat=True)
                    
                    already_delegated_important_ids = DelegationGrant.objects.filter(
                        profile=profile
                    ).exclude(pk=self.instance.pk).values_list('delegate_important_documents', flat=True)
                    
                    # Include currently selected docs OR docs not delegated elsewhere
                    self.fields['delegate_estate_documents'].queryset = all_estate_docs.filter(
                        Q(id__in=current_estate_ids) | ~Q(id__in=already_delegated_estate_ids)
                    )
                    self.fields['delegate_important_documents'].queryset = all_important_docs.filter(
                        Q(id__in=current_important_ids) | ~Q(id__in=already_delegated_important_ids)
                    )
                else:
                    # For creating: exclude docs already delegated to any contact
                    already_delegated_estate_ids = DelegationGrant.objects.filter(
                        profile=profile
                    ).values_list('delegate_estate_documents', flat=True)
                    
                    already_delegated_important_ids = DelegationGrant.objects.filter(
                        profile=profile
                    ).values_list('delegate_important_documents', flat=True)
                    
                    self.fields['delegate_estate_documents'].queryset = all_estate_docs.exclude(
                        id__in=already_delegated_estate_ids
                    )
                    self.fields['delegate_important_documents'].queryset = all_important_docs.exclude(
                        id__in=already_delegated_important_ids
                    )
                
                available_estate_count = self.fields['delegate_estate_documents'].queryset.count()
                available_important_count = self.fields['delegate_important_documents'].queryset.count()
                
                self.fields['delegate_estate_documents'].help_text = (
                    f"{available_estate_count} estate document(s) available for delegation. "
                    "Documents already delegated to other contacts are not shown."
                )
                self.fields['delegate_important_documents'].help_text = (
                    f"{available_important_count} important document(s) available for delegation. "
                    "Documents already delegated to other contacts are not shown."
                )
                
            except Profile.DoesNotExist:
                self.fields['delegate_to'].queryset = Contact.objects.none()
                self.fields['delegate_estate_documents'].queryset = DigitalEstateDocument.objects.none()
                self.fields['delegate_important_documents'].queryset = ImportantDocument.objects.none()

        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Delegation Details',
                Field('delegate_to', css_class='select'),
                Field('delegation_category', css_class='select'),
            ),
            Fieldset(
                'Estate Documents',
                HTML('<p class="field-help-text">Select which estate documents this delegation covers:</p>'),
                Field('delegate_estate_documents', css_class='checkbox-list'),
            ),
            Fieldset(
                'Important Documents',
                HTML('<p class="field-help-text">Select which important documents this delegation covers (optional):</p>'),
                Field('delegate_important_documents', css_class='checkbox-list'),
            ),
            Fieldset(
                'When Does This Apply?',
                Div(
                    Field('applies_on_death', css_class='checkboxinput form-check-input'),
                    Field('applies_on_incapacity', css_class='checkboxinput form-check-input'),
                    Field('applies_immediately', css_class='checkboxinput form-check-input'),
                    css_class='checkbox-grid'
                ),
            ),
            Field('notes_for_contact', css_class='textarea'),
            Div(
                Submit('submit', 'Save Delegation Grant', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )
    
    def clean(self):
        """Validate that at least one document is selected"""
        cleaned_data = super().clean()
        estate_docs = cleaned_data.get('delegate_estate_documents')
        important_docs = cleaned_data.get('delegate_important_documents')
        
        # Check if any documents are selected
        has_estate = estate_docs and estate_docs.exists()
        has_important = important_docs and important_docs.exists()
        
        if not has_estate and not has_important:
            raise forms.ValidationError(
                "You must select at least one estate document or important document to delegate."
            )
        
        return cleaned_data