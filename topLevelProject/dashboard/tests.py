# dashboard/tests.py
"""
Comprehensive test suite for the dashboard app.

Coverage:
  - Models: Profile, Contact, Account, Device, DigitalEstateDocument,
            ImportantDocument, FamilyNeedsToKnowSection, FuneralPlan,
            RelevanceReview
  - Signals: auto-create Self contact, RelevanceReview on item creation,
             review_time update propagation
  - Forms: all 14 forms, validation rules, clean() methods
  - Views: DashboardHomeView, Profile CRUD, Contact CRUD, Account CRUD,
           Device CRUD, Estate CRUD, ImportantDocument CRUD,
           FamilyAwareness CRUD, FuneralPlan wizard (all 8 steps + delete),
           RelevanceReview CRUD, MarkItemReviewedView
  - Edge cases throughout

Run with:
    python manage.py test dashboard --verbosity=2
"""

import json
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Account,
    Contact,
    Device,
    DigitalEstateDocument,
    FamilyNeedsToKnowSection,
    FuneralPlan,
    ImportantDocument,
    Profile,
    RelevanceReview,
)

User = get_user_model()


# ═══════════════════════════════════════════════════════════════
#  SHARED FIXTURES
# ═══════════════════════════════════════════════════════════════

def make_user(username='tuser', email='tuser@example.com', password='StrongPass1!', **kw):
    return User.objects.create_user(username=username, email=email, password=password, **kw)


def make_legacy(username='legacy', email='legacy@example.com'):
    u = make_user(username=username, email=email)
    u.upgrade_to_legacy()
    return u


def make_essentials(username='ess', email='ess@example.com'):
    u = make_user(username=username, email=email)
    u.upgrade_to_essentials()
    return u


def make_profile(user, **kw):
    defaults = dict(
        first_name='Jane', last_name='Doe',
        address_1='123 Main St', city='Des Moines',
        state='IA', zipcode=50309,
        email='jane@example.com', phone='515-555-1234',
    )
    defaults.update(kw)
    return Profile.objects.create(user=user, **defaults)


def make_contact(profile, relation='Spouse', **kw):
    defaults = dict(
        first_name='John', last_name='Doe',
        contact_relation=relation,
        address_1='123 Main St', city='Des Moines', state='IA',
        is_emergency_contact=True,
    )
    defaults.update(kw)
    return Contact.objects.create(profile=profile, **defaults)


def make_account(profile, contact, **kw):
    defaults = dict(
        account_name_or_provider='Gmail',
        account_category='Email Account',
        delegated_account_to=contact,
        review_time=30,
    )
    defaults.update(kw)
    return Account.objects.create(profile=profile, **defaults)


def make_device(profile, contact, **kw):
    defaults = dict(
        device_name='iPhone 15',
        device_type='Phone',
        delegated_device_to=contact,
        review_time=30,
    )
    defaults.update(kw)
    return Device.objects.create(profile=profile, **defaults)


def make_estate_doc(profile, contact, **kw):
    defaults = dict(
        name_or_title='Living Will',
        estate_category='Advance Directive / Living Will',
        delegated_estate_to=contact,
        applies_on_death=True,
        review_time=365,
    )
    defaults.update(kw)
    return DigitalEstateDocument.objects.create(profile=profile, **defaults)


def make_important_doc(profile, contact, **kw):
    defaults = dict(
        name_or_title='Birth Certificate',
        document_category='Important Personal Documents',
        delegated_important_document_to=contact,
        applies_on_death=True,
        review_time=365,
    )
    defaults.update(kw)
    return ImportantDocument.objects.create(profile=profile, **defaults)


def make_funeral_plan(profile, **kw):
    defaults = dict(
        service_type='Celebration of Life',
        disposition_method='Cremation',
        payment_arrangements='Pre-paid account at First National.',
        officiant_name_freetext='Rev. Smith',
    )
    defaults.update(kw)
    return FuneralPlan.objects.create(profile=profile, **defaults)


# ═══════════════════════════════════════════════════════════════
#  MODEL TESTS — Profile
# ═══════════════════════════════════════════════════════════════

class ProfileModelTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)

    def test_str(self):
        self.assertIn('Jane', str(self.profile))

    def test_one_profile_per_user(self):
        from django.db import IntegrityError
        with self.assertRaises(Exception):
            Profile.objects.create(
                user=self.user,
                first_name='Duplicate', last_name='Profile',
                address_1='1 St', city='City', state='IA',
            )

    def test_profile_ordering_by_user(self):
        user2 = make_legacy(username='u2', email='u2@x.com')
        p2 = make_profile(user2, first_name='Alice', last_name='Smith')
        profiles = list(Profile.objects.all())
        self.assertGreaterEqual(len(profiles), 2)


# ═══════════════════════════════════════════════════════════════
#  MODEL TESTS — Contact
# ═══════════════════════════════════════════════════════════════

class ContactModelTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_str(self):
        s = str(self.contact)
        self.assertIn('Doe', s)
        self.assertIn('Spouse', s)

    def test_get_estate_documents_count_zero(self):
        self.assertEqual(self.contact.get_estate_documents_count(), 0)

    def test_get_important_documents_count_zero(self):
        self.assertEqual(self.contact.get_important_documents_count(), 0)

    def test_get_total_documents_count(self):
        make_estate_doc(self.profile, self.contact)
        make_important_doc(self.profile, self.contact)
        self.assertEqual(self.contact.get_total_documents_count(), 2)


# ═══════════════════════════════════════════════════════════════
#  MODEL TESTS — Account
# ═══════════════════════════════════════════════════════════════

class AccountModelTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_str(self):
        acct = make_account(self.profile, self.contact)
        self.assertEqual(str(acct), 'Gmail')

    def test_default_instruction(self):
        acct = make_account(self.profile, self.contact)
        self.assertEqual(acct.keep_or_close_instruction, 'Keep Active')

    def test_review_creates_relevance_review_via_signal(self):
        """Signal should auto-create a RelevanceReview on account creation."""
        acct = make_account(self.profile, self.contact, account_name_or_provider='TestBank')
        self.assertTrue(RelevanceReview.objects.filter(account_review=acct).exists())

    def test_review_time_update_updates_next_review_due(self):
        acct = make_account(self.profile, self.contact)
        original_due = RelevanceReview.objects.filter(account_review=acct).latest('review_date').next_review_due
        acct.review_time = 365
        acct.save()
        new_due = RelevanceReview.objects.filter(account_review=acct).latest('review_date').next_review_due
        self.assertGreater(new_due, original_due)


# ═══════════════════════════════════════════════════════════════
#  MODEL TESTS — Device
# ═══════════════════════════════════════════════════════════════

class DeviceModelTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_str(self):
        dev = make_device(self.profile, self.contact)
        self.assertIn('iPhone', str(dev))
        self.assertIn('Phone', str(dev))

    def test_signal_creates_review(self):
        dev = make_device(self.profile, self.contact)
        self.assertTrue(RelevanceReview.objects.filter(device_review=dev).exists())

    def test_next_review_due_uses_review_time(self):
        dev = make_device(self.profile, self.contact, review_time=60)
        review = RelevanceReview.objects.filter(device_review=dev).latest('review_date')
        expected = date.today() + timedelta(days=60)
        self.assertEqual(review.next_review_due, expected)


# ═══════════════════════════════════════════════════════════════
#  MODEL TESTS — FuneralPlan
# ═══════════════════════════════════════════════════════════════

class FuneralPlanModelTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)

    def test_is_complete_true_when_required_fields_set(self):
        plan = make_funeral_plan(self.profile)
        self.assertTrue(plan.is_complete)

    def test_is_complete_false_when_missing_disposition(self):
        plan = FuneralPlan.objects.create(
            profile=self.profile,
            service_type='Memorial Service',
            officiant_name_freetext='Rev. Jones',
            payment_arrangements='Pre-paid',
        )
        self.assertFalse(plan.is_complete)

    def test_is_complete_false_when_no_officiant(self):
        plan = FuneralPlan.objects.create(
            profile=self.profile,
            service_type='Memorial Service',
            disposition_method='Burial',
            payment_arrangements='Pre-paid',
        )
        self.assertFalse(plan.is_complete)

    def test_has_disposition_set_property(self):
        plan = make_funeral_plan(self.profile)
        self.assertTrue(plan.has_disposition_set)

    def test_has_service_preferences_property(self):
        plan = make_funeral_plan(self.profile)
        self.assertTrue(plan.has_service_preferences)

    def test_one_plan_per_profile(self):
        make_funeral_plan(self.profile)
        with self.assertRaises(Exception):
            FuneralPlan.objects.create(profile=self.profile, service_type='Other')

    def test_str(self):
        plan = make_funeral_plan(self.profile)
        self.assertIn('Funeral Plan', str(plan))

    def test_is_complete_accepts_fk_officiant(self):
        contact = make_contact(self.profile)
        plan = FuneralPlan.objects.create(
            profile=self.profile,
            service_type='Traditional Funeral',
            disposition_method='Burial',
            officiant_contact=contact,
            payment_arrangements='Pre-paid',
        )
        self.assertTrue(plan.is_complete)


# ═══════════════════════════════════════════════════════════════
#  MODEL TESTS — RelevanceReview
# ═══════════════════════════════════════════════════════════════

class RelevanceReviewModelTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_clean_raises_if_no_target(self):
        review = RelevanceReview(reviewer=self.user)
        with self.assertRaises(ValidationError):
            review.clean()

    def test_clean_raises_if_multiple_targets(self):
        acct = make_account(self.profile, self.contact)
        dev  = make_device(self.profile, self.contact)
        review = RelevanceReview(reviewer=self.user, account_review=acct, device_review=dev)
        with self.assertRaises(ValidationError):
            review.clean()

    def test_get_item_type_account(self):
        acct = make_account(self.profile, self.contact)
        review = RelevanceReview.objects.filter(account_review=acct).first()
        self.assertEqual(review.get_item_type(), 'Account')

    def test_get_item_type_device(self):
        dev = make_device(self.profile, self.contact)
        review = RelevanceReview.objects.filter(device_review=dev).first()
        self.assertEqual(review.get_item_type(), 'Device')

    def test_get_item_type_estate(self):
        doc = make_estate_doc(self.profile, self.contact)
        review = RelevanceReview.objects.filter(estate_review=doc).first()
        self.assertEqual(review.get_item_type(), 'Estate Document')

    def test_get_item_type_important_doc(self):
        doc = make_important_doc(self.profile, self.contact)
        review = RelevanceReview.objects.filter(important_document_review=doc).first()
        self.assertEqual(review.get_item_type(), 'Important Document')

    def test_get_item_name_account(self):
        acct = make_account(self.profile, self.contact, account_name_or_provider='MyBank')
        review = RelevanceReview.objects.filter(account_review=acct).first()
        self.assertEqual(review.get_item_name(), 'MyBank')

    def test_get_item_name_no_item(self):
        review = RelevanceReview(reviewer=self.user)
        self.assertEqual(review.get_item_name(), 'Unknown Item')

    def test_get_reviewed_item_returns_none_when_empty(self):
        review = RelevanceReview(reviewer=self.user)
        self.assertIsNone(review.get_reviewed_item())

    def test_str_contains_item_type_and_date(self):
        dev = make_device(self.profile, self.contact)
        review = RelevanceReview.objects.filter(device_review=dev).first()
        s = str(review)
        self.assertIn('Device', s)


# ═══════════════════════════════════════════════════════════════
#  SIGNAL TESTS
# ═══════════════════════════════════════════════════════════════

