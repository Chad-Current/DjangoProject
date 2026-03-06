# vault/models.py
#
# SETUP REQUIRED:
#   1. pip install cryptography
#   2. Add to settings.py:
#        import os
#        VAULT_ENCRYPTION_KEY = os.environ.get('VAULT_ENCRYPTION_KEY')
#   3. Generate a key once and store it in your environment / Bitwarden Secrets:
#        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#   4. Add 'vault' to INSTALLED_APPS
#   5. python manage.py makemigrations vault && python manage.py migrate

import base64
import logging
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------

def _get_fernet() -> Fernet:
    """
    Return a Fernet instance using VAULT_ENCRYPTION_KEY from settings.
    Raises ImproperlyConfigured if the key is missing or invalid.
    """
    key = getattr(settings, 'VAULT_ENCRYPTION_KEY', None)
    if not key:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            "VAULT_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_password(plaintext: str) -> str:
    """Encrypt a plaintext password and return a UTF-8 safe base64 string."""
    if not plaintext:
        return ''
    f = _get_fernet()
    token = f.encrypt(plaintext.encode('utf-8'))
    return token.decode('utf-8')


def decrypt_password(token: str) -> str:
    """
    Decrypt an encrypted token back to plaintext.
    Returns '[decryption error]' on failure so the UI degrades gracefully.
    """
    if not token:
        return ''
    try:
        f = _get_fernet()
        return f.decrypt(token.encode('utf-8')).decode('utf-8')
    except (InvalidToken, Exception) as exc:
        logger.error("VaultEntry decryption failed: %s", exc)
        return '[decryption error]'


# ---------------------------------------------------------------------------
# VaultEntry
# ---------------------------------------------------------------------------

class VaultEntry(models.Model):
    """
    A single encrypted credential stored in the add-on Vault.

    Linked (optionally) to a dashboard Account OR a dashboard Device.
    Exactly one of `linked_account` / `linked_device` should be set;
    both may be null for a standalone entry.

    The raw password is NEVER persisted — only the Fernet-encrypted token.
    """

    ENTRY_TYPE_CHOICES = [
        ('account',  'Digital Account'),
        ('device',   'Device'),
        ('other',    'Other / Standalone'),
    ]

    # ── Ownership ────────────────────────────────────────────────────────────
    profile = models.ForeignKey(
        'dashboard.Profile',
        on_delete=models.CASCADE,
        related_name='vault_entries',
        help_text="Owner profile.",
    )

    # ── Source linkage (both nullable — at most one should be set) ───────────
    linked_account = models.ForeignKey(
        'dashboard.Account',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='vault_entries',
        help_text="The Account this credential belongs to (optional).",
    )
    linked_device = models.ForeignKey(
        'dashboard.Device',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='vault_entries',
        help_text="The Device this PIN / password belongs to (optional).",
    )

    # ── Entry metadata ───────────────────────────────────────────────────────
    entry_type = models.CharField(
        max_length=20,
        choices=ENTRY_TYPE_CHOICES,
        default='other',
    )
    label = models.CharField(
        max_length=200,
        help_text="A descriptive label, e.g. 'Gmail master password' or 'iPhone PIN'.",
    )
    username_or_email = models.CharField(
        max_length=254,
        blank=True,
        help_text="The login identifier (username or email). Not encrypted.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional context — recovery codes, security questions, etc.",
    )

    # ── Encrypted payload ────────────────────────────────────────────────────
    encrypted_password = models.TextField(
        help_text="Fernet-encrypted password token. Never store plaintext here.",
    )

    # ── Audit ────────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the most recent decryption / reveal.",
    )

    # ── Slug (for URL routing) ────────────────────────────────────────────────
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
    )

    class Meta:
        db_table        = 'vault_entries'
        ordering        = ['-updated_at']
        verbose_name    = 'Vault Entry'
        verbose_name_plural = 'Vault Entries'

    # ── String representation ────────────────────────────────────────────────

    def __str__(self):
        return self.label

    # ── Slug generation ──────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.label)[:180]
            slug = base
            n    = 1
            while VaultEntry.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n   += 1
            self.slug = slug
        super().save(*args, **kwargs)

    # ── Encryption helpers ────────────────────────────────────────────────────

    def set_password(self, plaintext: str):
        """Encrypt and store a plaintext password. Call save() afterwards."""
        self.encrypted_password = encrypt_password(plaintext)

    def get_password(self) -> str:
        """
        Decrypt and return the plaintext password.
        Records `last_accessed` timestamp automatically.
        """
        self.last_accessed = timezone.now()
        # update_fields to avoid touching updated_at on a reveal
        VaultEntry.objects.filter(pk=self.pk).update(last_accessed=self.last_accessed)
        return decrypt_password(self.encrypted_password)

    # ── Convenience ──────────────────────────────────────────────────────────

    @property
    def source_name(self) -> str:
        """Human-readable name of the linked source, if any."""
        if self.linked_account:
            return self.linked_account.account_name_or_provider
        if self.linked_device:
            return self.linked_device.device_name
        return '—'

    @property
    def has_linked_source(self) -> bool:
        return bool(self.linked_account_id or self.linked_device_id)


# ---------------------------------------------------------------------------
# VaultAccessLog  (optional audit trail)
# ---------------------------------------------------------------------------

class VaultAccessLog(models.Model):
    """
    Immutable audit record written each time a vault entry password is revealed.
    """
    entry      = models.ForeignKey(
        VaultEntry,
        on_delete=models.CASCADE,
        related_name='access_logs',
    )
    accessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'vault_access_logs'
        ordering = ['-accessed_at']

    def __str__(self):
        return f"{self.accessed_by} accessed '{self.entry.label}' at {self.accessed_at}"