"""
Management command: notify_review_due

Finds active subscribers whose RelevanceReview items are due or overdue,
sends each user a single summary email listing all affected reviews, then
stamps last_notified so the same review is not re-emailed within the
NOTIFY_THROTTLE_DAYS window.

Usage:
    python manage.py notify_review_due

Recommended cron (run daily at 07:00):
    0 7 * * * /path/to/venv/bin/python manage.py notify_review_due

Behaviour:
  - Only emails users with an active Stripe subscription.
  - Lapsed / canceled / free-tier users are silently skipped.
  - A review is included when next_review_due <= today AND
    (last_notified is NULL OR last_notified <= today - NOTIFY_THROTTLE_DAYS).
  - All qualifying reviews for one user are batched into a single email.
  - last_notified is set on every review that is included in the email.
"""

import logging
from collections import defaultdict
from datetime import date, timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.template.loader import render_to_string

from dashboard.models import RelevanceReview

logger = logging.getLogger(__name__)

# Re-notify at most once every N days for the same overdue review.
NOTIFY_THROTTLE_DAYS = 7


class Command(BaseCommand):
    help = 'Email active subscribers whose review items are due or overdue.'

    def handle(self, *args, **options):
        today           = date.today()
        throttle_cutoff = today - timedelta(days=NOTIFY_THROTTLE_DAYS)
        from_email      = getattr(settings, 'DEFAULT_FROM_EMAIL', 'hello@digitalestateplan.com')
        site_url        = getattr(settings, 'SITE_URL', 'digitalestateplan.com')

        # Reviews that are due/overdue and haven't been notified recently.
        due_reviews = (
            RelevanceReview.objects
            .filter(
                next_review_due__lte=today,
                reviewer__subscription_status='active',
            )
            .exclude(reviewer__stripe_subscription_id='')
            .filter(
                Q(last_notified__isnull=True) |
                Q(last_notified__lte=throttle_cutoff)
            )
            .select_related(
                'reviewer',
                'account_review',
                'device_review',
                'estate_review',
                'important_document_review',
            )
            .order_by('reviewer__email', 'next_review_due')
        )

        if not due_reviews.exists():
            self.stdout.write('notify_review_due: no reviews to notify.')
            return

        # Group reviews by user.
        user_reviews = defaultdict(list)
        for review in due_reviews:
            user_reviews[review.reviewer].append(review)

        sent = 0
        skipped = 0
        for user, reviews in user_reviews.items():
            # Double-check subscription state at send time.
            if not user.is_subscription_active():
                skipped += 1
                logger.info(
                    'notify_review_due: skipped %s — subscription not active', user.email
                )
                continue

            overdue  = [r for r in reviews if r.next_review_due < today]
            due_today = [r for r in reviews if r.next_review_due == today]

            context = {
                'user':       user,
                'reviews':    reviews,
                'overdue':    overdue,
                'due_today':  due_today,
                'today':      today,
                'site_url':   site_url,
            }

            subject   = self._build_subject(len(reviews), len(overdue))
            text_body = render_to_string('dashboard/emails/review_due.txt',  context)
            html_body = render_to_string('dashboard/emails/review_due.html', context)

            try:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_body,
                    from_email=from_email,
                    to=[user.email],
                )
                msg.attach_alternative(html_body, 'text/html')
                msg.send(fail_silently=False)

                # Stamp every notified review so they won't be re-sent within throttle window.
                review_pks = [r.pk for r in reviews]
                RelevanceReview.objects.filter(pk__in=review_pks).update(last_notified=today)

                sent += 1
                logger.info(
                    'notify_review_due: emailed %s (%d review(s))',
                    user.email, len(reviews),
                )

            except Exception as exc:
                logger.error(
                    'notify_review_due: failed to email %s — %s', user.email, exc
                )

        self.stdout.write(
            f'notify_review_due: done — {sent} email(s) sent, {skipped} skipped.'
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_subject(self, total, overdue_count):
        if overdue_count == total:
            return (
                f'Action needed: {total} review{"s" if total != 1 else ""} overdue'
                ' — Digital Estate Plan'
            )
        if overdue_count > 0:
            return (
                f'{total} review{"s" if total != 1 else ""} need your attention'
                ' — Digital Estate Plan'
            )
        return (
            f'{total} review{"s" if total != 1 else ""} due today'
            ' — Digital Estate Plan'
        )
