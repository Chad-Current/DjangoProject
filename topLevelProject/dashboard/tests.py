# dashboard/tests.py
"""
Comprehensive test suite for the dashboard app.

CONTACT DELETION RULE (business requirement)
============================================
A Contact CANNOT be deleted while ANY of the following records reference it:

  1. Account.delegated_account_to          (on_delete=PROTECT  — DB enforced)
  2. Device.delegated_device_to            (on_delete=PROTECT  — DB enforced)
  3. DigitalEstateDocument.delegated_estate_to
                                           (on_delete=PROTECT  — DB enforced)
  4. ImportantDocument.delegated_important_document_to
                                           (on_delete=PROTECT  — DB enforced)
  5. FamilyNeedsToKnowSection.relation     (on_delete=CASCADE  — view enforced)

The view must check the count of all five types and refuse deletion if any
total > 0.  The four PROTECT types are also enforced at the database level;
FamilyNeedsToKnowSection.relation uses CASCADE so the view must catch it
*before* the database call — once the DB deletes the contact it would silently
cascade away, but the user must explicitly clear those notes first.

Run with:
    python manage.py test dashboard --verbosity=2
"""

import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
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

def make_user(username='tuser', email='tuser@example.com',
              password='StrongPass1!', **kw):
    return User.objects.create_user(
        username=username, email=email, password=password, **kw
    )


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
    return Profile.objects.get_or_create(user=user, defaults=defaults)[0]


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


def make_family_note(contact, **kw):
    """Create a FamilyNeedsToKnowSection tied to a contact via .relation."""
    defaults = dict(
        content='Remember to check the safe.',
        is_location_of_legal_will=True,
    )
    defaults.update(kw)
    return FamilyNeedsToKnowSection.objects.create(relation=contact, **defaults)


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

    def test_str_contains_first_name(self):
        self.assertIn('Jane', str(self.profile))

    def test_one_profile_per_user_enforced(self):
        with self.assertRaises(Exception):
            Profile.objects.create(
                user=self.user,
                first_name='Duplicate', last_name='Profile',
                address_1='1 St', city='City', state='IA',
            )

    def test_profile_cascades_when_user_deleted(self):
        user2 = make_legacy(username='cascade', email='cascade@x.com')
        p2 = make_profile(user2)
        pk = p2.pk
        user2.delete()
        self.assertFalse(Profile.objects.filter(pk=pk).exists())


# ═══════════════════════════════════════════════════════════════
#  MODEL TESTS — Contact: DB-level protection
# ═══════════════════════════════════════════════════════════════

class ContactModelProtectionTest(TestCase):
    """
    Verify the on_delete=PROTECT constraints at the database layer.
    These fire regardless of the view — they are the last line of defence.
    """

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_str_contains_name_and_relation(self):
        s = str(self.contact)
        self.assertIn('Doe', s)
        self.assertIn('Spouse', s)

    def test_db_protects_contact_with_account(self):
        make_account(self.profile, self.contact)
        with self.assertRaises(ProtectedError):
            self.contact.delete()

    def test_db_protects_contact_with_device(self):
        make_device(self.profile, self.contact)
        with self.assertRaises(ProtectedError):
            self.contact.delete()

    def test_db_protects_contact_with_estate_document(self):
        make_estate_doc(self.profile, self.contact)
        with self.assertRaises(ProtectedError):
            self.contact.delete()

    def test_db_protects_contact_with_important_document(self):
        make_important_doc(self.profile, self.contact)
        with self.assertRaises(ProtectedError):
            self.contact.delete()

    def test_db_cascades_family_note_on_contact_delete(self):
        """
        FamilyNeedsToKnowSection uses on_delete=CASCADE, so at the raw DB
        level a contact with only family notes CAN be deleted and the notes
        are removed automatically.  The VIEW layer must catch this case BEFORE
        reaching the DB and return an error to the user instead.
        """
        note = make_family_note(self.contact)
        note_pk = note.pk
        self.contact.delete()                                          # succeeds at DB level
        self.assertFalse(FamilyNeedsToKnowSection.objects.filter(pk=note_pk).exists())

    def test_bare_contact_can_be_deleted_at_db_level(self):
        """A contact with no assignments at all can be deleted directly."""
        bare = make_contact(self.profile, relation='Other',
                            first_name='Bare', last_name='Contact')
        pk = bare.pk
        bare.delete()
        self.assertFalse(Contact.objects.filter(pk=pk).exists())

    def test_contact_deletable_after_all_four_protect_items_removed(self):
        """
        Removing every PROTECT-type assignment allows DB-level deletion.
        Family notes are not present here — that is the pure DB behaviour test.
        """
        acct   = make_account(self.profile, self.contact)
        dev    = make_device(self.profile, self.contact)
        estate = make_estate_doc(self.profile, self.contact)
        imp    = make_important_doc(self.profile, self.contact)

        acct.delete()
        dev.delete()
        estate.delete()
        imp.delete()

        pk = self.contact.pk
        self.contact.delete()
        self.assertFalse(Contact.objects.filter(pk=pk).exists())

    def test_get_total_documents_count_aggregates_estate_and_important(self):
        make_estate_doc(self.profile, self.contact)
        make_important_doc(self.profile, self.contact)
        self.assertEqual(self.contact.get_total_documents_count(), 2)


# ═══════════════════════════════════════════════════════════════
#  MODEL TESTS — Account signals
# ═══════════════════════════════════════════════════════════════

class AccountModelTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_str_returns_provider_name(self):
        self.assertEqual(str(make_account(self.profile, self.contact)), 'Gmail')

    def test_default_instruction_is_keep_active(self):
        self.assertEqual(
            make_account(self.profile, self.contact).keep_or_close_instruction,
            'Keep Active',
        )

    def test_creation_auto_creates_relevance_review(self):
        acct = make_account(self.profile, self.contact)
        self.assertTrue(RelevanceReview.objects.filter(account_review=acct).exists())

    def test_review_due_date_matches_review_time_field(self):
        acct = make_account(self.profile, self.contact, review_time=60)
        review = RelevanceReview.objects.filter(account_review=acct).latest('review_date')
        self.assertEqual(review.next_review_due, date.today() + timedelta(days=60))

    def test_changing_review_time_updates_next_due_date(self):
        acct = make_account(self.profile, self.contact, review_time=30)
        original = RelevanceReview.objects.filter(
            account_review=acct
        ).latest('review_date').next_review_due

        acct.review_time = 365
        acct.save()

        updated = RelevanceReview.objects.filter(
            account_review=acct
        ).latest('review_date').next_review_due
        self.assertGreater(updated, original)

    def test_saving_with_same_review_time_does_not_alter_due_date(self):
        acct = make_account(self.profile, self.contact, review_time=30)
        original = RelevanceReview.objects.filter(
            account_review=acct
        ).latest('review_date').next_review_due
        acct.save()   # no field changed
        unchanged = RelevanceReview.objects.filter(
            account_review=acct
        ).latest('review_date').next_review_due
        self.assertEqual(original, unchanged)


