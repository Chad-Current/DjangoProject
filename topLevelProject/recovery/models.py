from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.utils import timezone
from dashboard.models import Profile, Account, Contact

class RecoveryRequest(models.Model):
    """
    Requests to recover accounts (for deceased or incapacitated users).
    Can be initiated by authenticated users OR external contacts via verification.
    """
    STATUS_CHOICES = [
        ('Pending Verification', 'Pending Verification'),
        ('Verified', 'Verified'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Denied', 'Denied'),
        ('Cancelled', 'Cancelled'),
    ]
    
    REASON_CHOICES = [
        ('Death', 'Account owner is deceased'),
        ('Incapacitation', 'Account owner is incapacitated'),
        ('Other', 'Other circumstance'),
    ]
    
    # The profile being requested access to
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='recovery_requests',
        editable=False,
        help_text="Profile of the deceased/incapacitated user"
    )
    
    # Requester information - can be authenticated user OR external contact
    requested_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='recovery_requests_made',
        null=True,
        blank=True,
        help_text="Authenticated user making the request (if applicable)"
    )
    
    # External requester fields (when requested_by_user is NULL)
    requester_first_name = models.CharField(max_length=100, blank=True)
    requester_last_name = models.CharField(max_length=100, blank=True)
    requester_email = models.EmailField(blank=True)
    requester_phone = models.CharField(max_length=20, blank=True)
    requester_relationship = models.CharField(
        max_length=50,
        blank=True,
        help_text="Relationship to account owner"
    )
    
    # Verification
    verification_token = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        editable=False,
        help_text="Token sent to requester's email for verification"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_attempts = models.PositiveSmallIntegerField(default=0)
    
    # Request details
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        default='Death'
    )
    
    target_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        related_name='recovery_requests',
        null=True,
        blank=True,
        help_text="Specific account to recover (optional)"
    )
    
    target_description = models.CharField(
        max_length=500,
        help_text="Description of what needs to be recovered"
    )
    
    # Supporting documentation
    death_certificate = models.FileField(
        upload_to='recovery_requests/certificates/%Y/%m/',
        blank=True,
        null=True,
        help_text="Death certificate or medical documentation"
    )
    
    proof_of_relationship = models.FileField(
        upload_to='recovery_requests/proof/%Y/%m/',
        blank=True,
        null=True,
        help_text="Proof of relationship (e.g., marriage certificate, birth certificate)"
    )
    
    legal_authorization = models.FileField(
        upload_to='recovery_requests/legal/%Y/%m/',
        blank=True,
        null=True,
        help_text="Power of attorney, executor documentation, court order, etc."
    )
    
    additional_notes = models.TextField(
        blank=True,
        help_text="Additional information supporting the request"
    )
    
    # Status and tracking
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='Pending Verification'
    )
    
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='reviewed_recovery_requests',
        null=True,
        blank=True,
        help_text="Admin who reviewed this request"
    )
    
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    provider_ticket_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="External service provider ticket/case number"
    )
    
    steps_taken = models.TextField(
        blank=True,
        help_text="Actions taken to process this request"
    )
    
    outcome_notes = models.TextField(
        blank=True,
        help_text="Final outcome and resolution details"
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'recovery_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['verification_token']),
            models.Index(fields=['requester_email']),
        ]
    
    def __str__(self):
        requester = self.get_requester_name()
        return f"Recovery: {self.target_description[:50]} by {requester} ({self.status})"
    
    def get_requester_name(self):
        """Get the name of the person making the request"""
        if self.requested_by_user:
            return str(self.requested_by_user)
        elif self.requester_first_name or self.requester_last_name:
            return f"{self.requester_first_name} {self.requester_last_name}".strip()
        return "Anonymous"
    
    def get_requester_email(self):
        """Get the email of the person making the request"""
        if self.requested_by_user:
            return self.requested_by_user.email
        return self.requester_email
    
    def is_verified(self):
        """Check if the request has been verified"""
        return self.verified_at is not None
    
    def is_external_request(self):
        """Check if this is an external (non-user) request"""
        return self.requested_by_user is None
    
    def generate_verification_token(self):
        """Generate a unique verification token"""
        import secrets
        self.verification_token = secrets.token_urlsafe(32)
        return self.verification_token
    
    def verify(self):
        """Mark the request as verified"""
        self.verified_at = timezone.now()
        if self.status == 'Pending Verification':
            self.status = 'Verified'
        self.save()
    
    def clean(self):
        """Validate that either user or external requester info is provided"""
        from django.core.exceptions import ValidationError
        
        if not self.requested_by_user and not (self.requester_email or self.requester_first_name):
            raise ValidationError(
                "Either an authenticated user or external requester information must be provided."
            )