import json
import logging
from django.utils import timezone
from datetime import timedelta
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import RedirectView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, ProtectedError, Q, F
from django.http import HttpResponseRedirect, JsonResponse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Min, Max
from datetime import datetime, timedelta
from django.contrib.messages.views import SuccessMessageMixin
from accounts.mixins import FullAccessMixin, ViewAccessMixin, DeleteAccessMixin, FreeTierLimitMixin, LapsedViewLimitMixin
from .models import (
    Profile,
    Contact,
    Account,
    Device,
    DigitalEstateDocument,
    ImportantDocument,
    FamilyNeedsToKnowSection,
    FuneralPlan,
    RelevanceReview,
)
from infrapps.models import VaultEntry

from .forms import (
    ProfileForm,
    ContactForm,
    AccountForm,
    DeviceForm,
    DigitalEstateDocumentForm,
    ImportantDocumentForm,
    FamilyNeedsToKnowSectionForm,
    RelevanceReviewForm,
    FuneralPlanPersonalInfoForm,
    FuneralPlanServiceForm,
    FuneralPlanDispositionForm,
    FuneralPlanCeremonyForm,
    FuneralPlanReceptionForm,
    FuneralPlanObituaryForm,
    FuneralPlanAdminForm,
    FuneralPlanInstructionsForm,
    FuneralPlanFullForm,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Slug mixin — add to any CBV that needs get_object() to look up by slug
# ---------------------------------------------------------------------------

class SlugLookupMixin:
    """
    Swaps PK-based get_object() for slug-based lookup.
    Set slug_field on the subclass to override the model field name
    (defaults to 'slug').
    """
    slug_field     = 'slug'
    slug_url_kwarg = 'slug'


# ============================================================================
# DASHBOARD HOME
# ============================================================================

class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        
        if not user.has_paid:
            if user.is_free_tier():
                try:
                    user.profile
                except Profile.DoesNotExist:
                    Profile.objects.create(user=user)
                return super().dispatch(request, *args, **kwargs)
            messages.warning(request, "Please complete payment to access your dashboard.")
            return redirect(reverse("accounts:payment"))

        try:
            profile = user.profile
        except Profile.DoesNotExist:
            messages.info(request, "Welcome! Let's set up your profile to get started.")
            return redirect(reverse("dashboard:profile_create"))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            profile = Profile.objects.get(user=user)
            context['user']    = user
            context['profile'] = profile
            context['session_expires'] = self.request.session.get_expiry_date()

            # Counts
            context['accounts_count']    = Account.objects.filter(profile=profile).count()
            context['devices_count']     = Device.objects.filter(profile=profile).count()
            context['contacts_count']    = Contact.objects.filter(profile=profile).count()
            context['estates_count']     = DigitalEstateDocument.objects.filter(profile=profile).count()
            context['documents_count']   = ImportantDocument.objects.filter(profile=profile).count()
            context['family_knows_count']= FamilyNeedsToKnowSection.objects.filter(relation__profile=profile).count()
            context['funeral_planned']   = FuneralPlan.objects.filter(profile=profile).count()

            tier_targets = self._get_tier_targets(user)
            context['tier_targets'] = tier_targets

            context['progress'] = self._calculate_progress(
                targets      = tier_targets,
                accounts     = context['accounts_count'],
                devices      = context['devices_count'],
                contacts     = context['contacts_count'],
                estates      = context['estates_count'],
                documents    = context['documents_count'],
                family_knows = context['family_knows_count'],
            )

            context['remaining_tasks'] = self._calculate_remaining_tasks(
                accounts     = context['accounts_count'],
                devices      = context['devices_count'],
                contacts     = context['contacts_count'],
                estates      = context['estates_count'],
                documents    = context['documents_count'],
                family_knows = context['family_knows_count'],
            )

            context['account_categories'] = self._get_account_categories(profile)

            context['device_types'] = {
                'phones':       Device.objects.filter(profile=profile, device_type='Phone').count(),
                'tablets':      Device.objects.filter(profile=profile, device_type='Tablet').count(),
                'laptops':      Device.objects.filter(profile=profile, device_type='Laptop').count(),
                'desktops':     Device.objects.filter(profile=profile, device_type='Desktop').count(),
                'smartwatches': Device.objects.filter(profile=profile, device_type='Smart Watch').count(),
                'others':       Device.objects.filter(profile=profile, device_type='Other').count(),
            }

            if user.is_subscription_active():
                review_stats = self._get_review_stats(profile)
                context.update(review_stats)
                upcoming_reviews = RelevanceReview.objects.filter(
                    Q(account_review__profile=profile) |
                    Q(device_review__profile=profile) |
                    Q(estate_review__profile=profile) |
                    Q(important_document_review__profile=profile)
                ).exclude(
                    next_review_due__isnull=True
                ).select_related(
                    'account_review', 'device_review',
                    'estate_review', 'important_document_review'
                ).order_by('next_review_due')[:5]
            else:
                context.update({
                    'soonest_review': None,
                    'first_delta':    None,
                    'alert_due':      False,
                    'alert_attention': False,
                })
                upcoming_reviews = RelevanceReview.objects.none()

            context['upcoming_reviews']  = upcoming_reviews
            context['today']             = datetime.now().date()
            context['week_from_now']     = datetime.now().date() + timedelta(days=7)

            context['tier_display']  = user.get_tier_display_name()
            context['can_modify']    = user.can_modify_data()
            context['can_view']      = user.can_view_data()
            context['is_free_tier']  = user.is_free_tier()

            context['show_onboarding'] = self._should_show_onboarding(context)

        except Profile.DoesNotExist:
            messages.warning(self.request, "Profile not found. Please create your profile.")
            return redirect(reverse("dashboard:profile_create"))

        return context

    def _should_show_onboarding(self, context):
        completed = sum([
            1 if context.get('accounts_count', 0)    > 0 else 0,
            1 if context.get('devices_count', 0)     > 0 else 0,
            1 if context.get('contacts_count', 0)    > 0 else 0,
            1 if context.get('estates_count', 0)     > 0 else 0,
            1 if context.get('documents_count', 0)   > 0 else 0,
            1 if context.get('family_knows_count', 0)> 0 else 0,
        ])
        return completed < 3

    def _get_tier_targets(self, user):
        """Return per-category display targets based on the user's subscription tier."""
        if user.subscription_tier == 'legacy':
            return {
                'contacts':     5,
                'accounts':    10,
                'devices':      5,
                'estates':      3,
                'documents':    8,
                'family_knows': 5,
            }
        elif user.subscription_tier == 'essentials':
            lim = user.ESSENTIAL_TIER_LIMITS
            return {
                'contacts':     lim['contacts'],
                'accounts':     lim['accounts'],
                'devices':      lim['devices'],
                'estates':      lim['estate_documents'],
                'documents':    lim['important_documents'],
                'family_knows': lim['family_awareness'],
            }
        else:  # free / none
            lim = user.FREE_TIER_LIMITS
            return {
                'contacts':     lim['contacts'],
                'accounts':     lim['accounts'],
                'devices':      lim['devices'],
                'estates':      lim['estate_documents'],
                'documents':    lim['important_documents'],
                'family_knows': lim['family_awareness'],
            }

    def _calculate_progress(self, targets, **kwargs):
        criteria = {
            'accounts':     {'weight': 0.25, 'target': targets['accounts']},
            'devices':      {'weight': 0.15, 'target': targets['devices']},
            'contacts':     {'weight': 0.10, 'target': targets['contacts']},
            'estates':      {'weight': 0.25, 'target': targets['estates']},
            'documents':    {'weight': 0.15, 'target': targets['documents']},
            'family_knows': {'weight': 0.10, 'target': targets['family_knows']},
        }
        total = 0
        for key, cfg in criteria.items():
            count  = kwargs.get(key, 0)
            total += min(count / cfg['target'], 1.0) * cfg['weight']
        return round(total * 100)

    def _calculate_remaining_tasks(self, **kwargs):
        tasks = [
            ('accounts', 1), ('devices', 1), ('contacts', 1),
            ('estates', 1),  ('documents', 1), ('family_knows', 1),
        ]
        return sum(1 for key, threshold in tasks if kwargs.get(key, 0) < threshold)

    def _get_account_categories(self, profile):
        from django.db.models import Count
        cats = (
            Account.objects
            .filter(profile=profile)
            .values('account_category')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        return {c['account_category']: c['count'] for c in cats}

    def _get_review_stats(self, profile):
        from datetime import date
        review_dates = RelevanceReview.objects.filter(
            Q(account_review__profile=profile) |
            Q(device_review__profile=profile) |
            Q(estate_review__profile=profile) |
            Q(important_document_review__profile=profile)
        ).exclude(next_review_due__isnull=True).aggregate(soonest=Min('next_review_due'))

        soonest = review_dates['soonest']
        stats = {
            'soonest_review':   soonest,
            'first_delta':      None,
            'alert_due':        False,
            'alert_attention':  False,
        }
        if soonest:
            delta = soonest - date.today()
            stats['first_delta'] = delta
            if delta.days <= 0:
                stats['alert_due'] = True
            elif delta.days <= 7:
                stats['alert_attention'] = True
        return stats


# ============================================================================
# PROFILE VIEWS
# ============================================================================

class ProfileCreateView(LoginRequiredMixin, CreateView):
    model         = Profile
    form_class    = ProfileForm
    template_name = 'dashboard/profiles/profile.html'
    success_url   = reverse_lazy('dashboard:onboarding_welcome')
    login_url     = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        try:
            _ = user.profile
            messages.info(request, "You already have a profile. Use the edit page to make changes.")
            return redirect(reverse('dashboard:profile_detail'))
        except Profile.DoesNotExist:
            pass
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Profile created! Let\'s set up your estate plan.')
        super().form_valid(form)
        return redirect(reverse('dashboard:onboarding_welcome'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_initial_setup'] = True
        context['page_title']       = 'Create Your Profile'
        context['submit_text']      = 'Create Profile & Continue'
        return context


class ProfileDetailView(ViewAccessMixin, DetailView):
    """
    Profile detail — no slug in the URL; object is always the
    current user's profile fetched via get_or_create.
    """
    model               = Profile
    template_name       = 'dashboard/profiles/profile_detail.html'
    context_object_name = 'profile'
    owner_field         = 'user'

    def get_object(self, queryset=None):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model         = Profile
    form_class    = ProfileForm
    template_name = 'dashboard/profiles/profile_form.html'
    success_url   = reverse_lazy('dashboard:dashboard_home')
    login_url     = '/accounts/login/'

    def get_object(self, queryset=None):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully.')
        return super().form_valid(form)


# ============================================================================
# ACCOUNT VIEWS
# ============================================================================

class AccountListView(LapsedViewLimitMixin, ViewAccessMixin, ListView):
    model               = Account
    template_name       = 'dashboard/accounts/account_list.html'
    context_object_name = 'accounts'
    owner_field         = 'profile__user'
    paginate_by         = 5
    free_tier_item      = 'accounts'

    def get_queryset(self):
        try:
            profile  = Profile.objects.get(user=self.request.user)
            queryset = Account.objects.filter(profile=profile)

            category_id = self.request.GET.get('account_category')
            if category_id:
                queryset = queryset.filter(account_category=category_id)

            return queryset.order_by('-created_at')
        except Profile.DoesNotExist:
            return Account.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data() or self.request.user.is_free_tier()
        return context


class AccountPrintView(ViewAccessMixin, TemplateView):
    template_name = 'dashboard/accounts/account_print.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            profile  = Profile.objects.get(user=user)
            accounts = Account.objects.filter(profile=profile).order_by('account_category', 'account_name_or_provider')
        except Profile.DoesNotExist:
            accounts = Account.objects.none()

        context['accounts']       = accounts
        context['account_count']  = accounts.count()
        context['user_full_name'] = f"{user.first_name} {user.last_name}".strip() or user.username
        today = timezone.localdate()
        context['print_date']     = f"{today.strftime('%B')} {today.day}, {today.year}"
        return context


class AccountDetailView(SlugLookupMixin, ViewAccessMixin, DetailView):
    model               = Account
    template_name       = 'dashboard/accounts/account_detail.html'
    context_object_name = 'account'
    owner_field         = 'profile__user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        from infrapps.models import VaultEntry
        context['has_vault_entry'] = VaultEntry.objects.filter(
            linked_account=self.object
        ).exists()
        return context


class AccountCreateView(FreeTierLimitMixin, FullAccessMixin, CreateView):
    free_tier_item = 'accounts'
    model         = Account
    form_class    = AccountForm
    template_name = 'dashboard/accounts/account_form.html'
    success_url   = reverse_lazy('dashboard:account_list')
    owner_field   = 'profile__user'

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Digital account created successfully.')
        return super().form_valid(form)


class AccountUpdateView(SlugLookupMixin, FullAccessMixin, UpdateView):
    model         = Account
    form_class    = AccountForm
    template_name = 'dashboard/accounts/account_form.html'
    success_url   = reverse_lazy('dashboard:account_list')
    owner_field   = 'profile__user'

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Digital account updated successfully.')
        return super().form_valid(form)


class AccountDeleteView(SlugLookupMixin, DeleteAccessMixin, DeleteView):
    model         = Account
    template_name = 'dashboard/accounts/account_confirm_delete.html'
    success_url   = reverse_lazy('dashboard:account_list')
    owner_field   = 'profile__user'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Account deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# DEVICE VIEWS
# ============================================================================

class DeviceListView(LapsedViewLimitMixin, ViewAccessMixin, ListView):
    model               = Device
    template_name       = 'dashboard/devices/device_list.html'
    context_object_name = 'devices'
    owner_field         = 'profile__user'
    paginate_by         = 10
    free_tier_item      = 'devices'

    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return Device.objects.filter(profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return Device.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data() or self.request.user.is_free_tier()
        return context


class DevicePrintView(ViewAccessMixin, TemplateView):
    template_name = 'dashboard/devices/device_print.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            profile = Profile.objects.get(user=user)
            devices = Device.objects.filter(profile=profile).order_by('device_type', 'device_name')
        except Profile.DoesNotExist:
            devices = Device.objects.none()

        context['devices']        = devices
        context['device_count']   = devices.count()
        context['user_full_name'] = f"{user.first_name} {user.last_name}".strip() or user.username
        today = timezone.localdate()
        context['print_date']     = f"{today.strftime('%B')} {today.day}, {today.year}"
        return context


class DeviceDetailView(SlugLookupMixin, ViewAccessMixin, DetailView):
    model               = Device
    template_name       = 'dashboard/devices/device_detail.html'
    context_object_name = 'device'
    owner_field         = 'profile__user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        from infrapps.models import VaultEntry
        context['has_vault_entry'] = VaultEntry.objects.filter(
            linked_device=self.object
        ).exists()
        return context


class DeviceCreateView(FreeTierLimitMixin, FullAccessMixin, CreateView):
    free_tier_item = 'devices'
    model         = Device
    form_class    = DeviceForm
    template_name = 'dashboard/devices/device_form.html'
    success_url   = reverse_lazy('dashboard:device_list')
    owner_field   = 'profile__user'

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Device created successfully.')
        return super().form_valid(form)


class DeviceUpdateView(SlugLookupMixin, FullAccessMixin, UpdateView):
    model         = Device
    form_class    = DeviceForm
    template_name = 'dashboard/devices/device_form.html'
    success_url   = reverse_lazy('dashboard:device_list')
    owner_field   = 'profile__user'

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Device updated successfully.')
        return super().form_valid(form)


class DeviceDeleteView(SlugLookupMixin, DeleteAccessMixin, DeleteView):
    model         = Device
    template_name = 'dashboard/devices/device_confirm_delete.html'
    success_url   = reverse_lazy('dashboard:device_list')
    owner_field   = 'profile__user'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Device deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# ESTATE DOCUMENT VIEWS
# ============================================================================

class EstateListView(LapsedViewLimitMixin, ViewAccessMixin, ListView):
    model               = DigitalEstateDocument
    template_name       = 'dashboard/estates/estate_list.html'
    context_object_name = 'estates'
    owner_field         = 'profile__user'
    paginate_by         = 10
    free_tier_item      = 'estate_documents'

    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return DigitalEstateDocument.objects.filter(profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return DigitalEstateDocument.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data() or self.request.user.is_free_tier()
        return context


class EstatePrintView(ViewAccessMixin, TemplateView):
    template_name = 'dashboard/estates/estate_print.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            profile = Profile.objects.get(user=user)
            estates = DigitalEstateDocument.objects.filter(profile=profile).order_by('estate_category', 'name_or_title')
        except Profile.DoesNotExist:
            estates = DigitalEstateDocument.objects.none()

        context['estates']        = estates
        context['estate_count']   = estates.count()
        context['user_full_name'] = f"{user.first_name} {user.last_name}".strip() or user.username
        today = timezone.localdate()
        context['print_date']     = f"{today.strftime('%B')} {today.day}, {today.year}"
        return context


class EstateDetailView(SlugLookupMixin, ViewAccessMixin, DetailView):
    model               = DigitalEstateDocument
    template_name       = 'dashboard/estates/estate_detail.html'
    context_object_name = 'estate'
    owner_field         = 'profile__user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class EstateCreateView(FreeTierLimitMixin, FullAccessMixin, CreateView):
    free_tier_item = 'estate_documents'
    model         = DigitalEstateDocument
    form_class    = DigitalEstateDocumentForm
    template_name = 'dashboard/estates/estate_form.html'
    success_url   = reverse_lazy('dashboard:estate_list')
    owner_field   = 'profile__user'

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Estate document created successfully.')
        return super().form_valid(form)


class EstateUpdateView(SlugLookupMixin, FullAccessMixin, UpdateView):
    model         = DigitalEstateDocument
    form_class    = DigitalEstateDocumentForm
    template_name = 'dashboard/estates/estate_form.html'
    success_url   = reverse_lazy('dashboard:estate_list')
    owner_field   = 'profile__user'

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Estate document updated successfully.')
        return super().form_valid(form)


class EstateDeleteView(SlugLookupMixin, DeleteAccessMixin, DeleteView):
    model         = DigitalEstateDocument
    template_name = 'dashboard/estates/estate_confirm_delete.html'
    success_url   = reverse_lazy('dashboard:estate_list')
    owner_field   = 'profile__user'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Estate document deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# FAMILY AWARENESS VIEWS
# ============================================================================

class FamilyAwarenessListView(LapsedViewLimitMixin, ViewAccessMixin, ListView):
    model               = FamilyNeedsToKnowSection
    template_name       = 'dashboard/familyaware/familyawareness_list.html'
    context_object_name = 'familyawareness_objects'
    owner_field         = 'relation__profile__user'
    paginate_by         = 10
    free_tier_item      = 'family_awareness'

    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return FamilyNeedsToKnowSection.objects.filter(
                relation__profile=profile
            ).order_by('-created_at')
        except Profile.DoesNotExist:
            return FamilyNeedsToKnowSection.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data() or self.request.user.is_free_tier()
        return context


class FamilyAwarenessPrintView(ViewAccessMixin, TemplateView):
    template_name = 'dashboard/familyaware/familyawareness_print.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            profile = Profile.objects.get(user=user)
            items   = FamilyNeedsToKnowSection.objects.filter(relation__profile=profile).order_by('relation', 'created_at')
        except Profile.DoesNotExist:
            items = FamilyNeedsToKnowSection.objects.none()

        context['familyawareness_objects'] = items
        context['item_count']              = items.count()
        context['user_full_name']          = f"{user.first_name} {user.last_name}".strip() or user.username
        today = timezone.localdate()
        context['print_date']              = f"{today.strftime('%B')} {today.day}, {today.year}"
        return context


class FamilyAwarenessDetailView(SlugLookupMixin, ViewAccessMixin, DetailView):
    model               = FamilyNeedsToKnowSection
    template_name       = 'dashboard/familyaware/familyawareness_detail.html'
    context_object_name = 'familyawareness'
    owner_field         = 'relation__profile__user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class FamilyAwarenessCreateView(FreeTierLimitMixin, FullAccessMixin, CreateView):
    model          = FamilyNeedsToKnowSection
    form_class     = FamilyNeedsToKnowSectionForm
    template_name  = 'dashboard/familyaware/familyawareness_form.html'
    success_url    = reverse_lazy('dashboard:familyawareness_list')
    owner_field    = 'relation__profile__user'
    free_tier_item = 'family_awareness'
    count_filter   = 'relation__profile__user'

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Family awareness section created successfully.')
        return super().form_valid(form)


class FamilyAwarenessUpdateView(SlugLookupMixin, FullAccessMixin, UpdateView):
    model         = FamilyNeedsToKnowSection
    form_class    = FamilyNeedsToKnowSectionForm
    template_name = 'dashboard/familyaware/familyawareness_form.html'
    success_url   = reverse_lazy('dashboard:familyawareness_list')
    owner_field   = 'relation__profile__user'

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Family awareness section updated successfully.')
        return super().form_valid(form)


class FamilyAwarenessDeleteView(SlugLookupMixin, DeleteAccessMixin, DeleteView):
    model         = FamilyNeedsToKnowSection
    template_name = 'dashboard/familyaware/familyawareness_confirm_delete.html'
    success_url   = reverse_lazy('dashboard:familyawareness_list')
    owner_field   = 'relation__profile__user'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Family awareness section deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# IMPORTANT DOCUMENT VIEWS
# ============================================================================

class ImportantDocumentListView(LapsedViewLimitMixin, ViewAccessMixin, ListView):
    model               = ImportantDocument
    template_name       = 'dashboard/importantdocuments/importantdocument_list.html'
    context_object_name = 'documents'
    owner_field         = 'profile__user'
    paginate_by         = 10
    free_tier_item      = 'important_documents'

    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return ImportantDocument.objects.filter(profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return ImportantDocument.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data() or self.request.user.is_free_tier()
        return context


class ImportantDocumentPrintView(ViewAccessMixin, TemplateView):
    template_name = 'dashboard/importantdocuments/importantdocument_print.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            profile   = Profile.objects.get(user=user)
            documents = ImportantDocument.objects.filter(profile=profile).order_by('document_category', 'name_or_title')
        except Profile.DoesNotExist:
            documents = ImportantDocument.objects.none()

        context['documents']      = documents
        context['document_count'] = documents.count()
        context['user_full_name'] = f"{user.first_name} {user.last_name}".strip() or user.username
        today = timezone.localdate()
        context['print_date']     = f"{today.strftime('%B')} {today.day}, {today.year}"
        return context


class ImportantDocumentDetailView(SlugLookupMixin, ViewAccessMixin, DetailView):
    model               = ImportantDocument
    template_name       = 'dashboard/importantdocuments/importantdocument_detail.html'
    context_object_name = 'document'
    owner_field         = 'profile__user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class ImportantDocumentCreateView(FreeTierLimitMixin, FullAccessMixin, CreateView):
    free_tier_item = 'important_documents'
    model         = ImportantDocument
    form_class    = ImportantDocumentForm
    template_name = 'dashboard/importantdocuments/importantdocument_form.html'
    success_url   = reverse_lazy('dashboard:importantdocument_list')
    owner_field   = 'profile__user'

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Document created successfully.')
        return super().form_valid(form)


class ImportantDocumentUpdateView(SlugLookupMixin, FullAccessMixin, UpdateView):
    model         = ImportantDocument
    form_class    = ImportantDocumentForm
    template_name = 'dashboard/importantdocuments/importantdocument_form.html'
    success_url   = reverse_lazy('dashboard:importantdocument_list')
    owner_field   = 'profile__user'

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Document updated successfully.')
        return super().form_valid(form)


class ImportantDocumentDeleteView(SlugLookupMixin, DeleteAccessMixin, DeleteView):
    model         = ImportantDocument
    template_name = 'dashboard/importantdocuments/importantdocument_confirm_delete.html'
    success_url   = reverse_lazy('dashboard:importantdocument_list')
    owner_field   = 'profile__user'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Document deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# CONTACT VIEWS
# ============================================================================

class ContactListView(LapsedViewLimitMixin, ViewAccessMixin, ListView):
    model               = Contact
    template_name       = 'dashboard/contacts/contact_list.html'
    context_object_name = 'contacts'
    owner_field         = 'profile__user'
    paginate_by         = 20
    free_tier_item      = 'contacts'

    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return Contact.objects.filter(profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return Contact.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data() or self.request.user.is_free_tier()
        return context


class ContactDetailView(SlugLookupMixin, ViewAccessMixin, DetailView):
    model               = Contact
    template_name       = 'dashboard/contacts/contact_detail.html'
    context_object_name = 'contact'
    owner_field         = 'profile__user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()

        contact = self.object
        estate_docs    = DigitalEstateDocument.objects.filter(delegated_estate_to=contact).order_by('name_or_title')
        important_docs = ImportantDocument.objects.filter(delegated_important_document_to=contact).order_by('name_or_title')
        devices_listed = Device.objects.filter(delegated_device_to=contact).order_by('device_name')
        accounts_listed= Account.objects.filter(delegated_account_to=contact).order_by('account_name_or_provider')
        family_listed  = FamilyNeedsToKnowSection.objects.filter(relation=contact).order_by('-updated_at')

        context['delegated_estate_documents']    = estate_docs
        context['delegated_important_documents'] = important_docs
        context['delegated_devices']             = devices_listed
        context['delegated_accounts']            = accounts_listed
        context['family_notes']                  = family_listed
        context['total_assignments'] = (
            estate_docs.count() + important_docs.count() +
            devices_listed.count() + accounts_listed.count()
            + family_listed.count()
        )
        return context


class ContactCreateView(FreeTierLimitMixin, FullAccessMixin, CreateView):
    free_tier_item = 'contacts'
    model         = Contact
    form_class    = ContactForm
    template_name = 'dashboard/contacts/contact_form.html'
    success_url   = reverse_lazy('dashboard:contact_list')
    owner_field   = 'profile__user'

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Contact created successfully.')
        return super().form_valid(form)


class ContactUpdateView(SlugLookupMixin, FullAccessMixin, UpdateView):
    model         = Contact
    form_class    = ContactForm
    template_name = 'dashboard/contacts/contact_form.html'
    success_url   = reverse_lazy('dashboard:contact_list')
    owner_field   = 'profile__user'

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Contact updated successfully.')
        return super().form_valid(form)


class ContactDeleteView(SlugLookupMixin, DeleteAccessMixin, DeleteView):
    model         = Contact
    template_name = 'dashboard/contacts/contact_confirm_delete.html'
    success_url   = reverse_lazy('dashboard:contact_list')
    owner_field   = 'profile__user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = self.object

        estate_docs      = DigitalEstateDocument.objects.filter(delegated_estate_to=contact).select_related('profile')
        important_docs   = ImportantDocument.objects.filter(delegated_important_document_to=contact).select_related('profile')
        assigned_accounts= Account.objects.filter(delegated_account_to=contact).select_related('profile')
        assigned_devices = Device.objects.filter(delegated_device_to=contact).select_related('profile')
        family_notes     = FamilyNeedsToKnowSection.objects.filter(relation=contact).select_related('relation')

        context['estate_documents']    = estate_docs
        context['important_documents'] = important_docs
        context['assigned_accounts']   = assigned_accounts
        context['assigned_devices']    = assigned_devices
        context['family_notes']        = family_notes

        context['total_documents']     = estate_docs.count() + important_docs.count()
        context['total_accounts']      = assigned_accounts.count()
        context['total_devices']       = assigned_devices.count()
        context['total_notes']        =  family_notes.count()
        context['has_assignments']     = (
            estate_docs.exists() or important_docs.exists() or
            assigned_accounts.exists() or assigned_devices.exists()
            or family_notes.exists()
        )

        if context['has_assignments']:
            other_contacts = Contact.objects.filter(
                profile=contact.profile
            ).exclude(id=contact.id).order_by('last_name')
            context['other_contacts']     = other_contacts
            context['has_other_contacts'] = other_contacts.exists()

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        contact = self.object

        estate_count      = DigitalEstateDocument.objects.filter(delegated_estate_to=contact).count()
        important_count   = ImportantDocument.objects.filter(delegated_important_document_to=contact).count()
        account_count     = Account.objects.filter(delegated_account_to=contact).count()
        device_count      = Device.objects.filter(delegated_device_to=contact).count()
        family_note_count = FamilyNeedsToKnowSection.objects.filter(relation=contact).count()
        total_restrictions = estate_count + important_count + account_count + device_count + family_note_count

        if total_restrictions > 0:
            messages.error(
                request,
                f'Cannot delete {contact.first_name} {contact.last_name} because they have '
                f'{total_restrictions} item(s) assigned to them '
                # f'({estate_count} estate, {important_count} important, '
                # f'{account_count} account, {device_count} device). '
                # f'{family_note_count} family notes. '
                f'Please reassign these to another contact first.'
            )
            return HttpResponseRedirect(
                reverse('dashboard:contact_detail', kwargs={'slug': contact.slug})
            )

        try:
            return self.delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                f'Cannot delete {contact.first_name} {contact.last_name} because they have '
                'items assigned. Please reassign them first.'
            )
            return HttpResponseRedirect(
                reverse('dashboard:contact_detail', kwargs={'slug': contact.slug})
            )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        contact_name = f"{self.object.first_name} {self.object.last_name}"
        messages.success(request, f'Contact "{contact_name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# FUNERAL PLAN VIEWS
# ============================================================================

class FuneralPlanMixin(LoginRequiredMixin):
    """
    Shared base for all funeral-plan step views.
    Enforces payment and profile prerequisites.
    """
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.subscription_tier != 'legacy' or not user.can_view_data():
            messages.warning(request, "Funeral Planning is included with the Legacy plan.")
            return redirect(reverse("accounts:payment"))
        try:
            _ = user.profile
        except Profile.DoesNotExist:
            messages.info(request, "Please create your profile first.")
            return redirect(reverse("dashboard:profile_create"))
        return super().dispatch(request, *args, **kwargs)

    def get_or_create_plan(self):
        profile = self.request.user.profile
        plan, created = FuneralPlan.objects.get_or_create(profile=profile)
        return plan, created

    def get_plan_progress(self):
        plan, _ = self.get_or_create_plan()
        return {
            'plan':          plan,
            'personal_info': any([plan.preferred_name, plan.occupation, plan.marital_status,
                                  plan.religion_or_spiritual_affiliation, plan.is_veteran]),
            'service':       any([plan.service_type, plan.preferred_funeral_home,
                                  plan.preferred_venue, plan.officiant_contact,
                                  plan.officiant_name_freetext, plan.desired_timing,
                                  plan.open_casket_viewing]),
            'disposition':   any([plan.disposition_method, plan.burial_or_interment_location,
                                  plan.casket_type_preference, plan.urn_type_preference,
                                  plan.headstone_or_marker_inscription]),
            'ceremony':      any([plan.music_choices, plan.flowers_or_colors,
                                  plan.readings_poems_or_scriptures, plan.eulogists_notes,
                                  plan.pallbearers_notes]),
            'reception':     plan.reception_desired is not None or bool(plan.reception_location),
            'obituary':      any([plan.obituary_key_achievements, plan.obituary_photo_description,
                                  plan.obituary_publications, plan.charitable_donations_in_lieu]),
            'admin':         any([plan.payment_arrangements, plan.funeral_insurance_policy_number,
                                  plan.death_certificates_requested]),
            'instructions':  bool(plan.additional_instructions),
            'is_complete':   plan.is_complete,
        }

    def _base_context(self):
        return {
            'progress':    self.get_plan_progress(),
            'total_steps': 8,
            'can_modify':  self.request.user.can_modify_data(),
        }


class FuneralPlanIndexView(FuneralPlanMixin, TemplateView):
    template_name = 'dashboard/funeralplan/funeralplan_index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan, created = self.get_or_create_plan()
        if created:
            messages.info(self.request, "We've started your funeral plan. Complete each section at your own pace.")
        context.update(self._base_context())
        context['plan']       = plan
        context['page_title'] = "My Funeral Plan"
        return context


class FuneralPlanDetailView(FuneralPlanMixin, TemplateView):
    template_name = 'dashboard/funeralplan/funeralplan_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan, _ = self.get_or_create_plan()
        context.update(self._base_context())
        context['plan']       = plan
        context['page_title'] = "Funeral Plan Summary"

        context['has_personal_info'] = any([
            plan.preferred_name, plan.occupation,
            plan.marital_status, plan.religion_or_spiritual_affiliation,
            plan.is_veteran,
        ])
        context['has_service_prefs'] = any([
            plan.service_type, plan.preferred_funeral_home,
            plan.preferred_venue, plan.officiant_contact,
            plan.officiant_name_freetext, plan.desired_timing,
            plan.open_casket_viewing,
        ])
        context['has_disposition'] = any([
            plan.disposition_method, plan.burial_or_interment_location,
            plan.casket_type_preference, plan.urn_type_preference,
            plan.headstone_or_marker_inscription,
        ])
        context['has_ceremony'] = any([
            plan.music_choices, plan.flowers_or_colors,
            plan.readings_poems_or_scriptures, plan.eulogists_notes,
            plan.pallbearers_notes, plan.clothing_or_jewelry_description,
            plan.religious_cultural_customs, plan.items_to_display,
        ])
        context['has_reception'] = any([
            plan.reception_desired, plan.reception_location,
            plan.reception_food_preferences, plan.reception_atmosphere_notes,
            plan.reception_guest_list_notes,
        ])
        context['has_obituary'] = any([
            plan.obituary_photo_description, plan.obituary_key_achievements,
            plan.obituary_publications, plan.charitable_donations_in_lieu,
        ])
        context['has_admin'] = any([
            plan.funeral_insurance_policy_number,
            plan.death_certificates_requested,
            plan.payment_arrangements,
        ])
        context['has_instructions'] = bool(plan.additional_instructions)
        return context


class FuneralPlanPrintView(FuneralPlanMixin, TemplateView):
    template_name = 'dashboard/funeralplan/funeralplan_print.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan, _ = self.get_or_create_plan()
        context.update(self._base_context())
        context['plan']       = plan
        context['page_title'] = "Print Funeral Plan"

        user = self.request.user
        context['user_full_name'] = (
            f"{user.first_name} {user.last_name}".strip() or user.username
        )
        today = timezone.localdate()
        context['print_date'] = f"{today.strftime('%B')} {today.day}, {today.year}"

        context['has_personal_info'] = any([
            plan.preferred_name, plan.occupation,
            plan.marital_status, plan.religion_or_spiritual_affiliation,
            plan.is_veteran,
        ])
        context['has_service_prefs'] = any([
            plan.service_type, plan.preferred_funeral_home,
            plan.preferred_venue, plan.officiant_contact,
            plan.officiant_name_freetext, plan.desired_timing,
            plan.open_casket_viewing,
        ])
        context['has_disposition'] = any([
            plan.disposition_method, plan.burial_or_interment_location,
            plan.casket_type_preference, plan.urn_type_preference,
            plan.headstone_or_marker_inscription,
        ])
        context['has_ceremony'] = any([
            plan.music_choices, plan.flowers_or_colors,
            plan.readings_poems_or_scriptures, plan.eulogists_notes,
            plan.pallbearers_notes, plan.clothing_or_jewelry_description,
            plan.religious_cultural_customs, plan.items_to_display,
        ])
        context['has_reception'] = any([
            plan.reception_desired, plan.reception_location,
            plan.reception_food_preferences, plan.reception_atmosphere_notes,
            plan.reception_guest_list_notes,
        ])
        context['has_obituary'] = any([
            plan.obituary_photo_description, plan.obituary_key_achievements,
            plan.obituary_publications, plan.charitable_donations_in_lieu,
        ])
        context['has_admin'] = any([
            plan.funeral_insurance_policy_number,
            plan.death_certificates_requested,
            plan.payment_arrangements,
        ])
        context['has_instructions'] = bool(plan.additional_instructions)
        return context


class _FuneralPlanStepBase(FuneralPlanMixin, TemplateView):
    """
    Abstract base for the 8 section step views.
    Subclasses must define form_class, step, section_label, next_url, and prev_url.
    """
    template_name = 'dashboard/funeralplan/funeralplan_step.html'
    form_class    = None
    step          = None
    section_label = ''
    next_url      = None
    prev_url      = None  # None means first step (goes back to overview)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan, _ = self.get_or_create_plan()
        context.update(self._base_context())
        context['plan']          = plan
        context['step']          = self.step
        context['section_label'] = self.section_label
        context['page_title']    = f"Step {self.step} — {self.section_label}"
        context['prev_url']      = self.prev_url
        if 'form' not in context:
            context['form'] = self.form_class(instance=plan, user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.can_modify_data():
            messages.error(request, "You don't have permission to edit your funeral plan.")
            return redirect(reverse('dashboard:funeralplan_index'))

        plan, _ = self.get_or_create_plan()
        form = self.form_class(request.POST, instance=plan, user=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, f'"{self.section_label}" saved successfully.')
            return redirect(
                reverse(self.next_url) if self.next_url
                else reverse('dashboard:funeralplan_detail')
            )

        context = self.get_context_data()
        context['form'] = form
        messages.error(request, "Please correct the errors below.")
        return self.render_to_response(context)


class FuneralPlanStep1View(_FuneralPlanStepBase):
    form_class    = FuneralPlanPersonalInfoForm
    step          = 1
    section_label = "Personal Information"
    prev_url      = None  # first step → overview
    next_url      = 'dashboard:funeralplan_step2'


class FuneralPlanStep2View(_FuneralPlanStepBase):
    form_class    = FuneralPlanServiceForm
    step          = 2
    section_label = "Service Preferences"
    prev_url      = 'dashboard:funeralplan_step1'
    next_url      = 'dashboard:funeralplan_step3'


class FuneralPlanStep3View(_FuneralPlanStepBase):
    form_class    = FuneralPlanDispositionForm
    step          = 3
    section_label = "Final Disposition"
    prev_url      = 'dashboard:funeralplan_step2'
    next_url      = 'dashboard:funeralplan_step4'


class FuneralPlanStep4View(_FuneralPlanStepBase):
    form_class    = FuneralPlanCeremonyForm
    step          = 4
    section_label = "Ceremony Personalization"
    prev_url      = 'dashboard:funeralplan_step3'
    next_url      = 'dashboard:funeralplan_step5'


class FuneralPlanStep5View(_FuneralPlanStepBase):
    form_class    = FuneralPlanReceptionForm
    step          = 5
    section_label = "Reception / Gathering"
    prev_url      = 'dashboard:funeralplan_step4'
    next_url      = 'dashboard:funeralplan_step6'


class FuneralPlanStep6View(_FuneralPlanStepBase):
    form_class    = FuneralPlanObituaryForm
    step          = 6
    section_label = "Obituary & Memorial"
    prev_url      = 'dashboard:funeralplan_step5'
    next_url      = 'dashboard:funeralplan_step7'


class FuneralPlanStep7View(_FuneralPlanStepBase):
    form_class    = FuneralPlanAdminForm
    step          = 7
    section_label = "Administrative & Financial"
    prev_url      = 'dashboard:funeralplan_step6'
    next_url      = 'dashboard:funeralplan_step8'


class FuneralPlanStep8View(_FuneralPlanStepBase):
    form_class    = FuneralPlanInstructionsForm
    step          = 8
    section_label = "Additional Instructions"
    prev_url      = 'dashboard:funeralplan_step7'
    next_url      = None  # last step → summary



class FuneralPlanDeleteView(FuneralPlanMixin, TemplateView):
    template_name = 'dashboard/funeralplan/funeralplan_confirm_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan, _ = self.get_or_create_plan()
        context.update(self._base_context())
        context['plan']       = plan
        context['page_title'] = "Delete Funeral Plan"
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.can_modify_data():
            messages.error(request, "You don't have permission to delete your funeral plan.")
            return redirect(reverse('dashboard:funeralplan_index'))

        if request.POST.get('confirm_text', '').strip() != 'DELETE':
            messages.error(request, "Deletion cancelled. Type DELETE (all caps) to confirm.")
            return self.get(request, *args, **kwargs)

        try:
            plan = FuneralPlan.objects.get(profile=request.user.profile)
            plan.delete()
            messages.warning(request, "Your funeral plan has been permanently deleted.")
        except FuneralPlan.DoesNotExist:
            messages.info(request, "No funeral plan was found to delete.")

        return redirect(reverse('dashboard:funeralplan_index'))


class FuneralPlanUpdateView(FuneralPlanMixin, TemplateView):
    """Full-plan edit view — renders all 8 sections in one scrollable form."""
    template_name = 'dashboard/funeralplan/funeralplan_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan, _ = self.get_or_create_plan()
        context.update(self._base_context())
        context['plan']        = plan
        context['object']      = plan
        context['page_title']  = "Edit Funeral Plan"
        context['form_action'] = "Update"
        if 'form' not in context:
            context['form'] = FuneralPlanFullForm(instance=plan, user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.can_modify_data():
            messages.error(request, "You don't have permission to edit your funeral plan.")
            return redirect(reverse('dashboard:funeralplan_index'))

        plan, _ = self.get_or_create_plan()
        form = FuneralPlanFullForm(request.POST, instance=plan, user=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Your funeral plan has been updated.")
            return redirect(reverse('dashboard:funeralplan_detail'))

        context = self.get_context_data()
        context['form'] = form
        messages.error(request, "Please correct the errors below.")
        return self.render_to_response(context)


# ============================================================================
# RELEVANCE REVIEW VIEWS
# ============================================================================

class RelevanceReviewListView(LoginRequiredMixin, ListView):
    model               = RelevanceReview
    template_name       = 'dashboard/relevancereview_list.html'
    context_object_name = 'reviews'
    paginate_by         = 5
    login_url           = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_subscription_active():
            messages.warning(request, 'An active subscription is required to access reviews.')
            return redirect(reverse("accounts:payment"))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            qs = RelevanceReview.objects.filter(
                Q(account_review__profile=profile) |
                Q(device_review__profile=profile) |
                Q(estate_review__profile=profile) |
                Q(important_document_review__profile=profile)
            ).select_related(
                'account_review', 'device_review',
                'estate_review', 'important_document_review', 'reviewer'
            )

            filter_type = self.request.GET.get('type')
            item_slug   = self.request.GET.get('item_slug')

            if filter_type == 'account' and item_slug:
                qs = qs.filter(account_review__slug=item_slug)
            elif filter_type == 'device' and item_slug:
                qs = qs.filter(device_review__slug=item_slug)
            elif filter_type == 'estate' and item_slug:
                qs = qs.filter(estate_review__slug=item_slug)
            elif filter_type == 'important' and item_slug:
                qs = qs.filter(important_document_review__slug=item_slug)

            return qs.order_by(F('next_review_due').asc(nulls_last=True))
        except Profile.DoesNotExist:
            return RelevanceReview.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()

        filter_type = self.request.GET.get('type')
        item_slug   = self.request.GET.get('item_slug')

        if filter_type and item_slug:
            try:
                if filter_type == 'account':
                    context['filtered_item'] = Account.objects.get(slug=item_slug, profile__user=self.request.user)
                    context['filtered_type'] = 'Account'
                elif filter_type == 'device':
                    context['filtered_item'] = Device.objects.get(slug=item_slug, profile__user=self.request.user)
                    context['filtered_type'] = 'Device'
                elif filter_type == 'estate':
                    context['filtered_item'] = DigitalEstateDocument.objects.get(slug=item_slug, profile__user=self.request.user)
                    context['filtered_type'] = 'Estate Document'
                elif filter_type == 'important':
                    context['filtered_item'] = ImportantDocument.objects.get(slug=item_slug, profile__user=self.request.user)
                    context['filtered_type'] = 'Important Document'
            except (Account.DoesNotExist, Device.DoesNotExist,
                    DigitalEstateDocument.DoesNotExist, ImportantDocument.DoesNotExist):
                pass

        return context


class RelevanceReviewDetailView(LoginRequiredMixin, DetailView):
    model               = RelevanceReview
    template_name       = 'dashboard/relevancereview_detail.html'
    context_object_name = 'review'
    slug_field          = 'slug'
    slug_url_kwarg      = 'slug'
    login_url           = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_subscription_active():
            messages.warning(request, 'An active subscription is required to access reviews.')
            return redirect(reverse("accounts:payment"))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        try:
            profile = Profile.objects.get(user=self.request.user)
            item    = obj.get_reviewed_item()
            if not item:
                raise PermissionDenied("Invalid review — no item found.")
            if hasattr(item, 'profile') and item.profile != profile:
                raise PermissionDenied("You don't have permission to view this review.")
        except Profile.DoesNotExist:
            raise PermissionDenied("Profile not found.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify']    = self.request.user.can_modify_data()
        review = self.object
        context['reviewed_item'] = review.get_reviewed_item()
        context['item_type']     = review.get_item_type()
        context['item_name']     = review.get_item_name()
        return context


class RelevanceReviewCreateView(LoginRequiredMixin, CreateView):
    model         = RelevanceReview
    form_class    = RelevanceReviewForm
    template_name = 'dashboard/relevancereview_form.html'
    login_url     = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_subscription_active():
            messages.warning(request, 'An active subscription is required to create reviews.')
            return redirect(reverse("accounts:payment"))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        filter_type = self.request.GET.get('type')
        item_slug   = self.request.GET.get('item_slug')
        if filter_type and item_slug:
            kwargs['initial'] = {'review_type': filter_type, 'item_slug': item_slug}
        return kwargs

    def form_valid(self, form):
        form.instance.reviewer = self.request.user
        if form.instance.account_review:
            item_name = form.instance.account_review.account_name_or_provider
            item_type = "account"
        elif form.instance.device_review:
            item_name = form.instance.device_review.device_name
            item_type = "device"
        elif form.instance.estate_review:
            item_name = form.instance.estate_review.name_or_title
            item_type = "estate document"
        elif form.instance.important_document_review:
            item_name = form.instance.important_document_review.name_or_title
            item_type = "important document"
        else:
            item_name = item_type = "item"

        messages.success(self.request, f'Review created successfully for {item_type}: {item_name}.')
        return super().form_valid(form)

    def get_success_url(self):
        review = self.object
        if review.account_review:
            return reverse_lazy('dashboard:account_detail',            kwargs={'slug': review.account_review.slug})
        elif review.device_review:
            return reverse_lazy('dashboard:device_detail',             kwargs={'slug': review.device_review.slug})
        elif review.estate_review:
            return reverse_lazy('dashboard:estate_detail',             kwargs={'slug': review.estate_review.slug})
        elif review.important_document_review:
            return reverse_lazy('dashboard:importantdocument_detail',  kwargs={'slug': review.important_document_review.slug})
        return reverse_lazy('dashboard:relevancereview_list')


class RelevanceReviewUpdateView(LoginRequiredMixin, UpdateView):
    model          = RelevanceReview
    form_class     = RelevanceReviewForm
    template_name  = 'dashboard/relevancereview_form.html'
    slug_field     = 'slug'
    slug_url_kwarg = 'slug'
    login_url      = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_subscription_active():
            messages.warning(request, 'An active subscription is required to edit reviews.')
            return redirect(reverse("accounts:payment"))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        try:
            profile = Profile.objects.get(user=self.request.user)
            item    = obj.get_reviewed_item()
            if not item:
                raise PermissionDenied("Invalid review — no item found.")
            if hasattr(item, 'profile') and item.profile != profile:
                raise PermissionDenied("You don't have permission to edit this review.")
        except Profile.DoesNotExist:
            raise PermissionDenied("Profile not found.")
        return obj

    def get_form_kwargs(self):
        kwargs         = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        item_name = form.instance.get_item_name()
        item_type = form.instance.get_item_type()
        messages.success(self.request, f'Review updated successfully for {item_type}: {item_name}.')
        return super().form_valid(form)

    def get_success_url(self):
        review = self.object
        if review.account_review:
            return reverse_lazy('dashboard:account_detail',           kwargs={'slug': review.account_review.slug})
        elif review.device_review:
            return reverse_lazy('dashboard:device_detail',            kwargs={'slug': review.device_review.slug})
        elif review.estate_review:
            return reverse_lazy('dashboard:estate_detail',            kwargs={'slug': review.estate_review.slug})
        elif review.important_document_review:
            return reverse_lazy('dashboard:importantdocument_detail', kwargs={'slug': review.important_document_review.slug})
        return reverse_lazy('dashboard:relevancereview_list')


class RelevanceReviewDeleteView(LoginRequiredMixin, DeleteView):
    model          = RelevanceReview
    template_name  = 'dashboard/relevancereview_confirm_delete.html'
    success_url    = reverse_lazy('dashboard:relevancereview_list')
    slug_field     = 'slug'
    slug_url_kwarg = 'slug'
    login_url      = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_subscription_active():
            messages.warning(request, 'An active subscription is required to delete reviews.')
            return redirect(reverse("accounts:payment"))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        try:
            profile = Profile.objects.get(user=self.request.user)
            item    = obj.get_reviewed_item()
            if not item:
                raise PermissionDenied("Invalid review — no item found.")
            if hasattr(item, 'profile') and item.profile != profile:
                raise PermissionDenied("You don't have permission to delete this review.")
        except Profile.DoesNotExist:
            raise PermissionDenied("Profile not found.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        review = self.object
        context['reviewed_item'] = review.get_reviewed_item()
        context['item_type']     = review.get_item_type()
        context['item_name']     = review.get_item_name()
        return context

    def delete(self, request, *args, **kwargs):
        review    = self.get_object()
        item_name = review.get_item_name()
        item_type = review.get_item_type()
        messages.success(request, f'Review deleted successfully for {item_type}: {item_name}.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# MARK ITEM REVIEWED (AJAX)
# ============================================================================

class MarkItemReviewedView(LoginRequiredMixin, View):
    """
    Mark an item as reviewed.  URL kwarg is now ``review_slug`` (not review_pk).
    """
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_subscription_active():
            return JsonResponse({
                'success': False,
                'error':   'An active subscription is required to mark reviews.'
            }, status=403)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, review_slug):
        try:
            try:
                review = RelevanceReview.objects.select_related(
                    'account_review', 'device_review',
                    'estate_review', 'important_document_review'
                ).get(slug=review_slug)
            except RelevanceReview.DoesNotExist:
                logger.error(f"Review not found: {review_slug}")
                return JsonResponse({'success': False, 'error': 'Review not found'}, status=404)

            try:
                profile = Profile.objects.get(user=request.user)
            except Profile.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Profile not found'}, status=404)

            item = review.get_reviewed_item()
            if not item:
                return JsonResponse({'success': False, 'error': 'Invalid review — no item found'}, status=404)

            if hasattr(item, 'profile') and item.profile != profile:
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

            if not request.user.can_modify_data():
                return JsonResponse({'success': False, 'error': 'You do not have permission to modify data'}, status=403)

            try:
                item.updated_at = timezone.now()
                item.save(update_fields=['updated_at'])
            except Exception as e:
                logger.error(f"Error updating item timestamp: {e}")
                return JsonResponse({'success': False, 'error': 'Failed to update item timestamp'}, status=500)

            try:
                days = self._calculate_next_review_days(review, item)
                review.next_review_due = timezone.now().date() + timedelta(days=days)
                review.save(update_fields=['next_review_due'])
            except Exception as e:
                logger.error(f"Error updating review due date: {e}")

            return JsonResponse({
                'success':         True,
                'updated_at':      item.updated_at.strftime('%B %d, %Y at %I:%M %p'),
                'next_review_due': review.next_review_due.strftime('%B %d, %Y') if review.next_review_due else None,
                'message':         f'{review.get_item_type()} marked as reviewed!',
                'item_type':       review.get_item_type(),
                'item_name':       review.get_item_name(),
            })

        except Exception as e:
            logger.error(f"Unexpected error in MarkItemReviewedView: {e}", exc_info=True)
            return JsonResponse({'success': False, 'error': 'An unexpected error occurred.'}, status=500)

    def _calculate_next_review_days(self, review, item):
        if hasattr(item, 'review_time') and item.review_time:
            return item.review_time
        if review.account_review:
            return 180
        elif review.device_review:
            return 180
        elif review.estate_review:
            return 365
        elif review.important_document_review:
            return 365
        return 365

    def get(self, request, review_slug):
        return JsonResponse({
            'success': False,
            'error':   'Method not allowed. Use POST.'
        }, status=405)


# ============================================================================
# ONBOARDING VIEWS
# ============================================================================

class OnboardingMixin(LoginRequiredMixin):
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        try:
            _ = user.profile
        except Exception:
            return redirect(reverse("dashboard:profile_create"))
        return super().dispatch(request, *args, **kwargs)

    def get_onboarding_progress(self):
        user = self.request.user
        try:
            profile = user.profile
            return {
                'contacts':     Contact.objects.filter(profile=profile).exclude(contact_relation='Self').count(),
                'accounts':     Account.objects.filter(profile=profile).count(),
                'devices':      Device.objects.filter(profile=profile).count(),
                'estates':      DigitalEstateDocument.objects.filter(profile=profile).count(),
                'documents':    ImportantDocument.objects.filter(profile=profile).count(),
                'family_knows': FamilyNeedsToKnowSection.objects.filter(relation__profile=profile).count(),
            }
        except Exception:
            return {k: 0 for k in ('contacts', 'accounts', 'devices', 'estates', 'documents', 'family_knows')}

    def _tier_limit_reached(self, key, model):
        """
        Returns (at_limit: bool, limit: int|None, tier_label: str|None).
        Mirrors FreeTierLimitMixin logic for use in TemplateView-based onboarding steps.
        """
        from accounts.models import CustomUser
        user = self.request.user
        if user.is_free_tier():
            limit = CustomUser.FREE_TIER_LIMITS.get(key)
            tier_label = "free tier"
        elif user.can_modify_data() and user.subscription_tier == 'essentials':
            limit = CustomUser.ESSENTIAL_TIER_LIMITS.get(key)
            tier_label = "Essentials tier"
        else:
            return False, None, None  # Legacy — no limit

        if limit is None:
            return False, None, None

        profile = self.request.user.profile
        if key == 'family_awareness':
            qs = model.objects.filter(relation__profile=profile)
        else:
            qs = model.objects.filter(profile=profile)
            if key == 'contacts':
                qs = qs.exclude(contact_relation='Self')
        count = qs.count()
        return count >= limit, limit, tier_label


class OnboardingWelcomeView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/welcome.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['progress']    = self.get_onboarding_progress()
        context['step']        = 0
        context['total_steps'] = 6
        return context


class OnboardingContactView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/step_contacts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['contacts']    = Contact.objects.filter(profile=profile).exclude(contact_relation='Self').order_by('last_name')
        context['progress']    = self.get_onboarding_progress()
        context['form']        = ContactForm(user=self.request.user)
        context['step']        = 1
        context['total_steps'] = 6
        at_limit, tier_limit, tier_label = self._tier_limit_reached('contacts', Contact)
        context['at_limit']   = at_limit
        context['tier_limit'] = tier_limit
        context['tier_label'] = tier_label
        return context

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
        at_limit, tier_limit, tier_label = self._tier_limit_reached('contacts', Contact)
        if at_limit:
            messages.warning(
                request,
                f"You've reached the {tier_label} limit ({tier_limit} contacts). "
                "Upgrade your subscription to add more."
            )
            return redirect(reverse('dashboard:onboarding_contacts'))
        form = ContactForm(request.POST, user=request.user)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.profile = profile
            contact.save()
            messages.success(request, f'Contact "{contact.first_name} {contact.last_name}" added!')
            return redirect(reverse('dashboard:onboarding_contacts'))
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class OnboardingAccountView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/step_accounts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['accounts']    = Account.objects.filter(profile=profile).order_by('-created_at')[:10]
        context['progress']    = self.get_onboarding_progress()
        context['form']        = AccountForm(user=self.request.user)
        context['step']        = 2
        context['total_steps'] = 6
        at_limit, tier_limit, tier_label = self._tier_limit_reached('accounts', Account)
        context['at_limit']   = at_limit
        context['tier_limit'] = tier_limit
        context['tier_label'] = tier_label
        return context

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
        at_limit, tier_limit, tier_label = self._tier_limit_reached('accounts', Account)
        if at_limit:
            messages.warning(
                request,
                f"You've reached the {tier_label} limit ({tier_limit} accounts). "
                "Upgrade your subscription to add more."
            )
            return redirect(reverse('dashboard:onboarding_accounts'))
        form = AccountForm(request.POST, user=request.user)
        if form.is_valid():
            account = form.save(commit=False)
            account.profile = profile
            account.save()
            messages.success(request, f'Account "{account.account_name_or_provider}" added!')
            return redirect(reverse('dashboard:onboarding_accounts'))
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class OnboardingDeviceView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/step_devices.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['devices']     = Device.objects.filter(profile=profile).order_by('-created_at')[:10]
        context['progress']    = self.get_onboarding_progress()
        context['form']        = DeviceForm(user=self.request.user)
        context['step']        = 3
        context['total_steps'] = 6
        at_limit, tier_limit, tier_label = self._tier_limit_reached('devices', Device)
        context['at_limit']   = at_limit
        context['tier_limit'] = tier_limit
        context['tier_label'] = tier_label
        return context

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
        at_limit, tier_limit, tier_label = self._tier_limit_reached('devices', Device)
        if at_limit:
            messages.warning(
                request,
                f"You've reached the {tier_label} limit ({tier_limit} devices). "
                "Upgrade your subscription to add more."
            )
            return redirect(reverse('dashboard:onboarding_devices'))
        form = DeviceForm(request.POST, user=request.user)
        if form.is_valid():
            device = form.save(commit=False)
            device.profile = profile
            device.save()
            messages.success(request, f'Device "{device.device_name}" added!')
            return redirect(reverse('dashboard:onboarding_devices'))
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class OnboardingEstateView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/step_estate.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['estates']     = DigitalEstateDocument.objects.filter(profile=profile).order_by('-created_at')[:10]
        context['progress']    = self.get_onboarding_progress()
        context['form']        = DigitalEstateDocumentForm(user=self.request.user)
        context['step']        = 4
        context['total_steps'] = 6
        at_limit, tier_limit, tier_label = self._tier_limit_reached('estate_documents', DigitalEstateDocument)
        context['at_limit']   = at_limit
        context['tier_limit'] = tier_limit
        context['tier_label'] = tier_label
        return context

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
        at_limit, tier_limit, tier_label = self._tier_limit_reached('estate_documents', DigitalEstateDocument)
        if at_limit:
            messages.warning(
                request,
                f"You've reached the {tier_label} limit ({tier_limit} estate documents). "
                "Upgrade your subscription to add more."
            )
            return redirect(reverse('dashboard:onboarding_estate'))
        form = DigitalEstateDocumentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.profile = profile
            doc.save()
            messages.success(request, f'Estate document "{doc.name_or_title}" added!')
            return redirect(reverse('dashboard:onboarding_estate'))
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class OnboardingDocumentsView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/step_documents.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['documents']   = ImportantDocument.objects.filter(profile=profile).order_by('-created_at')[:10]
        context['progress']    = self.get_onboarding_progress()
        context['form']        = ImportantDocumentForm(user=self.request.user)
        context['step']        = 5
        context['total_steps'] = 6
        at_limit, tier_limit, tier_label = self._tier_limit_reached('important_documents', ImportantDocument)
        context['at_limit']   = at_limit
        context['tier_limit'] = tier_limit
        context['tier_label'] = tier_label
        return context

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
        at_limit, tier_limit, tier_label = self._tier_limit_reached('important_documents', ImportantDocument)
        if at_limit:
            messages.warning(
                request,
                f"You've reached the {tier_label} limit ({tier_limit} important documents). "
                "Upgrade your subscription to add more."
            )
            return redirect(reverse('dashboard:onboarding_documents'))
        form = ImportantDocumentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.profile = profile
            doc.save()
            messages.success(request, f'Document "{doc.name_or_title}" added!')
            return redirect(reverse('dashboard:onboarding_documents'))
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class OnboardingFamilyView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/step_family.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['family_notes'] = FamilyNeedsToKnowSection.objects.filter(
            relation__profile=profile
        ).select_related('relation').order_by('-created_at')[:10]
        context['progress']    = self.get_onboarding_progress()
        context['form']        = FamilyNeedsToKnowSectionForm(user=self.request.user)
        context['step']        = 6
        context['total_steps'] = 6
        at_limit, tier_limit, tier_label = self._tier_limit_reached('family_awareness', FamilyNeedsToKnowSection)
        context['at_limit']   = at_limit
        context['tier_limit'] = tier_limit
        context['tier_label'] = tier_label
        return context

    def post(self, request, *args, **kwargs):
        at_limit, tier_limit, tier_label = self._tier_limit_reached('family_awareness', FamilyNeedsToKnowSection)
        if at_limit:
            messages.warning(
                request,
                f"You've reached the {tier_label} limit ({tier_limit} family awareness notes). "
                "Upgrade your subscription to add more."
            )
            return redirect(reverse('dashboard:onboarding_family'))
        form = FamilyNeedsToKnowSectionForm(request.POST, user=request.user)
        if form.is_valid():
            note = form.save()
            messages.success(request, f'Note for "{note.relation.first_name} {note.relation.last_name}" added!')
            return redirect(reverse('dashboard:onboarding_family'))
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class OnboardingCompleteView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/complete.html'

    def dispatch(self, request, *args, **kwargs):
        plan_intent = request.session.get('plan_intent', '')
        if plan_intent and not request.user.is_subscription_active():
            return redirect(reverse('accounts:payment'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['progress']    = self.get_onboarding_progress()
        context['step']        = 7
        context['total_steps'] = 6
        return context


# ============================================================================
# GRANTED ESTATE ACCESS — read-only views for verified family members
# ============================================================================

class GrantedEstateListView(LoginRequiredMixin, ListView):
    """
    Shows all profiles the logged-in user has been granted access to.
    No subscription required — access is controlled solely by ProfileAccessGrant.
    """
    template_name = 'dashboard/granted/grant_list.html'
    context_object_name = 'grants'
    login_url = '/accounts/login/'

    def get_queryset(self):
        from recovery.models import ProfileAccessGrant
        now = timezone.now()
        return (
            ProfileAccessGrant.objects
            .filter(
                granted_to=self.request.user,
                is_active=True,
            )
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
            .select_related('profile', 'recovery_request')
            .order_by('-granted_at')
        )

class GrantedEstateDetailView(LoginRequiredMixin, TemplateView):
    """
    Read-only view of a granted profile's full estate data.
    Access is allowed only when the logged-in user has a valid ProfileAccessGrant
    for the requested profile.
    """
    template_name = 'dashboard/granted/grant_detail.html'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        from recovery.models import ProfileAccessGrant
        self.grant = get_object_or_404(
            ProfileAccessGrant,
            profile_id=self.kwargs['profile_pk'],
            granted_to=request.user,
            is_active=True,
        )
        if self.grant.is_expired():
            messages.warning(request, 'Your access to this profile has expired.')
            return redirect(reverse_lazy('dashboard:granted_list'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile  = self.grant.profile
        grantee  = self.grant.granted_to

        # Find the Contact record on this profile whose email matches the grantee's
        # site-account email.  This is how delegation is tied to a real user.
        grantee_contact = Contact.objects.filter(
            profile=profile,
            email__iexact=grantee.email,
        ).first()

        if grantee_contact:
            # Scope every item queryset to only items delegated to this contact.
            accounts        = Account.objects.filter(profile=profile, delegated_account_to=grantee_contact).select_related('delegated_account_to')
            devices         = Device.objects.filter(profile=profile, delegated_device_to=grantee_contact).select_related('delegated_device_to')
            estate_docs     = DigitalEstateDocument.objects.filter(profile=profile, delegated_estate_to=grantee_contact).select_related('delegated_estate_to')
            important_docs  = ImportantDocument.objects.filter(profile=profile, delegated_important_document_to=grantee_contact).select_related('delegated_important_document_to')
            family_sections = FamilyNeedsToKnowSection.objects.filter(relation=grantee_contact).select_related('relation')

            # Vault entries: only those linked to accounts or devices delegated to this contact.
            # Resolve PKs first to avoid subquery issues with select_related querysets.
            try:
                from infrapps.models import VaultEntry
                account_ids = list(accounts.values_list('pk', flat=True))
                device_ids  = list(devices.values_list('pk', flat=True))
                vault_entries = VaultEntry.objects.filter(
                    Q(linked_account_id__in=account_ids) | Q(linked_device_id__in=device_ids)
                ).select_related('linked_account', 'linked_device')
            except Exception:
                vault_entries = []
        else:
            # No Contact record matched the grantee's email — show nothing.
            accounts        = Account.objects.none()
            devices         = Device.objects.none()
            estate_docs     = DigitalEstateDocument.objects.none()
            important_docs  = ImportantDocument.objects.none()
            family_sections = FamilyNeedsToKnowSection.objects.none()
            vault_entries   = []

        funeral_plan = FuneralPlan.objects.filter(profile=profile).first()

        context.update({
            'grant':            self.grant,
            'profile':          profile,
            'grantee_contact':  grantee_contact,
            'contacts':         Contact.objects.filter(profile=profile).order_by('last_name'),
            'accounts':         accounts,
            'devices':          devices,
            'estate_docs':      estate_docs,
            'important_docs':   important_docs,
            'funeral_plan':     funeral_plan,
            'vault_entries':    vault_entries,
            'family_sections':  family_sections,
        })
        return context