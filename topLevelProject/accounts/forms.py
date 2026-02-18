from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import get_user_model
User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already registered')
        return email.lower()
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already taken')
        return username
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    username_or_email = forms.CharField(
        label="Username or Email",
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password',
            'autocomplete': 'new-password'
        }),
        strip=False,
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        }),
        strip=False,
    )



    """
    Serves the checklist PDF as a download and logs the event.
    Place the PDF at:  <BASE_DIR>/static/baseapp/downloads/digital-estate-checklist.pdf
    """
    import os
    from django.http import FileResponse

    PDF_RELATIVE_PATH = ('static', 'baseapp', 'downloads', 'digital-estate-checklist.pdf')

    def get(self, request):
        import os
        from django.conf import settings
        from django.http import FileResponse, Http404

        path = os.path.join(settings.BASE_DIR, *self.PDF_RELATIVE_PATH)
        if not os.path.exists(path):
            logger.error('Checklist PDF not found at %s', path)
            raise Http404('Checklist file not found.')

        logger.info(
            'Checklist PDF downloaded by %s',
            request.user.email if request.user.is_authenticated else 'anonymous'
        )
        return FileResponse(
            open(path, 'rb'),
            as_attachment=True,
            filename='digital-estate-checklist.pdf',
        )