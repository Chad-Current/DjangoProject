from django.db import models
from django.utils import timezone


class ChecklistEmailLog(models.Model):
    """
    Tracks every time the Digital Estate Readiness Checklist is emailed.
    Useful for monitoring demand and following up with prospects.
    """
    email = models.EmailField(
        db_index=True,
        help_text="Recipient email address."
    )
    first_name = models.CharField(
        max_length=80,
        blank=True,
        default='',
        help_text="Optional first name provided by the requester."
    )
    sent_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the checklist email was successfully sent."
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the requester."
    )
    converted = models.BooleanField(
        default=False,
        help_text="Did this lead eventually create an account?"
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Internal admin notes about this lead."
    )

    class Meta:
        db_table = 'checklist_email_log'
        ordering = ['-sent_at']
        verbose_name = 'Checklist Email Log'
        verbose_name_plural = 'Checklist Email Logs'

    def __str__(self):
        name = f" ({self.first_name})" if self.first_name else ""
        return f"{self.email}{name} — {self.sent_at.strftime('%Y-%m-%d %H:%M')}"