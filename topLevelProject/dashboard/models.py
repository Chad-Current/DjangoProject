# ============================================================================
# PART 9: DASHBOARD MODELS - WITH M2M DELEGATE_DOC
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
        ('Email Account', 'Email Account'),
        ('Social Media Account', 'Social Media Account'),
        ('Cloud Storage Account', 'Cloud Storage Account'),
        ('Streaming Media Account', 'Streaming Media Account'),
        ('Ecommerce Marketplace Account', 'Ecommerce Marketplace Account'),
        ('Online Banking Account', 'Online Banking Account'),
        ('Neobank/Digital Bank Account', 'Neobank/Digital Bank Account'),
        ('Brokerage/Investment Account', 'Brokerage/Investment Account'),
        ('Cryptocurrency Exchange Account', 'Cryptocurrency Exchange Account'),
        ('Payment Wallet Account', 'Payment Wallet Account'),
        ('Payment Processor Account', 'Payment Processor Account'),
        ('App Store Account', 'App Store Account'),
        ('Gaming Platform Account', 'Gaming Platform Account'),
        ('Forum/Community Account', 'Forum/Community Account'),
        ('Education/Elearning Account', 'Education/Elearning Account'),
        ('Subscription Account', 'Subscription Account'),
        ('Government Portal Account', 'Government Portal Account'),
        ('Utilities/Telecom Portal Account', 'Utilities/Telecom Portal Account'),
        ('Health Portal Account', 'Health Portal Account'),
        ('Smart Home/IoT Account', 'Smart Home/IoT Account'),
        ('Travel Booking Account', 'Travel Booking Account'),
        ('Password Manager Account', 'Password Manager Account'),
        ('Not Listed', 'Not Listed'),
    ]
    INSTRUCTION_CHOICES = [
        ('Keep Active', 'Keep Active'),
        ('Close Account', 'Close Account'),
        ('Memorialize', 'Memorialize'),
        ('Other (See Notes)', 'Other (See Notes)'),
    ]
    
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='accounts',
        editable=False
    )
    account_category = models.CharField(
        max_length=200,
        choices=ACCOUNT_CATEGORIES,
        default='email'
    ) 
    account_name_or_provider = models.CharField(
        max_length=200, 
        help_text="Account name or service"
        )
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
        ordering = ['-is_critical', 'account_name_or_provider']
        indexes = [
            models.Index(fields=['profile', '-created_at']),
            models.Index(fields=['account_category']),
        ]
    
    def __str__(self):
        return f"{self.account_name_or_provider}" 


class AccountRelevanceReview(models.Model):
    """
    Periodic reviews to determine if accounts still matter
    """
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='relevance_reviews'
    )
    # FOR DATA INTEGRITY (KEEP?)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='account_reviews',
        editable=False
    )
    matters = models.BooleanField(
        default=True,
        help_text="Does this account still matter?"
    )
    review_date = models.DateTimeField(auto_now_add=True)
    reasoning = models.TextField(blank=True)
    next_review_due = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # If this is a new object, set the review date 90 days from now
        if not self.pk:  # Check if this is a new object
            if self.account.is_critical:
                self.next_review_due = timezone.now().date() + timedelta(days=90)
            else:
                self.next_review_due = timezone.now().date() + timedelta(days=365)
        super(AccountRelevanceReview, self).save(*args, **kwargs)
            
    class Meta:
        db_table = 'account_relevance_reviews'
        ordering = ['-review_date']
    
    def __str__(self):
        return f"Review of {self.account.account_name} on {self.review_date.date()}"


