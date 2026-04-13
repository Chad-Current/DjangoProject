from django import forms
from django.db.models import Case, IntegerField, Value, When
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, HTML

from dashboard.models import Account, Device
from .models import VaultEntry


FINANCIAL_CATEGORIES = frozenset([
    'Brokerage/Investment Account',
    'Cryptocurrency Exchange Account',
    'Neobank/Digital Bank Account',
    'Online Banking Account',
    'Payment Processor Account',
    'Payment Wallet Account',
])


class FinancialAccountSelect(forms.Select):
    """
    Select widget that renders financial account options as disabled,
    with a label tag indicating passwords cannot be stored for them.
    """
    def __init__(self, *args, financial_account_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.financial_account_ids = financial_account_ids or set()

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        # value is ModelChoiceIteratorValue in Django 3.1+; get the raw PK
        pk = value.value if hasattr(value, 'value') else value
        if pk and pk in self.financial_account_ids:
            option['attrs']['disabled'] = True
            option['label'] = f"{label} — Financial Account Password Can't Be Stored"
        return option


RISK_ACKNOWLEDGED_FIELD = forms.BooleanField(
    required=True,
    label=(
        'I understand that storing credentials carries inherent risk. '
        'I accept this risk and acknowledge that this service is not liable '
        'for unauthorized access to information I choose to store here.'
    ),
    error_messages={'required': 'You must acknowledge the risk to save this entry.'},
)


class VaultEntryForm(forms.ModelForm):
    """
    Legacy combined form — kept for reference but superseded by the typed
    forms below.  VaultUpdateView now uses AccountVaultEntryForm or
    DeviceVaultEntryForm based on the entry's existing FK.
    """
    risk_acknowledged = RISK_ACKNOWLEDGED_FIELD
    raw_password = forms.CharField(
        widget=forms.PasswordInput(render_value=True),
        required=False,
        label='Password / PIN',
        help_text='Leave blank when editing to keep the existing password.',
    )

    class Meta:
        model  = VaultEntry
        fields = ['linked_account', 'linked_device', 'username_or_email']

    def __init__(self, *args, profile=None, is_update=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_update = is_update

        if profile:
            qs = (
                Account.objects.filter(profile=profile)
                .annotate(
                    is_restricted=Case(
                        When(account_category__in=FINANCIAL_CATEGORIES, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
                .order_by('is_restricted', 'account_name_or_provider')
            )
            financial_ids = set(qs.filter(is_restricted=1).values_list('pk', flat=True))
            # Widget must be set BEFORE queryset so the queryset setter wires
            # widget.choices to the new widget instance, not the old one.
            self.fields['linked_account'].widget = FinancialAccountSelect(
                financial_account_ids=financial_ids
            )
            self.fields['linked_account'].queryset = qs
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
        )

    def clean_linked_account(self):
        account = self.cleaned_data.get('linked_account')
        if account and account.account_category in FINANCIAL_CATEGORIES:
            raise forms.ValidationError(
                "Financial account passwords cannot be stored in the vault."
            )
        return account

    def clean(self):
        cleaned_data = super().clean()
        if not self.is_update and not cleaned_data.get('raw_password', '').strip():
            self.add_error('raw_password', 'A password or PIN is required.')
        return cleaned_data


# ---------------------------------------------------------------------------
# Typed forms — one per entry type
# ---------------------------------------------------------------------------

class AccountVaultEntryForm(forms.ModelForm):
    """
    Create / update form for vault entries linked to a digital Account.
    Only exposes linked_account — linked_device is never shown.
    """
    risk_acknowledged = RISK_ACKNOWLEDGED_FIELD
    raw_password = forms.CharField(
        widget=forms.PasswordInput(render_value=True),
        required=False,
        label='Password / PIN',
        help_text='Leave blank when editing to keep the existing password.',
    )

    class Meta:
        model  = VaultEntry
        fields = ['linked_account', 'username_or_email']

    def __init__(self, *args, profile=None, is_update=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_update = is_update

        if profile:
            qs = (
                Account.objects.filter(profile=profile)
                .annotate(
                    is_restricted=Case(
                        When(account_category__in=FINANCIAL_CATEGORIES, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
                .order_by('is_restricted', 'account_name_or_provider')
            )
            financial_ids = set(qs.filter(is_restricted=1).values_list('pk', flat=True))
            # Widget must be set BEFORE queryset so the queryset setter wires
            # widget.choices to the new widget instance, not the old one.
            self.fields['linked_account'].widget = FinancialAccountSelect(
                financial_account_ids=financial_ids
            )
            self.fields['linked_account'].queryset = qs

        self.fields['linked_account'].required  = True
        self.fields['linked_account'].empty_label = '— Select Account —'

    def clean_linked_account(self):
        account = self.cleaned_data.get('linked_account')
        if account and account.account_category in FINANCIAL_CATEGORIES:
            raise forms.ValidationError(
                "Financial account passwords cannot be stored in the vault."
            )
        return account

    def clean(self):
        cleaned_data = super().clean()
        if not self.is_update and not cleaned_data.get('raw_password', '').strip():
            self.add_error('raw_password', 'A password or PIN is required.')
        return cleaned_data


class DeviceVaultEntryForm(forms.ModelForm):
    """
    Create / update form for vault entries linked to a Device.
    Only exposes linked_device — linked_account is never shown.
    """
    risk_acknowledged = RISK_ACKNOWLEDGED_FIELD
    raw_password = forms.CharField(
        widget=forms.PasswordInput(render_value=True),
        required=False,
        label='Password / PIN',
        help_text='Leave blank when editing to keep the existing password.',
    )

    class Meta:
        model  = VaultEntry
        fields = ['linked_device', 'username_or_email']

    def __init__(self, *args, profile=None, is_update=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_update = is_update

        if profile:
            self.fields['linked_device'].queryset = (
                Device.objects.filter(profile=profile)
                .order_by('device_name')
            )

        self.fields['linked_device'].required   = True
        self.fields['linked_device'].empty_label = '— Select Device —'

    def clean(self):
        cleaned_data = super().clean()
        if not self.is_update and not cleaned_data.get('raw_password', '').strip():
            self.add_error('raw_password', 'A password or PIN is required.')
        return cleaned_data
