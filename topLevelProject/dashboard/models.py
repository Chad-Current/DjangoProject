from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Profile(TimeStampedModel):
    """
    The primary person whose digital estate is being organized.
    """
    user = models.OneToOneField(
        User,
        related_name="estate_profile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=200)
    date_of_birth = models.DateField(null=True, blank=True)
    primary_email = models.EmailField()
    phone_number = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)

    has_digital_executor = models.BooleanField(default=False)
    digital_executor_name = models.CharField(max_length=200, blank=True)
    digital_executor_contact = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Estate Profile"
        verbose_name_plural = "Estate Profiles"

    def __str__(self):
        return self.full_name


class AccountCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class DigitalAccount(TimeStampedModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="accounts")
    category = models.ForeignKey(
        AccountCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accounts",
    )

    name = models.CharField(max_length=200)
    provider = models.CharField(max_length=200, blank=True)
    website_url = models.URLField(blank=True)
    username_or_email = models.CharField(max_length=255, blank=True)

    credential_storage_location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Where to find login credentials (password manager, safe, etc.).",
    )

    is_critical = models.BooleanField(default=True)
    keep_or_close_instruction = models.CharField(
        max_length=50,
        choices=(
            ("KEEP", "Keep active"),
            ("CLOSE", "Close after estate settlement"),
            ("MEMORIALIZE", "Memorialize"),
            ("UNSURE", "Unsure / needs review"),
        ),
        default="KEEP",
    )
    notes_for_family = models.TextField(blank=True)

    class Meta:
        ordering = ["-is_critical", "name"]

    def __str__(self):
        return f"{self.name} ({self.profile})"


class AccountRelevanceReview(TimeStampedModel):
    account = models.ForeignKey(DigitalAccount, on_delete=models.CASCADE, related_name="relevance_reviews")
    reviewer = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="account_relevance_reviews",
    )
    matters = models.BooleanField()
    reasoning = models.TextField(blank=True)
    next_review_due = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class Contact(TimeStampedModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="contacts")
    full_name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=255, blank=True)

    is_emergency_contact = models.BooleanField(default=False)
    is_digital_executor = models.BooleanField(default=False)
    is_caregiver = models.BooleanField(default=False)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.relationship})"


class DelegationScope(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class DelegationGrant(TimeStampedModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="delegations")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="delegations")
    scope = models.ForeignKey(DelegationScope, on_delete=models.CASCADE, related_name="grants")

    applies_on_death = models.BooleanField(default=True)
    applies_on_incapacity = models.BooleanField(default=True)
    applies_immediately = models.BooleanField(default=False)

    notes_for_contact = models.TextField(blank=True)

    class Meta:
        unique_together = ("profile", "contact", "scope")


class Device(TimeStampedModel):
    DEVICE_TYPE_CHOICES = (
        ("PHONE", "Phone"),
        ("TABLET", "Tablet"),
        ("LAPTOP", "Laptop"),
        ("DESKTOP", "Desktop"),
        ("SERVER", "Server/NAS"),
        ("OTHER", "Other"),
    )

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="devices")
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPE_CHOICES)
    name = models.CharField(max_length=200)
    operating_system = models.CharField(max_length=100, blank=True)
    owner_label = models.CharField(max_length=100, blank=True)
    location_description = models.CharField(max_length=255, blank=True)

    unlock_method_description = models.CharField(max_length=255, blank=True)
    has_full_disk_encryption = models.BooleanField(default=True)
    used_for_2fa = models.BooleanField(default=False)

    decommission_instruction = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.name} ({self.profile})"