class Device(models.Model):
    """
    Physical devices (phones, computers, tablets, etc.)
    """
    DEVICE_TYPE_CHOICES = [
        ('Phone', 'Phone'),
        ('Tablet', 'Tablet'),
        ('Laptop', 'Laptop'),
        ('Desktop', 'Desktop'),
        ('Smart Watch', 'Smart Watch'),
        ('Other', 'Other'),
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
    )
    decommission_instruction = models.TextField(
        blank=True,
        help_text="What to do with this device after death"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'devices'
        ordering = ['device_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.device_type})"


class Contact(models.Model):
    """
    Notes for specific contacts
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='relation_contacts',
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
        ('Father-in-law', 'Father-in-law'),
        ('Sister-in-law', 'Sister-in-law'),
        ('Brother-in-law', 'Brother-in-law'),
        ('Daughter-in-law', 'Daughter-in-law'),
        ('Son-in-Law', 'Son-in-Law'),
        ('Cousin', 'Cousin'),
        ('Other', 'Other'),
    ]

    contact_name = models.CharField(
        max_length=200,
        default="Enter name"
    )
    body = models.TextField(help_text="Emergency message content")
    contact_relation = models.CharField(max_length=50, choices=CONTACTS_CHOICES)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_emergency_contact = models.BooleanField(default=False)
    is_digital_executor = models.BooleanField(default=False)
    is_caregiver = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'primary_contacts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.contact_name} ({self.contact_relation})"


class DigitalEstateDocument(models.Model):
    """
    The main digital estate planning document
    """
    PERSONAL_ESTATE_DOCUMENTS = [
        ("Healthcare Documents", [
            ("Advance Directive / Living Will", "Advance Directive / Living Will — States your wishes for end-of-life or critical medical care."),
            ("Durable Power of Attorney for Healthcare", "Durable Power of Attorney for Healthcare — Authorizes someone to make medical decisions if you cannot."),
            ("Living Will / Advance Directive", "Living Will / Advance Directive — States your wishes for end-of-life or critical medical care."),
            ("HIPAA Authorizations", "HIPAA Authorizations — Allows named individuals to access your medical information."),
            ("Organ Donation Preferences", "Organ Donation Preferences — Documents or forms stating your organ donation wishes."),
        ]),
        ("Financial and Legal Documents", [
            ("Durable Power of Attorney for Financial Matters", "Durable Power of Attorney for Financial Matters — Authorizes someone to manage finances if you are incapacitated."),
            ("Beneficiary Designations", "Beneficiary Designations — Forms for life insurance, retirement accounts, etc., naming who receives benefits."),
            ("Guardianship Designations", "Guardianship Designations — Documents naming guardians for minor children or dependents."),
            ("Trust Documents", "Trust Documents — Revocable or irrevocable trust agreements holding and distributing property."),
        ]),
        ("Estate Administration and Final Instructions", [
            ("Executor / Personal Representative Info", "Executor / Personal Representative Info — Information about the person(s) designated to administer your estate."),
            ("Letter of Instruction", "Letter of Instruction — Provides guidance for heirs, location of assets, and personal wishes."),
            ("Will and Codicils", "Will and Codicils — Last Will and Testament and any amendments (codicils)."),
        ]),
    ]
    
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='estate_documents',
        editable=False
    )
    
    # ManyToMany relationship with Contact through DelegationGrant
    # This is established via the reverse relationship from DelegationGrant
    
    estate_document = models.CharField(
        max_length=200,
        choices=PERSONAL_ESTATE_DOCUMENTS,
        default='important_personal_documents',
    )

    name_or_title = models.CharField(
        max_length=100,
        blank=False,
        help_text="Specific name of Document"
    )

    estate_file = models.FileField(
        upload_to='documents/%Y/%m/',
        blank=True,
        null=True,
        help_text="Upload digital copy"
    )

    overall_instructions = models.CharField(
        max_length=500,
        blank=True,
        help_text="General instructions for family"
    )
   
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        db_table = 'digital_estate_documents'
        ordering = ['-name_or_title', '-created_at']
    
    def is_delegated(self):
        """Check if this document is already delegated"""
        return self.delegation_grants.exists()
    
    def delegated_to(self):
        """Return the contact this document is delegated to, if any"""
        grant = self.delegation_grants.first()
        return grant.delegate_to if grant else None
    
    def __str__(self):
        return f"{self.estate_document}"


class FamilyNeedsToKnowSection(models.Model):
    """
    Sections within the estate document that family needs to know
    """
    relation = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='family_relations',
    )
    content = models.TextField(help_text="What family needs to know")
    is_location_of_legal_will = models.BooleanField(default=False)
    is_password_manager = models.BooleanField(default=False)
    is_social_media = models.BooleanField(default=False)
    is_photos_or_files = models.BooleanField(default=False)
    is_data_retention_preferences = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'family_needs_to_know_sections'
        ordering = ['relation', 'content']
        
    def __str__(self):
        return f"{self.relation} - {self.content}"


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
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ]
    
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
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    summary = models.TextField(blank=True)
    
    all_accounts_reviewed = models.BooleanField(default=False)
    all_devices_reviewed = models.BooleanField(default=False)
    contacts_up_to_date = models.BooleanField(default=False)
    documents_up_to_date = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checkups'
        ordering = ['-due_date']
    
    def __str__(self):
        status = "Completed" if self.completed_at else "Pending"
        return f"Checkup - {self.due_date} ({status})"  
    
    def is_overdue(self):
        if self.completed_at:
            return False
        return timezone.now().date() > self.due_date


class CareRelationship(models.Model):
    """
    Relationships with caregivers or those providing care
    """
    RELATIONSHIP_CHOICES = [
        ('Caregiver', 'Caregiver'),
        ('Healthcare-proxy', 'Healthcare Proxy'),
        ('Power-of-attorney', 'Power of Attorney'),
        ('Trustee', 'Trustee'),
        ('Other', 'Other'),
    ]
    
    ROLE_CHOICES = [
        ('View Only', 'View Only'),
        ('Editor', 'Editor'),
        ('Administrator', 'Administrator'),
    ]
    
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='care_relationships',
        editable=False
    )
    contact_name = models.ForeignKey(
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
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'care_relationships'
        ordering = ['contact_name']
    
    def __str__(self):
        return f"{self.contact_name} - {self.relationship_type}"


class RecoveryRequest(models.Model):
    """
    Requests to recover accounts (for deceased or incapacitated users)
    """
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Denied', 'Denied'),
        ('Cancelled', 'Cancelled'),
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
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'recovery_requests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Recovery: {self.target_description} ({self.status})"


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
    
    # ManyToMany relationship with Contact through DelegationGrant
    # This is established via the reverse relationship from DelegationGrant

    DOCUMENT_CATEGORY_CHOICES = [
        # 1. Personal Identification & Legal Records
        ("Personal Identification", "Driver’s license, passport, and other official IDs."),
        ("Important Personal Documents", "Birth certificate, marriage certificate, and similar records."),
        ("Social Security Information", "Social Security number and benefit details."),
        ("Property Deeds and Titles", "Ownership records for homes, vehicles, or land."),
        ("Safe Deposit Box Information", "Location, access instructions, and contents list."),

        # 2. Health & Care Information
        ("Medical Summary", "Includes allergies, medications, medical history, and specialists."),
        ("Care Preferences and Providers", "In-home care, nursing home info, and care instructions."),
        ("Health Insurance and Benefits", "Insurance policy details, Medicare/Medicaid info."),
        ("Dependents and Pet Care", "Dependent care needs and pet care instructions."),
        ("Funeral and Memorial Wishes", "Funeral, burial, or memorial preferences."),

        # 3. Financial Accounts & Assets
        ("Bank and Cash Accounts", "Checking, savings, and credit card details."),
        ("Loans and Liabilities", "Debts, mortgages, and other financial obligations."),
        ("Investments and Retirement", "Investment accounts, pensions, and annuities."),
        ("Income and Budgets", "Income sources, monthly bills, and recurring expenses."),
        ("Insurance Policies", "Life, disability, and long-term care policies."),
        ("Tax and Financial Records", "Tax returns, property records, and valuation documents."),

        # 4. Business & Legal Interests
        ("Business Ownership Documents", "Operating agreements, partnership and ownership records."),
        ("Charitable Giving and Memberships", "Charitable plans, affiliations, and organizations."),

        # 5. Digital & Online Accounts
        ("Online Accounts and Passwords", "Online services, financial logins, and subscriptions."),
        ("Cloud and Email Accounts", "Cloud storage, email accounts, and access credentials."),
        ("Password Management", "Password manager info and recovery instructions."),
        ("Social Media Accounts", "Profiles and legacy social media preferences."),

        # 6. Personal Property & Notes
        ("Personal Property and Valuables", "Inventory of personal valuables."),
        ("Notes and Special Instructions", "Additional notes or specific personal guidance."),
    ]

    name_or_title = models.CharField(
    max_length=100,
    blank=False,
    help_text="Specific name of Document"
    )

    description = models.CharField(
        max_length=200, 
        blank=True
    )
    
    document_category = models.CharField(
        max_length=50,
        choices=DOCUMENT_CATEGORY_CHOICES,
        default='Important Personal Documents'
    )

    physical_location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Where physical document is stored"
    )

    digital_location = models.CharField(
        max_length=500,
        blank=True,
        help_text="Where digital copy is stored"
    )

    important_file = models.FileField(
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
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        db_table = 'important_documents'
        ordering = ['document_category']
    
    def is_delegated(self):
        """Check if this document is already delegated"""
        return self.delegation_grants.exists()
    
    def delegated_to(self):
        """Return the contact this document is delegated to, if any"""
        grant = self.delegation_grants.first()
        return grant.delegate_to if grant else None
    
    def __str__(self):
        return self.document_category


class DelegationGrant(models.Model):
    """
    Grants of authority to contacts for specific scopes.
    This is the through model that connects Contact with DigitalEstateDocument and ImportantDocument.
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='delegation_grants',
        editable=False
    )

    delegate_to = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='delegation_grants',
        help_text="Contact receiving this delegation"
    )

    # ManyToMany relationships
    delegate_estate_documents = models.ManyToManyField(
        DigitalEstateDocument,
        related_name='delegation_grants',
        blank=True,
        help_text="Estate documents this delegation covers"
    )

    delegate_important_documents = models.ManyToManyField(
        ImportantDocument,
        related_name='delegation_grants',
        blank=True,
        help_text="Important documents this delegation covers"
    )
    
    DELEGATION_SCOPE_CHOICES = [
        ("Estate and Property Oversight", "Estate and Property Oversight"),
        ("Family Affairs", "Family Affairs"),
        ("Financial Authority", "Financial Authority"),
        ("Healthcare Decision-Making", "Healthcare Decision-Making"),
        ("Personal Items", "Personal Items"),
    ]
    
    delegation_category = models.CharField(
        max_length=200,
        choices=DELEGATION_SCOPE_CHOICES,
        default='MEDICAL_TREATMENT_DECISIONS'
    )
    
    applies_on_death = models.BooleanField(default=False)
    applies_on_incapacity = models.BooleanField(default=False)
    applies_immediately = models.BooleanField(default=False)
    
    notes_for_contact = models.TextField(
        blank=True,
        help_text="Instructions for the contact"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'delegation_grants'
        ordering = ['delegate_to', '-created_at']
    
    def __str__(self):
        return f"Delegation to {self.delegate_to.contact_name}"
    
    def get_estate_documents_count(self):
        """Return the count of delegated estate documents"""
        return self.delegate_estate_documents.count()
    
    def get_important_documents_count(self):
        """Return the count of delegated important documents"""
        return self.delegate_important_documents.count()

