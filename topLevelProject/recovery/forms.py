from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import RecoveryRequest
from dashboard.models import Profile, Account


class ExternalRecoveryRequestForm(forms.ModelForm):
    """
    Form for external (non-authenticated) users to submit recovery requests.
    """
    # Profile identification
    deceased_user_email = forms.EmailField(
        label="Email of Deceased/Incapacitated Account Owner",
        required=True,
        help_text="Enter the email address of the account owner",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'account.owner@example.com'
        })
    )
    
    # Terms acceptance
    accept_terms = forms.BooleanField(
        required=True,
        label="I certify that the information provided is accurate and I have legal authority to make this request",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = RecoveryRequest
        fields = [
            'requester_first_name',
            'requester_last_name',
            'requester_email',
            'requester_phone',
            'requester_relationship',
            'reason',
            'target_description',
            'death_certificate',
            'proof_of_relationship',
            'legal_authorization',
            'additional_notes',
        ]
        widgets = {
            'requester_first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your first name'
            }),
            'requester_last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your last name'
            }),
            'requester_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@example.com'
            }),
            'requester_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(555) 123-4567'
            }),
            'requester_relationship': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Spouse, Child, Executor'
            }),
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'target_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe what accounts or information you need to access'
            }),
            'additional_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Any additional information to support your request'
            }),
            'death_certificate': forms.FileInput(attrs={'class': 'form-control'}),
            'proof_of_relationship': forms.FileInput(attrs={'class': 'form-control'}),
            'legal_authorization': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_deceased_user_email(self):
        """Verify the profile exists"""
        email = self.cleaned_data.get('deceased_user_email')
        try:
            # Try to find profile by user email or profile email
            profile = Profile.objects.filter(
                Q(user__email=email) | Q(email=email)
            ).first()
            
            if not profile:
                raise ValidationError(
                    "We could not find an account with that email address. "
                    "Please verify the email and try again."
                )
            
            self.profile = profile
            return email
        except Exception as e:
            raise ValidationError(f"Error validating email: {str(e)}")
    
    def clean_requester_email(self):
        """Ensure requester email is provided"""
        email = self.cleaned_data.get('requester_email')
        if not email:
            raise ValidationError("Your email address is required for verification.")
        return email
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.profile = self.profile
        instance.status = 'Pending Verification'
        
        if commit:
            # Generate verification token
            instance.generate_verification_token()
            instance.save()
            
            # Send verification email
            self.send_verification_email(instance)
        
        return instance
    
    def send_verification_email(self, instance):
        """Send verification email to requester"""
        from django.core.mail import send_mail
        from django.conf import settings
        from django.urls import reverse
        
        # NEED TO CHANGE FOR PRODUCTION LEVEL
        # verification_url = f"{settings.SITE_URL}{reverse('recovery:verify_recovery_request', kwargs={'token': instance.verification_token})}"
        verification_url = f"http://localhost:8000"
        subject = "Verify Your Account Recovery Request"
        message = f"""
Dear {instance.requester_first_name} {instance.requester_last_name},

Thank you for submitting an account recovery request. To proceed, please verify your email address by clicking the link below:

{verification_url}

This link will expire in 48 hours.

If you did not make this request, please ignore this email.

Best regards,
Digital Estate Planning Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.requester_email],
            fail_silently=False,
        )


class AuthenticatedRecoveryRequestForm(forms.ModelForm):
    """
    Form for authenticated users to submit recovery requests.
    """
    class Meta:
        model = RecoveryRequest
        fields = [
            'reason',
            'target_account',
            'target_description',
            'death_certificate',
            'proof_of_relationship',
            'legal_authorization',
            'additional_notes',
        ]
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'target_account': forms.Select(attrs={'class': 'form-control'}),
            'target_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe what you need to access'
            }),
            'additional_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'death_certificate': forms.FileInput(attrs={'class': 'form-control'}),
            'proof_of_relationship': forms.FileInput(attrs={'class': 'form-control'}),
            'legal_authorization': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, profile=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile
        self.user = user
        
        # Filter target_account to only accounts belonging to the profile
        if profile:
            self.fields['target_account'].queryset = Account.objects.filter(profile=profile)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.profile = self.profile
        instance.requested_by_user = self.user
        instance.status = 'Verified'  # Authenticated users are pre-verified
        instance.verified_at = timezone.now()
        
        if commit:
            instance.save()
        
        return instance


class VerificationForm(forms.Form):
    """
    Simple form to verify the token
    """
    token = forms.CharField(widget=forms.HiddenInput())


class AdminRecoveryReviewForm(forms.ModelForm):
    """
    Form for admins to review and update recovery requests.
    """
    class Meta:
        model = RecoveryRequest
        fields = [
            'status',
            'provider_ticket_number',
            'steps_taken',
            'outcome_notes',
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'provider_ticket_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Provider case/ticket number'
            }),
            'steps_taken': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5
            }),
            'outcome_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5
            }),
        }
    
    def save(self, commit=True, reviewer=None):
        instance = super().save(commit=False)
        
        if reviewer:
            instance.reviewed_by = reviewer
            instance.reviewed_at = timezone.now()
        
        if instance.status == 'Completed' and not instance.completed_at:
            instance.completed_at = timezone.now()
        
        if commit:
            instance.save()
        
        return instance