# ═══════════════════════════════════════════════════════════════
#  MODEL TESTS — FuneralPlan
# ═══════════════════════════════════════════════════════════════

class FuneralPlanModelTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)

    def test_is_complete_true_when_all_four_required_fields_set(self):
        self.assertTrue(make_funeral_plan(self.profile).is_complete)

    def test_is_complete_false_without_disposition_method(self):
        plan = FuneralPlan.objects.create(
            profile=self.profile,
            service_type='Memorial Service',
            officiant_name_freetext='Rev. Jones',
            payment_arrangements='Pre-paid',
        )
        self.assertFalse(plan.is_complete)

    def test_is_complete_false_without_service_type(self):
        plan = FuneralPlan.objects.create(
            profile=self.profile,
            disposition_method='Cremation',
            officiant_name_freetext='Rev. Jones',
            payment_arrangements='Pre-paid',
        )
        self.assertFalse(plan.is_complete)

    def test_is_complete_false_without_any_officiant(self):
        plan = FuneralPlan.objects.create(
            profile=self.profile,
            service_type='Memorial Service',
            disposition_method='Cremation',
            payment_arrangements='Pre-paid',
        )
        self.assertFalse(plan.is_complete)

    def test_is_complete_false_without_payment_arrangements(self):
        plan = FuneralPlan.objects.create(
            profile=self.profile,
            service_type='Memorial Service',
            disposition_method='Cremation',
            officiant_name_freetext='Rev. Jones',
        )
        self.assertFalse(plan.is_complete)

    def test_is_complete_accepts_fk_contact_as_officiant(self):
        contact = make_contact(self.profile)
        plan = FuneralPlan.objects.create(
            profile=self.profile,
            service_type='Traditional Funeral',
            disposition_method='Burial',
            officiant_contact=contact,
            payment_arrangements='Pre-paid',
        )
        self.assertTrue(plan.is_complete)

    def test_one_plan_per_profile_enforced(self):
        make_funeral_plan(self.profile)
        with self.assertRaises(Exception):
            FuneralPlan.objects.create(profile=self.profile, service_type='Other')

    def test_has_disposition_set_property(self):
        self.assertTrue(make_funeral_plan(self.profile).has_disposition_set)

    def test_has_service_preferences_property(self):
        self.assertTrue(make_funeral_plan(self.profile).has_service_preferences)


# ═══════════════════════════════════════════════════════════════
#  MODEL TESTS — RelevanceReview
# ═══════════════════════════════════════════════════════════════

class RelevanceReviewModelTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def test_clean_raises_if_no_target(self):
        with self.assertRaises(ValidationError):
            RelevanceReview(reviewer=self.user).clean()

    def test_clean_raises_if_two_targets_set(self):
        acct = make_account(self.profile, self.contact)
        dev  = make_device(self.profile, self.contact)
        with self.assertRaises(ValidationError):
            RelevanceReview(
                reviewer=self.user, account_review=acct, device_review=dev
            ).clean()

    def test_get_item_type_account(self):
        acct = make_account(self.profile, self.contact)
        self.assertEqual(
            RelevanceReview.objects.filter(account_review=acct).first().get_item_type(),
            'Account',
        )

    def test_get_item_type_device(self):
        dev = make_device(self.profile, self.contact)
        self.assertEqual(
            RelevanceReview.objects.filter(device_review=dev).first().get_item_type(),
            'Device',
        )

    def test_get_item_type_estate_document(self):
        doc = make_estate_doc(self.profile, self.contact)
        self.assertEqual(
            RelevanceReview.objects.filter(estate_review=doc).first().get_item_type(),
            'Estate Document',
        )

    def test_get_item_type_important_document(self):
        doc = make_important_doc(self.profile, self.contact)
        self.assertEqual(
            RelevanceReview.objects.filter(
                important_document_review=doc
            ).first().get_item_type(),
            'Important Document',
        )

    def test_get_item_name_uses_account_provider(self):
        acct = make_account(self.profile, self.contact, account_name_or_provider='MyBank')
        self.assertEqual(
            RelevanceReview.objects.filter(account_review=acct).first().get_item_name(),
            'MyBank',
        )

    def test_get_reviewed_item_returns_none_when_empty(self):
        self.assertIsNone(RelevanceReview(reviewer=self.user).get_reviewed_item())

    def test_get_item_name_returns_unknown_when_no_item(self):
        self.assertEqual(
            RelevanceReview(reviewer=self.user).get_item_name(),
            'Unknown Item',
        )


# ═══════════════════════════════════════════════════════════════
#  SIGNAL TESTS
# ═══════════════════════════════════════════════════════════════

class SignalTest(TestCase):

    def setUp(self):
        self.user = make_legacy()

    def test_complete_profile_auto_creates_self_contact(self):
        profile = make_profile(self.user)
        self.assertTrue(
            Contact.objects.filter(profile=profile, contact_relation='Self').exists()
        )

    def test_profile_update_syncs_self_contact_name(self):
        profile = make_profile(self.user)
        profile.first_name = 'Updated'
        profile.save()
        self.assertEqual(
            Contact.objects.get(profile=profile, contact_relation='Self').first_name,
            'Updated',
        )

    def test_incomplete_profile_does_not_create_self_contact(self):
        profile = Profile.objects.create(
            user=self.user, first_name='', last_name='',
            address_1='', city='', state='',
        )
        self.assertFalse(
            Contact.objects.filter(profile=profile, contact_relation='Self').exists()
        )

    def test_saving_profile_twice_does_not_duplicate_self_contact(self):
        profile = make_profile(self.user)
        profile.first_name = 'Once'
        profile.save()
        profile.first_name = 'Twice'
        profile.save()
        self.assertEqual(
            Contact.objects.filter(profile=profile, contact_relation='Self').count(), 1
        )

    def test_account_creation_creates_exactly_one_review(self):
        profile = make_profile(self.user)
        contact = make_contact(profile)
        acct = make_account(profile, contact)
        self.assertEqual(RelevanceReview.objects.filter(account_review=acct).count(), 1)

    def test_device_creation_creates_exactly_one_review(self):
        profile = make_profile(self.user)
        contact = make_contact(profile)
        dev = make_device(profile, contact)
        self.assertEqual(RelevanceReview.objects.filter(device_review=dev).count(), 1)

    def test_estate_doc_creation_creates_exactly_one_review(self):
        profile = make_profile(self.user)
        contact = make_contact(profile)
        doc = make_estate_doc(profile, contact)
        self.assertEqual(RelevanceReview.objects.filter(estate_review=doc).count(), 1)

    def test_important_doc_creation_creates_exactly_one_review(self):
        profile = make_profile(self.user)
        contact = make_contact(profile)
        doc = make_important_doc(profile, contact)
        self.assertEqual(
            RelevanceReview.objects.filter(important_document_review=doc).count(), 1
        )

    def test_review_initial_due_date_respects_review_time(self):
        profile = make_profile(self.user)
        contact = make_contact(profile)
        dev = make_device(profile, contact, review_time=180)
        review = RelevanceReview.objects.filter(device_review=dev).first()
        self.assertEqual(review.next_review_due, date.today() + timedelta(days=180))


