# dashboard/forms.py
from django import forms
from datetime import timezone
from django.core.exceptions import ValidationError
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
    ImportantDocument,
)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "email",
            "phone",
            "address_1",
            "address_2",
            "city",
            "state",
            "zipcode",
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
                Field('first_name', css_class='textinput'),
                Field('last_name', css_class='textinput'),
                Field('date_of_birth', css_class='dateinput'),
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
                Submit('submit', 'Save Profile', css_class='btn btn-primary'),
                css_class='button-group'
            )
        )


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = [
            'contact_relation',
            'first_name',
            'last_name',
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
        ]
        labels = {
            'is_emergency_contact': 'Emergency Contact',
            'is_digital_executor': 'Digital Account Executor',
            'is_caregiver': 'Caregiver',
            'is_legal_executor': 'Legal Executor',
            'is_trustee': 'Trustee',
            'is_financial_agent': 'Financial Agent',
            'is_healthcare_proxy': 'Healthcare Proxy',
            'is_guardian_for_dependents': 'Guardian for Dependents',
            'is_pet_caregiver': 'Pet Caregiver',
            'is_memorial_contact': 'Memorial Contact',
            'is_legacy_contact': 'Legacy Contact',
            'is_professional_advisor': 'Professional Advisor',
            'is_notification_only': 'Notification Only',
            'is_knowledge_contact': 'Information Knowledge Only',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                "Contact Information",
                Field('contact_relation', css_class='select'),
                Field('first_name', css_class='textinput'),
                Field('last_name', css_class='textinput'),
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
                Field('is_legal_executor', css_class='checkboxinput form-check-input'),
                Field('is_trustee', css_class='checkboxinput form-check-input'),
                Field('is_financial_agent', css_class='checkboxinput form-check-input'),
                Field('is_healthcare_proxy', css_class='checkboxinput form-check-input'),
                Field('is_guardian_for_dependents', css_class='checkboxinput form-check-input'),
                Field('is_pet_caregiver', css_class='checkboxinput form-check-input'),
                Field('is_memorial_contact', css_class='checkboxinput form-check-input'),
                Field('is_legacy_contact', css_class='checkboxinput form-check-input'),
                Field('is_professional_advisor', css_class='checkboxinput form-check-input'),
                Field('is_notification_only', css_class='checkboxinput form-check-input'),
                Field('is_knowledge_contact', css_class='checkboxinput form-check-input'),
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
            "delegated_account_to": "Assign Account to",
            "account_category": "Type of Account",
            "account_name_or_provider": "Name or Provider",
            "website_url": "Website URL",
            "username_or_email": "Username or Email",
            "credential_storage_location": "Credential Storage Location",
            'review_time': "Review needed in ",
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
            ),
            Fieldset(
                'Instructions for Family',
                Field('keep_or_close_instruction', css_class='select'),
                Field('notes_for_family', css_class='textarea'),
            ),
            Fieldset(
                'Review Requirements',
                Field('review_time', css_class='select'),
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
            "review_time",
        ]
        labels = {
            "delegated_device_to": "Assign Device To",
            "device_type": "Type of Device",
            "device_name": "Name",
            "owner_label": "Labeled as",
            "location_description": "Typical Location of Device",
            "unlock_method_description": "Unlock Method",
            "used_for_2fa": "Used For Two Factor Authentication",
            "decommission_instruction": "Decommission Instructions",
            'review_time': "Review needed in",
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
            ),
            Fieldset(
                'Review Requirements',
                Field('review_time', css_class='select'),
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
            "review_time",
        ]
        labels = {
            "delegated_estate_to": "Assign Document to",
            "estate_category": "Category",
            "name_or_title": "Name or Title",
            "estate_overall_instructions": "Instructions",
            "estate_physical_location": "Physical Location",
            "estate_digital_location": "Digital Location",
            "estate_file": "Upload File",
            "applies_on_death": "Applies Upon Death",
            "applies_on_incapacity": "Applies On Incapacitation",
            "applies_immediately": "Applies Immediately",
            'review_time': "Review needed in",
        }
        widgets = {
            'applies_on_death': forms.CheckboxInput(),
            'applies_on_incapacity': forms.CheckboxInput(),
            'applies_immediately': forms.CheckboxInput(),
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
        self.helper.form_show_errors = False
        self.helper.layout = Layout(
            HTML('''
                {% if form.non_field_errors %}
                <ul class="errorlist nonfield">
                    {% for error in form.non_field_errors %}
                    <li>{{ error }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
            '''),
            Fieldset(
                'Estate Document Assignment',
                HTML('<div class="alert alert-warning"><strong>Required:</strong> You must assign this document to a contact.</div>'),
                Field('delegated_estate_to', css_class='select'),
            ),
            Fieldset(
                'Estate Document Details',
                Field('name_or_title', css_class='textinput'),
                Field('estate_category', css_class='select'),
                Field('estate_file', css_class='fileinput'),
                Field('estate_overall_instructions', css_class='textarea'),
            ),
            Fieldset(
                'Estate Document Location',
                Field('estate_physical_location', css_class='textinput'),
                Field('estate_digital_location', css_class='textinput'),
            ),
            Fieldset(
                'Review Requirements',
                Field('review_time', css_class='select'),
            ),
            Fieldset(
                'Declarations',
                HTML('<div class="alert alert-warning"><strong>Required:</strong> At least one declaration must be selected.</div>'),
                Field('applies_on_death', css_class='checkboxinput form-check-input'),
                Field('applies_on_incapacity', css_class='checkboxinput form-check-input'),
                Field('applies_immediately', css_class='checkboxinput form-check-input'),
            ),
            Div(
                Submit('submit', 'Save Estate Document', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        applies_on_death = cleaned_data.get('applies_on_death')
        applies_on_incapacity = cleaned_data.get('applies_on_incapacity')
        applies_immediately = cleaned_data.get('applies_immediately')

        if not any([applies_on_death, applies_on_incapacity, applies_immediately]):
            raise forms.ValidationError(
                "Please select at least one declaration"
            )
        return cleaned_data


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
            "relation": "Who Needs To Be Informed",
            "content": "What Do You Want To Tell Them",
            "is_location_of_legal_will": "For Location Of Will?",
            "is_password_manager": "Password Manager Information",
            "is_social_media": "How To Handle Social Media Accounts",
            "is_photos_or_files": "What To Do With Photos Or Files",
            "is_data_retention_preferences": "How Long Do You Wish To Retain Information",
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
            "review_time",
        ]
        labels = {
            "delegated_important_document_to": "Assign Document To",
            "name_or_title": "Name or Title",
            "document_category": "Category",
            "description": "Description",
            "physical_location": "Physical Location",
            "digital_location": "Other Digital Locations",
            "important_file": "Upload File",
            "requires_legal_review": "Requires Professional Legal Review",
            "applies_on_death": "Applies On Death",
            "applies_on_incapacity": "Applies On Incapacitation",
            "applies_immediately": "Applies Immediately",
        }
        widgets = {
            'applies_on_death': forms.CheckboxInput(),
            'applies_on_incapacity': forms.CheckboxInput(),
            'applies_immediately': forms.CheckboxInput(),
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
        self.helper.form_show_errors = False
        self.helper.layout = Layout(
                HTML('''
                    {% if form.non_field_errors %}
                    <ul class="errorlist nonfield">
                        {% for error in form.non_field_errors %}
                        <li>{{ error }}</li>
                        {% endfor %}
                    </ul>
                    {% endif %}
                '''),
            Fieldset(
                'Important Document Assignment',
                HTML('<div class="alert alert-warning"><strong>Required:</strong> You must assign this document to a contact.</div>'),
                Field('delegated_important_document_to', css_class='select'),
            ),
            Fieldset(
                'Important Document',
                Field('name_or_title', css_class='textinput'),
                Field('document_category', css_class='select'),
                Field('description', css_class='textarea'),
                Field('requires_legal_review', css_class='checkboxinput form-check-input'),
            ),
            Fieldset(
                'Review Requirements',
                Field('review_time', css_class='select'),
            ),
            Fieldset(
                'Declarations',
                HTML('<div class="alert alert-warning"><strong>Required:</strong> At least one declaration must be selected.</div>'),
                Field('applies_on_death', css_class='checkboxinput form-check-input'),
                Field('applies_on_incapacity', css_class='checkboxinput form-check-input'),
                Field('applies_immediately', css_class='checkboxinput form-check-input'),
            ),
            Fieldset(
                'Important Document Location',
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

    def clean(self):
        cleaned_data = super().clean()
        applies_on_death = cleaned_data.get('applies_on_death')
        applies_on_incapacity = cleaned_data.get('applies_on_incapacity')
        applies_immediately = cleaned_data.get('applies_immediately')

        if not any([applies_on_death, applies_on_incapacity, applies_immediately]):
            raise forms.ValidationError(
                "Please select at least one declaration"
            )
        return cleaned_data


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