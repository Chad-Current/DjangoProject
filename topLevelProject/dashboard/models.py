from django.db import models
from django.conf import settings
from django.core.validators import URLValidator
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
import uuid

DAY_CHOICES = [
    (30,  '30 Days (One Month)'),
    (60,  '60 Days (2 Months)'),
    (90,  '90 Days (3 Months)'),
    (180, '180 Days (6 Months)'),
    (365, '365 Days (1 Year)'),
]


def _unique_slug(model_class, base_text, slug_field='slug'):
    """
    Generate a URL-safe slug from ``base_text`` that is guaranteed to be
    unique within ``model_class``.  Appends a short random hex suffix when
    a collision is detected (or when base_text is empty).
    """
    base  = slugify(base_text)[:50] or 'item'
    slug  = f"{base}-{uuid.uuid4().hex[:8]}"
    # Extremely unlikely but guard against the 1-in-2^32 collision anyway
    while model_class.objects.filter(**{slug_field: slug}).exists():
        slug = f"{base}-{uuid.uuid4().hex[:8]}"
    return slug


# ============================================================================
# PROFILE
# ============================================================================

class Profile(models.Model):
    """
    User profile containing personal information for digital estate planning.
    One profile per user.  No slug needed — accessed via the logged-in user,
    never by a public-facing URL that exposes an identifier.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        editable=False,
    )
    first_name    = models.CharField(max_length=100)
    last_name     = models.CharField(max_length=100)
    date_of_birth = models.DateField(blank=True, null=True)
    email         = models.EmailField(blank=True)
    phone         = models.CharField(max_length=20, blank=True)
    address_1     = models.CharField(max_length=50)
    address_2     = models.CharField(max_length=50, blank=True)
    city          = models.CharField(max_length=50)
    state         = models.CharField(max_length=20)
    zipcode       = models.IntegerField(blank=True, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'profiles'
        ordering = ['user']

    def __str__(self):
        return f"{self.first_name} ({self.user})"


# ============================================================================
# CONTACT
# ============================================================================

class Contact(models.Model):
    """
    Contacts for estate planning.
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='relation_contacts',
        editable=False,
    )

    CONTACTS_CHOICES = [
        ('Self',             'Self'),
        ('Spouse',           'Spouse'),
        ('Mother',           'Mother'),
        ('Father',           'Father'),
        ('Sister',           'Sister'),
        ('Brother',          'Brother'),
        ('Daughter',         'Daughter'),
        ('Son',              'Son'),
        ('Mother-in-law',    'Mother-in-law'),
        ('Father-in-law',    'Father-in-law'),
        ('Sister-in-law',    'Sister-in-law'),
        ('Brother-in-law',   'Brother-in-law'),
        ('Daughter-in-law',  'Daughter-in-law'),
        ('Son-in-Law',       'Son-in-Law'),
        ('Cousin',           'Cousin'),
        ('Other',            'Other'),
    ]

    slug          = models.SlugField(max_length=80, unique=True, null=True, blank=True, db_index=True)
    first_name    = models.CharField(max_length=100)
    last_name     = models.CharField(max_length=100)
    body          = models.CharField(max_length=1000, help_text="Emergency message content", blank=True)
    contact_relation = models.CharField(max_length=50, choices=CONTACTS_CHOICES)
    email         = models.EmailField(blank=True)
    phone         = models.CharField(max_length=20, blank=True)
    address_1     = models.CharField(max_length=50)
    address_2     = models.CharField(max_length=50, blank=True)
    city          = models.CharField(max_length=50)
    state         = models.CharField(max_length=20)
    zipcode       = models.IntegerField(blank=True, null=True)

    is_emergency_contact      = models.BooleanField(default=False, help_text="Contact to notify and provide access during medical emergencies or sudden incapacity.")
    is_digital_executor       = models.BooleanField(default=False, help_text="Responsible for managing digital assets (accounts, passwords, online services) after death.")
    is_caregiver              = models.BooleanField(default=False, help_text="Primary person providing or coordinating long-term care needs and health decisions.")
    is_legal_executor         = models.BooleanField(default=False, help_text="Named executor/personal representative to administer overall estate and will.")
    is_trustee                = models.BooleanField(default=False, help_text="Manages trusts, distributions, and trust assets according to trust terms.")
    is_financial_agent        = models.BooleanField(default=False, help_text="Authorized under financial power of attorney to handle money/bills if incapacitated.")
    is_healthcare_proxy       = models.BooleanField(default=False, help_text="Makes medical decisions if you're unable to communicate (healthcare power of attorney).")
    is_guardian_for_dependents= models.BooleanField(default=False, help_text="Named legal guardian for minor children or dependent adults.")
    is_pet_caregiver          = models.BooleanField(default=False, help_text="Responsible for pet care, veterinary decisions, and related expenses.")
    is_memorial_contact       = models.BooleanField(default=False, help_text="Handles funeral, memorial service, and burial/cremation preferences.")
    is_legacy_contact         = models.BooleanField(default=False, help_text="Designated for platform-specific legacy access (e.g., Apple, Google, Facebook).")
    is_professional_advisor   = models.BooleanField(default=False, help_text="Attorney, accountant, or advisor to consult for legal/financial guidance.")
    is_notification_only      = models.BooleanField(default=False, help_text="Receives notifications and basic info but has no decision-making authority or tasks.")
    is_knowledge_contact      = models.BooleanField(default=False, help_text="Delegated specific knowledge/info (e.g., account locations) but no action required.")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'primary_contacts'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(
                Contact,
                f"{self.first_name} {self.last_name}",
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.contact_relation})"

    def get_estate_documents_count(self):
        return self.delegated_estate_documents.count()

    def get_important_documents_count(self):
        return self.delegated_important_documents.count()

    def get_total_documents_count(self):
        return self.get_estate_documents_count() + self.get_important_documents_count()


