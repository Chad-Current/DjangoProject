# dashboard/forms.py
import re
from django import forms
from datetime import date
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Field, Fieldset, Div, Submit, Button
from .models import (
    Profile,
    Contact,
    Account,
    Device,
    DigitalEstateDocument,
    ImportantDocument,
    FamilyNeedsToKnowSection,
    RelevanceReview,
    FuneralPlan
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def validate_phone_digits(value):
    """Allow digits, spaces, dashes, parentheses, and a leading +."""
    cleaned = re.sub(r'[\s\-().+]', '', value)
    if not cleaned.isdigit():
        raise ValidationError(
            "Phone number may only contain digits, spaces, dashes, parentheses, and a leading '+'."
        )


# ---------------------------------------------------------------------------
# ProfileForm
# ---------------------------------------------------------------------------

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

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError("Enter a valid email address (e.g. name@example.com).")
        return email

    def clean_home_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            cleaned = re.sub(r'[\s\-().+]', '', phone)
            if not cleaned.isdigit():
                raise ValidationError(
                    "Phone number may only contain digits, spaces, dashes, "
                    "parentheses, and a leading '+'."
                )
        return phone


# ---------------------------------------------------------------------------
# ContactForm
# ---------------------------------------------------------------------------

# Only the boolean role fields — used by clean() to check at least one is set.
CONTACT_ROLE_FIELDS = [
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

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if not first_name:
            raise ValidationError("First name is required.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if not last_name:
            raise ValidationError("Last name is required.")
        return last_name

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError("Enter a valid email address (e.g. name@example.com).")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            validate_phone_digits(phone)
        return phone

    def clean(self):
        cleaned_data = super().clean()

        # Check that at least one boolean role checkbox is selected.
        if not any(cleaned_data.get(f) for f in CONTACT_ROLE_FIELDS):
            raise ValidationError(
                "Please select at least one role for this contact."
            )

        return cleaned_data


# ---------------------------------------------------------------------------
# AccountForm
# ---------------------------------------------------------------------------

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

    def clean_website_url(self):
        url = self.cleaned_data.get('website_url', '').strip()
        if url:
            # Django's URLField validator runs automatically, but we add a
            # friendlier message here by catching any resulting error.
            from django.core.validators import URLValidator
            validator = URLValidator()
            try:
                validator(url)
            except ValidationError:
                raise ValidationError(
                    "Enter a valid URL including the scheme, e.g. https://example.com"
                )
        return url


# ---------------------------------------------------------------------------
# DeviceForm
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# DigitalEstateDocumentForm
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# FamilyNeedsToKnowSectionForm
# ---------------------------------------------------------------------------

FAMILY_CHECKBOX_FIELDS = [
    'is_location_of_legal_will',
    'is_password_manager',
    'is_social_media',
    'is_photos_or_files',
    'is_data_retention_preferences',
]


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
            HTML('''
                {% if form.non_field_errors %}
                <ul class="errorlist nonfield">
                    {% for error in form.non_field_errors %}
                    <li>{{ error }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
            '''),
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

    def clean_relation(self):
        relation = self.cleaned_data.get('relation')
        if not relation:
            raise ValidationError("Please select a contact to inform.")
        return relation

    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if not content:
            raise ValidationError("Please enter what you want to tell this person.")
        return content

    def clean(self):
        cleaned_data = super().clean()
        if not any(cleaned_data.get(f) for f in FAMILY_CHECKBOX_FIELDS):
            raise ValidationError(
                "Please select at least one topic category for this message."
            )
        return cleaned_data


# ---------------------------------------------------------------------------
# ImportantDocumentForm
# ---------------------------------------------------------------------------

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



# ---------------------------------------------------------------------------
# FuneralPlanForm
# ---------------------------------------------------------------------------
# ===========================================================================
# FUNERAL PLAN SECTION FORMS
# ===========================================================================
# One ModelForm per section.  All share the same pattern:
#   - pop 'user' from kwargs (base forms never need it; service form uses it
#     to scope the officiant queryset)
#   - crispy layout
#   - field-level validation where needed
#
# IMPORTANT: These forms are bound to an *existing* FuneralPlan instance via
# the views' get_or_create_plan() helper, so they always update — never insert
# a second row.  The OneToOneField constraint on profile is therefore safe.
# ===========================================================================


class FuneralPlanPersonalInfoForm(forms.ModelForm):
    """Section 1 — supplemental personal identity."""

    class Meta:
        model = FuneralPlan
        fields = [
            'preferred_name', 'occupation', 'marital_status',
            'religion_or_spiritual_affiliation', 'is_veteran', 'veteran_branch',
        ]
        labels = {
            'preferred_name':                    'Preferred Name / Nickname',
            'occupation':                        'Occupation or Former Occupation',
            'marital_status':                    'Marital Status',
            'religion_or_spiritual_affiliation': 'Religion or Spiritual Affiliation',
            'is_veteran':                        'Veteran',
            'veteran_branch':                    'Branch of Service',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Personal Information',
                Field('preferred_name', css_class='textinput'),
                Field('occupation', css_class='textinput'),
                Field('marital_status', css_class='select'),
                Field('religion_or_spiritual_affiliation', css_class='textinput'),
                Field('is_veteran', css_class='checkboxinput form-check-input'),
                Field('veteran_branch', css_class='textinput'),
            ),
            Div(
                Submit('submit', 'Save & Continue', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )

    def clean_veteran_branch(self):
        is_veteran = self.cleaned_data.get('is_veteran', False)
        branch     = self.cleaned_data.get('veteran_branch', '').strip()
        if is_veteran and not branch:
            raise forms.ValidationError(
                "Please enter the branch of service, or uncheck the Veteran field."
            )
        return '' if not is_veteran else branch


class FuneralPlanServiceForm(forms.ModelForm):
    """Section 2 — service and timing preferences."""

    class Meta:
        model = FuneralPlan
        fields = [
            'service_type', 'preferred_funeral_home', 'funeral_home_phone',
            'funeral_home_address', 'preferred_venue',
            'officiant_contact', 'officiant_name_freetext',
            'desired_timing', 'open_casket_viewing',
        ]
        labels = {
            'service_type':            'Type of Service',
            'preferred_funeral_home':  'Preferred Funeral Home',
            'funeral_home_phone':      'Funeral Home Phone',
            'funeral_home_address':    'Funeral Home Address',
            'preferred_venue':         'Preferred Venue',
            'officiant_contact':       'Officiant (from Contacts)',
            'officiant_name_freetext': 'Officiant Name (if not in Contacts)',
            'desired_timing':          'Preferred Day / Time',
            'open_casket_viewing':     'Viewing Preference',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['officiant_contact'].required = False

        if self.user:
            try:
                profile = Profile.objects.get(user=self.user)
                self.fields['officiant_contact'].queryset = Contact.objects.filter(profile=profile)
            except Profile.DoesNotExist:
                self.fields['officiant_contact'].queryset = Contact.objects.none()

        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Service Preferences',
                Field('service_type', css_class='select'),
                Field('preferred_funeral_home', css_class='textinput'),
                Field('funeral_home_phone', css_class='textinput'),
                Field('funeral_home_address', css_class='textinput'),
                Field('preferred_venue', css_class='textinput'),
                Field('officiant_contact', css_class='select'),
                Field('officiant_name_freetext', css_class='textinput'),
                Field('desired_timing', css_class='select'),
                Field('open_casket_viewing', css_class='select'),
            ),
            Div(
                Submit('submit', 'Save & Continue', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )

    def clean_funeral_home_phone(self):
        phone = self.cleaned_data.get('funeral_home_phone', '').strip()
        if phone:
            cleaned = re.sub(r'[\s\-().+]', '', phone)
            if not cleaned.isdigit():
                raise ValidationError(
                    "Phone number may only contain digits, spaces, dashes, "
                    "parentheses, and a leading '+'."
                )
        return phone

    def clean_officiant_name_freetext(self):
        contact  = self.cleaned_data.get('officiant_contact')
        freetext = self.cleaned_data.get('officiant_name_freetext', '').strip()
        if contact and freetext:
            raise ValidationError(
                "Please use either the Contacts list or the free-text field — not both."
            )
        return freetext


class FuneralPlanDispositionForm(forms.ModelForm):
    """Section 3 — final disposition preferences."""

    class Meta:
        model = FuneralPlan
        fields = [
            'disposition_method', 'burial_or_interment_location',
            'burial_plot_or_niche_purchased', 'casket_type_preference',
            'urn_type_preference', 'headstone_or_marker_inscription',
        ]
        labels = {
            'disposition_method':              'Method of Disposition',
            'burial_or_interment_location':    'Burial or Interment Location',
            'burial_plot_or_niche_purchased':  'Plot or Niche Already Purchased?',
            'casket_type_preference':          'Casket Type / Material Preference',
            'urn_type_preference':             'Urn Type (if cremation)',
            'headstone_or_marker_inscription': 'Headstone or Marker Inscription Ideas',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['burial_plot_or_niche_purchased'].required = False

        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Final Disposition',
                Field('disposition_method', css_class='select'),
                Field('burial_or_interment_location', css_class='textinput'),
                Field('burial_plot_or_niche_purchased', css_class='checkboxinput form-check-input'),
                Field('casket_type_preference', css_class='textinput'),
                Field('urn_type_preference', css_class='textinput'),
                Field('headstone_or_marker_inscription', css_class='textarea'),
            ),
            Div(
                Submit('submit', 'Save & Continue', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )


class FuneralPlanCeremonyForm(forms.ModelForm):
    """Section 4 — ceremony personalization."""

    class Meta:
        model = FuneralPlan
        fields = [
            'music_choices', 'flowers_or_colors', 'readings_poems_or_scriptures',
            'eulogists_notes', 'pallbearers_notes', 'clothing_or_jewelry_description',
            'religious_cultural_customs', 'items_to_display',
        ]
        labels = {
            'music_choices':                   'Music Choices',
            'flowers_or_colors':               'Flowers or Colors',
            'readings_poems_or_scriptures':    'Readings, Poems, or Scriptures',
            'eulogists_notes':                 'Eulogists / Speakers',
            'pallbearers_notes':               'Pallbearers',
            'clothing_or_jewelry_description': 'Clothing or Jewelry for Deceased',
            'religious_cultural_customs':      'Religious or Cultural Customs',
            'items_to_display':                'Items to Display',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Ceremony Personalization',
                Field('music_choices', css_class='textarea'),
                Field('flowers_or_colors', css_class='textinput'),
                Field('readings_poems_or_scriptures', css_class='textarea'),
                Field('eulogists_notes', css_class='textarea'),
                Field('pallbearers_notes', css_class='textarea'),
                Field('clothing_or_jewelry_description', css_class='textinput'),
                Field('religious_cultural_customs', css_class='textarea'),
                Field('items_to_display', css_class='textarea'),
            ),
            Div(
                Submit('submit', 'Save & Continue', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )


class FuneralPlanReceptionForm(forms.ModelForm):
    """Section 5 — post-service reception details."""

    class Meta:
        model = FuneralPlan
        fields = [
            'reception_desired', 'reception_location',
            'reception_food_preferences', 'reception_atmosphere_notes',
            'reception_guest_list_notes',
        ]
        labels = {
            'reception_desired':           'Post-Service Gathering Desired?',
            'reception_location':          'Reception Location',
            'reception_food_preferences':  'Food or Catering Preferences',
            'reception_atmosphere_notes':  'Music / Atmosphere Notes',
            'reception_guest_list_notes':  'Guest List or Invitation Notes',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['reception_desired'].required = False

        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Reception / Gathering',
                Field('reception_desired', css_class='checkboxinput form-check-input'),
                Field('reception_location', css_class='textinput'),
                Field('reception_food_preferences', css_class='textarea'),
                Field('reception_atmosphere_notes', css_class='textarea'),
                Field('reception_guest_list_notes', css_class='textarea'),
            ),
            Div(
                Submit('submit', 'Save & Continue', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('reception_desired') and not cleaned_data.get('reception_location'):
            raise ValidationError(
                "Please provide a reception location, or uncheck 'Post-Service Gathering Desired'."
            )
        return cleaned_data


class FuneralPlanObituaryForm(forms.ModelForm):
    """Section 6 — obituary and memorial information."""

    class Meta:
        model = FuneralPlan
        fields = [
            'obituary_photo_description', 'obituary_key_achievements',
            'obituary_publications', 'charitable_donations_in_lieu',
        ]
        labels = {
            'obituary_photo_description':    'Preferred Photo Description / Location',
            'obituary_key_achievements':     'Key Achievements or Memories to Include',
            'obituary_publications':         'Publications or Websites for Obituary',
            'charitable_donations_in_lieu':  'Charitable Donations in Lieu of Flowers',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Obituary & Memorial',
                Field('obituary_photo_description', css_class='textinput'),
                Field('obituary_key_achievements', css_class='textarea'),
                Field('obituary_publications', css_class='textarea'),
                Field('charitable_donations_in_lieu', css_class='textinput'),
            ),
            Div(
                Submit('submit', 'Save & Continue', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )


class FuneralPlanAdminForm(forms.ModelForm):
    """Section 7 — administrative and financial details."""

    class Meta:
        model = FuneralPlan
        fields = [
            'funeral_insurance_policy_number',
            'death_certificates_requested',
            'payment_arrangements',
            'review_time',
        ]
        labels = {
            'funeral_insurance_policy_number': 'Funeral Plan Insurance Policy Number',
            'death_certificates_requested':    'Number of Death Certificates Requested',
            'payment_arrangements':            'Payment Arrangements or Funding Source',
            'review_time':                     'Review Reminder',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Administrative & Financial',
                Field('funeral_insurance_policy_number', css_class='textinput'),
                Field('death_certificates_requested', css_class='textinput'),
                Field('payment_arrangements', css_class='textarea'),
            ),
            Fieldset(
                'Review Settings',
                Field('review_time', css_class='select'),
            ),
            Div(
                Submit('submit', 'Save & Continue', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )

    def clean_death_certificates_requested(self):
        count = self.cleaned_data.get('death_certificates_requested')
        if count is not None and count < 1:
            raise ValidationError(
                "Enter a positive number, or leave blank if unknown. "
                "Most families need between 6 and 12 certified copies."
            )
        return count


class FuneralPlanInstructionsForm(forms.ModelForm):
    """Section 8 — additional instructions and final messages."""

    class Meta:
        model = FuneralPlan
        fields = ['additional_instructions']
        labels = {
            'additional_instructions': 'Additional Instructions or Messages to Family',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-wrapper'
        self.helper.layout = Layout(
            Fieldset(
                'Additional Instructions',
                Field('additional_instructions', css_class='textarea'),
            ),
            Div(
                Submit('submit', 'Save & Finish', css_class='btn btn-primary'),
                Button('back', 'Back', css_class='btn btn-secondary', onclick="history.back();"),
                css_class='button-group'
            ),
        )

# ---------------------------------------------------------------------------
# RelevanceReviewForm
# ---------------------------------------------------------------------------

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

                self.fields['account_review'].queryset = Account.objects.filter(profile=profile)
                self.fields['device_review'].queryset = Device.objects.filter(profile=profile)
                self.fields['estate_review'].queryset = DigitalEstateDocument.objects.filter(profile=profile)
                self.fields['important_document_review'].queryset = ImportantDocument.objects.filter(profile=profile)

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
                {% if form.non_field_errors %}
                <ul class="errorlist nonfield">
                    {% for error in form.non_field_errors %}
                    <li>{{ error }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
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

    def clean_next_review_due(self):
        review_date = self.cleaned_data.get('next_review_due')
        if review_date and review_date <= date.today():
            raise ValidationError("Next review date must be in the future.")
        return review_date

    def clean(self):
        """Validate that exactly one review target is selected."""
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