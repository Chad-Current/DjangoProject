# ============================================================================
# PART 9: DASHBOARD MODELS - COMPLETE
# ============================================================================

# ============================================================================
# dashboard/models.py
# ============================================================================
from django.db import models
from django.conf import settings
from django.core.validators import URLValidator
from django.utils import timezone
from datetime import timedelta

class Profile(models.Model):
    """
    User profile containing personal information for digital estate planning.
    One profile per user.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        editable=False
    )
    full_name = models.CharField(max_length=200)
    date_of_birth = models.DateField(null=True, blank=True)
    primary_email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True, help_text="Personal notes")
    
    # Digital Executor Information
    has_digital_executor = models.BooleanField(
        default=False,
        help_text="Have you designated a digital executor?"
    )
    digital_executor_name = models.CharField(max_length=200, blank=True)
    digital_executor_contact = models.CharField(
        max_length=200,
        blank=True,
        help_text="Email or phone number"
    )
    # created_at = models.DateTimeField(default=timezone.now)
    # Change back once migrations are completed
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'profiles'
        ordering = ['user']
    
    def __str__(self):
        return f"{self.full_name} ({self.user})"


class Account(models.Model):
    """
    Individual digital accounts (social media, email, banking, etc.)
    """
    ACCOUNT_CATEGORIES = [
        ('email', 'Email Account'),
        ('social_media', 'Social Media Account'),
        ('cloud_storage', 'Cloud Storage Account'),
        ('streaming_media', 'Streaming Media Account'),
        ('ecommerce_marketplace', 'Ecommerce Marketplace Account'),
        ('online_banking', 'Online Banking Account'),
        ('neobank_digital_bank', 'Neobank/Digital Bank Account'),
        ('brokerage_investment', 'Brokerage/Investment Account'),
        ('cryptocurrency_exchange', 'Cryptocurrency Exchange Account'),
        ('payment_wallet', 'Payment Wallet Account'),
        ('payment_processor', 'Payment Processor Account'),
        ('productivity_collaboration', 'Productivity/Collaboration Account'),
        ('developer_platform', 'Developer Platform Account'),
        ('app_store', 'App Store Account'),
        ('gaming_platform', 'Gaming Platform Account'),
        ('forum_community', 'Forum/Community Account'),
        ('education_elearning', 'Education/Elearning Account'),
        ('subscription_saas', 'Subscription/SaaS Account'),
        ('government_portal', 'Government Portal Account'),
        ('utilities_telecom_portal', 'Utilities/Telecom Portal Account'),
        ('health_portal', 'Health Portal Account'),
        ('smart_home_iot', 'Smart Home/IoT Account'),
        ('travel_booking', 'Travel Booking Account'),
        ('ride_hailing_delivery', 'Ride-Hailing/Delivery Account'),
        ('password_manager', 'Password Manager Account'),
        ('not_listed', 'Not Listed'),
    ]
    INSTRUCTION_CHOICES = [
        ('keep', 'Keep Active'),
        ('close', 'Close Account'),
        ('memorialize', 'Memorialize'),
        ('other', 'Other (See Notes)'),
    ]
    
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='accounts',
        editable=False
    )
    account_name = models.CharField(max_length=200, help_text="Account name or service")
    account_category = models.CharField(
        max_length=200,
        choices=ACCOUNT_CATEGORIES,
        default='email'
    ) 
    provider = models.CharField(max_length=200, help_text="Company/service provider")
    website_url = models.URLField(blank=True, validators=[URLValidator()])
    username_or_email = models.CharField(
        max_length=200,
        blank=True,
        help_text="Username or email used for login"
    )
    credential_storage_location = models.CharField(
        max_length=500,
        blank=True,
        help_text="Where password is stored (e.g., 1Password, LastPass)"
    )
    is_critical = models.BooleanField(
        default=False,
        help_text="Mark as critical/important account"
    )
    keep_or_close_instruction = models.CharField(
        max_length=20,
        choices=INSTRUCTION_CHOICES,
        default='other'
    )
    notes_for_family = models.TextField(
        blank=True,
        help_text="Instructions or notes for family members"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts'
        ordering = ['-is_critical', 'account_name']
        indexes = [
            models.Index(fields=['profile', '-created_at']),
            models.Index(fields=['account_category']),
        ]
    
    def __str__(self):
        return f"{self.account_name} - {self.provider}"


class AccountRelevanceReview(models.Model):
    """
    Periodic reviews to determine if accounts still matter
    """
    account_relevance = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='relevance_reviews'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='account_reviews',
        editable=False
    )
    review_date = models.DateTimeField(auto_now_add=True)
    matters = models.BooleanField(
        default=True,
        help_text="Does this account still matter?"
    )
    reasoning = models.TextField(blank=True)
    next_review_due = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

### THIS WAS ADDED TO SAVE THE ACCOUNT CREATION DATE AND ADD 90 DAYS TO CRITICAL ACCOUNTS
    def save(self, *args, **kwargs):
            # If this is a new object, set the review date 90 days from now
            if not self.review_date and self.account_relevance.is_critical:
                self.next_review_due = timezone.now().date() + timedelta(days=90)
            elif not self.review_date:
                self.next_review_due = timezone.now().date() + timedelta(days=365)
            super(AccountRelevanceReview, self).save(*args, **kwargs)
            
    class Meta:
        db_table = 'account_relevance_reviews'
        ordering = ['-review_date']
    
    def __str__(self):
        return f"Review of {self.account_relevance.account_name} created {self.account_relevance.created_at.date()}"

################ ### MARKED FOR REMOVAL POSSIBLY ### #########################
class Contact(models.Model):
    """
    Important contacts (family, friends, digital executor, etc.)
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='contacts',
        editable=False
    )
    full_name = models.CharField(max_length=200)
    relationship = models.CharField(
        max_length=100,
        help_text="e.g., Spouse, Child, Friend, Attorney"
    )
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    is_emergency_contact = models.BooleanField(default=False)
    is_digital_executor = models.BooleanField(default=False)
    is_caregiver = models.BooleanField(default=False)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contacts'
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['profile', 'full_name']),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.relationship})"