# ============================================================================
# ACCOUNT
# ============================================================================

class Account(models.Model):
    """
    Individual digital accounts (social media, email, banking, etc.)
    """
    ACCOUNT_CATEGORIES = [
        ('App Store Account',              'App Store'),
        ('Brokerage/Investment Account',   'Brokerage/Investment'),
        ('Cloud Storage Account',          'Cloud Storage'),
        ('Cryptocurrency Exchange Account','Cryptocurrency Exchange'),
        ('Ecommerce Marketplace Account',  'Ecommerce Marketplace'),
        ('Education/Elearning Account',    'Education or Elearning'),
        ('Email Account',                  'Email'),
        ('Forum/Community Account',        'Forum/Community'),
        ('Gaming Platform Account',        'Gaming Platform'),
        ('Government Portal Account',      'Government Portal'),
        ('Health Portal Account',          'Health Portal'),
        ('Neobank/Digital Bank Account',   'Neobank/Digital Bank'),
        ('Online Banking Account',         'Online Banking'),
        ('Password Manager Account',       'Password Manager'),
        ('Payment Processor Account',      'Payment Processor'),
        ('Payment Wallet Account',         'Payment Wallet'),
        ('Smart Home/IoT Account',         'Smart Home/IoT'),
        ('Social Media Account',           'Social Media'),
        ('Streaming Media Account',        'Streaming Media'),
        ('Subscription Account',           'Subscription'),
        ('Travel Booking Account',         'Travel Booking'),
        ('Utilities/Telecom Portal Account','Utilities or Telecom Portal'),
        ('Not Listed',                     'Not Listed'),
    ]

    INSTRUCTION_CHOICES = [
        ('Close Account',      'Close Account'),
        ('Keep Active',        'Keep Active'),
        ('Memorialize',        'Memorialize'),
        ('Other (See Notes)',  'Other (See Notes)'),
    ]

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='accounts',
        editable=False,
    )
    delegated_account_to = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name='delegated_accounts',
        help_text="Contact who has access to this account",
    )

    slug                       = models.SlugField(max_length=80, unique=True, null=True, blank=True, db_index=True)
    account_category           = models.CharField(max_length=200, choices=ACCOUNT_CATEGORIES, default='Email Account')
    account_name_or_provider   = models.CharField(max_length=200, help_text="Account name or service")
    website_url                = models.URLField(blank=True, validators=[URLValidator()], help_text='Format must use https://www.example.com to validate, leave blank if unsure')
    username_or_email          = models.CharField(max_length=200, blank=True, help_text="Username or email used for login")
    credential_storage_location= models.CharField(max_length=500, blank=True, help_text="Where password is stored (e.g., 1Password, LastPass)")
    review_time                = models.PositiveSmallIntegerField(choices=DAY_CHOICES, default=30, help_text='How often would you like to review this item (Email Notification will be sent)')
    keep_or_close_instruction  = models.CharField(max_length=20, choices=INSTRUCTION_CHOICES, default='Keep Active')
    notes_for_family           = models.TextField(blank=True, help_text="Instructions or notes for family members")
    created_at                 = models.DateTimeField(default=timezone.now)
    updated_at                 = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts'
        ordering = ['-created_at', 'delegated_account_to', 'account_name_or_provider']
        indexes  = [models.Index(fields=['profile', 'delegated_account_to'])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Account, self.account_name_or_provider)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.account_name_or_provider}"