class DigitalEstateDocument(TimeStampedModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="digital_estate_documents")
    title = models.CharField(max_length=200, default="Digital Estate Instructions")
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    overall_instructions = models.TextField()
    location_of_legal_will = models.CharField(max_length=255, blank=True)
    location_of_password_manager_instructions = models.CharField(max_length=255, blank=True)
    wishes_for_social_media = models.TextField(blank=True)
    wishes_for_photos_and_files = models.TextField(blank=True)
    data_retention_preferences = models.TextField(blank=True)

    class Meta:
        ordering = ["-version"]
        unique_together = ("profile", "version")

    def __str__(self):
        return f"{self.title} v{self.version} for {self.profile}"


class FamilyNeedsToKnowSection(models.Model):
    document = models.ForeignKey(
        DigitalEstateDocument,
        on_delete=models.CASCADE,
        related_name="family_sections",
    )
    heading = models.CharField(max_length=200)
    sort_order = models.PositiveIntegerField(default=0)
    content = models.TextField()

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.heading} ({self.document})"


class AccountDirectoryEntry(TimeStampedModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="directory_entries")

    label = models.CharField(max_length=200)
    category_label = models.CharField(max_length=100, blank=True)
    website_url = models.URLField(blank=True)
    username_hint = models.CharField(max_length=255, blank=True)
    criticality = models.CharField(
        max_length=20,
        choices=(("HIGH", "High"), ("MEDIUM", "Medium"), ("LOW", "Low")),
        default="HIGH",
    )
    action_after_death = models.CharField(
        max_length=50,
        choices=(
            ("KEEP", "Keep"),
            ("CLOSE", "Close"),
            ("MEMORIALIZE", "Memorialize"),
            ("ARCHIVE", "Archive data only"),
        ),
        default="KEEP",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-criticality", "label"]


class EmergencyNote(TimeStampedModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="emergency_notes")
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_notes",
    )
    title = models.CharField(max_length=200)
    body = models.TextField()

    def __str__(self):
        return self.title


class CheckupType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    frequency = models.CharField(
        max_length=20,
        choices=(
            ("QUARTERLY", "Quarterly"),
            ("ANNUAL", "Annual"),
            ("ONE_OFF", "One-off"),
        ),
    )
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Checkup(TimeStampedModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="checkups")
    checkup_type = models.ForeignKey(CheckupType, on_delete=models.CASCADE, related_name="checkups")
    due_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_checkups",
    )
    summary = models.TextField(blank=True)

    all_accounts_reviewed = models.BooleanField(default=False)
    all_devices_reviewed = models.BooleanField(default=False)
    contacts_up_to_date = models.BooleanField(default=False)
    documents_up_to_date = models.BooleanField(default=False)

    class Meta:
        ordering = ["-due_date"]


class CareRelationship(TimeStampedModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="care_relationships")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="care_relationships")

    relationship_type = models.CharField(
        max_length=50,
        choices=(
            ("SPOUSE", "Spouse/Partner"),
            ("CAREGIVER", "Caregiver"),
            ("POA", "Power of Attorney"),
            ("TRUSTEE", "Trustee"),
            ("OTHER", "Other"),
        ),
    )
    has_portal_access = models.BooleanField(default=False)
    portal_role = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("profile", "contact", "relationship_type")


class RecoveryRequest(TimeStampedModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="recovery_requests")
    requested_by = models.ForeignKey(
        Contact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recovery_requests",
    )
    target_account = models.ForeignKey(
        DigitalAccount,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recovery_requests",
    )
    target_description = models.CharField(max_length=255, blank=True)

    STATUS_CHOICES = (
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In progress"),
        ("RESOLVED", "Resolved"),
        ("FAILED", "Failed / not possible"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPEN")

    provider_ticket_number = models.CharField(max_length=100, blank=True)
    steps_taken = models.TextField(blank=True)
    outcome_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Recovery #{self.id} for {self.profile}"


class DocumentCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class ImportantDocument(TimeStampedModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="important_documents")
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    physical_location = models.CharField(max_length=255, blank=True)
    digital_location = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to="estate_documents/", blank=True, null=True)

    requires_legal_review = models.BooleanField(default=False)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