# ═══════════════════════════════════════════════════════════════
#  FORM TESTS
# ═══════════════════════════════════════════════════════════════

class ProfileFormTest(TestCase):

    def _data(self, **kw):
        d = dict(first_name='Jane', last_name='Doe', address_1='123 Main',
                 city='Des Moines', state='IA', zipcode='50309',
                 email='jane@example.com', phone='515-555-0000')
        d.update(kw)
        return d

    def test_valid_form_passes(self):
        from .forms import ProfileForm
        self.assertTrue(ProfileForm(data=self._data()).is_valid())

    def test_invalid_email_rejected(self):
        from .forms import ProfileForm
        form = ProfileForm(data=self._data(email='not-an-email'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_invalid_phone_rejected(self):
        from .forms import ProfileForm
        form = ProfileForm(data=self._data(phone='abc123'))
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_blank_phone_accepted(self):
        from .forms import ProfileForm
        self.assertTrue(ProfileForm(data=self._data(phone='')).is_valid())


class ContactFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        make_profile(self.user)

    def _data(self, **kw):
        d = dict(contact_relation='Spouse', first_name='John', last_name='Doe',
                 address_1='1 Main', city='Ames', state='IA',
                 is_emergency_contact=True)
        d.update(kw)
        return d

    def test_valid_form_passes(self):
        from .forms import ContactForm
        self.assertTrue(ContactForm(data=self._data(), user=self.user).is_valid())

    def test_no_role_raises_non_field_error(self):
        from .forms import ContactForm
        form = ContactForm(data=self._data(is_emergency_contact=False), user=self.user)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_blank_first_name_rejected(self):
        from .forms import ContactForm
        self.assertFalse(
            ContactForm(data=self._data(first_name=''), user=self.user).is_valid()
        )

    def test_blank_last_name_rejected(self):
        from .forms import ContactForm
        self.assertFalse(
            ContactForm(data=self._data(last_name=''), user=self.user).is_valid()
        )

    def test_invalid_phone_rejected(self):
        from .forms import ContactForm
        self.assertFalse(
            ContactForm(data=self._data(phone='xyz!'), user=self.user).is_valid()
        )

    def test_multiple_roles_valid(self):
        from .forms import ContactForm
        self.assertTrue(
            ContactForm(
                data=self._data(is_emergency_contact=True, is_digital_executor=True),
                user=self.user,
            ).is_valid()
        )


class AccountFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def _data(self, **kw):
        d = dict(delegated_account_to=self.contact.pk,
                 account_category='Email Account',
                 account_name_or_provider='Gmail',
                 review_time=30,
                 keep_or_close_instruction='Keep Active')
        d.update(kw)
        return d

    def test_valid_form_passes(self):
        from .forms import AccountForm
        self.assertTrue(AccountForm(data=self._data(), user=self.user).is_valid())

    def test_invalid_url_rejected(self):
        from .forms import AccountForm
        form = AccountForm(data=self._data(website_url='not-a-url'), user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('website_url', form.errors)

    def test_valid_https_url_accepted(self):
        from .forms import AccountForm
        self.assertTrue(
            AccountForm(
                data=self._data(website_url='https://gmail.com'), user=self.user
            ).is_valid()
        )

    def test_missing_contact_rejected(self):
        from .forms import AccountForm
        self.assertFalse(
            AccountForm(data=self._data(delegated_account_to=''), user=self.user).is_valid()
        )


class DigitalEstateDocumentFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)

    def _data(self, **kw):
        d = dict(delegated_estate_to=self.contact.pk,
                 estate_category='Advance Directive / Living Will',
                 name_or_title='My Living Will',
                 review_time=365,
                 applies_on_death=True)
        d.update(kw)
        return d

    def test_valid_form_passes(self):
        from .forms import DigitalEstateDocumentForm
        self.assertTrue(
            DigitalEstateDocumentForm(data=self._data(), user=self.user).is_valid()
        )

    def test_no_declaration_rejected(self):
        from .forms import DigitalEstateDocumentForm
        form = DigitalEstateDocumentForm(
            data=self._data(applies_on_death=False), user=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_applies_immediately_alone_valid(self):
        from .forms import DigitalEstateDocumentForm
        self.assertTrue(
            DigitalEstateDocumentForm(
                data=self._data(applies_on_death=False, applies_immediately=True),
                user=self.user,
            ).is_valid()
        )


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

    def test_non_veteran_branch_cleared_on_save(self):
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

    def test_both_officiant_fields_simultaneously_rejected(self):
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

    def test_invalid_funeral_home_phone_rejected(self):
        from .forms import FuneralPlanServiceForm
        form = FuneralPlanServiceForm(
            data={'funeral_home_phone': 'ABC-DEFG'},
            instance=self.plan, user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('funeral_home_phone', form.errors)

    def test_freetext_officiant_alone_valid(self):
        from .forms import FuneralPlanServiceForm
        self.assertTrue(
            FuneralPlanServiceForm(
                data={'officiant_name_freetext': 'Rev. Smith'},
                instance=self.plan, user=self.user,
            ).is_valid()
        )


class FuneralPlanReceptionFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.plan, _ = FuneralPlan.objects.get_or_create(profile=self.profile)

    def test_reception_desired_without_location_rejected(self):
        from .forms import FuneralPlanReceptionForm
        self.assertFalse(
            FuneralPlanReceptionForm(
                data={'reception_desired': True, 'reception_location': ''},
                instance=self.plan, user=self.user,
            ).is_valid()
        )

    def test_reception_desired_with_location_valid(self):
        from .forms import FuneralPlanReceptionForm
        self.assertTrue(
            FuneralPlanReceptionForm(
                data={'reception_desired': True, 'reception_location': 'Community Hall'},
                instance=self.plan, user=self.user,
            ).is_valid()
        )

    def test_no_reception_valid_without_location(self):
        from .forms import FuneralPlanReceptionForm
        self.assertTrue(
            FuneralPlanReceptionForm(
                data={'reception_desired': False},
                instance=self.plan, user=self.user,
            ).is_valid()
        )


class FuneralPlanAdminFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.plan, _ = FuneralPlan.objects.get_or_create(profile=self.profile)

    def test_zero_death_certificates_rejected(self):
        from .forms import FuneralPlanAdminForm
        form = FuneralPlanAdminForm(
            data={'death_certificates_requested': 0, 'review_time': 365},
            instance=self.plan, user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('death_certificates_requested', form.errors)

    def test_blank_death_certificates_accepted(self):
        from .forms import FuneralPlanAdminForm
        self.assertTrue(
            FuneralPlanAdminForm(
                data={'death_certificates_requested': '', 'review_time': 365},
                instance=self.plan, user=self.user,
            ).is_valid()
        )

    def test_positive_count_accepted(self):
        from .forms import FuneralPlanAdminForm
        self.assertTrue(
            FuneralPlanAdminForm(
                data={'death_certificates_requested': 8, 'review_time': 365},
                instance=self.plan, user=self.user,
            ).is_valid()
        )


class RelevanceReviewFormTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.acct = make_account(self.profile, self.contact)

    def test_valid_single_target_passes(self):
        from .forms import RelevanceReviewForm
        form = RelevanceReviewForm(
            data={
                'account_review': self.acct.pk,
                'matters': True,
                'next_review_due': (date.today() + timedelta(days=30)).isoformat(),
            },
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_no_target_rejected(self):
        from .forms import RelevanceReviewForm
        form = RelevanceReviewForm(data={'matters': True}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_past_review_date_rejected(self):
        from .forms import RelevanceReviewForm
        form = RelevanceReviewForm(
            data={
                'account_review': self.acct.pk,
                'matters': True,
                'next_review_due': (date.today() - timedelta(days=1)).isoformat(),
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('next_review_due', form.errors)

    def test_today_as_review_date_rejected(self):
        from .forms import RelevanceReviewForm
        form = RelevanceReviewForm(
            data={
                'account_review': self.acct.pk,
                'matters': True,
                'next_review_due': date.today().isoformat(),
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_multiple_targets_rejected(self):
        from .forms import RelevanceReviewForm
        dev = make_device(self.profile, self.contact)
        form = RelevanceReviewForm(
            data={
                'account_review': self.acct.pk,
                'device_review': dev.pk,
                'matters': True,
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — DashboardHomeView
# ═══════════════════════════════════════════════════════════════

class DashboardHomeViewTest(TestCase):

    def test_unpaid_user_redirected_to_payment(self):
        user = make_user(username='np', email='np@x.com')
        self.client.force_login(user)
        self.assertRedirects(
            self.client.get(reverse('dashboard:dashboard_home')),
            reverse('accounts:payment'),
        )

    def test_paid_user_without_profile_redirected_to_profile_create(self):
        user = make_legacy(username='noprof', email='np2@x.com')
        self.client.force_login(user)
        self.assertRedirects(
            self.client.get(reverse('dashboard:dashboard_home')),
            reverse('dashboard:profile_create'),
        )

    def test_fully_set_up_user_sees_dashboard(self):
        user = make_legacy()
        make_profile(user)
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:dashboard_home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/dashboard.html')

    def test_context_includes_correct_account_count(self):
        user = make_legacy()
        profile = make_profile(user)
        contact = make_contact(profile)
        make_account(profile, contact)
        self.client.force_login(user)
        self.assertEqual(
            self.client.get(reverse('dashboard:dashboard_home')).context['accounts_count'], 1
        )

    def test_onboarding_shown_when_fewer_than_three_categories_filled(self):
        user = make_legacy()
        make_profile(user)
        self.client.force_login(user)
        self.assertTrue(
            self.client.get(reverse('dashboard:dashboard_home')).context['show_onboarding']
        )

    def test_progress_is_integer_between_0_and_100(self):
        user = make_legacy()
        make_profile(user)
        self.client.force_login(user)
        p = self.client.get(reverse('dashboard:dashboard_home')).context['progress']
        self.assertIsInstance(p, int)
        self.assertGreaterEqual(p, 0)
        self.assertLessEqual(p, 100)

    def test_unauthenticated_user_cannot_access_dashboard(self):
        self.assertNotEqual(
            self.client.get(reverse('dashboard:dashboard_home')).status_code, 200
        )


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — Contact CRUD & deletion enforcement
# ═══════════════════════════════════════════════════════════════

class ContactDeletionViewTest(TestCase):
    """
    All five assignment types (Account, Device, DigitalEstateDocument,
    ImportantDocument, FamilyNeedsToKnowSection) must be removed before
    the view will allow a contact to be deleted.

    The view checks a combined total of all five counts and returns an error
    to the user if any remain — regardless of whether the DB would cascade
    or protect the row.
    """

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.client.force_login(self.user)
        self.delete_url = reverse('dashboard:contact_delete', args=[self.contact.pk])

    # ── Each type blocks individually ────────────────────────

    def test_account_assignment_blocks_deletion(self):
        make_account(self.profile, self.contact)
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())

    def test_device_assignment_blocks_deletion(self):
        make_device(self.profile, self.contact)
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())

    def test_estate_document_assignment_blocks_deletion(self):
        make_estate_doc(self.profile, self.contact)
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())

    def test_important_document_assignment_blocks_deletion(self):
        make_important_doc(self.profile, self.contact)
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())

    def test_family_note_assignment_blocks_deletion(self):
        """
        FamilyNeedsToKnowSection.relation uses CASCADE at the DB level, but
        the view must refuse deletion if any family notes exist — the user
        must explicitly delete the notes first.
        """
        make_family_note(self.contact)
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())

    def test_all_five_present_blocks_deletion(self):
        make_account(self.profile, self.contact)
        make_device(self.profile, self.contact)
        make_estate_doc(self.profile, self.contact)
        make_important_doc(self.profile, self.contact)
        make_family_note(self.contact)
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())

    # ── Single remaining assignment still blocks ──────────────

    def test_one_remaining_account_still_blocks_after_others_cleared(self):
        acct   = make_account(self.profile, self.contact)
        dev    = make_device(self.profile, self.contact)
        estate = make_estate_doc(self.profile, self.contact)
        imp    = make_important_doc(self.profile, self.contact)
        note   = make_family_note(self.contact)

        dev.delete()
        estate.delete()
        imp.delete()
        note.delete()
        # Account still present → blocked
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())

    def test_one_remaining_family_note_still_blocks_after_others_cleared(self):
        acct   = make_account(self.profile, self.contact)
        dev    = make_device(self.profile, self.contact)
        estate = make_estate_doc(self.profile, self.contact)
        imp    = make_important_doc(self.profile, self.contact)
        _note  = make_family_note(self.contact)   # left in place

        acct.delete()
        dev.delete()
        estate.delete()
        imp.delete()
        # Family note still present → view must block
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())

    # ── Step-by-step removal: blocked until the very last item gone ──

    def test_deletion_blocked_until_all_five_types_removed(self):
        """
        Remove one assignment type at a time and confirm the contact survives
        each intermediate attempt.  Only after the last assignment is gone
        should deletion succeed.
        """
        acct   = make_account(self.profile, self.contact)
        dev    = make_device(self.profile, self.contact)
        estate = make_estate_doc(self.profile, self.contact)
        imp    = make_important_doc(self.profile, self.contact)
        note   = make_family_note(self.contact)

        acct.delete()
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists(),
                        'Contact deleted too early — device/estate/imp/note still present')

        dev.delete()
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists(),
                        'Contact deleted too early — estate/imp/note still present')

        estate.delete()
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists(),
                        'Contact deleted too early — imp/note still present')

        imp.delete()
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists(),
                        'Contact deleted too early — note still present')

        # Delete the last remaining assignment type (family note)
        note.delete()
        self.client.post(self.delete_url)
        self.assertFalse(
            Contact.objects.filter(pk=self.contact.pk).exists(),
            'Contact should have been deleted once all five assignment types were cleared',
        )

    # ── Deletion succeeds when truly empty ───────────────────

    def test_contact_with_no_assignments_deleted_successfully(self):
        bare = make_contact(self.profile, relation='Other',
                            first_name='Bare', last_name='Contact')
        self.client.post(reverse('dashboard:contact_delete', args=[bare.pk]))
        self.assertFalse(Contact.objects.filter(pk=bare.pk).exists())

    # ── Reassignment allows deletion ─────────────────────────

    def test_reassigning_all_five_types_then_deleting_succeeds(self):
        """
        Reassign every assignment to a different contact; the original
        contact should then be deletable.
        """
        replacement = make_contact(
            self.profile, relation='Other', first_name='Alt', last_name='C'
        )
        acct   = make_account(self.profile, self.contact)
        dev    = make_device(self.profile, self.contact)
        estate = make_estate_doc(self.profile, self.contact)
        imp    = make_important_doc(self.profile, self.contact)
        note   = make_family_note(self.contact)

        acct.delegated_account_to = replacement;   acct.save()
        dev.delegated_device_to = replacement;     dev.save()
        estate.delegated_estate_to = replacement;  estate.save()
        imp.delegated_important_document_to = replacement; imp.save()
        note.delete()   # FamilyNeedsToKnowSection has no delegation target — must be deleted

        self.client.post(self.delete_url)
        self.assertFalse(Contact.objects.filter(pk=self.contact.pk).exists())

    # ── Context surface: confirmation page ───────────────────

    def test_delete_confirm_page_shows_assignment_summary(self):
        make_account(self.profile, self.contact)
        make_device(self.profile, self.contact)
        make_family_note(self.contact)
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['has_assignments'])
        self.assertEqual(response.context['total_accounts'], 1)
        self.assertEqual(response.context['total_devices'], 1)

    def test_delete_confirm_page_suggests_other_contacts_for_reassignment(self):
        make_account(self.profile, self.contact)
        make_contact(self.profile, relation='Other', first_name='Alt', last_name='C')
        response = self.client.get(self.delete_url)
        self.assertTrue(response.context['has_other_contacts'])

    # ── Ownership isolation ───────────────────────────────────

    def test_other_user_cannot_delete_contact(self):
        other = make_legacy(username='iso_del', email='iso_del@x.com')
        make_profile(other)
        self.client.force_login(other)
        self.client.post(self.delete_url)
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())

    def test_other_user_cannot_view_contact_detail(self):
        other = make_legacy(username='iso_det', email='iso_det@x.com')
        make_profile(other)
        self.client.force_login(other)
        response = self.client.get(
            reverse('dashboard:contact_detail', args=[self.contact.pk])
        )
        self.assertEqual(response.status_code, 404)


class ContactCRUDViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.client.force_login(self.user)

    def test_list_200(self):
        self.assertEqual(self.client.get(reverse('dashboard:contact_list')).status_code, 200)

    def test_detail_200(self):
        self.assertEqual(
            self.client.get(
                reverse('dashboard:contact_detail', args=[self.contact.pk])
            ).status_code, 200
        )

    def test_create_adds_contact(self):
        count = Contact.objects.filter(profile=self.profile).count()
        self.client.post(reverse('dashboard:contact_create'), {
            'contact_relation': 'Daughter',
            'first_name': 'Alice', 'last_name': 'Doe',
            'address_1': '1 Oak', 'city': 'Ames', 'state': 'IA',
            'is_emergency_contact': True,
        })
        self.assertGreater(Contact.objects.filter(profile=self.profile).count(), count)

    def test_update_modifies_contact(self):
        self.client.post(reverse('dashboard:contact_update', args=[self.contact.pk]), {
            'contact_relation': 'Spouse',
            'first_name': 'Jonathan', 'last_name': 'Doe',
            'address_1': '1 Main', 'city': 'Ames', 'state': 'IA',
            'is_emergency_contact': True,
        })
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.first_name, 'Jonathan')

    def test_detail_context_shows_all_assignment_types(self):
        make_account(self.profile, self.contact)
        make_device(self.profile, self.contact)
        make_estate_doc(self.profile, self.contact)
        make_important_doc(self.profile, self.contact)
        response = self.client.get(
            reverse('dashboard:contact_detail', args=[self.contact.pk])
        )
        self.assertEqual(response.context['total_assignments'], 4)


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — Account CRUD (deletion frees contact)
# ═══════════════════════════════════════════════════════════════

class AccountViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.account = make_account(self.profile, self.contact)
        self.client.force_login(self.user)

    def test_list_200(self):
        self.assertEqual(self.client.get(reverse('dashboard:account_list')).status_code, 200)

    def test_detail_200(self):
        self.assertEqual(
            self.client.get(
                reverse('dashboard:account_detail', args=[self.account.pk])
            ).status_code, 200
        )

    def test_create_adds_account(self):
        count = Account.objects.filter(profile=self.profile).count()
        self.client.post(reverse('dashboard:account_create'), {
            'delegated_account_to': self.contact.pk,
            'account_category': 'Email Account',
            'account_name_or_provider': 'Yahoo Mail',
            'review_time': 30,
            'keep_or_close_instruction': 'Close Account',
        })
        self.assertGreater(Account.objects.filter(profile=self.profile).count(), count)

    def test_delete_removes_account(self):
        self.client.post(reverse('dashboard:account_delete', args=[self.account.pk]))
        self.assertFalse(Account.objects.filter(pk=self.account.pk).exists())

    def test_deleting_only_account_then_allows_contact_deletion(self):
        contact_pk = self.contact.pk
        self.client.post(reverse('dashboard:account_delete', args=[self.account.pk]))
        self.client.post(reverse('dashboard:contact_delete', args=[contact_pk]))
        self.assertFalse(Contact.objects.filter(pk=contact_pk).exists())

    def test_other_user_cannot_access_account_detail(self):
        other = make_legacy(username='a_iso', email='a_iso@x.com')
        make_profile(other)
        self.client.force_login(other)
        self.assertEqual(
            self.client.get(
                reverse('dashboard:account_detail', args=[self.account.pk])
            ).status_code, 404
        )

    def test_list_paginates_at_20(self):
        for i in range(22):
            make_account(self.profile, self.contact, account_name_or_provider=f'A-{i}')
        response = self.client.get(reverse('dashboard:account_list'))
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['accounts']), 20)


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
            self.client.get(
                reverse('dashboard:device_detail', args=[self.device.pk])
            ).status_code, 200
        )

    def test_create_adds_device(self):
        count = Device.objects.filter(profile=self.profile).count()
        self.client.post(reverse('dashboard:device_create'), {
            'delegated_device_to': self.contact.pk,
            'device_type': 'Laptop',
            'device_name': 'MacBook Pro',
            'review_time': 30,
        })
        self.assertGreater(Device.objects.filter(profile=self.profile).count(), count)

    def test_delete_removes_device(self):
        self.client.post(reverse('dashboard:device_delete', args=[self.device.pk]))
        self.assertFalse(Device.objects.filter(pk=self.device.pk).exists())

    def test_deleting_only_device_then_allows_contact_deletion(self):
        contact_pk = self.contact.pk
        self.client.post(reverse('dashboard:device_delete', args=[self.device.pk]))
        self.client.post(reverse('dashboard:contact_delete', args=[contact_pk]))
        self.assertFalse(Contact.objects.filter(pk=contact_pk).exists())


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — Estate & Important Document CRUD
# ═══════════════════════════════════════════════════════════════