# ============================================================================
# DEVICE
# ============================================================================

class Device(models.Model):
    """
    Physical devices (phones, computers, tablets, etc.)
    """
    DEVICE_TYPE_CHOICES = [
        ('Desktop',    'Desktop'),
        ('Laptop',     'Laptop'),
        ('Phone',      'Phone'),
        ('Smart Watch','Smart Watch'),
        ('Tablet',     'Tablet'),
        ('Other',      'Other'),
    ]

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='devices',
        editable=False,
    )
    delegated_device_to = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name='delegated_devices',
        help_text="Contact who has access to this device",
    )

    slug                        = models.SlugField(max_length=80, unique=True, null=True, blank=True, db_index=True)
    device_type                 = models.CharField(max_length=20, choices=DEVICE_TYPE_CHOICES)
    device_name                 = models.CharField(max_length=200, help_text="Device name or model")
    owner_label                 = models.CharField(max_length=100, blank=True, help_text="e.g., 'Mom's iPhone', 'Work Laptop'")
    location_description        = models.CharField(max_length=200, blank=True, help_text="Where device is typically kept")
    unlock_method_description   = models.CharField(max_length=200, blank=True, help_text="How to unlock (without revealing actual password)")
    used_for_2fa                = models.BooleanField(default=False)
    decommission_instruction    = models.TextField(blank=True, help_text="What to do with this device after death")
    review_time                 = models.PositiveSmallIntegerField(choices=DAY_CHOICES, default=30, help_text='How often would you like to review this item (Email Notification will be sent)')
    created_at                  = models.DateTimeField(default=timezone.now)
    updated_at                  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'devices'
        ordering = ['-created_at', 'delegated_device_to', 'device_name']
        indexes  = [models.Index(fields=['profile', 'delegated_device_to'])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Device, self.device_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.device_name} ({self.device_type})"


# ============================================================================
# DIGITAL ESTATE DOCUMENT
# ============================================================================