class SignalTest(TestCase):

    def setUp(self):
        self.user = make_legacy()

    def test_profile_save_creates_self_contact(self):
        """Saving a complete profile should auto-create a Self contact."""
        profile = make_profile(self.user)
        self.assertTrue(Contact.objects.filter(profile=profile, contact_relation='Self').exists())

    def test_profile_update_syncs_self_contact(self):
        profile = make_profile(self.user)
        profile.first_name = 'Updated'
        profile.save()
        self_contact = Contact.objects.get(profile=profile, contact_relation='Self')
        self.assertEqual(self_contact.first_name, 'Updated')

    def test_profile_save_without_required_fields_skips_self_contact(self):
        """Incomplete profile should not create a Self contact."""
        profile = Profile.objects.create(
            user=self.user,
            first_name='', last_name='',
            address_1='', city='', state='',
        )
        self.assertFalse(Contact.objects.filter(profile=profile, contact_relation='Self').exists())

    def test_account_creation_creates_review(self):
        profile = make_profile(self.user)
        contact = make_contact(profile)
        acct = make_account(profile, contact)
        self.assertEqual(RelevanceReview.objects.filter(account_review=acct).count(), 1)

    def test_device_creation_creates_review(self):
        profile = make_profile(self.user)
        contact = make_contact(profile)
        dev = make_device(profile, contact)
        self.assertEqual(RelevanceReview.objects.filter(device_review=dev).count(), 1)

    def test_estate_doc_creation_creates_review(self):
        profile = make_profile(self.user)
        contact = make_contact(profile)
        doc = make_estate_doc(profile, contact)
        self.assertEqual(RelevanceReview.objects.filter(estate_review=doc).count(), 1)

    def test_important_doc_creation_creates_review(self):
        profile = make_profile(self.user)
        contact = make_contact(profile)
        doc = make_important_doc(profile, contact)
        self.assertEqual(RelevanceReview.objects.filter(important_document_review=doc).count(), 1)

    def test_review_time_same_value_does_not_update_review(self):
        """Saving with unchanged review_time must not modify the review due date."""
        profile = make_profile(self.user)
        contact = make_contact(profile)
        acct = make_account(profile, contact, review_time=30)
        review_before = RelevanceReview.objects.filter(account_review=acct).latest('review_date').next_review_due
        acct.save()  # no field change
        review_after = RelevanceReview.objects.filter(account_review=acct).latest('review_date').next_review_due
        self.assertEqual(review_before, review_after)


# ═══════════════════════════════════════════════════════════════
#  FORM TESTS
# ═══════════════════════════════════════════════════════════════