class EstateDocumentViewTest(TestCase):

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
            self.client.get(
                reverse('dashboard:estate_detail', args=[self.doc.pk])
            ).status_code, 200
        )

    def test_delete_removes_document(self):
        self.client.post(reverse('dashboard:estate_delete', args=[self.doc.pk]))
        self.assertFalse(DigitalEstateDocument.objects.filter(pk=self.doc.pk).exists())

    def test_deleting_only_estate_doc_then_allows_contact_deletion(self):
        contact_pk = self.contact.pk
        self.client.post(reverse('dashboard:estate_delete', args=[self.doc.pk]))
        self.client.post(reverse('dashboard:contact_delete', args=[contact_pk]))
        self.assertFalse(Contact.objects.filter(pk=contact_pk).exists())


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
            self.client.get(
                reverse('dashboard:importantdocument_detail', args=[self.doc.pk])
            ).status_code, 200
        )

    def test_create_adds_document(self):
        count = ImportantDocument.objects.filter(profile=self.profile).count()
        self.client.post(reverse('dashboard:importantdocument_create'), {
            'delegated_important_document_to': self.contact.pk,
            'name_or_title': 'Passport',
            'document_category': 'Personal Identification',
            'review_time': 365,
            'applies_on_death': True,
        })
        self.assertGreater(ImportantDocument.objects.filter(profile=self.profile).count(), count)

    def test_delete_removes_document(self):
        self.client.post(reverse('dashboard:importantdocument_delete', args=[self.doc.pk]))
        self.assertFalse(ImportantDocument.objects.filter(pk=self.doc.pk).exists())

    def test_deleting_only_important_doc_then_allows_contact_deletion(self):
        contact_pk = self.contact.pk
        self.client.post(reverse('dashboard:importantdocument_delete', args=[self.doc.pk]))
        self.client.post(reverse('dashboard:contact_delete', args=[contact_pk]))
        self.assertFalse(Contact.objects.filter(pk=contact_pk).exists())


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — FamilyAwareness CRUD
# ═══════════════════════════════════════════════════════════════

class FamilyAwarenessViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.note = make_family_note(self.contact)
        self.client.force_login(self.user)

    def test_list_200(self):
        self.assertEqual(
            self.client.get(reverse('dashboard:familyawareness_list')).status_code, 200
        )

    def test_detail_200(self):
        self.assertEqual(
            self.client.get(
                reverse('dashboard:familyawareness_detail', args=[self.note.pk])
            ).status_code, 200
        )

    def test_delete_removes_note(self):
        self.client.post(reverse('dashboard:familyawareness_delete', args=[self.note.pk]))
        self.assertFalse(FamilyNeedsToKnowSection.objects.filter(pk=self.note.pk).exists())

    def test_deleting_only_family_note_then_allows_contact_deletion(self):
        """
        Deleting the FamilyNeedsToKnowSection via its own delete view must
        unblock the contact for deletion.
        """
        contact_pk = self.contact.pk
        self.client.post(reverse('dashboard:familyawareness_delete', args=[self.note.pk]))
        self.client.post(reverse('dashboard:contact_delete', args=[contact_pk]))
        self.assertFalse(Contact.objects.filter(pk=contact_pk).exists())

    def test_family_note_deletion_does_not_delete_contact(self):
        """Cascade is one-way: deleting the note must not delete the contact."""
        contact_pk = self.contact.pk
        self.client.post(reverse('dashboard:familyawareness_delete', args=[self.note.pk]))
        self.assertTrue(Contact.objects.filter(pk=contact_pk).exists())


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — FuneralPlan wizard
# ═══════════════════════════════════════════════════════════════

class FuneralPlanViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.client.force_login(self.user)

    def test_index_auto_creates_plan_on_first_visit(self):
        self.assertFalse(FuneralPlan.objects.filter(profile=self.profile).exists())
        self.client.get(reverse('dashboard:funeralplan_index'))
        self.assertTrue(FuneralPlan.objects.filter(profile=self.profile).exists())

    def test_index_200(self):
        self.assertEqual(
            self.client.get(reverse('dashboard:funeralplan_index')).status_code, 200
        )

    def test_detail_200(self):
        FuneralPlan.objects.create(profile=self.profile)
        self.assertEqual(
            self.client.get(reverse('dashboard:funeralplan_detail')).status_code, 200
        )

    def test_all_eight_steps_return_200(self):
        for step in range(1, 9):
            response = self.client.get(reverse(f'dashboard:funeralplan_step{step}'))
            self.assertEqual(response.status_code, 200, f'Step {step} returned {response.status_code}')

    def test_step1_post_saves_data_and_redirects_to_step2(self):
        response = self.client.post(reverse('dashboard:funeralplan_step1'), {
            'preferred_name': 'Janie', 'occupation': 'Teacher',
            'is_veteran': False, 'veteran_branch': '',
        })
        self.assertRedirects(response, reverse('dashboard:funeralplan_step2'))
        self.assertEqual(FuneralPlan.objects.get(profile=self.profile).preferred_name, 'Janie')

    def test_step8_post_redirects_to_summary_detail(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        response = self.client.post(reverse('dashboard:funeralplan_step8'), {
            'additional_instructions': 'Play jazz.',
        })
        self.assertRedirects(response, reverse('dashboard:funeralplan_detail'))

    def test_sequential_step_saves_accumulate_data(self):
        self.client.post(reverse('dashboard:funeralplan_step1'), {
            'preferred_name': 'Jay', 'is_veteran': False, 'veteran_branch': '',
        })
        self.client.post(reverse('dashboard:funeralplan_step2'), {
            'service_type': 'Graveside Service',
        })
        plan = FuneralPlan.objects.get(profile=self.profile)
        self.assertEqual(plan.preferred_name, 'Jay')
        self.assertEqual(plan.service_type, 'Graveside Service')

    def test_invalid_step1_rerenders_with_form_error(self):
        response = self.client.post(reverse('dashboard:funeralplan_step1'), {
            'is_veteran': True,
            'veteran_branch': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response, 'form', 'veteran_branch',
            'Please enter the branch of service, or uncheck the Veteran field.',
        )

    def test_unpaid_user_redirected_from_funeralplan_index(self):
        unpaid = make_user(username='fp_unp', email='fp_unp@x.com')
        Profile.objects.create(
            user=unpaid, first_name='U', last_name='P',
            address_1='1 St', city='City', state='IA',
        )
        self.client.force_login(unpaid)
        self.assertRedirects(
            self.client.get(reverse('dashboard:funeralplan_index')),
            reverse('accounts:payment'),
        )

    def test_expired_essentials_post_to_step_is_blocked(self):
        exp = make_essentials(username='fp_exp', email='fp_exp@x.com')
        exp.essentials_expires = timezone.now() - timedelta(days=1)
        exp.save()
        make_profile(exp)
        FuneralPlan.objects.create(profile=exp.profile)
        self.client.force_login(exp)
        self.client.post(reverse('dashboard:funeralplan_step1'), {
            'preferred_name': 'Blocked', 'is_veteran': False,
        })
        self.assertNotEqual(
            FuneralPlan.objects.get(profile=exp.profile).preferred_name, 'Blocked'
        )

    # ── Delete ────────────────────────────────────────────────

    def test_delete_get_renders_confirm_template(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        response = self.client.get(reverse('dashboard:funeralplan_delete'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'dashboard/funeralplan/funeralplan_confirm_delete.html'
        )

    def test_delete_wrong_confirmation_text_preserves_plan(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        self.client.post(reverse('dashboard:funeralplan_delete'), {'confirm_text': 'delete'})
        self.assertTrue(FuneralPlan.objects.filter(profile=self.profile).exists())

    def test_delete_mixed_case_confirmation_preserves_plan(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        self.client.post(reverse('dashboard:funeralplan_delete'), {'confirm_text': 'Delete'})
        self.assertTrue(FuneralPlan.objects.filter(profile=self.profile).exists())

    def test_delete_correct_DELETE_removes_plan(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        self.client.post(reverse('dashboard:funeralplan_delete'), {'confirm_text': 'DELETE'})
        self.assertFalse(FuneralPlan.objects.filter(profile=self.profile).exists())

    def test_delete_redirects_to_index(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        response = self.client.post(
            reverse('dashboard:funeralplan_delete'), {'confirm_text': 'DELETE'}
        )
        self.assertRedirects(response, reverse('dashboard:funeralplan_index'))

    def test_delete_when_no_plan_exists_shows_info_message(self):
        response = self.client.post(
            reverse('dashboard:funeralplan_delete'), {'confirm_text': 'DELETE'}
        )
        msgs = list(response.wsgi_request._messages)
        self.assertTrue(any('no funeral plan' in str(m).lower() for m in msgs))

    def test_delete_requires_csrf(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.user)
        response = c.post(
            reverse('dashboard:funeralplan_delete'), {'confirm_text': 'DELETE'}
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(FuneralPlan.objects.filter(profile=self.profile).exists())

    def test_expired_essentials_cannot_delete_plan(self):
        exp = make_essentials(username='fp_delexp', email='fp_delexp@x.com')
        exp.essentials_expires = timezone.now() - timedelta(days=1)
        exp.save()
        make_profile(exp)
        FuneralPlan.objects.create(profile=exp.profile)
        self.client.force_login(exp)
        self.client.post(reverse('dashboard:funeralplan_delete'), {'confirm_text': 'DELETE'})
        self.assertTrue(FuneralPlan.objects.filter(profile=exp.profile).exists())


# ═══════════════════════════════════════════════════════════════
#  VIEW TESTS — RelevanceReview & MarkItemReviewed
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
        self.assertEqual(
            self.client.get(reverse('dashboard:relevancereview_list')).status_code, 200
        )

    def test_detail_200(self):
        self.assertEqual(
            self.client.get(
                reverse('dashboard:relevancereview_detail', args=[self.review.pk])
            ).status_code, 200
        )

    def test_other_user_cannot_view_review(self):
        other = make_legacy(username='rv_iso', email='rv_iso@x.com')
        make_profile(other)
        self.client.force_login(other)
        response = self.client.get(
            reverse('dashboard:relevancereview_detail', args=[self.review.pk])
        )
        self.assertIn(response.status_code, [403, 404])

    def test_unpaid_user_redirected_from_list(self):
        unpaid = make_user(username='rv_unp', email='rv_unp@x.com')
        self.client.force_login(unpaid)
        self.assertRedirects(
            self.client.get(reverse('dashboard:relevancereview_list')),
            reverse('accounts:payment'),
        )


class MarkItemReviewedViewTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.acct = make_account(self.profile, self.contact)
        self.review = RelevanceReview.objects.filter(account_review=self.acct).first()
        self.client.force_login(self.user)
        self.url = reverse('dashboard:mark_item_reviewed', args=[self.review.pk])

    def test_get_returns_method_not_allowed(self):
        data = json.loads(self.client.get(self.url).content)
        self.assertFalse(data['success'])

    def test_post_returns_success_with_timestamps(self):
        data = json.loads(self.client.post(self.url).content)
        self.assertTrue(data['success'])
        self.assertIn('updated_at', data)
        self.assertIn('next_review_due', data)

    def test_post_advances_next_review_due(self):
        old_due = self.review.next_review_due
        self.client.post(self.url)
        self.review.refresh_from_db()
        self.assertGreater(self.review.next_review_due, old_due)

    def test_nonexistent_review_returns_404(self):
        self.assertEqual(
            self.client.post(
                reverse('dashboard:mark_item_reviewed', args=[99999])
            ).status_code, 404
        )

    def test_unpaid_user_returns_403(self):
        unpaid = make_user(username='mk_unp', email='mk_unp@x.com')
        self.client.force_login(unpaid)
        self.assertEqual(self.client.post(self.url).status_code, 403)

    def test_other_users_review_returns_error(self):
        other = make_legacy(username='mk_oth', email='mk_oth@x.com')
        make_profile(other)
        self.client.force_login(other)
        data = json.loads(self.client.post(self.url).content)
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

    def test_progress_context_has_all_six_keys(self):
        p = self.client.get(reverse('dashboard:onboarding_welcome')).context['progress']
        for key in ('contacts', 'accounts', 'devices', 'estates', 'documents', 'family_knows'):
            self.assertIn(key, p)

    def test_contacts_step_post_adds_contact(self):
        count = Contact.objects.filter(
            profile=self.profile
        ).exclude(contact_relation='Self').count()
        self.client.post(reverse('dashboard:onboarding_contacts'), {
            'contact_relation': 'Daughter',
            'first_name': 'Lily', 'last_name': 'Doe',
            'address_1': '1 Oak', 'city': 'Ames', 'state': 'IA',
            'is_emergency_contact': True,
        })
        self.assertEqual(
            Contact.objects.filter(
                profile=self.profile
            ).exclude(contact_relation='Self').count(),
            count + 1,
        )

    def test_unpaid_user_redirected_from_onboarding(self):
        unpaid = make_user(username='ob_unp', email='ob_unp@x.com')
        self.client.force_login(unpaid)
        self.assertRedirects(
            self.client.get(reverse('dashboard:onboarding_welcome')),
            reverse('accounts:payment'),
        )


# ═══════════════════════════════════════════════════════════════
#  EDGE CASES
# ═══════════════════════════════════════════════════════════════

class EdgeCaseTest(TestCase):

    def setUp(self):
        self.user = make_legacy()
        self.profile = make_profile(self.user)
        self.contact = make_contact(self.profile)
        self.client.force_login(self.user)

    def test_progress_never_exceeds_100(self):
        for i in range(25):
            make_account(self.profile, self.contact, account_name_or_provider=f'A-{i}')
        p = self.client.get(reverse('dashboard:dashboard_home')).context['progress']
        self.assertLessEqual(p, 100)

    def test_progress_zero_for_empty_profile(self):
        self.assertEqual(
            self.client.get(reverse('dashboard:dashboard_home')).context['progress'], 0
        )

    def test_account_list_only_shows_own_accounts(self):
        other = make_legacy(username='iso_a', email='iso_a@x.com')
        op = make_profile(other)
        oc = make_contact(op, first_name='O', last_name='P')
        make_account(op, oc, account_name_or_provider='OtherBank')
        for acct in self.client.get(reverse('dashboard:account_list')).context['accounts']:
            self.assertEqual(acct.profile, self.profile)

    def test_self_contact_not_duplicated_on_multiple_profile_saves(self):
        self.profile.first_name = 'A'; self.profile.save()
        self.profile.first_name = 'B'; self.profile.save()
        self.assertEqual(
            Contact.objects.filter(profile=self.profile, contact_relation='Self').count(), 1
        )

    def test_account_list_empty_for_paid_user_without_profile(self):
        """get_queryset must handle Profile.DoesNotExist gracefully."""
        no_prof = make_legacy(username='np3', email='np3@x.com')
        self.client.force_login(no_prof)
        response = self.client.get(reverse('dashboard:account_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context.get('accounts', [])), [])

    def test_review_due_date_exact_days_from_today(self):
        acct = make_account(self.profile, self.contact, review_time=90)
        review = RelevanceReview.objects.filter(account_review=acct).first()
        self.assertEqual(review.next_review_due, date.today() + timedelta(days=90))

    def test_funeral_plan_recreatable_after_deletion(self):
        FuneralPlan.objects.get_or_create(profile=self.profile)
        self.client.post(reverse('dashboard:funeralplan_delete'), {'confirm_text': 'DELETE'})
        self.client.get(reverse('dashboard:funeralplan_index'))   # triggers get_or_create
        self.assertTrue(FuneralPlan.objects.filter(profile=self.profile).exists())

    def test_partial_contact_reassignment_still_blocks_deletion(self):
        """
        Reassigning Account but leaving Device means deletion is still blocked
        (view must check all five counts, not stop at the first non-zero one).
        """
        acct = make_account(self.profile, self.contact)
        _dev = make_device(self.profile, self.contact)
        replacement = make_contact(
            self.profile, relation='Other', first_name='R', last_name='C'
        )
        acct.delegated_account_to = replacement
        acct.save()
        self.client.post(reverse('dashboard:contact_delete', args=[self.contact.pk]))
        self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())