class DigitalEstateDocument(models.Model):
    """
    Estate planning documents — must be assigned to a contact.
    """
    PERSONAL_ESTATE_DOCUMENTS = [
        ("Healthcare Documents", [
            ("Advance Directive / Living Will",                "Advance Directive / Living Will — States your wishes for end-of-life or critical medical care."),
            ("Durable Power of Attorney for Healthcare",       "Durable Power of Attorney for Healthcare — Authorizes someone to make medical decisions if you cannot."),
            ("HIPAA Authorizations",                           "HIPAA Authorizations — Allows named individuals to access your medical information."),
            ("Organ Donation Preferences",                     "Organ Donation Preferences — Documents or forms stating your organ donation wishes."),
        ]),
        ("Financial and Legal Documents", [
            ("Durable Power of Attorney for Financial Matters","Durable Power of Attorney for Financial Matters — Authorizes someone to manage finances if you are incapacitated."),
            ("Beneficiary Designations",                       "Beneficiary Designations — Forms for life insurance, retirement accounts, etc., naming who receives benefits."),
            ("Guardianship Designations",                      "Guardianship Designations — Documents naming guardians for minor children or dependents."),
            ("Trust Documents",                                "Trust Documents — Revocable or irrevocable trust agreements holding and distributing property."),
        ]),
        ("Estate Administration and Final Instructions", [
            ("Executor / Personal Representative Info",        "Executor / Personal Representative Info — Information about the person(s) designated to administer your estate."),
            ("Letter of Instruction",                          "Letter of Instruction — Provides guidance for heirs, location of assets, and personal wishes."),
            ("Will and Codicils",                              "Will and Codicils — Last Will and Testament and any amendments (codicils)."),
        ]),
    ]

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='estate_documents',
        editable=False,
    )
    delegated_estate_to = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name='delegated_estate_documents',
        help_text="Contact who has access to this document",
    )

    slug                        = models.SlugField(max_length=80, unique=True, null=True, blank=True, db_index=True)
    estate_category             = models.CharField(max_length=200, choices=PERSONAL_ESTATE_DOCUMENTS, default='Advance Directive / Living Will')
    name_or_title               = models.CharField(max_length=100, help_text="Specific name of Document")
    estate_file                 = models.FileField(upload_to='documents/%Y/%m/', blank=True, null=True, help_text="Upload digital copy")
    estate_overall_instructions = models.CharField(max_length=500, blank=True, help_text="General instructions for family")
    estate_physical_location    = models.CharField(max_length=200, blank=True, help_text="Where physical document is stored")
    estate_digital_location     = models.CharField(max_length=500, blank=True, help_text="Where digital copy is stored")
    review_time                 = models.PositiveSmallIntegerField(choices=DAY_CHOICES, default=30, help_text='How often would you like to review this item (Email Notification will be sent)')
    created_at                  = models.DateTimeField(default=timezone.now)
    updated_at                  = models.DateTimeField(auto_now=True)
    applies_on_death            = models.BooleanField(default=False)
    applies_on_incapacity       = models.BooleanField(default=False)
    applies_immediately         = models.BooleanField(default=False)

    class Meta:
        db_table = 'digital_estate_documents'
        ordering = ['delegated_estate_to', 'estate_category']
        indexes  = [models.Index(fields=['profile', 'delegated_estate_to'])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(DigitalEstateDocument, self.name_or_title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name_or_title} → {self.delegated_estate_to.first_name} {self.delegated_estate_to.last_name}"


# ============================================================================
# IMPORTANT DOCUMENT
# ============================================================================

class ImportantDocument(models.Model):
    """
    Important documents — must be assigned to a contact.
    """
    DOCUMENT_CATEGORY_CHOICES = [
        ("Bank and Cash Accounts",          "Checking, savings, and credit card details."),
        ("Business Ownership Documents",    "Operating agreements, partnership and ownership records."),
        ("Care Preferences and Providers",  "In-home care, nursing home info, and care instructions."),
        ("Charitable Giving and Memberships","Charitable plans, affiliations, and organizations."),
        ("Cloud and Email Accounts",        "Cloud storage, email accounts, and access credentials."),
        ("Dependents and Pet Care",         "Dependent care needs and pet care instructions."),
        ("Funeral and Memorial Wishes",     "Funeral, burial, or memorial preferences."),
        ("Health Insurance and Benefits",   "Insurance policy details, Medicare/Medicaid info."),
        ("Important Personal Documents",    "Birth certificate, marriage certificate, and similar records."),
        ("Income and Budgets",              "Income sources, monthly bills, and recurring expenses."),
        ("Insurance Policies",             "Life, disability, and long-term care policies."),
        ("Investments and Retirement",      "Investment accounts, pensions, and annuities."),
        ("Loans and Liabilities",           "Debts, mortgages, and other financial obligations."),
        ("Medical Summary",                 "Includes allergies, medications, medical history, and specialists."),
        ("Notes and Special Instructions",  "Additional notes or specific personal guidance."),
        ("Online Accounts and Passwords",   "Online services, financial logins, and subscriptions."),
        ("Password Management",             "Password manager info and recovery instructions."),
        ("Personal Identification",         "Driver's license, passport, and other official IDs."),
        ("Personal Property and Valuables", "Inventory of personal valuables."),
        ("Property Deeds and Titles",       "Ownership records for homes, vehicles, or land."),
        ("Safe Deposit Box Information",    "Location, access instructions, and contents list."),
        ("Social Media Accounts",           "Profiles and legacy social media preferences."),
        ("Social Security Information",     "Social Security number and benefit details."),
        ("Tax and Financial Records",       "Tax returns, property records, and valuation documents."),
        ('Not Listed',                      'Not Listed'),
    ]

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='important_documents',
        editable=False,
    )
    delegated_important_document_to = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name='delegated_important_documents',
        help_text="Contact who has access to this document",
    )

    slug                  = models.SlugField(max_length=80, unique=True, null=True, blank=True, db_index=True)
    name_or_title         = models.CharField(max_length=100, help_text="Specific name of Document")
    description           = models.CharField(max_length=200, blank=True)
    document_category     = models.CharField(max_length=50, choices=DOCUMENT_CATEGORY_CHOICES)
    physical_location     = models.CharField(max_length=200, blank=True, help_text="Where physical document is stored")
    digital_location      = models.CharField(max_length=500, blank=True, help_text="Where digital copy is stored")
    important_file        = models.FileField(upload_to='documents/%Y/%m/', blank=True, null=True, help_text="Upload digital copy")
    requires_legal_review = models.BooleanField(default=False)
    applies_on_death      = models.BooleanField(default=False)
    applies_on_incapacity = models.BooleanField(default=False)
    applies_immediately   = models.BooleanField(default=False)
    review_time           = models.PositiveSmallIntegerField(choices=DAY_CHOICES, default=30, help_text='How often would you like to review this item (Email Notification will be sent)')
    created_at            = models.DateTimeField(default=timezone.now)
    updated_at            = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'important_documents'
        ordering = ['delegated_important_document_to', 'document_category']
        indexes  = [models.Index(fields=['profile', 'delegated_important_document_to'])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(ImportantDocument, self.name_or_title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name_or_title} → {self.delegated_important_document_to.first_name} {self.delegated_important_document_to.last_name}"


# ============================================================================
# FAMILY NEEDS TO KNOW SECTION
# ============================================================================

class FamilyNeedsToKnowSection(models.Model):
    """
    Sections within the estate document that family needs to know.
    """
    relation = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='family_relations',
    )

    slug                        = models.SlugField(max_length=80, unique=True, null=True, blank=True, db_index=True)
    content                     = models.TextField(help_text="What family needs to know")
    is_location_of_legal_will   = models.BooleanField(default=False)
    is_password_manager         = models.BooleanField(default=False)
    is_social_media             = models.BooleanField(default=False)
    is_photos_or_files          = models.BooleanField(default=False)
    is_data_retention_preferences = models.BooleanField(default=False)
    created_at                  = models.DateTimeField(default=timezone.now)
    updated_at                  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'family_needs_to_know_sections'
        ordering = ['relation', 'content']

    def save(self, *args, **kwargs):
        if not self.slug:
            # Build the base from the related contact name when available,
            # otherwise fall back to the first 40 chars of content.
            try:
                base = f"{self.relation.first_name} {self.relation.last_name} note"
            except Exception:
                base = (self.content or 'note')[:40]
            self.slug = _unique_slug(FamilyNeedsToKnowSection, base)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.relation} - {self.content[:50]}"


