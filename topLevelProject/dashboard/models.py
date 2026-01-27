# ============================================================================
# PART 9: DASHBOARD MODELS - CORRECTED
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
    account = models.ForeignKey(
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
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'family_needs_to_know_sections'
        ordering = ['document', 'sort_order', 'heading']
    
    def __str__(self):
        return f"{self.document.title} - {self.heading}"


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
        ('Father-in-law', 'Father-in-law'),
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
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
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
        EmergencyContact,
        on_delete=models.CASCADE,
        related_name='delegations_received'
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
        ordering = ['contact']
    
    def __str__(self):
        return f"Delegation to {self.contact.contact_name}"


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
    contact_name = models.ForeignKey(
        EmergencyContact,
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
    DOCUMENT_CATEGORY_CHOICES = [
        ("personal_identification", "Personal Identification"),
        ("contact_information", "Contact Information"),
        ("emergency_contacts", "Emergency Contacts"),
        ("family_relationships", "Family Relationships"),
        ("dependents_and_care_needs", "Dependents and Care Needs"),
        ("primary_physician_information", "Primary Physician Information"),
        ("medical_specialists", "Medical Specialists"),
        ("current_medications", "Current Medications"),
        ("medical_history", "Medical History"),
        ("allergies_and_sensitivities", "Allergies and Sensitivities"),
        ("health_insurance_policies", "Health Insurance Policies"),
        ("medicare_medicaid_information", "Medicare / Medicaid Information"),
        ("advance_directive_living_will", "Advance Directive / Living Will"),
        ("durable_power_of_attorney_healthcare", "Durable Power of Attorney for Healthcare"),
        ("hipaa_authorizations", "HIPAA Authorizations"),
        ("primary_bank_accounts", "Primary Bank Accounts"),
        ("investment_accounts", "Investment Accounts"),
        ("retirement_accounts", "Retirement Accounts"),
        ("pensions_and_annuities", "Pensions and Annuities"),
        ("life_insurance_policies", "Life Insurance Policies"),
        ("disability_insurance_policies", "Disability Insurance Policies"),
        ("long_term_care_insurance", "Long-Term Care Insurance"),
        ("social_security_information", "Social Security Information"),
        ("income_sources", "Income Sources"),
        ("budget_and_recurring_bills", "Budget and Recurring Bills"),
        ("real_estate_documents", "Real Estate Documents"),
        ("vehicle_titles_and_registration", "Vehicle Titles and Registration"),
        ("personal_property_and_valuables", "Personal Property and Valuables"),
        ("safe_deposit_box_information", "Safe Deposit Box Information"),
        ("business_ownership_documents", "Business Ownership Documents"),
        ("will_and_codicils", "Will and Codicils"),
        ("trust_documents", "Trust Documents"),
        ("durable_power_of_attorney_financial", "Durable Power of Attorney for Financial Matters"),
        ("guardianship_designations", "Guardianship Designations"),
        ("executor_personal_representative_info", "Executor / Personal Representative Info"),
        ("beneficiary_designations", "Beneficiary Designations"),
        ("tax_returns_and_records", "Tax Returns and Records"),
        ("debts_and_liabilities", "Debts and Liabilities"),
        ("loans_and_mortgages", "Loans and Mortgages"),
        ("credit_card_accounts", "Credit Card Accounts"),
        ("online_accounts_and_passwords", "Online Accounts and Passwords"),
        ("email_accounts", "Email Accounts"),
        ("social_media_accounts", "Social Media Accounts"),
        ("cloud_storage_accounts", "Cloud Storage Accounts"),
        ("online_banking_and_finance_logins", "Online Banking and Finance Logins"),
        ("digital_subscriptions_and_services", "Digital Subscriptions and Services"),
        ("password_manager_information", "Password Manager Information"),
        ("funeral_and_burial_wishes", "Funeral and Burial Wishes"),
        ("organ_donation_preferences", "Organ Donation Preferences"),
        ("memorial_instructions", "Memorial Instructions"),
        ("care_preferences_at_home", "Care Preferences at Home"),
        ("assisted_living_or_nursing_home_info", "Assisted Living or Nursing Home Info"),
        ("in_home_care_providers", "In-Home Care Providers"),
        ("pet_care_and_ownership", "Pet Care and Ownership"),
        ("membership_and_affiliations", "Membership and Affiliations"),
        ("charitable_giving_plans", "Charitable Giving Plans"),
        ("important_personal_documents", "Important Personal Documents"),
        ("notes_and_special_instructions", "Notes and Special Instructions"),
    ]
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=200,blank=True)
    document_category = models.CharField(
        max_length=50,
        choices=DOCUMENT_CATEGORY_CHOICES,
        default='important_personal_documents'
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
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'important_documents'
        ordering = ['document_category', 'title']
    
    def __str__(self):
        return self.title