from django import forms


class ChecklistEmailForm(forms.Form):
    """
    Public form — no account required.
    Lets anyone request the Digital Estate Readiness Checklist by email.
    """

    first_name = forms.CharField(
        label="First name",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name (optional)',
            'autocomplete': 'given-name',
        }),
    )
    email = forms.EmailField(
        label="Email address",
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your email address',
            'autocomplete': 'email',
        }),
    )

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_first_name(self):
        return self.cleaned_data.get('first_name', '').strip()