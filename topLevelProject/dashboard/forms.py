# dashboard/forms.py
from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Field, Fieldset, Div, Submit, Button
from .models import (
    Profile,
    Account,
    RelevanceReview,
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


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = [
            'contact_relation',
            'contact_name',
            'email',
            'phone',
            'address_1',
            'address_2',
            'city',
            'state',
            'zipcode',
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
            ),
            Fieldset(
                'Address',
                Field('address_1', css_class='textinput'),
                Field('address_2', css_class='textinput'),
                Field('city', css_class='textinput'),
                Field('state', css_class='textinput'),
                Field('zipcode', css_class='textinput'),
            ),
            Div(
                Field('is_emergency_contact', css_class='checkboxinput form-check-input'),
                Field('is_digital_executor', css_class='checkboxinput form-check-input'),
                Field('is_caregiver', css_class='checkboxinput form-check-input'),
                css_class='checkbox-group'
            ),
                Field('body', css_class='textarea'),
            Div(
                Submit('submit', 'Save Contact', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )    

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            "delegated_account_to",
            "account_category",
            "account_name_or_provider",
            "website_url",
            "username_or_email",
            "credential_storage_location",
            "review_time",
            "keep_or_close_instruction",
            "notes_for_family",
        ]
        labels = {
            "delegated_account_to":"Assign Account to",
            "account_category":"Type of Account",
            "account_name_or_provider":"Name or Provider",
            "website_url":"Website URL",
            "username_or_email":"Username or Email",
            "credential_storage_location":"Crediential Storage Location",
            'review_time':"Review needed in"
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
        # Make delegated_to required
        self.fields['delegated_account_to'].required = True

        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['delegated_account_to'].queryset = Contact.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['delegated_account_to'].queryset = Contact.objects.none()

        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Account Assignment',
                HTML('<div class="alert alert-warning"><strong>Required:</strong> You must assign this account to a contact.</div>'),
                Field('delegated_account_to', css_class='select'),
            ),
            Fieldset(
                'Account Details',
                Field('account_category', css_class='select'),
                Field('account_name_or_provider', css_class='textinput'),
                Field('website_url', css_class='urlinput', placeholder="https://"),
                Field('username_or_email', css_class='textinput'),
                Field('credential_storage_location', css_class='textinput'),
                Field('review_time', css_class='select'),
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


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            "delegated_device_to", 
            "device_type",
            "device_name",
            "owner_label",
            "location_description",
            "unlock_method_description",
            "used_for_2fa",
            "decommission_instruction",
            "review_time"
        ]
        labels = {
            "delegated_device_to":"Assign Device To", 
            "device_type":"Type of Device",
            "device_name":"Name",
            "owner_label":"Labeled as",
            "location_description":"Typical Location of Device",
            "unlock_method_description":"Unlock Method",
            "used_for_2fa":"Used For Two Factor Authentication",
            "decommission_instruction":"Decommission Instructions",
            'review_time':"Review needed in"
        }
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Make delegated_to required
        self.fields['delegated_device_to'].required = True

        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['delegated_device_to'].queryset = Contact.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['delegated_device_to'].queryset = Contact.objects.none()

        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Device Assignment',
                HTML('<div class="alert alert-warning"><strong>Required:</strong> You must assign this device to a contact.</div>'),
                Field('delegated_device_to', css_class='select'),
            ),
            Fieldset(
                'Device Information',
                Field('device_type', css_class='select'),
                Field('device_name', css_class='textinput'),
                Field('owner_label', css_class='textinput'),
                Field('location_description', css_class='textinput'),
            ),
            Fieldset(
                'Security Information',
                Field('unlock_method_description', css_class='textarea'),
                Field('decommission_instruction', css_class='textarea'),
                Field('used_for_2fa', css_class='checkboxinput form-check-input'),
                Field('review_time', css_class='select')
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
            "delegated_estate_to",  
            "estate_category",
            "name_or_title",
            "estate_overall_instructions",
            "estate_physical_location",
            "estate_digital_location",
            "estate_file",
            "applies_on_death",
            "applies_on_incapacity",
            "applies_immediately",
            "review_time"
        ]

        labels = {
            "delegated_estate_to":"Assign Document to",  
            "estate_category":"Category",
            "name_or_title":"Name or Title",
            "estate_overall_instructions":"Instructions",
            "estate_physical_location":"Physical Location",
            "estate_digital_location":"Digital Location",
            "estate_file":"File",
            "applies_on_death":"Applied Upon Death",
            "applies_on_incapacity":"Applied On Incapacitation",
            "applies_immediately":"Applies Immeditately",
            'review_time':"Review needed in"           
        }

        widgets = {
            'applies_on_death': forms.CheckboxInput(),  
            'applies_on_incapacity': forms.CheckboxInput(),
            'applies_immediately': forms.CheckboxInput()
        }
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make delegated_to required
        self.fields['delegated_estate_to'].required = True
        
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['delegated_estate_to'].queryset = Contact.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['delegated_estate_to'].queryset = Contact.objects.none()
        
        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Document Assignment',
                HTML('<div class="alert alert-warning"><strong>Required:</strong> You must assign this document to a contact.</div>'),
                Field('delegated_estate_to', css_class='select'),
            ),
            Fieldset(
                'Document Details',
                Field('name_or_title', css_class='textinput'),
                Field('estate_category', css_class='select'),
                Field('estate_file', css_class='fileinput'),
                Field('estate_overall_instructions', css_class='textarea'),
            ),
            Fieldset(
                'Document Location',
                Field('estate_physical_location', css_class='textinput'),
                Field('estate_digital_location', css_class='textinput'),
            ),
            Fieldset(
                'Declarations',
                Field('review_time', css_class='select'),
                Field('applies_on_death',css_class='checkboxinput form-check-input'),
                Field('applies_on_incapacity',css_class='checkboxinput form-check-input'),
                Field('applies_immediately',css_class='checkboxinput form-check-input'),
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
        labels = {
            "relation":"Who Needs To Be Informed",
            "content":"What Do You Want To Tell Them",
            "is_location_of_legal_will":"For Location Of Will?",
            "is_password_manager":"Password Manager Information",
            "is_social_media":"How To Handle Social Media Accounts",
            "is_photos_or_files":"What To Do With Photos Or Files",
            "is_data_retention_preferences":"How Long Do Wish To Retain Information",  
        }
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
            "delegated_important_document_to", 
            "name_or_title",
            "document_category",
            "description",
            "physical_location",
            "digital_location",
            "important_file",
            "requires_legal_review",            
            "applies_on_death",
            "applies_on_incapacity",
            "applies_immediately",
            "review_time"
        ]
        labels = {
            "delegated_important_document_to":"Assign Document To", 
            "name_or_title":"Name or Title",
            "document_category":"Category",
            "description":"Description",
            "physical_location":"Physical Location",
            "digital_location":"Other Digital Locations",
            "important_file":"File",
            "requires_legal_review":"Requires Professional Legal Review",            
            "applies_on_death":"Applies On Death",
            "applies_on_incapacity":"Applies On Incapacitation",
            "applies_immediately":"Applies Immediately",   
        }
        widgets = {
            'applies_on_death': forms.CheckboxInput(),  
            'applies_on_incapacity': forms.CheckboxInput(),
            'applies_immediately': forms.CheckboxInput()
        }

    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make delegated_to required
        self.fields['delegated_important_document_to'].required = True
        
        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['delegated_important_document_to'].queryset = Contact.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['delegated_important_document_to'].queryset = Contact.objects.none()
        
        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Document Assignment',
                HTML('<div class="alert alert-warning"><strong>Required:</strong> You must assign this document to a contact.</div>'),
                Field('delegated_important_document_to', css_class='select'),
            ),
            Fieldset(
                'Document',
                Field('name_or_title', css_class='textinput'),
                Field('document_category', css_class='select'),
                Field('description', css_class='textarea'),
                Field('requires_legal_review', css_class='checkboxinput form-check-input'),
                Field('applies_on_death',css_class='checkboxinput form-check-input'),
                Field('applies_on_incapacity',css_class='checkboxinput form-check-input'),
                Field('applies_immediately',css_class='checkboxinput form-check-input'),
                Field('review_time', css_class='select')
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


class RelevanceReviewForm(forms.ModelForm):
    class Meta:
        model = RelevanceReview
        fields = [
            "account_review",
            "device_review",
            "estate_review",
            "important_document_review",
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
                
                # Filter querysets to only show items belonging to this user's profile
                self.fields['account_review'].queryset = Account.objects.filter(profile=profile)
                self.fields['device_review'].queryset = Device.objects.filter(profile=profile)
                self.fields['estate_review'].queryset = DigitalEstateDocument.objects.filter(profile=profile)
                self.fields['important_document_review'].queryset = ImportantDocument.objects.filter(profile=profile)
                
                # Make all review fields optional (user picks one)
                self.fields['account_review'].required = False
                self.fields['device_review'].required = False
                self.fields['estate_review'].required = False
                self.fields['important_document_review'].required = False
                
            except Profile.DoesNotExist:
                self.fields['account_review'].queryset = Account.objects.none()
                self.fields['device_review'].queryset = Device.objects.none()
                self.fields['estate_review'].queryset = DigitalEstateDocument.objects.none()
                self.fields['important_document_review'].queryset = ImportantDocument.objects.none()
        
        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            HTML('''
                <div class="alert alert-info mb-3">
                    <strong>Select ONE item to review:</strong> Choose an account, device, estate document, or important document.
                </div>
            '''),
            Fieldset(
                'What Are You Reviewing?',
                Field('account_review', css_class='select'),
                Field('device_review', css_class='select'),
                Field('estate_review', css_class='select'),
                Field('important_document_review', css_class='select'),
            ),
            Fieldset(
                'Review Details',
                Field('matters', css_class='select'),
                Field('next_review_due', css_class='dateinput'),
                Field('reasoning', css_class='textarea'),
            ),
            Div(
                Submit('submit', 'Save Review', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )
    
    def clean(self):
        """Validate that exactly one review target is selected"""
        cleaned_data = super().clean()
        
        account = cleaned_data.get('account_review')
        device = cleaned_data.get('device_review')
        estate = cleaned_data.get('estate_review')
        important = cleaned_data.get('important_document_review')
        
        targets = [account, device, estate, important]
        set_count = sum(1 for target in targets if target is not None)
        
        if set_count == 0:
            raise forms.ValidationError(
                "You must select exactly ONE item to review (account, device, estate document, or important document)."
            )
        elif set_count > 1:
            raise forms.ValidationError(
                "You can only review ONE item at a time. Please select only one option."
            )
        
        return cleaned_data