# ============================================================================
# FUNERAL PLAN
# ============================================================================

class FuneralPlan(models.Model):
    """
    Comprehensive funeral and end-of-life planning preferences for a user.
    One plan per user profile (OneToOne).  No slug — accessed only through
    the authenticated user's profile, never via a public URL.
    """
    profile = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name='funeral_plan',
        editable=False,
    )

    # ── 1. Personal Information ───────────────────────────────────────────────
    preferred_name                 = models.CharField(max_length=100, blank=True, help_text="Nickname or preferred name to use in service/obituary.")
    occupation                     = models.CharField(max_length=200, blank=True, help_text="Current or former occupation to include in obituary.")

    MARITAL_STATUS_CHOICES = [
        ('Single',              'Single'),
        ('Married',             'Married'),
        ('Widowed',             'Widowed'),
        ('Divorced',            'Divorced'),
        ('Separated',           'Separated'),
        ('Domestic Partnership','Domestic Partnership'),
        ('Prefer Not to Say',   'Prefer Not to Say'),
    ]
    marital_status                 = models.CharField(max_length=50, choices=MARITAL_STATUS_CHOICES, blank=True)
    religion_or_spiritual_affiliation = models.CharField(max_length=200, blank=True, help_text="Religion, denomination, or spiritual tradition (if any).")
    is_veteran                     = models.BooleanField(default=False, help_text="Did the person serve in the military?")
    veteran_branch                 = models.CharField(max_length=100, blank=True, help_text="Branch of military service (e.g., Army, Navy, Air Force).")

    # ── 2. Service Preferences ────────────────────────────────────────────────
    SERVICE_TYPE_CHOICES = [
        ('Traditional Funeral', 'Traditional Funeral'),
        ('Memorial Service',    'Memorial Service'),
        ('Graveside Service',   'Graveside Service'),
        ('Celebration of Life', 'Celebration of Life'),
        ('Private / Family Only','Private / Family Only'),
        ('No Service',          'No Service'),
        ('Other',               'Other'),
    ]
    service_type                   = models.CharField(max_length=50, choices=SERVICE_TYPE_CHOICES, blank=True)
    preferred_funeral_home         = models.CharField(max_length=200, blank=True, help_text="Name of preferred funeral home or funeral director.")
    funeral_home_phone             = models.CharField(max_length=20, blank=True)
    funeral_home_address           = models.CharField(max_length=300, blank=True)
    preferred_venue                = models.CharField(max_length=300, blank=True, help_text="Preferred location for the service (funeral home, church, outdoors, etc.).")
    officiant_contact              = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='officiant_for_plans', help_text="Clergy, celebrant, or officiant from your contacts list.")
    officiant_name_freetext        = models.CharField(max_length=200, blank=True, help_text="Officiant name if not yet in contacts.")

    TIMING_CHOICES = [
        ('Weekday - Daytime', 'Weekday - Daytime'),
        ('Weekday - Evening', 'Weekday - Evening'),
        ('Weekend - Daytime', 'Weekend - Daytime'),
        ('Weekend - Evening', 'Weekend - Evening'),
        ('No Preference',     'No Preference'),
    ]
    desired_timing                 = models.CharField(max_length=50, choices=TIMING_CHOICES, blank=True)

    VIEWING_CHOICES = [
        ('Yes - Open Casket', 'Yes - Open Casket'),
        ('Family Only',       'Family Only'),
        ('No Viewing',        'No Viewing'),
        ('No Preference',     'No Preference'),
    ]
    open_casket_viewing            = models.CharField(max_length=50, choices=VIEWING_CHOICES, blank=True)

    # ── 3. Final Disposition ──────────────────────────────────────────────────
    DISPOSITION_CHOICES = [
        ('Burial',                'Burial'),
        ('Cremation',             'Cremation'),
        ('Green / Natural Burial','Green / Natural Burial'),
        ('Donation to Science',   'Donation to Science'),
        ('Other',                 'Other'),
        ('No Preference',         'No Preference'),
    ]
    disposition_method             = models.CharField(max_length=50, choices=DISPOSITION_CHOICES, blank=True)
    burial_or_interment_location   = models.CharField(max_length=300, blank=True, help_text="Cemetery name, columbarium, or scatter site.")
    burial_plot_or_niche_purchased = models.BooleanField(null=True, blank=True, help_text="Has a burial plot or cremation niche already been purchased?")
    casket_type_preference         = models.CharField(max_length=200, blank=True, help_text="Casket material or style preference (e.g., wood, eco-friendly, simple).")
    urn_type_preference            = models.CharField(max_length=200, blank=True, help_text="Urn style or material preference (if cremation).")
    headstone_or_marker_inscription= models.TextField(blank=True, help_text="Ideas or wording for a headstone, marker, or memorial plaque.")

    # ── 4. Ceremony Personalization ───────────────────────────────────────────
    music_choices                  = models.TextField(blank=True, help_text="Songs, hymns, performers, or instruments desired at the service.")
    flowers_or_colors              = models.CharField(max_length=300, blank=True, help_text="Preferred flowers, arrangements, or color palette.")
    readings_poems_or_scriptures   = models.TextField(blank=True, help_text="Specific readings, poems, or scripture passages to be included.")
    eulogists_notes                = models.TextField(blank=True, help_text="Names of desired eulogists or speakers, and topics to address.")
    pallbearers_notes              = models.TextField(blank=True, help_text="Desired pallbearers (names or relationship descriptions).")
    clothing_or_jewelry_description= models.CharField(max_length=300, blank=True, help_text="What clothing or jewelry the deceased should be dressed in.")
    religious_cultural_customs     = models.TextField(blank=True, help_text="Religious rites, cultural traditions, or customs to observe.")
    items_to_display               = models.TextField(blank=True, help_text="Photos, memorabilia, military flag, hobby items, or other displays.")

    # ── 5. Reception ──────────────────────────────────────────────────────────
    reception_desired              = models.BooleanField(null=True, blank=True, help_text="Is a post-service gathering or reception desired?")
    reception_location             = models.CharField(max_length=300, blank=True)
    reception_food_preferences     = models.TextField(blank=True, help_text="Catering style, dietary notes, or specific food/drink preferences.")
    reception_atmosphere_notes     = models.TextField(blank=True, help_text="Music, ambiance, or atmosphere preferences for the reception.")
    reception_guest_list_notes     = models.TextField(blank=True, help_text="Notes on invitations, guest list scope, or who to notify.")

    # ── 6. Obituary and Memorial ──────────────────────────────────────────────
    obituary_photo_description     = models.CharField(max_length=300, blank=True, help_text="Description or location of preferred photo for obituary/service.")
    obituary_key_achievements      = models.TextField(blank=True, help_text="Key life achievements, milestones, or memories to highlight.")
    obituary_publications          = models.TextField(blank=True, help_text="Newspapers, websites, or platforms to publish the obituary.")
    charitable_donations_in_lieu   = models.CharField(max_length=300, blank=True, help_text="Charity or cause to suggest in lieu of flowers.")

    # ── 7. Administrative and Financial ───────────────────────────────────────
    funeral_insurance_policy_number= models.CharField(max_length=100, blank=True, help_text="Pre-paid funeral plan or funeral insurance policy number.")
    death_certificates_requested   = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Number of certified death certificate copies needed (typically 6-12).")
    payment_arrangements           = models.TextField(blank=True, help_text="Funding source or payment arrangements for funeral expenses.")

    # ── 8. Additional Instructions ────────────────────────────────────────────
    additional_instructions        = models.TextField(blank=True, help_text="Any other instructions, requests, or personal messages to family.")

    # ── Metadata ──────────────────────────────────────────────────────────────
    review_time = models.PositiveSmallIntegerField(
        choices=[
            (30,  '30 Days (One Month)'),
            (60,  '60 Days (2 Months)'),
            (90,  '90 Days (3 Months)'),
            (180, '180 Days (6 Months)'),
            (365, '365 Days (1 Year)'),
        ],
        default=365,
        help_text='How often to send a reminder email to review this plan.',
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'funeral_plans'
        ordering = ['-updated_at']

    def __str__(self):
        return f"Funeral Plan - {self.profile}"

    @property
    def has_disposition_set(self):
        return bool(self.disposition_method)

    @property
    def has_service_preferences(self):
        return bool(self.service_type or self.preferred_venue)

    @property
    def is_complete(self):
        """
        Rough completeness check — returns True when the four most critical
        sections (disposition, service type, officiant, and payment) are filled.
        """
        return all([
            self.disposition_method,
            self.service_type,
            self.officiant_contact or self.officiant_name_freetext,
            self.payment_arrangements or self.funeral_insurance_policy_number,
        ])


# ============================================================================
# RELEVANCE REVIEW
# ============================================================================

class RelevanceReview(models.Model):
    """
    Periodic reviews to determine if accounts, devices, estate documents,
    or important documents still matter.
    Only ONE of the four foreign keys should be set per review instance.
    """
    account_review = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='account_reviews',
        null=True, blank=True,
    )
    device_review = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='device_reviews',
        null=True, blank=True,
    )
    estate_review = models.ForeignKey(
        DigitalEstateDocument,
        on_delete=models.CASCADE,
        related_name='estate_reviews',
        null=True, blank=True,
    )
    important_document_review = models.ForeignKey(
        ImportantDocument,
        on_delete=models.CASCADE,
        related_name='important_document_reviews',
        null=True, blank=True,
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='relevance_reviews',
        editable=False,
    )

    slug           = models.SlugField(max_length=80, unique=True, null=True, blank=True, db_index=True)
    matters        = models.BooleanField(default=True, help_text="Does this still matter?")
    review_date    = models.DateTimeField(auto_now_add=True)
    reasoning      = models.TextField(blank=True, help_text="Why does this still matter or not?")
    next_review_due= models.DateField(null=True, blank=True)
    created_at     = models.DateTimeField(default=timezone.now)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'relevance_reviews'
        ordering = ['-next_review_due', '-review_date']
        indexes  = [
            models.Index(fields=['account_review']),
            models.Index(fields=['device_review']),
            models.Index(fields=['estate_review']),
            models.Index(fields=['important_document_review']),
            models.Index(fields=['next_review_due']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            # Build a descriptive base from the item being reviewed.
            item_name = self.get_item_name() or 'review'
            self.slug = _unique_slug(RelevanceReview, f"review {item_name}")
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        targets   = [self.account_review, self.device_review, self.estate_review, self.important_document_review]
        set_count = sum(1 for t in targets if t is not None)
        if set_count == 0:
            raise ValidationError("You must select one item to review (account, device, estate document, or important document).")
        if set_count > 1:
            raise ValidationError("You can only review one item at a time.")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_reviewed_item(self):
        if self.account_review:
            return self.account_review
        elif self.device_review:
            return self.device_review
        elif self.estate_review:
            return self.estate_review
        elif self.important_document_review:
            return self.important_document_review
        return None

    def get_item_type(self):
        if self.account_review:
            return "Account"
        elif self.device_review:
            return "Device"
        elif self.estate_review:
            return "Estate Document"
        elif self.important_document_review:
            return "Important Document"
        return "Unknown"

    def get_item_name(self):
        item = self.get_reviewed_item()
        if not item:
            return "Unknown Item"
        if hasattr(item, 'account_name_or_provider'):
            return item.account_name_or_provider
        elif hasattr(item, 'device_name'):
            return item.device_name
        elif hasattr(item, 'name_or_title'):
            return item.name_or_title
        return str(item)

    def __str__(self):
        return f"Review of {self.get_item_type()}: {self.get_item_name()} on {self.review_date.date()}"