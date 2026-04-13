"""
Management command: notify_expiring_grants

Emails grantees whose ProfileAccessGrant will expire within the next
NOTIFY_DAYS days (default: 14).  Each grant is notified exactly once —
the expiry_notified flag is set to True after the email is sent.

Typical cron schedule: daily
    0 8 * * * /path/to/venv/bin/python manage.py notify_expiring_grants

To re-send a notification (e.g. after extending expires_at), flip the
grant's expiry_notified field back to False in the Django admin.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from datetime import timedelta


class Command(BaseCommand):
    help = (
        "Email grantees whose ProfileAccessGrant expires within NOTIFY_DAYS days. "
        "Each grant is notified at most once (expiry_notified flag)."
    )

    NOTIFY_DAYS = 14

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=self.NOTIFY_DAYS,
            help=f'Days ahead to check for expiring grants (default: {self.NOTIFY_DAYS}).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be sent without actually sending emails or updating flags.',
        )

    def handle(self, *args, **options):
        from recovery.models import ProfileAccessGrant

        days      = options['days']
        dry_run   = options['dry_run']
        now       = timezone.now()
        threshold = now + timedelta(days=days)

        grants = ProfileAccessGrant.objects.filter(
            is_active=True,
            expiry_notified=False,
            expires_at__isnull=False,
            expires_at__gt=now,
            expires_at__lte=threshold,
        ).select_related('granted_to', 'profile')

        count = grants.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expiring grants to notify.'))
            return

        notified = 0
        failed   = 0

        for grant in grants:
            grantee = grant.granted_to
            profile = grant.profile
            email   = grantee.email

            if not email:
                self.stdout.write(
                    self.style.WARNING(
                        f'  Skipping grant #{grant.pk}: grantee {grantee} has no email address.'
                    )
                )
                failed += 1
                continue

            days_left    = (grant.expires_at - now).days
            expiry_date  = grant.expires_at.strftime('%B %d, %Y')
            profile_name = f'{profile.first_name} {profile.last_name}'

            subject = f'Your estate access for {profile_name} expires in {days_left} day{"s" if days_left != 1 else ""}'
            body = (
                f'Dear {grantee.first_name or grantee.username},\n\n'
                f'This is a reminder that your read-only access to the estate plan for '
                f'{profile_name} will expire on {expiry_date}.\n\n'
                f'After this date you will no longer be able to view the estate information. '
                f'If you need continued access, please contact the estate administrator.\n\n'
                f'Best regards,\nNovatern'
            )

            if dry_run:
                self.stdout.write(
                    f'[DRY RUN] Would email {email} — grant #{grant.pk} expires {expiry_date}'
                )
                notified += 1
                continue

            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                grant.expiry_notified = True
                grant.save(update_fields=['expiry_notified'])
                notified += 1
                self.stdout.write(
                    f'  Notified {email} — grant #{grant.pk} expires {expiry_date}'
                )
            except Exception as exc:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  Failed to email {email} for grant #{grant.pk}: {exc}'
                    )
                )

        summary = f'Done. Notified: {notified}'
        if failed:
            summary += f', Failed: {failed}'
        self.stdout.write(self.style.SUCCESS(summary))
