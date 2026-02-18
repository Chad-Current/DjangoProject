import json
import logging
from django.utils import timezone
from datetime import timedelta
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
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
from accounts.mixins import FullAccessMixin, ViewAccessMixin, DeleteAccessMixin
from .models import (
    Profile,
    Account,
    RelevanceReview,
    Device,
    DigitalEstateDocument,
    FamilyNeedsToKnowSection,
    Contact,
    ImportantDocument,
)
from .forms import (
    ProfileForm,
    AccountForm,
    RelevanceReviewForm,
    DeviceForm,
    DigitalEstateDocumentForm,
    FamilyNeedsToKnowSectionForm,
    ContactForm,
    ImportantDocumentForm,
)
logger = logging.getLogger(__name__)
# ============================================================================
# DASHBOARD HOME
# ============================================================================
class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        
        # Check payment first
        if not getattr(user, "has_paid", False):
            messages.warning(request, "Please complete payment to access your dashboard.")
            return redirect(reverse("accounts:payment"))
        
        # Check for profile - redirect to creation if it doesn't exist
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
            context['user'] = user
            context['profile'] = profile
            context['session_expires'] = self.request.session.get_expiry_date()
                    
            # ALL COUNTS
            context['accounts_count'] = Account.objects.filter(profile=profile).count()
            context['devices_count'] = Device.objects.filter(profile=profile).count()
            context['contacts_count'] = Contact.objects.filter(profile=profile).count()
            context['estates_count'] = DigitalEstateDocument.objects.filter(profile=profile).count()
            context['documents_count'] = ImportantDocument.objects.filter(profile=profile).count()
            context['family_knows_count'] = FamilyNeedsToKnowSection.objects.filter(relation__profile=profile).count()
            
            # CALCULATE PROGRESS (Weighted scoring)
            progress = self._calculate_progress(
                accounts=context['accounts_count'],
                devices=context['devices_count'],
                contacts=context['contacts_count'],
                estates=context['estates_count'],
                documents=context['documents_count'],
                family_knows=context['family_knows_count'],
            )
            context['progress'] = progress
            
            # CALCULATE REMAINING TASKS
            remaining_tasks = self._calculate_remaining_tasks(
                accounts=context['accounts_count'],
                devices=context['devices_count'],
                contacts=context['contacts_count'],
                estates=context['estates_count'],
                documents=context['documents_count'],
                family_knows=context['family_knows_count'],
            )
            context['remaining_tasks'] = remaining_tasks
            
            # ACCOUNT CATEGORY COUNTS
            context['account_categories'] = self._get_account_categories(profile)
            
            # DEVICE TYPE COUNTS
            context['device_types'] = {
                'phones': Device.objects.filter(profile=profile, device_type='Phone').count(),
                'tablets': Device.objects.filter(profile=profile, device_type='Tablet').count(),
                'laptops': Device.objects.filter(profile=profile, device_type='Laptop').count(),
                'desktops': Device.objects.filter(profile=profile, device_type='Desktop').count(),
                'smartwatches': Device.objects.filter(profile=profile, device_type='Smart Watch').count(),
                'others': Device.objects.filter(profile=profile, device_type='Other').count(),
            }
            
            # REVIEW STATS
            review_stats = self._get_review_stats(profile)
            context.update(review_stats)
            
            # UPCOMING REVIEWS (next 5 reviews)
            upcoming_reviews = RelevanceReview.objects.filter(
                Q(account_review__profile=profile) |
                Q(device_review__profile=profile) |
                Q(estate_review__profile=profile) |
                Q(important_document_review__profile=profile)
            ).exclude(
                next_review_due__isnull=True
            ).select_related(
                'account_review',
                'device_review',
                'estate_review',
                'important_document_review'
            ).order_by('next_review_due')[:5]
            
            context['upcoming_reviews'] = upcoming_reviews
            context['today'] = datetime.now().date()
            context['week_from_now'] = datetime.now().date() + timedelta(days=7)
            
            # PERMISSIONS CONTEXT
            context['tier_display'] = user.get_tier_display_name()
            context['can_modify'] = user.can_modify_data()
            context['can_view'] = user.can_view_data()
            
            # SUBSCRIPTION INFO
            if user.subscription_tier == 'essentials':
                context['is_edit_active'] = user.is_essentials_edit_active()
                context['days_remaining'] = user.days_until_essentials_expires()
                context['essentials_expires'] = user.essentials_expires

            if user.subscription_tier == 'legacy':
                context['legacy_granted'] = user.legacy_granted_date
            
            # ONBOARDING HINTS - show if profile is new and incomplete
            context['show_onboarding'] = self._should_show_onboarding(context)

        except Profile.DoesNotExist:
            # This should never happen due to dispatch check, but just in case
            messages.warning(self.request, "Profile not found. Please create your profile.")
            return redirect(reverse("dashboard:profile_create"))

        return context
    
    def _should_show_onboarding(self, context):
        """
        Determine if onboarding hints should be shown.
        Show if user has completed less than 3 of the 7 main categories.
        """
        completed_categories = sum([
            1 if context.get('accounts_count', 0) > 0 else 0,
            1 if context.get('devices_count', 0) > 0 else 0,
            1 if context.get('contacts_count', 0) > 0 else 0,
            1 if context.get('estates_count', 0) > 0 else 0,
            1 if context.get('documents_count', 0) > 0 else 0,
            1 if context.get('family_knows_count', 0) > 0 else 0,
        ])
        return completed_categories < 3
    
    def _calculate_progress(self, **kwargs):
        """
        Calculate progress based on weighted completion criteria.
        
        Weights:
        - Accounts: 25% (target: 10)
        - Contacts: 20% (target: 5)
        - Devices: 15% (target: 5)
        - Estate Docs: 15% (target: 3)
        - Important Docs: 15% (target: 5)
        - Family Knows: 5% (target: 3)
        #Correct this later
        """
        criteria = {
            'accounts': {'weight': 0.25, 'target': 10},
            'devices': {'weight': 0.15, 'target': 5},
            'contacts': {'weight': 0.20, 'target': 5},
            'estates': {'weight': 0.15, 'target': 3},
            'documents': {'weight': 0.15, 'target': 5},
            'family_knows': {'weight': 0.05, 'target': 5},
        }
        
        total_progress = 0
        
        for key, config in criteria.items():
            count = kwargs.get(key, 0)
            target = config['target']
            weight = config['weight']
            
            # Calculate progress for this item (capped at 100% per item)
            item_progress = min(count / target, 1.0) * weight
            total_progress += item_progress
        
        # Convert to percentage (0-100)
        return round(total_progress * 100)
    
    def _calculate_remaining_tasks(self, **kwargs):
        """Calculate how many major categories are not yet started."""
        tasks = [
            ('accounts', 1),
            ('devices', 1),
            ('contacts', 1),
            ('estates', 1),
            ('documents', 1),
            ('family_knows', 1),
        ]
        
        remaining = 0
        for key, threshold in tasks:
            if kwargs.get(key, 0) < threshold:
                remaining += 1
        
        return remaining
    
    def _get_account_categories(self, profile):
        """Get account counts by category."""
        from django.db.models import Count
        
        categories = Account.objects.filter(profile=profile).values('account_category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Return as dictionary
        return {cat['account_category']: cat['count'] for cat in categories}
    
    def _get_review_stats(self, profile):
        """Get review statistics including next due date."""
        from django.db.models import Min
        from datetime import date
        
        # Get the soonest review date across all item types
        review_dates = RelevanceReview.objects.filter(
            Q(account_review__profile=profile) |
            Q(device_review__profile=profile) |
            Q(estate_review__profile=profile) |
            Q(important_document_review__profile=profile)
        ).exclude(next_review_due__isnull=True).aggregate(
            soonest=Min('next_review_due')
        )
        
        soonest_review = review_dates['soonest']
        
        stats = {
            'soonest_review': soonest_review,
            'first_delta': None,
            'alert_due': False,
            'alert_attention': False,
        }
        
        if soonest_review:
            today = date.today()
            delta = soonest_review - today
            stats['first_delta'] = delta
            
            if delta.days <= 0:
                stats['alert_due'] = True
            elif delta.days <= 7:
                stats['alert_attention'] = True
        
        return stats


# ============================================================================
# PROFILE VIEWS
# ============================================================================

# KEEP ViewAccessMixin to allow user to change details even after expiration if not Legacy
class ProfileCreateView(LoginRequiredMixin, CreateView):
    """
    Initial profile creation - only accessible to users without a profile.
    """
    model = Profile
    form_class = ProfileForm
    template_name = 'dashboard/profile.html'
    success_url = reverse_lazy('dashboard:dashboard_home')
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        
        if not getattr(user, "has_paid", False):
            messages.warning(request, "Please complete payment to create your profile.")
            return redirect(reverse("accounts:payment"))
        
        try:
            profile = user.profile
            messages.info(request, "You already have a profile. Use the edit page to make changes.")
            return redirect(reverse('dashboard:profile_detail'))
        except Profile.DoesNotExist:
            pass
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, '🎉 Profile created! Let\'s set up your estate plan.')
        response = super().form_valid(form)
        return redirect(reverse('dashboard:onboarding_welcome'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_initial_setup'] = True
        context['page_title'] = 'Create Your Profile'
        context['submit_text'] = 'Create Profile & Continue'
        context['steps'] = [
            {'number': 1, 'title': 'Create Profile', 'url': 'dashboard:profile_create'},
            {'number': 2, 'title': 'Add Contacts', 'url': 'dashboard:contact_create'},
            {'number': 3, 'title': 'Add Accounts', 'url': 'dashboard:account_create'},
        ]
        return context
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_initial_setup'] = True
        context['page_title'] = 'Create Your Profile'
        context['submit_text'] = 'Create Profile & Continue'
        return context

class ProfileDetailView(ViewAccessMixin, DetailView):
    model = Profile
    template_name = 'dashboard/profile_detail.html'
    context_object_name = 'profile'
    owner_field = 'user'
    
    def get_object(self, queryset=None):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile

class ProfileUpdateView(FullAccessMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = 'dashboard/profile_form.html'
    success_url = reverse_lazy('dashboard:dashboard_home')
    owner_field = 'user'
    
    def get_object(self, queryset=None):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile
    
    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully.')
        return super().form_valid(form)

    
# ============================================================================
# ACCOUNT VIEWS
# ============================================================================
class AccountListView(ViewAccessMixin, ListView):
    model = Account
    template_name = 'dashboard/accounts/account_list.html'
    context_object_name = 'accounts'
    owner_field = 'profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            queryset = Account.objects.filter(profile=profile)
            
            category_id = self.request.GET.get('account_category')
            if category_id:
                queryset = queryset.filter(account_category=category_id)  # Fixed field name
            
            is_critical = self.request.GET.get('critical')
            if is_critical:
                queryset = queryset.filter(is_critical=True)
            
            return queryset.order_by('-created_at')
        except Profile.DoesNotExist:
            return Account.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        try:
            profile = Profile.objects.get(user=self.request.user)
            context['accounts'] = Account.objects.filter(profile=profile)  # Fixed context key
        except Profile.DoesNotExist:
            context['accounts'] = Account.objects.none()
        return context

class AccountDetailView(ViewAccessMixin, DetailView):
    model = Account
    template_name = 'dashboard/accounts/account_detail.html'
    context_object_name = 'account'
    owner_field = 'profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context

class AccountCreateView(FullAccessMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = 'dashboard/accounts/account_form.html'
    success_url = reverse_lazy('dashboard:account_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Digital account created successfully.')
        return super().form_valid(form)

class AccountUpdateView(FullAccessMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = 'dashboard/accounts/account_form.html'
    success_url = reverse_lazy('dashboard:account_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Digital account updated successfully.')
        return super().form_valid(form)

class AccountDeleteView(DeleteAccessMixin, DeleteView):
    model = Account
    template_name = 'dashboard/accounts/account_confirm_delete.html'
    success_url = reverse_lazy('dashboard:account_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Account deleted successfully.')
        return super().delete(request, *args, **kwargs)
    

# ============================================================================
# DEVICE VIEWS
# ============================================================================
class DeviceListView(ViewAccessMixin, ListView):
    model = Device
    template_name = 'dashboard/devices/device_list.html'
    context_object_name = 'devices'
    owner_field = 'profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return Device.objects.filter(profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return Device.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context

class DeviceDetailView(ViewAccessMixin, DetailView):
    model = Device
    template_name = 'dashboard/devices/device_detail.html'
    context_object_name = 'device'
    owner_field = 'profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context

class DeviceCreateView(FullAccessMixin, CreateView):
    model = Device
    form_class = DeviceForm
    template_name = 'dashboard/devices/device_form.html'
    success_url = reverse_lazy('dashboard:device_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):          # ADD THIS
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Device created successfully.')
        return super().form_valid(form)

class DeviceUpdateView(FullAccessMixin, UpdateView):
    model = Device
    form_class = DeviceForm
    template_name = 'dashboard/devices/device_form.html'
    success_url = reverse_lazy('dashboard:device_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):          # ADD THIS
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Device updated successfully.')
        return super().form_valid(form)
    
class DeviceDeleteView(DeleteAccessMixin, DeleteView):
    model = Device
    template_name = 'dashboard/devices/device_confirm_delete.html'
    success_url = reverse_lazy('dashboard:device_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Device deleted successfully.')
        return super().delete(request, *args, **kwargs)
  

# ============================================================================
# ESTATE DOCUMENT VIEWS
# ============================================================================
class EstateListView(ViewAccessMixin, ListView):
    model = DigitalEstateDocument
    template_name = 'dashboard/estates/estate_list.html'
    context_object_name = 'estates'
    owner_field = 'profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return DigitalEstateDocument.objects.filter(profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return DigitalEstateDocument.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context

class EstateDetailView(ViewAccessMixin, DetailView):
    model = DigitalEstateDocument
    template_name = 'dashboard/estates/estate_detail.html'
    context_object_name = 'estate'
    owner_field = 'profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context

class EstateCreateView(FullAccessMixin, CreateView):
    model = DigitalEstateDocument
    form_class = DigitalEstateDocumentForm
    template_name = 'dashboard/estates/estate_form.html'
    success_url = reverse_lazy('dashboard:estate_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Estate document created successfully.')
        return super().form_valid(form)

class EstateUpdateView(FullAccessMixin, UpdateView):
    model = DigitalEstateDocument
    form_class = DigitalEstateDocumentForm
    template_name = 'dashboard/estates/estate_form.html'
    success_url = reverse_lazy('dashboard:estate_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Estate document updated successfully.')
        return super().form_valid(form)

class EstateDeleteView(DeleteAccessMixin, DeleteView):
    model = DigitalEstateDocument
    template_name = 'dashboard/estates/estate_confirm_delete.html'
    success_url = reverse_lazy('dashboard:estate_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Estate document deleted successfully.')
        return super().delete(request, *args, **kwargs)
    
# ============================================================================
# FAMILY AWARENESS VIEWS (FamilyNeedsToKnowSection)
# ============================================================================
class FamilyAwarenessListView(ViewAccessMixin, ListView):
    model = FamilyNeedsToKnowSection
    template_name = 'dashboard/familyaware/familyawareness_list.html'
    context_object_name = 'familyawareness_objects'
    owner_field = 'relation__profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return FamilyNeedsToKnowSection.objects.filter(relation__profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return FamilyNeedsToKnowSection.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context

class FamilyAwarenessDetailView(ViewAccessMixin, DetailView):
    model = FamilyNeedsToKnowSection
    template_name = 'dashboard/familyaware/familyawareness_detail.html'
    context_object_name = 'familyawareness'
    owner_field = 'relation__profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context

class FamilyAwarenessCreateView(FullAccessMixin, CreateView):
    model = FamilyNeedsToKnowSection
    form_class = FamilyNeedsToKnowSectionForm
    template_name = 'dashboard/familyaware/familyawareness_form.html'
    success_url = reverse_lazy('dashboard:familyawareness_list')
    owner_field = 'relation__profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Family awareness section created successfully.')
        return super().form_valid(form)

class FamilyAwarenessUpdateView(FullAccessMixin, UpdateView):
    model = FamilyNeedsToKnowSection
    form_class = FamilyNeedsToKnowSectionForm
    template_name = 'dashboard/familyaware/familyawareness_form.html'
    success_url = reverse_lazy('dashboard:familyawareness_list')
    owner_field = 'relation__profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Family awareness section updated successfully.')
        return super().form_valid(form)

class FamilyAwarenessDeleteView(DeleteAccessMixin, DeleteView):
    model = FamilyNeedsToKnowSection
    template_name = 'dashboard/familyaware/familyawareness_confirm_delete.html'
    success_url = reverse_lazy('dashboard:familyawareness_list')
    owner_field = 'relation__profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Family awareness section deleted successfully.')
        return super().delete(request, *args, **kwargs)

# ============================================================================
# IMPORTANT DOCUMENT VIEWS
# ============================================================================
class ImportantDocumentListView(ViewAccessMixin, ListView):
    model = ImportantDocument
    template_name = 'dashboard/importantdocuments/importantdocument_list.html'
    context_object_name = 'documents'
    owner_field = 'profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return ImportantDocument.objects.filter(profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return ImportantDocument.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context

class ImportantDocumentDetailView(ViewAccessMixin, DetailView):
    model = ImportantDocument
    template_name = 'dashboard/importantdocuments/importantdocument_detail.html'
    context_object_name = 'document'
    owner_field = 'profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context

class ImportantDocumentCreateView(FullAccessMixin, CreateView):
    model = ImportantDocument
    form_class = ImportantDocumentForm
    template_name = 'dashboard/importantdocuments/importantdocument_form.html'
    success_url = reverse_lazy('dashboard:importantdocument_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Document created successfully.')
        return super().form_valid(form)

class ImportantDocumentUpdateView(FullAccessMixin, UpdateView):
    model = ImportantDocument
    form_class = ImportantDocumentForm
    template_name = 'dashboard/importantdocuments/importantdocument_form.html'
    success_url = reverse_lazy('dashboard:importantdocument_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Document updated successfully.')
        return super().form_valid(form)

class ImportantDocumentDeleteView(DeleteAccessMixin, DeleteView):
    model = ImportantDocument
    template_name = 'dashboard/importantdocuments/importantdocument_confirm_delete.html'
    success_url = reverse_lazy('dashboard:importantdocument_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Document deleted successfully.')
        return super().delete(request, *args, **kwargs)
    
# ============================================================================
# CONTACT VIEWS
# ============================================================================
class ContactListView(ViewAccessMixin, ListView):
    model = Contact
    template_name = 'dashboard/contacts/contact_list.html'
    context_object_name = 'contacts'
    owner_field = 'profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return Contact.objects.filter(profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return Contact.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context

class ContactDetailView(ViewAccessMixin, DetailView):
    model = Contact
    template_name = 'dashboard/contacts/contact_detail.html'
    context_object_name = 'contact'
    owner_field = 'profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        
        contact = self.object
        
        # Get ALL documents assigned to this contact
        estate_docs = DigitalEstateDocument.objects.filter(delegated_estate_to=contact).order_by('name_or_title')
        important_docs = ImportantDocument.objects.filter(delegated_important_document_to=contact).order_by('name_or_title')
        devices_listed = Device.objects.filter(delegated_device_to=contact).order_by('device_name')
        accounts_listed = Account.objects.filter(delegated_account_to=contact).order_by('account_name_or_provider')


        context['delegated_estate_documents'] = estate_docs
        context['delegated_important_documents'] = important_docs
        context['delegated_devices'] = devices_listed
        context['delegated_accounts'] = accounts_listed

        context['total_assignments'] = estate_docs.count() + important_docs.count() + devices_listed.count() + accounts_listed.count()
        # context['total_devices'] = devices_listed.count()
        # context['total_accounts'] = accounts_listed.count()
        
        return context

class ContactCreateView(FullAccessMixin, CreateView):
    model = Contact
    form_class = ContactForm
    template_name = 'dashboard/contacts/contact_form.html'
    success_url = reverse_lazy('dashboard:contact_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Contact created successfully.')
        return super().form_valid(form)

class ContactUpdateView(FullAccessMixin, UpdateView):
    model = Contact
    form_class = ContactForm
    template_name = 'dashboard/contacts/contact_form.html'
    success_url = reverse_lazy('dashboard:contact_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Contact updated successfully.')
        return super().form_valid(form)

class ContactDeleteView(DeleteAccessMixin, DeleteView):
    model = Contact
    template_name = 'dashboard/contacts/contact_confirm_delete.html'
    success_url = reverse_lazy('dashboard:contact_list')
    owner_field = 'profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = self.object
        
        # Check for assigned documents, accounts or devices
        estate_docs = DigitalEstateDocument.objects.filter(
            delegated_estate_to=contact
        ).select_related('profile')
        
        important_docs = ImportantDocument.objects.filter(
            delegated_important_document_to=contact
        ).select_related('profile')
        
        assigned_accounts = Account.objects.filter(
            delegated_account_to=contact
        ).select_related('profile')

        assigned_devices = Device.objects.filter(
            delegated_device_to=contact
        ).select_related('profile')


        # Add document information to context
        context['estate_documents'] = estate_docs
        context['important_documents'] = important_docs
        context['assigned_accounts'] = assigned_accounts
        context['assigned_devices'] = assigned_devices
        context['total_documents'] = estate_docs.count() + important_docs.count()
        context['total_accounts'] = assigned_accounts.count()
        context['total_devices'] = assigned_devices.count()
        context['has_assignments'] = estate_docs.exists() or important_docs.exists() or assigned_accounts.exists() or assigned_devices.exists()
        
        # Get other contacts for potential reassignment suggestions
        if context['has_assignments']:
            other_contacts = Contact.objects.filter(
                profile=contact.profile
            ).exclude(id=contact.id).order_by('last_name')
            context['other_contacts'] = other_contacts
            context['has_other_contacts'] = other_contacts.exists()
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle the delete request with proper error handling"""
        self.object = self.get_object()
        contact = self.object
        
        # Check if contact has documents before attempting deletion
        estate_count = DigitalEstateDocument.objects.filter(delegated_estate_to=contact).count()
        important_count = ImportantDocument.objects.filter(delegated_important_document_to=contact).count()
        account_count = Account.objects.filter(delegated_account_to=contact).count()
        device_count = Device.objects.filter(delegated_device_to=contact).count()
        total_resictions = estate_count + important_count + account_count + device_count
        
        if total_resictions > 0:
            # Contact has documents - cannot delete
            messages.error(
                request,
                f'Cannot delete {contact.contact_name} because they have {total_resictions} '
                f'document(s) assigned to them ({estate_count} estate, {important_count} important, {account_count} account, {device_count} device)'
                f'Please reassign these to another contact first.'
            )
            return HttpResponseRedirect(
                reverse('dashboard:contact_detail', kwargs={'pk': contact.pk})
            )
        
        # No documents - safe to delete
        try:
            return self.delete(request, *args, **kwargs)
        except ProtectedError as e:
            # This shouldn't happen since we checked above, but just in case
            messages.error(
                request,
                f'Cannot delete {contact.contact_name} because they have documents assigned. '
                'Please reassign the documents first.'
            )
            return HttpResponseRedirect(
                reverse('dashboard:contact_detail', kwargs={'pk': contact.pk})
            )
    
    def delete(self, request, *args, **kwargs):
        """Override delete to add success message"""
        contact_name = self.object.contact_name
        messages.success(request, f'Contact "{contact_name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# RELEVANCE REVIEW VIEWS
# ============================================================================

class RelevanceReviewListView(LoginRequiredMixin, ListView):
    """
    List all reviews for the current user's items.
    NOTE: This view doesn't use ViewAccessMixin because RelevanceReview 
    doesn't have a direct 'user' field - ownership is determined through 
    the reviewed item's profile.
    """
    model = RelevanceReview
    template_name = 'dashboard/relevancereview_list.html'
    context_object_name = 'reviews'
    paginate_by = 5
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        """Check if user has paid before allowing access"""
        user = request.user
        if not getattr(user, "has_paid", False):
            return redirect(reverse("accounts:payment"))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Get all reviews for items belonging to this user's profile"""
        try:
            profile = Profile.objects.get(user=self.request.user)
            
            # Get all reviews for items belonging to this profile
            qs = RelevanceReview.objects.filter(
                Q(account_review__profile=profile) |
                Q(device_review__profile=profile) |
                Q(estate_review__profile=profile) |
                Q(important_document_review__profile=profile)
            ).select_related(
                'account_review',
                'device_review', 
                'estate_review',
                'important_document_review',
                'reviewer'
            )
            
            # Filter by specific item type if requested
            filter_type = self.request.GET.get('type')
            item_id = self.request.GET.get('item_id')
            
            if filter_type == 'account' and item_id:
                qs = qs.filter(account_review_id=item_id)
            elif filter_type == 'device' and item_id:
                qs = qs.filter(device_review_id=item_id)
            elif filter_type == 'estate' and item_id:
                qs = qs.filter(estate_review_id=item_id)
            elif filter_type == 'important' and item_id:
                qs = qs.filter(important_document_review_id=item_id)
            
            return qs.order_by(F('next_review_due').asc(nulls_last=True))
        except Profile.DoesNotExist:
            return RelevanceReview.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if user can modify data
        context['can_modify'] = self.request.user.can_modify_data()
        
        # Add filter information to context
        filter_type = self.request.GET.get('type')
        item_id = self.request.GET.get('item_id')
        
        if filter_type and item_id:
            try:
                if filter_type == 'account':
                    context['filtered_item'] = Account.objects.get(
                        id=item_id,
                        profile__user=self.request.user
                    )
                    context['filtered_type'] = 'Account'
                elif filter_type == 'device':
                    context['filtered_item'] = Device.objects.get(
                        id=item_id,
                        profile__user=self.request.user
                    )
                    context['filtered_type'] = 'Device'
                elif filter_type == 'estate':
                    context['filtered_item'] = DigitalEstateDocument.objects.get(
                        id=item_id,
                        profile__user=self.request.user
                    )
                    context['filtered_type'] = 'Estate Document'
                elif filter_type == 'important':
                    context['filtered_item'] = ImportantDocument.objects.get(
                        id=item_id,
                        profile__user=self.request.user
                    )
                    context['filtered_type'] = 'Important Document'
            except (Account.DoesNotExist, Device.DoesNotExist, 
                    DigitalEstateDocument.DoesNotExist, ImportantDocument.DoesNotExist):
                pass
        
        return context


class RelevanceReviewDetailView(LoginRequiredMixin, DetailView):
    """
    View details of a specific review.
    NOTE: This view doesn't use ViewAccessMixin because RelevanceReview 
    doesn't have a direct 'user' field.
    """
    model = RelevanceReview
    template_name = 'dashboard/relevancereview_detail.html'
    context_object_name = 'review'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        """Check if user has paid before allowing access"""
        user = request.user
        if not getattr(user, "has_paid", False):
            return redirect(reverse("accounts:payment"))
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """Get review and verify ownership through the reviewed item"""
        obj = super().get_object(queryset)
        
        # Verify the review belongs to the user's profile
        try:
            profile = Profile.objects.get(user=self.request.user)
            item = obj.get_reviewed_item()
            
            if not item:
                raise PermissionDenied("Invalid review - no item found.")
            
            if hasattr(item, 'profile') and item.profile != profile:
                raise PermissionDenied("You don't have permission to view this review.")
            
        except Profile.DoesNotExist:
            raise PermissionDenied("Profile not found.")
        
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        
        # Add the reviewed item to context
        review = self.object
        context['reviewed_item'] = review.get_reviewed_item()
        context['item_type'] = review.get_item_type()
        context['item_name'] = review.get_item_name()
        
        return context


class RelevanceReviewCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new review.
    NOTE: Uses LoginRequiredMixin and manual permission check instead of 
    FullAccessMixin because we need custom user filtering.
    """
    model = RelevanceReview
    form_class = RelevanceReviewForm
    template_name = 'dashboard/relevancereview_form.html'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        """Check permissions before allowing access"""
        user = request.user
        
        # Check if user has paid
        if not getattr(user, "has_paid", False):
            return redirect(reverse("accounts:payment"))
        
        # Check if user can modify data
        if not user.can_modify_data():
            messages.error(request, "You don't have permission to create reviews.")
            return redirect(reverse("dashboard:dashboard_home"))
        
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # Pre-populate based on URL parameters
        item_type = self.request.GET.get('type')
        item_id = self.request.GET.get('item_id')
        
        if item_type and item_id:
            kwargs['initial'] = {
                'review_type': item_type,
                'item_id': item_id
            }
        
        return kwargs

    def form_valid(self, form):
        form.instance.reviewer = self.request.user
        
        # Determine the item type for success message
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
            item_name = "item"
            item_type = "item"
        
        messages.success(
            self.request, 
            f'Review created successfully for {item_type}: {item_name}.'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to the appropriate detail page based on review type"""
        review = self.object
        
        if review.account_review:
            return reverse_lazy('dashboard:account_detail', kwargs={'pk': review.account_review.pk})
        elif review.device_review:
            return reverse_lazy('dashboard:device_detail', kwargs={'pk': review.device_review.pk})
        elif review.estate_review:
            return reverse_lazy('dashboard:estate_detail', kwargs={'pk': review.estate_review.pk})
        elif review.important_document_review:
            return reverse_lazy('dashboard:importantdocument_detail', kwargs={'pk': review.important_document_review.pk})
        
        # Fallback
        return reverse_lazy('dashboard:relevancereview_list')


class RelevanceReviewUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing review.
    NOTE: Uses LoginRequiredMixin and manual permission check instead of 
    FullAccessMixin because we need custom ownership verification.
    """
    model = RelevanceReview
    form_class = RelevanceReviewForm
    template_name = 'dashboard/relevancereview_form.html'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        """Check permissions before allowing access"""
        user = request.user
        
        # Check if user has paid
        if not getattr(user, "has_paid", False):
            return redirect(reverse("accounts:payment"))
        
        # Check if user can modify data
        if not user.can_modify_data():
            messages.error(request, "You don't have permission to edit reviews.")
            return redirect(reverse("dashboard:dashboard_home"))
        
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """Get review and verify ownership through the reviewed item"""
        obj = super().get_object(queryset)
        
        # Verify the review belongs to the user's profile
        try:
            profile = Profile.objects.get(user=self.request.user)
            item = obj.get_reviewed_item()
            
            if not item:
                raise PermissionDenied("Invalid review - no item found.")
            
            if hasattr(item, 'profile') and item.profile != profile:
                raise PermissionDenied("You don't have permission to edit this review.")
            
        except Profile.DoesNotExist:
            raise PermissionDenied("Profile not found.")
        
        return obj

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        item_name = form.instance.get_item_name()
        item_type = form.instance.get_item_type()
        
        messages.success(
            self.request, 
            f'Review updated successfully for {item_type}: {item_name}.'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to the appropriate detail page based on review type"""
        review = self.object
        
        if review.account_review:
            return reverse_lazy('dashboard:account_detail', kwargs={'pk': review.account_review.pk})
        elif review.device_review:
            return reverse_lazy('dashboard:device_detail', kwargs={'pk': review.device_review.pk})
        elif review.estate_review:
            return reverse_lazy('dashboard:estate_detail', kwargs={'pk': review.estate_review.pk})
        elif review.important_document_review:
            return reverse_lazy('dashboard:importantdocument_detail', kwargs={'pk': review.important_document_review.pk})
        
        # Fallback
        return reverse_lazy('dashboard:relevancereview_list')


class RelevanceReviewDeleteView(LoginRequiredMixin, DeleteView):


    """
    Delete a review.
    NOTE: Uses LoginRequiredMixin and manual permission check instead of 
    DeleteAccessMixin because we need custom ownership verification.
    """
    model = RelevanceReview
    template_name = 'dashboard/relevancereview_confirm_delete.html'
    success_url = reverse_lazy('dashboard:relevancereview_list')
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        """Check permissions before allowing access"""
        user = request.user
        
        # Check if user has paid
        if not getattr(user, "has_paid", False):
            return redirect(reverse("accounts:payment"))
        
        # Check if user can delete data
        if not user.can_delete_data():
            messages.error(request, "You don't have permission to delete reviews.")
            return redirect(reverse("dashboard:dashboard_home"))
        
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """Get review and verify ownership through the reviewed item"""
        obj = super().get_object(queryset)
        
        # Verify the review belongs to the user's profile
        try:
            profile = Profile.objects.get(user=self.request.user)
            item = obj.get_reviewed_item()
            
            if not item:
                raise PermissionDenied("Invalid review - no item found.")
            
            if hasattr(item, 'profile') and item.profile != profile:
                raise PermissionDenied("You don't have permission to delete this review.")
            
        except Profile.DoesNotExist:
            raise PermissionDenied("Profile not found.")
        
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        review = self.object
        
        context['reviewed_item'] = review.get_reviewed_item()
        context['item_type'] = review.get_item_type()
        context['item_name'] = review.get_item_name()
        
        return context

    def delete(self, request, *args, **kwargs):

        review = self.get_object()
        item_name = review.get_item_name()
        item_type = review.get_item_type()
        
        messages.success(
            request, 
            f'Review deleted successfully for {item_type}: {item_name}.'
        )
        return super().delete(request, *args, **kwargs)
    

class MarkItemReviewedView(LoginRequiredMixin, View):
    """
    Mark an item as reviewed by updating its updated_at timestamp.
    This is called via AJAX from the review detail page.
    """
    login_url = '/accounts/login/'
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user has paid before allowing access"""
        user = request.user
        if user.is_authenticated and not getattr(user, "has_paid", False):
            return JsonResponse({
                'success': False,
                'error': 'Payment required to access this feature'
            }, status=403)
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, review_pk):
        """
        Handle POST request to mark item as reviewed.
        
        Args:
            request: HttpRequest object
            review_pk: Primary key of the RelevanceReview
            
        Returns:
            JsonResponse with success status and updated timestamps
        """
        try:
            # Get the review
            try:
                review = RelevanceReview.objects.select_related(
                    'account_review',
                    'device_review',
                    'estate_review',
                    'important_document_review'
                ).get(pk=review_pk)
            except RelevanceReview.DoesNotExist:
                logger.error(f"Review not found: {review_pk}")
                return JsonResponse({
                    'success': False,
                    'error': 'Review not found'
                }, status=404)
            
            # Get user profile
            try:
                profile = Profile.objects.get(user=request.user)
            except Profile.DoesNotExist:
                logger.error(f"Profile not found for user: {request.user.username}")
                return JsonResponse({
                    'success': False,
                    'error': 'Profile not found'
                }, status=404)
            
            # Get the reviewed item
            item = review.get_reviewed_item()
            
            if not item:
                logger.error(f"No item found for review: {review_pk}")
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid review - no item found'
                }, status=404)
            
            # Check ownership
            if hasattr(item, 'profile') and item.profile != profile:
                logger.warning(f"Permission denied for user {request.user.username} on review {review_pk}")
                return JsonResponse({
                    'success': False,
                    'error': 'Permission denied - you do not own this item'
                }, status=403)
            
            # Check if user can modify data
            if not request.user.can_modify_data():
                logger.warning(f"User {request.user.username} lacks modify permission")
                return JsonResponse({
                    'success': False,
                    'error': 'You do not have permission to modify data'
                }, status=403)
            
            # Update the item's updated_at timestamp
            try:
                item.updated_at = timezone.now()
                item.save(update_fields=['updated_at'])
                logger.info(f"Updated item {item.pk} updated_at timestamp")
            except Exception as e:
                logger.error(f"Error updating item timestamp: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to update item timestamp'
                }, status=500)
            
            # Update the review's next_review_due date
            try:
                days_until_next = self._calculate_next_review_days(review, item)
                review.next_review_due = timezone.now().date() + timedelta(days=days_until_next)
                review.save(update_fields=['next_review_due'])
                logger.info(f"Updated review {review_pk} next_review_due to {review.next_review_due}")
            except Exception as e:
                logger.error(f"Error updating review due date: {str(e)}")
                # Don't fail completely if we can't update review date
                pass
            
            # Return success response with updated data
            return JsonResponse({
                'success': True,
                'updated_at': item.updated_at.strftime('%B %d, %Y at %I:%M %p'),
                'next_review_due': review.next_review_due.strftime('%B %d, %Y') if review.next_review_due else None,
                'message': f'{review.get_item_type()} marked as reviewed!',
                'item_type': review.get_item_type(),
                'item_name': review.get_item_name()
            })
            
        except Exception as e:
            # Catch-all for any unexpected errors
            logger.error(f"Unexpected error in MarkItemReviewedView: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred. Please try again.'
            }, status=500)
    
    def _calculate_next_review_days(self, review, item):
        """
        Calculate the number of days until the next review is due.
        
        Args:
            review: RelevanceReview instance
            item: The actual item being reviewed (Account, Device, etc.)
            
        Returns:
            int: Number of days until next review
        """
        # First, try to use the item's review_time if it exists
        if hasattr(item, 'review_time') and item.review_time:
            return item.review_time
        
        # Fallback logic for items without review_time
        # You can customize this based on item type
        if review.account_review:
            # For accounts without review_time, use a default
            return 180  # 6 months
        elif review.device_review:
            return 180  # 6 months for devices
        elif review.estate_review:
            return 365  # 1 year for estate documents
        elif review.important_document_review:
            return 365  # 1 year for important documents
        
        # Ultimate fallback
        return 365
    
    def get(self, request, review_pk):
        """
        Handle GET requests by returning method not allowed.
        This endpoint should only accept POST requests.
        """
        return JsonResponse({
            'success': False,
            'error': 'Method not allowed. Use POST to mark item as reviewed.'
        }, status=405)
    

class OnboardingMixin(LoginRequiredMixin):
    """Shared mixin — enforces payment and profile requirements."""
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not getattr(user, "has_paid", False):
            messages.warning(request, "Please complete payment to access setup.")
            return redirect(reverse("accounts:payment"))
        try:
            _ = user.profile
        except Exception:
            return redirect(reverse("dashboard:profile_create"))
        return super().dispatch(request, *args, **kwargs)

    def get_onboarding_progress(self):
        """Return counts for all 6 steps for the step rail and complete page."""
        user = self.request.user
        try:
            profile = user.profile
            return {
                'contacts':    Contact.objects.filter(profile=profile).exclude(contact_relation='Self').count(),
                'accounts':    Account.objects.filter(profile=profile).count(),
                'devices':     Device.objects.filter(profile=profile).count(),
                'estates':     DigitalEstateDocument.objects.filter(profile=profile).count(),
                'documents':   ImportantDocument.objects.filter(profile=profile).count(),
                'family_knows': FamilyNeedsToKnowSection.objects.filter(relation__profile=profile).count(),
            }
        except Exception:
            return {
                'contacts': 0, 'accounts': 0, 'devices': 0,
                'estates': 0, 'documents': 0, 'family_knows': 0,
            }


# ── Step 0: Welcome ──────────────────────────────────────────────────────────

class OnboardingWelcomeView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/welcome.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['progress'] = self.get_onboarding_progress()
        context['step'] = 0
        context['total_steps'] = 6
        return context


# ── Step 1: Contacts ─────────────────────────────────────────────────────────

class OnboardingContactView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/step_contacts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['contacts'] = Contact.objects.filter(profile=profile).exclude(contact_relation='Self').order_by('last_name')
        context['progress'] = self.get_onboarding_progress()
        context['form'] = ContactForm(user=self.request.user)
        context['step'] = 1
        context['total_steps'] = 6
        return context

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
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


# ── Step 2: Accounts ─────────────────────────────────────────────────────────

class OnboardingAccountView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/step_accounts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['accounts'] = Account.objects.filter(profile=profile).order_by('-created_at')[:10]
        context['progress'] = self.get_onboarding_progress()
        context['form'] = AccountForm(user=self.request.user)
        context['step'] = 2
        context['total_steps'] = 6
        return context

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
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


# ── Step 3: Devices ──────────────────────────────────────────────────────────

class OnboardingDeviceView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/step_devices.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['devices'] = Device.objects.filter(profile=profile).order_by('-created_at')[:10]
        context['progress'] = self.get_onboarding_progress()
        context['form'] = DeviceForm(user=self.request.user)
        context['step'] = 3
        context['total_steps'] = 6
        return context

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
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


# ── Step 4: Estate Documents ─────────────────────────────────────────────────

class OnboardingEstateView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/step_estate.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['estates'] = DigitalEstateDocument.objects.filter(profile=profile).order_by('-created_at')[:10]
        context['progress'] = self.get_onboarding_progress()
        context['form'] = DigitalEstateDocumentForm(user=self.request.user)
        context['step'] = 4
        context['total_steps'] = 6
        return context

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
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


# ── Step 5: Important Documents ──────────────────────────────────────────────

class OnboardingDocumentsView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/step_documents.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['documents'] = ImportantDocument.objects.filter(profile=profile).order_by('-created_at')[:10]
        context['progress'] = self.get_onboarding_progress()
        context['form'] = ImportantDocumentForm(user=self.request.user)
        context['step'] = 5
        context['total_steps'] = 6
        return context

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
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


# ── Step 6: Family Awareness ─────────────────────────────────────────────────

class OnboardingFamilyView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/step_family.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context['family_notes'] = FamilyNeedsToKnowSection.objects.filter(
            relation__profile=profile
        ).select_related('relation').order_by('-created_at')[:10]
        context['progress'] = self.get_onboarding_progress()
        context['form'] = FamilyNeedsToKnowSectionForm(user=self.request.user)
        context['step'] = 6
        context['total_steps'] = 6
        return context

    def post(self, request, *args, **kwargs):
        form = FamilyNeedsToKnowSectionForm(request.POST, user=request.user)
        if form.is_valid():
            note = form.save()
            messages.success(request, f'Note for "{note.relation.first_name} {note.relation.last_name}" added!')
            return redirect(reverse('dashboard:onboarding_family'))
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


# ── Complete ──────────────────────────────────────────────────────────────────

class OnboardingCompleteView(OnboardingMixin, TemplateView):
    template_name = 'dashboard/onboarding/complete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['progress'] = self.get_onboarding_progress()
        context['step'] = 7
        context['total_steps'] = 6
        return context