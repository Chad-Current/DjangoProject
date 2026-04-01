from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, HTML

from dashboard.models import Account, Device
from .models import VaultEntry


class VaultEntryForm(forms.ModelForm):
    raw_password = forms.CharField(
        widget=forms.PasswordInput(render_value=True),
        required=False,
        label='Password / PIN',
        help_text='Leave blank when editing to keep the existing password.',
    )

    class Meta:
        model  = VaultEntry
        fields = ['label', 'linked_account', 'linked_device', 'username_or_email', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, profile=None, is_update=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_update = is_update

        if profile:
            self.fields['linked_account'].queryset = (
                Account.objects.filter(profile=profile)
                .order_by('account_name_or_provider')
            )
            self.fields['linked_device'].queryset = (
                Device.objects.filter(profile=profile)
                .order_by('device_name')
            )

        self.fields['linked_account'].required = False
        self.fields['linked_device'].required  = False
        self.fields['linked_account'].empty_label = '— Select Account —'
        self.fields['linked_device'].empty_label  = '— Select Device —'

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                'Entry Details',
                Field('label'),
                Field('username_or_email'),
            ),
            Fieldset(
                'Link to Account or Device',
                HTML('<p class="form-text text-muted mb-2">Select exactly one — Account or Device.</p>'),
                Field('linked_account'),
                Field('linked_device'),
            ),
            Fieldset(
                'Credentials',
                Field('raw_password'),
            ),
            Fieldset(
                'Notes',
                Field('notes'),
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        if not self.is_update and not cleaned_data.get('raw_password', '').strip():
            self.add_error('raw_password', 'A password or PIN is required.')
        return cleaned_data