class DelegationScope(models.Model):
    """
    Types of authority that can be delegated (e.g., medical decisions, financial)
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'delegation_scopes'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class DelegationGrant(models.Model):
    """
    Grants of authority to contacts for specific scopes
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='delegation_grants',
        editable=False
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='delegations_received'
    )
    scope = models.ForeignKey(
        DelegationScope,
        on_delete=models.CASCADE,
        related_name='grants'
    )
    
    applies_on_death = models.BooleanField(default=False)
    applies_on_incapacity = models.BooleanField(default=False)
    applies_immediately = models.BooleanField(default=False)
    
    notes_for_contact = models.TextField(
        blank=True,
        help_text="Instructions for the contact"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'delegation_grants'
        ordering = ['contact', 'scope']
    
    def __str__(self):
        return f"{self.scope.name} → {self.contact.full_name}"


class Device(models.Model):
    """
    Physical devices (phones, computers, tablets, etc.)
    """
    DEVICE_TYPE_CHOICES = [
        ('phone', 'Phone'),
        ('tablet', 'Tablet'),
        ('laptop', 'Laptop'),
        ('desktop', 'Desktop'),
        ('smartwatch', 'Smart Watch'),
        ('other', 'Other'),
    ]
    
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='devices',
        editable=False
    )
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPE_CHOICES)
    name = models.CharField(max_length=200, help_text="Device name or model")
    owner_label = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g., 'Mom's iPhone', 'Work Laptop'"
    )
    location_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Where device is typically kept"
    )
    unlock_method_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="How to unlock (without revealing actual password)"
    )
    used_for_2fa = models.BooleanField(
        default=False,
        help_text="Used for two-factor authentication"
    )
    decommission_instruction = models.TextField(
        blank=True,
        help_text="What to do with this device after death"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'devices'
        ordering = ['device_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.device_type})"


class DigitalEstateDocument(models.Model):
    """
    The main digital estate planning document
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='estate_documents',
        editable=False
    )
    title = models.CharField(max_length=200)
    version = models.CharField(max_length=20, default="1.0")
    is_active = models.BooleanField(
        default=True,
        help_text="Is this the current active document?"
    )
    
    overall_instructions = models.TextField(
        blank=True,
        help_text="General instructions for family"
    )
    location_of_legal_will = models.TextField(blank=True)
    location_of_password_manager_instructions = models.TextField(blank=True)
    wishes_for_social_media = models.TextField(blank=True)
    wishes_for_photos_and_files = models.TextField(blank=True)
    data_retention_preferences = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'digital_estate_documents'
        ordering = ['-is_active', '-created_at']
    
    def __str__(self):
        return f"{self.title} v{self.version}"


class FamilyNeedsToKnowSection(models.Model):
    """
    Sections within the estate document that family needs to know
    """
    document = models.ForeignKey(
        DigitalEstateDocument,
        on_delete=models.CASCADE,
        related_name='family_sections'
    )
    heading = models.CharField(max_length=200)
    sort_order = models.IntegerField(default=0)
    content = models.TextField(help_text="What family needs to know")
    
    created_at = models.DateTimeField(default=timezone.now)
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'family_needs_to_know_sections'
        ordering = ['document', 'sort_order', 'heading']
    
    def __str__(self):
        return f"{self.document.title} - {self.heading}"

################ ### MARKED FOR REMOVAL ### #########################
class AccountDirectoryEntry(models.Model):
    """
    Quick reference directory of accounts
    """
    CRITICALITY_CHOICES = [
        ('critical', 'Critical'),
        ('important', 'Important'),
        ('nice-to-have', 'Nice to Have'),
    ]
    
    ACTION_CHOICES = [
        ('keep', 'Keep'),
        ('close', 'Close'),
        ('memorialize', 'Memorialize'),
        ('transfer', 'Transfer to Family'),
    ]
    
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='account_directory_entries',
        editable=False
    )
    label = models.CharField(max_length=200)
    category_label = models.CharField(max_length=100, blank=True)
    website_url = models.URLField(blank=True)
    username_hint = models.CharField(
        max_length=200,
        blank=True,
        help_text="Hint about username (not the actual username)"
    )
    criticality = models.CharField(
        max_length=20,
        choices=CRITICALITY_CHOICES,
        default='nice-to-have'
    )
    action_after_death = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        default='close'
    )
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'account_directory_entries'
        ordering = ['criticality', 'label']
        verbose_name_plural = 'Account directory entries'
    
    def __str__(self):
        return self.label


class EmergencyContact(models.Model):
    """
    Emergency notes for specific contacts
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='emergency_contacts',
        editable=False
    )
    CONTACTS_CHOICES = [
        ('Spouse', 'Spouse'),
        ('Mother', 'Mother'),
        ('Father', 'Father'),
        ('Sister', 'Sister'),
        ('Brother', 'Brother'),
        ('Daughter', 'Daughter'),
        ('Son', 'Son'),
        ('Mother-in-law', 'Mother-in-law'),
        ('Father-in-law', 'Father-in-low'),
        ('Sister-in-law', 'Sister-in-law'),
        ('Brother-in-law', 'Brother-in-law'),
        ('Daughter-in-law', 'Daughter-in-law'),
        ('Son-in-Law', 'Son-in-Law'),
        ('Cousin', 'Cousin'),
        ('Other', 'Other'),
    ]

    contact_name = models.CharField(max_length=200)
    body = models.TextField(help_text="Emergency message content")
    contact_relation = models.CharField(max_length=50, choices=CONTACTS_CHOICES)
    is_emergency_contact = models.BooleanField(default=False)
    is_digital_executor = models.BooleanField(default=False)
    is_caregiver = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'emergency_contacts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.contact_name} ({self.contact_relation})"

################ ### MARKED FOR REMOVAL ### #########################
class CheckupType(models.Model):
    """
    Types of periodic checkups (quarterly, annual, etc.)
    """
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ]
    
    name = models.CharField(max_length=100)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'checkup_types'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.frequency})"