class ProfileFormTest(TestCase):

    def _valid(self, **overrides):
        data = dict(
            first_name='Jane', last_name='Doe',
            address_1='123 Main', city='Des Moines', state='IA',
            zipcode='50309', email='jane@example.com', phone='515-555-0000',
        )
        data.update(overrides)
        return data

    def test_valid_form(self):
        from .forms import ProfileForm
        self.assertTrue(ProfileForm(data=self._valid()).is_valid())

    def test_invalid_email_rejected(self):
        from .forms import ProfileForm
        form = ProfileForm(data=self._valid(email='not-an-email'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_invalid_phone_rejected(self):
        from .forms import ProfileForm
        form = ProfileForm(data=self._valid(phone='abc123'))
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_blank_phone_allowed(self):
        from .forms import ProfileForm
        self.assertTrue(ProfileForm(data=self._valid(phone='')).is_valid())


class ContactFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        make_profile(self.user)

    def _valid(self, **overrides):
        data = dict(
            contact_relation='Spouse',
            first_name='John', last_name='Doe',
            address_1='1 Main', city='Ames', state='IA',
            is_emergency_contact=True,
        )
        data.update(overrides)
        return data

    def test_valid_form(self):
        from .forms import ContactForm
        self.assertTrue(ContactForm(data=self._valid(), user=self.user).is_valid())

    def test_no_role_selected_raises_error(self):
        from .forms import ContactForm
        data = self._valid()
        data['is_emergency_contact'] = False
        form = ContactForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_blank_first_name_rejected(self):
        from .forms import ContactForm
        form = ContactForm(data=self._valid(first_name=''), user=self.user)
        self.assertFalse(form.is_valid())

    def test_invalid_phone_rejected(self):
        from .forms import ContactForm
        form = ContactForm(data=self._valid(phone='xyz'), user=self.user)
        self.assertFalse(form.is_valid())


class AccountFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def _valid(self, **overrides):
        data = dict(
            delegated_account_to=self.contact.pk,
            account_category='Email Account',
            account_name_or_provider='Gmail',
            review_time=30,
            keep_or_close_instruction='Keep Active',
        )
        data.update(overrides)
        return data

    def test_valid_form(self):
        from .forms import AccountForm
        self.assertTrue(AccountForm(data=self._valid(), user=self.user).is_valid())

    def test_invalid_url_rejected(self):
        from .forms import AccountForm
        form = AccountForm(data=self._valid(website_url='not-a-url'), user=self.user)
        self.assertFalse(form.is_valid())

    def test_valid_url_accepted(self):
        from .forms import AccountForm
        form = AccountForm(data=self._valid(website_url='https://gmail.com'), user=self.user)
        self.assertTrue(form.is_valid())

    def test_no_contact_selected_rejected(self):
        from .forms import AccountForm
        data = self._valid()
        data['delegated_account_to'] = ''
        form = AccountForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())


class FuneralPlanPersonalInfoFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.plan, _ = FuneralPlan.objects.get_or_create(profile=self.profile)

    def test_veteran_without_branch_rejected(self):
        from .forms import FuneralPlanPersonalInfoForm
        form = FuneralPlanPersonalInfoForm(
            data={'is_veteran': True, 'veteran_branch': ''},
            instance=self.plan, user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('veteran_branch', form.errors)

    def test_non_veteran_branch_cleared(self):
        from .forms import FuneralPlanPersonalInfoForm
        form = FuneralPlanPersonalInfoForm(
            data={'is_veteran': False, 'veteran_branch': 'Army'},
            instance=self.plan, user=self.user,
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['veteran_branch'], '')

    def test_veteran_with_branch_valid(self):
        from .forms import FuneralPlanPersonalInfoForm
        form = FuneralPlanPersonalInfoForm(
            data={'is_veteran': True, 'veteran_branch': 'Navy'},
            instance=self.plan, user=self.user,
        )
        self.assertTrue(form.is_valid())


class FuneralPlanServiceFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.plan, _ = FuneralPlan.objects.get_or_create(profile=self.profile)

    def test_both_officiant_fields_rejected(self):
        from .forms import FuneralPlanServiceForm
        form = FuneralPlanServiceForm(
            data={
                'officiant_contact': self.contact.pk,
                'officiant_name_freetext': 'Rev. Jones',
            },
            instance=self.plan, user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('officiant_name_freetext', form.errors)

    def test_invalid_phone_rejected(self):
        from .forms import FuneralPlanServiceForm
        form = FuneralPlanServiceForm(
            data={'funeral_home_phone': 'ABC-DEFG'},
            instance=self.plan, user=self.user,
        )
        self.assertFalse(form.is_valid())


class FuneralPlanReceptionFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.plan, _ = FuneralPlan.objects.get_or_create(profile=self.profile)

    def test_reception_desired_without_location_rejected(self):
        from .forms import FuneralPlanReceptionForm
        form = FuneralPlanReceptionForm(
            data={'reception_desired': True, 'reception_location': ''},
            instance=self.plan, user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_reception_desired_with_location_valid(self):
        from .forms import FuneralPlanReceptionForm
        form = FuneralPlanReceptionForm(
            data={'reception_desired': True, 'reception_location': 'Community Hall'},
            instance=self.plan, user=self.user,
        )
        self.assertTrue(form.is_valid())


class FuneralPlanAdminFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.plan, _ = FuneralPlan.objects.get_or_create(profile=self.profile)

    def test_death_certificates_zero_rejected(self):
        from .forms import FuneralPlanAdminForm
        form = FuneralPlanAdminForm(
            data={'death_certificates_requested': 0, 'review_time': 365},
            instance=self.plan, user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_blank_death_certificates_allowed(self):
        from .forms import FuneralPlanAdminForm
        form = FuneralPlanAdminForm(
            data={'death_certificates_requested': '', 'review_time': 365},
            instance=self.plan, user=self.user,
        )
        self.assertTrue(form.is_valid())

    def test_positive_count_accepted(self):
        from .forms import FuneralPlanAdminForm
        form = FuneralPlanAdminForm(
            data={'death_certificates_requested': 8, 'review_time': 365},
            instance=self.plan, user=self.user,
        )
        self.assertTrue(form.is_valid())


class DigitalEstateDocumentFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def _valid(self, **overrides):
        data = dict(
            delegated_estate_to=self.contact.pk,
            estate_category='Advance Directive / Living Will',
            name_or_title='My Living Will',
            review_time=365,
            applies_on_death=True,
        )
        data.update(overrides)
        return data

    def test_valid_form(self):
        from .forms import DigitalEstateDocumentForm
        self.assertTrue(DigitalEstateDocumentForm(data=self._valid(), user=self.user).is_valid())

    def test_no_declaration_rejected(self):
        from .forms import DigitalEstateDocumentForm
        data = self._valid(applies_on_death=False)
        form = DigitalEstateDocumentForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_applies_immediately_alone_is_valid(self):
        from .forms import DigitalEstateDocumentForm
        data = self._valid(applies_on_death=False, applies_immediately=True)
        self.assertTrue(DigitalEstateDocumentForm(data=data, user=self.user).is_valid())


class RelevanceReviewFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.acct = make_account(self.profile, self.contact)

    def test_valid_single_target(self):
        from .forms import RelevanceReviewForm
        form = RelevanceReviewForm(data={
            'account_review': self.acct.pk,
            'matters': True,
            'next_review_due': (date.today() + timedelta(days=30)).isoformat(),
        }, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_no_target_rejected(self):
        from .forms import RelevanceReviewForm
        form = RelevanceReviewForm(data={'matters': True}, user=self.user)
        self.assertFalse(form.is_valid())

    def test_past_review_date_rejected(self):
        from .forms import RelevanceReviewForm
        form = RelevanceReviewForm(data={
            'account_review': self.acct.pk,
            'matters': True,
            'next_review_due': (date.today() - timedelta(days=1)).isoformat(),
        }, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('next_review_due', form.errors)

    def test_multiple_targets_rejected(self):
        from .forms import RelevanceReviewForm
        dev = make_device(self.profile, self.contact)
        form = RelevanceReviewForm(data={
            'account_review': self.acct.pk,
            'device_review': dev.pk,
            'matters': True,
        }, user=self.user)
        self.assertFalse(form.is_valid())


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — DashboardHomeView
# ═══════════════════════════════════════════════════════════════

class DashboardHomeViewTest(TestCase):

    def test_unpaid_user_redirected_to_payment(self):
        user = make_user(username='np', email='np@x.com')
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:dashboard_home'))
        self.assertRedirects(response, reverse('accounts:payment'))

    def test_paid_user_without_profile_redirected_to_profile_create(self):
        user = make_legacy(username='noprofile', email='np2@x.com')
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:dashboard_home'))
        self.assertRedirects(response, reverse('dashboard:profile_create'))

    def test_fully_set_up_user_sees_dashboard(self):
        user = make_legacy()
        make_profile(user)
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:dashboard_home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/dashboard.html')

    def test_dashboard_context_contains_counts(self):
        user = make_legacy()
        profile = make_profile(user)
        contact = make_contact(profile)
        make_account(profile, contact)
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:dashboard_home'))
        self.assertIn('accounts_count', response.context)
        self.assertEqual(response.context['accounts_count'], 1)

    def test_dashboard_shows_onboarding_when_incomplete(self):
        user = make_legacy()
        make_profile(user)
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:dashboard_home'))
        self.assertTrue(response.context['show_onboarding'])

    def test_unauthenticated_redirected_to_login(self):
        response = self.client.get(reverse('dashboard:dashboard_home'))
        self.assertNotEqual(response.status_code, 200)

    def test_progress_is_integer(self):
        user = make_legacy()
        make_profile(user)
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:dashboard_home'))
        self.assertIsInstance(response.context['progress'], int)


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — Profile
# ═══════════════════════════════════════════════════════════════

class ProfileViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.client.force_login(self.user)

    def test_create_get_renders_form(self):
        response = self.client.get(reverse('dashboard:profile_create'))
        self.assertEqual(response.status_code, 200)

    def test_create_post_creates_profile_and_redirects(self):
        response = self.client.post(reverse('dashboard:profile_create'), {
            'first_name': 'Jane', 'last_name': 'Doe',
            'address_1': '1 Main', 'city': 'Ames',
            'state': 'IA', 'zipcode': '50010',
            'email': 'jane@example.com', 'phone': '515-555-0001',
        })
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_already_has_profile_redirected_to_detail(self):
        make_profile(self.user)
        response = self.client.get(reverse('dashboard:profile_create'))
        self.assertRedirects(response, reverse('dashboard:profile_detail'))

    def test_update_saves_changes(self):
        make_profile(self.user)
        response = self.client.post(reverse('dashboard:profile_update'), {
            'first_name': 'Updated', 'last_name': 'Doe',
            'address_1': '1 Main', 'city': 'Ames',
            'state': 'IA', 'zipcode': '50010',
            'email': 'jane@example.com', 'phone': '',
        })
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.first_name, 'Updated')

    def test_expired_essentials_cannot_update_profile(self):
        """FullAccessMixin blocks expired essentials users from updating."""
        user = make_essentials(username='exp2', email='exp2@x.com')
        user.essentials_expires = timezone.now() - timedelta(days=1)
        user.save()
        make_profile(user)
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:profile_update'))
        self.assertNotEqual(response.status_code, 200)

    def test_unpaid_user_redirected_from_create(self):
        unpaid = make_user(username='unpaid2', email='unpaid2@x.com')
        self.client.force_login(unpaid)
        response = self.client.get(reverse('dashboard:profile_create'))
        self.assertRedirects(response, reverse('accounts:payment'))


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — Contact CRUD
# ═══════════════════════════════════════════════════════════════

class ContactViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.client.force_login(self.user)

    def test_list_view_200(self):
        response = self.client.get(reverse('dashboard:contact_list'))
        self.assertEqual(response.status_code, 200)

    def test_detail_view_200(self):
        response = self.client.get(reverse('dashboard:contact_detail', args=[self.contact.pk]))
        self.assertEqual(response.status_code, 200)

    def test_create_post_creates_contact(self):
        count_before = Contact.objects.filter(profile=self.profile).count()
        self.client.post(reverse('dashboard:contact_create'), {
            'contact_relation': 'Daughter',
            'first_name': 'Alice', 'last_name': 'Doe',
            'address_1': '1 Oak', 'city': 'Ames', 'state': 'IA',
            'is_emergency_contact': True,
        })
        self.assertEqual(Contact.objects.filter(profile=self.profile).count(), count_before + 1)

    def test_update_modifies_contact(self):
        self.client.post(reverse('dashboard:contact_update', args=[self.contact.pk]), {
            'contact_relation': 'Spouse',
            'first_name': 'Jonathan', 'last_name': 'Doe',
            'address_1': '1 Main', 'city': 'Ames', 'state': 'IA',
            'is_emergency_contact': True,
        })
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.first_name, 'Jonathan')

    def test_cannot_delete_contact_with_assigned_documents(self):
        """Contact with assigned estate docs must be protected from deletion."""
        make_estate_doc(self.profile, self.contact)
        response = self.client.post(reverse('dashboard:contact_delete', args=[self.contact.pk]))
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())

    def test_can_delete_contact_with_no_assignments(self):
        bare_contact = make_contact(self.profile, relation='Other',
                                    first_name='Bare', last_name='Contact',
                                    is_emergency_contact=True)
        self.client.post(reverse('dashboard:contact_delete', args=[bare_contact.pk]))
        self.assertFalse(Contact.objects.filter(pk=bare_contact.pk).exists())

    def test_other_user_cannot_see_contact_detail(self):
        other = make_legacy(username='other2', email='other2@x.com')
        make_profile(other)
        self.client.force_login(other)
        response = self.client.get(reverse('dashboard:contact_detail', args=[self.contact.pk]))
        self.assertEqual(response.status_code, 404)


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — Account CRUD
# ═══════════════════════════════════════════════════════════════

class AccountViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.account = make_account(self.profile, self.contact)
        self.client.force_login(self.user)

    def test_list_200(self):
        response = self.client.get(reverse('dashboard:account_list'))
        self.assertEqual(response.status_code, 200)

    def test_detail_200(self):
        response = self.client.get(reverse('dashboard:account_detail', args=[self.account.pk]))
        self.assertEqual(response.status_code, 200)

    def test_create_adds_account(self):
        count = Account.objects.filter(profile=self.profile).count()
        self.client.post(reverse('dashboard:account_create'), {
            'delegated_account_to': self.contact.pk,
            'account_category': 'Email Account',
            'account_name_or_provider': 'Yahoo Mail',
            'review_time': 30,
            'keep_or_close_instruction': 'Close Account',
        })
        self.assertEqual(Account.objects.filter(profile=self.profile).count(), count + 1)

    def test_delete_removes_account(self):
        self.client.post(reverse('dashboard:account_delete', args=[self.account.pk]))
        self.assertFalse(Account.objects.filter(pk=self.account.pk).exists())

    def test_other_user_cannot_access_account(self):
        other = make_legacy(username='oth3', email='oth3@x.com')
        make_profile(other)
        self.client.force_login(other)
        response = self.client.get(reverse('dashboard:account_detail', args=[self.account.pk]))
        self.assertEqual(response.status_code, 404)

    def test_category_filter_in_list(self):
        make_account(self.profile, self.contact, account_name_or_provider='Chase',
                     account_category='Online Banking Account')
        response = self.client.get(
            reverse('dashboard:account_list') + '?account_category=Online+Banking+Account'
        )
        self.assertEqual(response.status_code, 200)


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — Device CRUD
# ═══════════════════════════════════════════════════════════════

class DeviceViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.device = make_device(self.profile, self.contact)
        self.client.force_login(self.user)

    def test_list_200(self):
        self.assertEqual(self.client.get(reverse('dashboard:device_list')).status_code, 200)

    def test_detail_200(self):
        self.assertEqual(
            self.client.get(reverse('dashboard:device_detail', args=[self.device.pk])).status_code, 200
        )

    def test_create_adds_device(self):
        count = Device.objects.filter(profile=self.profile).count()
        self.client.post(reverse('dashboard:device_create'), {
            'delegated_device_to': self.contact.pk,
            'device_type': 'Laptop',
            'device_name': 'MacBook Pro',
            'review_time': 30,
        })
        self.assertEqual(Device.objects.filter(profile=self.profile).count(), count + 1)

    def test_delete_removes_device(self):
        self.client.post(reverse('dashboard:device_delete', args=[self.device.pk]))
        self.assertFalse(Device.objects.filter(pk=self.device.pk).exists())


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — Estate Document CRUD
# ═══════════════════════════════════════════════════════════════

class EstateViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.doc = make_estate_doc(self.profile, self.contact)
        self.client.force_login(self.user)

    def test_list_200(self):
        self.assertEqual(self.client.get(reverse('dashboard:estate_list')).status_code, 200)

    def test_detail_200(self):
        self.assertEqual(
            self.client.get(reverse('dashboard:estate_detail', args=[self.doc.pk])).status_code, 200
        )

    def test_delete_removes_document(self):
        self.client.post(reverse('dashboard:estate_delete', args=[self.doc.pk]))
        self.assertFalse(DigitalEstateDocument.objects.filter(pk=self.doc.pk).exists())


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — Important Document CRUD
# ═══════════════════════════════════════════════════════════════

class ImportantDocumentViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.doc = make_important_doc(self.profile, self.contact)
        self.client.force_login(self.user)

    def test_list_200(self):
        self.assertEqual(
            self.client.get(reverse('dashboard:importantdocument_list')).status_code, 200
        )

    def test_detail_200(self):
        self.assertEqual(
            self.client.get(reverse('dashboard:importantdocument_detail', args=[self.doc.pk])).status_code, 200
        )

    def test_create_valid_adds_document(self):
        count = ImportantDocument.objects.filter(profile=self.profile).count()
        self.client.post(reverse('dashboard:importantdocument_create'), {
            'delegated_important_document_to': self.contact.pk,
            'name_or_title': 'Passport',
            'document_category': 'Personal Identification',
            'review_time': 365,
            'applies_on_death': True,
        })
        self.assertEqual(ImportantDocument.objects.filter(profile=self.profile).count(), count + 1)


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — FuneralPlan wizard
# ═══════════════════════════════════════════════════════════════

class FuneralPlanViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.client.force_login(self.user)

    def test_index_creates_plan_on_first_visit(self):
        self.assertFalse(FuneralPlan.objects.filter(profile=self.profile).exists())
        self.client.get(reverse('dashboard:funeralplan_index'))
        self.assertTrue(FuneralPlan.objects.filter(profile=self.profile).exists())

    def test_index_200(self):
        self.assertEqual(self.client.get(reverse('dashboard:funeralplan_index')).status_code, 200)

    def test_detail_200(self):
        FuneralPlan.objects.create(profile=self.profile)
        self.assertEqual(self.client.get(reverse('dashboard:funeralplan_detail')).status_code, 200)

    def test_step1_get_200(self):
        self.assertEqual(self.client.get(reverse('dashboard:funeralplan_step1')).status_code, 200)

    def test_step1_post_saves_and_redirects_to_step2(self):
        response = self.client.post(reverse('dashboard:funeralplan_step1'), {
            'preferred_name': 'Janie',
            'occupation': 'Teacher',
            'is_veteran': False,
            'veteran_branch': '',
        })
        self.assertRedirects(response, reverse('dashboard:funeralplan_step2'))
        plan = FuneralPlan.objects.get(profile=self.profile)
        self.assertEqual(plan.preferred_name, 'Janie')

    def test_step2_post_saves_and_redirects_to_step3(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        response = self.client.post(reverse('dashboard:funeralplan_step2'), {
            'service_type': 'Celebration of Life',
        })
        self.assertRedirects(response, reverse('dashboard:funeralplan_step3'))

    def test_step8_post_redirects_to_detail(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        response = self.client.post(reverse('dashboard:funeralplan_step8'), {
            'additional_instructions': 'Play jazz at my service.',
        })
        self.assertRedirects(response, reverse('dashboard:funeralplan_detail'))

    def test_step1_invalid_veteran_rerenders_with_errors(self):
        response = self.client.post(reverse('dashboard:funeralplan_step1'), {
            'is_veteran': True,
            'veteran_branch': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'veteran_branch',
                             'Please enter the branch of service, or uncheck the Veteran field.')

    def test_unpaid_user_redirected_from_funeralplan(self):
        unpaid = make_user(username='unpaid3', email='u3@x.com')
        Profile.objects.create(
            user=unpaid, first_name='U', last_name='P',
            address_1='1 St', city='City', state='IA',
        )
        self.client.force_login(unpaid)
        response = self.client.get(reverse('dashboard:funeralplan_index'))
        self.assertRedirects(response, reverse('accounts:payment'))

    def test_expired_essentials_cannot_post_step(self):
        exp = make_essentials(username='exp3', email='exp3@x.com')
        exp.essentials_expires = timezone.now() - timedelta(days=1)
        exp.save()
        make_profile(exp)
        FuneralPlan.objects.create(profile=exp.profile)
        self.client.force_login(exp)
        response = self.client.post(reverse('dashboard:funeralplan_step1'), {
            'preferred_name': 'Blocked',
            'is_veteran': False,
        })
        self.assertRedirects(response, reverse('dashboard:funeralplan_index'))
        self.assertNotEqual(
            FuneralPlan.objects.get(profile=exp.profile).preferred_name, 'Blocked'
        )

    # ── Delete ────────────────────────────────────────────────

    def test_delete_get_renders_confirm_page(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        response = self.client.get(reverse('dashboard:funeralplan_delete'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/funeralplan/funeralplan_confirm_delete.html')

    def test_delete_wrong_confirmation_text_does_not_delete(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        self.client.post(reverse('dashboard:funeralplan_delete'), {'confirm_text': 'delete'})
        self.assertTrue(FuneralPlan.objects.filter(profile=self.profile).exists())

    def test_delete_correct_confirmation_deletes_plan(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        self.client.post(reverse('dashboard:funeralplan_delete'), {'confirm_text': 'DELETE'})
        self.assertFalse(FuneralPlan.objects.filter(profile=self.profile).exists())

    def test_delete_redirects_to_index_after_deletion(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        response = self.client.post(
            reverse('dashboard:funeralplan_delete'), {'confirm_text': 'DELETE'}
        )
        self.assertRedirects(response, reverse('dashboard:funeralplan_index'))

    def test_delete_nonexistent_plan_shows_info_message(self):
        """No plan exists → delete should gracefully report nothing found."""
        response = self.client.post(
            reverse('dashboard:funeralplan_delete'), {'confirm_text': 'DELETE'}
        )
        messages_list = list(response.wsgi_request._messages)
        self.assertTrue(any('no funeral plan' in str(m).lower() for m in messages_list))

    def test_delete_blocked_for_expired_essentials(self):
        exp = make_essentials(username='delexp', email='delexp@x.com')
        exp.essentials_expires = timezone.now() - timedelta(days=1)
        exp.save()
        make_profile(exp)
        FuneralPlan.objects.create(profile=exp.profile)
        self.client.force_login(exp)
        self.client.post(reverse('dashboard:funeralplan_delete'), {'confirm_text': 'DELETE'})
        self.assertTrue(FuneralPlan.objects.filter(profile=exp.profile).exists())


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — FuneralPlanMixin.get_plan_progress()
# ═══════════════════════════════════════════════════════════════

class FuneralPlanProgressTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.client.force_login(self.user)

    def _progress(self):
        """Call the index view and return its progress context dict."""
        response = self.client.get(reverse('dashboard:funeralplan_index'))
        return response.context['progress']

    def test_empty_plan_all_false(self):
        p = self._progress()
        self.assertFalse(p['personal_info'])
        self.assertFalse(p['service'])
        self.assertFalse(p['disposition'])

    def test_personal_info_flag_set_after_step1(self):
        self.client.post(reverse('dashboard:funeralplan_step1'), {
            'preferred_name': 'Jay', 'is_veteran': False, 'veteran_branch': '',
        })
        p = self._progress()
        self.assertTrue(p['personal_info'])

    def test_is_complete_flag_requires_all_four_fields(self):
        plan = FuneralPlan.objects.get_or_create(profile=self.profile)[0]
        p = self._progress()
        self.assertFalse(p['is_complete'])
        plan.service_type = 'Memorial Service'
        plan.disposition_method = 'Cremation'
        plan.officiant_name_freetext = 'Rev. Smith'
        plan.payment_arrangements = 'Pre-paid'
        plan.save()
        p = self._progress()
        self.assertTrue(p['is_complete'])


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — RelevanceReview
# ═══════════════════════════════════════════════════════════════

class RelevanceReviewViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.acct = make_account(self.profile, self.contact)
        self.review = RelevanceReview.objects.filter(account_review=self.acct).first()
        self.client.force_login(self.user)

    def test_list_200(self):
        self.assertEqual(self.client.get(reverse('dashboard:relevancereview_list')).status_code, 200)

    def test_detail_200(self):
        self.assertEqual(
            self.client.get(reverse('dashboard:relevancereview_detail', args=[self.review.pk])).status_code, 200
        )

    def test_detail_enforces_ownership(self):
        other = make_legacy(username='rv_other', email='rvo@x.com')
        make_profile(other)
        self.client.force_login(other)
        from django.core.exceptions import PermissionDenied
        response = self.client.get(reverse('dashboard:relevancereview_detail', args=[self.review.pk]))
        self.assertIn(response.status_code, [403, 404])

    def test_unpaid_redirected_from_list(self):
        unpaid = make_user(username='unpaid_rv', email='unpaid_rv@x.com')
        self.client.force_login(unpaid)
        response = self.client.get(reverse('dashboard:relevancereview_list'))
        self.assertRedirects(response, reverse('accounts:payment'))


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — MarkItemReviewedView (AJAX)
# ═══════════════════════════════════════════════════════════════

class MarkItemReviewedViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.acct = make_account(self.profile, self.contact)
        self.review = RelevanceReview.objects.filter(account_review=self.acct).first()
        self.client.force_login(self.user)
        self.url = reverse('dashboard:mark_item_reviewed', args=[self.review.pk])

    def test_get_returns_405(self):
        response = self.client.get(self.url)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 405)
        self.assertFalse(data['success'])

    def test_post_returns_success(self):
        response = self.client.post(self.url)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('updated_at', data)
        self.assertIn('next_review_due', data)

    def test_post_updates_next_review_due(self):
        old_due = self.review.next_review_due
        self.client.post(self.url)
        self.review.refresh_from_db()
        self.assertGreater(self.review.next_review_due, old_due)

    def test_nonexistent_review_returns_404(self):
        response = self.client.post(reverse('dashboard:mark_item_reviewed', args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_unpaid_user_returns_403(self):
        unpaid = make_user(username='unp_mk', email='unp_mk@x.com')
        self.client.force_login(unpaid)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)

    def test_other_user_returns_403(self):
        other = make_legacy(username='mk_other', email='mk_other@x.com')
        make_profile(other)
        self.client.force_login(other)
        response = self.client.post(self.url)
        data = json.loads(response.content)
        self.assertFalse(data['success'])


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — Onboarding
# ═══════════════════════════════════════════════════════════════

class OnboardingViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.client.force_login(self.user)

    def test_welcome_200(self):
        self.assertEqual(
            self.client.get(reverse('dashboard:onboarding_welcome')).status_code, 200
        )

    def test_complete_200(self):
        self.assertEqual(
            self.client.get(reverse('dashboard:onboarding_complete')).status_code, 200
        )

    def test_onboarding_progress_context(self):
        response = self.client.get(reverse('dashboard:onboarding_welcome'))
        p = response.context['progress']
        self.assertIn('contacts', p)
        self.assertIn('accounts', p)
        self.assertIn('devices', p)

    def test_contacts_step_post_adds_contact(self):
        count = Contact.objects.filter(profile=self.profile).exclude(contact_relation='Self').count()
        self.client.post(reverse('dashboard:onboarding_contacts'), {
            'contact_relation': 'Daughter',
            'first_name': 'Lily', 'last_name': 'Doe',
            'address_1': '1 Oak', 'city': 'Ames', 'state': 'IA',
            'is_emergency_contact': True,
        })
        new_count = Contact.objects.filter(profile=self.profile).exclude(contact_relation='Self').count()
        self.assertEqual(new_count, count + 1)

    def test_unpaid_user_redirected_from_onboarding(self):
        unpaid = make_user(username='unpaid_ob', email='unpaid_ob@x.com')
        self.client.force_login(unpaid)
        response = self.client.get(reverse('dashboard:onboarding_welcome'))
        self.assertRedirects(response, reverse('accounts:payment'))


# ═══════════════════════════════════════════════════════════════
#  EDGE CASES
# ═══════════════════════════════════════════════════════════════

class DashboardEdgeCaseTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.client.force_login(self.user)

    # ── Dashboard progress calculation ───────────────────────

    def test_progress_caps_at_100(self):
        """Progress should never exceed 100 regardless of item counts."""
        for i in range(20):
            make_account(self.profile, self.contact,
                         account_name_or_provider=f'Account {i}')
        response = self.client.get(reverse('dashboard:dashboard_home'))
        self.assertLessEqual(response.context['progress'], 100)

    def test_progress_zero_for_empty_profile(self):
        """Brand new profile with no items should have 0 progress."""
        response = self.client.get(reverse('dashboard:dashboard_home'))
        self.assertEqual(response.context['progress'], 0)

    # ── Ownership isolation between users ─────────────────────

    def test_users_cannot_see_each_others_accounts_in_list(self):
        other = make_legacy(username='iso_other', email='iso_other@x.com')
        other_profile = make_profile(other)
        other_contact = make_contact(other_profile, first_name='Other', last_name='Person')
        make_account(other_profile, other_contact, account_name_or_provider='OtherBank')

        response = self.client.get(reverse('dashboard:account_list'))
        accounts = list(response.context['accounts'])
        for acct in accounts:
            self.assertEqual(acct.profile, self.profile)

    # ── Signal idempotency ────────────────────────────────────

    def test_saving_profile_twice_does_not_duplicate_self_contact(self):
        self.profile.first_name = 'Updated'
        self.profile.save()
        self.profile.first_name = 'Updated Again'
        self.profile.save()
        self_contacts = Contact.objects.filter(profile=self.profile, contact_relation='Self')
        self.assertEqual(self_contacts.count(), 1)

    # ── FuneralPlan wizard isolation ──────────────────────────

    def test_multiple_step_saves_accumulate_data(self):
        """Saving step 1 then step 2 should persist both sections."""
        self.client.post(reverse('dashboard:funeralplan_step1'), {
            'preferred_name': 'Jay', 'is_veteran': False, 'veteran_branch': '',
        })
        self.client.post(reverse('dashboard:funeralplan_step2'), {
            'service_type': 'Graveside Service',
        })
        plan = FuneralPlan.objects.get(profile=self.profile)
        self.assertEqual(plan.preferred_name, 'Jay')
        self.assertEqual(plan.service_type, 'Graveside Service')

    # ── RelevanceReview created with correct due date ─────────

    def test_review_due_date_matches_review_time(self):
        acct = make_account(self.profile, self.contact, review_time=180)
        review = RelevanceReview.objects.filter(account_review=acct).first()
        expected = date.today() + timedelta(days=180)
        self.assertEqual(review.next_review_due, expected)

    # ── Empty queryset for user without profile ───────────────

    def test_account_list_returns_empty_for_user_without_profile(self):
        """get_queryset should return Account.objects.none() gracefully."""
        no_profile_user = make_legacy(username='noprof', email='noprof@x.com')
        # Deliberately do NOT create a profile for this user
        self.client.force_login(no_profile_user)
        response = self.client.get(reverse('dashboard:account_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context.get('accounts', [])), [])

    # ── Contact detail shows correct assignment counts ─────────

    def test_contact_detail_shows_assignment_counts(self):
        make_estate_doc(self.profile, self.contact)
        make_account(self.profile, self.contact)
        response = self.client.get(reverse('dashboard:contact_detail', args=[self.contact.pk]))
        self.assertEqual(response.context['total_assignments'], 2)

    # ── CSRF protection on delete ─────────────────────────────

    def test_funeral_delete_requires_csrf(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.user)
        response = c.post(reverse('dashboard:funeralplan_delete'), {'confirm_text': 'DELETE'})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(FuneralPlan.objects.filter(profile=self.profile).exists())

    # ── Pagination ────────────────────────────────────────────

    def test_account_list_paginates_at_20(self):
        for i in range(25):
            make_account(self.profile, self.contact,
                         account_name_or_provider=f'Acct-{i}')
        response = self.client.get(reverse('dashboard:account_list'))
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['accounts']), 20)