################ ### MARKED FOR POSSIBLE REMOVAL ### #########################
class Checkup(models.Model):
    """
    Scheduled checkups of digital estate information
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='checkups',
        editable=False
    )
    checkup_type = models.ForeignKey(
        CheckupType,
        on_delete=models.CASCADE,
        related_name='checkups'
    )
    due_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_checkups',
        editable=False
    )
    summary = models.TextField(blank=True)
    
    all_accounts_reviewed = models.BooleanField(default=False)
    all_devices_reviewed = models.BooleanField(default=False)
    contacts_up_to_date = models.BooleanField(default=False)
    documents_up_to_date = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checkups'
        ordering = ['-due_date']
    
    def __str__(self):
        status = "Completed" if self.completed_at else "Pending"
        return f"{self.checkup_type.name} - {self.due_date} ({status})"
    
    def is_overdue(self):
        if self.completed_at:
            return False
        return timezone.now().date() > self.due_date


class CareRelationship(models.Model):
    """
    Relationships with caregivers or those providing care
    """
    RELATIONSHIP_CHOICES = [
        ('caregiver', 'Caregiver'),
        ('healthcare-proxy', 'Healthcare Proxy'),
        ('power-of-attorney', 'Power of Attorney'),
        ('trustee', 'Trustee'),
        ('other', 'Other'),
    ]
    
    ROLE_CHOICES = [
        ('view-only', 'View Only'),
        ('editor', 'Editor'),
        ('admin', 'Administrator'),
    ]
    
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='care_relationships',
        editable=False
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='care_relationships'
    )
    relationship_type = models.CharField(
        max_length=30,
        choices=RELATIONSHIP_CHOICES
    )
    has_portal_access = models.BooleanField(
        default=False,
        help_text="Has access to digital estate portal"
    )
    portal_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='view-only',
        blank=True
    )
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'care_relationships'
        ordering = ['contact']
    
    def __str__(self):
        return f"{self.contact.full_name} - {self.relationship_type}"


class RecoveryRequest(models.Model):
    """
    Requests to recover accounts (for deceased or incapacitated users)
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in-progress', 'In Progress'),
        ('completed', 'Completed'),
        ('denied', 'Denied'),
        ('cancelled', 'Cancelled'),
    ]
    
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='recovery_requests',
        editable=False
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recovery_requests_made',
        editable=False
    )
    target_account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='recovery_requests',
        null=True,
        blank=True
    )
    target_description = models.CharField(
        max_length=500,
        help_text="Description of account to recover"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    provider_ticket_number = models.CharField(max_length=100, blank=True)
    steps_taken = models.TextField(blank=True)
    outcome_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'recovery_requests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Recovery: {self.target_description} ({self.status})"

################ ### MARKED FOR REMOVAL ### #########################
class DocumentCategory(models.Model):
    """
    Categories for important documents
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'document_categories'
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Document categories'
    
    def __str__(self):
        return self.name


class ImportantDocument(models.Model):
    """
    Important documents (wills, deeds, insurance, etc.)
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='important_documents',
        editable=False
    )
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    physical_location = models.TextField(
        blank=True,
        help_text="Where physical document is stored"
    )
    digital_location = models.CharField(
        max_length=500,
        blank=True,
        help_text="Where digital copy is stored"
    )
    file = models.FileField(
        upload_to='documents/%Y/%m/',
        blank=True,
        null=True,
        help_text="Upload digital copy"
    )
    requires_legal_review = models.BooleanField(
        default=False,
        help_text="Needs legal professional review"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    # created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'important_documents'
        ordering = ['category', 'title']
    
    def __str__(self):
        return self.title

