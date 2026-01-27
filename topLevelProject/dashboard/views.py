# ============================================================================
# PART 7: DASHBOARD APP - ALL VIEWS
# ============================================================================

# ============================================================================
# dashboard/views.py
# ============================================================================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.urls import reverse_lazy
from django.urls import reverse
from django.contrib import messages
from django.db.models import Min, Max
from datetime import datetime, timedelta
from django.contrib.messages.views import SuccessMessageMixin
from accounts.mixins import FullAccessMixin, ViewAccessMixin, DeleteAccessMixin
from .models import (
    Profile,
    Account,
    AccountRelevanceReview,
    DelegationGrant,
    Device,
    DigitalEstateDocument,
    FamilyNeedsToKnowSection,
    EmergencyContact,
    Checkup,
    CareRelationship,
    RecoveryRequest,
    ImportantDocument,
)
from .forms import (
    ProfileForm,
    AccountForm,
    AccountRelevanceReviewForm,
    DelegationGrantForm,
    DeviceForm,
    DigitalEstateDocumentForm,
    FamilyNeedsToKnowSectionForm,
    EmergencyContactForm,
    CheckupForm,
    CareRelationshipForm,
    RecoveryRequestForm,
    ImportantDocumentForm,
)


# ============================================================================
# DASHBOARD HOME
# ============================================================================
class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not getattr(user, "has_paid", False):
            return redirect(reverse("accounts:payment"))  #'payment checking'

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            profile = Profile.objects.get(user=user)
            context['user'] = user
            context['profile'] = profile
            context['session_expires'] = self.request.session.get_expiry_date()
            # COUNTS
            context['accounts_count'] = Account.objects.filter(profile=profile).count()
            context['devices_count'] = Device.objects.filter(profile=profile).count()
            context['delegation_count'] = DelegationGrant.objects.filter(profile=profile).count()
            context['documents_count'] = ImportantDocument.objects.filter(profile=profile).count()
            context['estate_count'] = DigitalEstateDocument.objects.filter(profile=profile).count()
            context['emergency_contacts_count'] = EmergencyContact.objects.filter(profile=profile).count()
            # context['emergency_digital_executor_count'] = EmergencyContact.objects.filter(is_digital_executor__profile=profile).count()
            # context['family_needs_to_know_count'] = FamilyNeedsToKnowSection.objects.filter(document_id__profile=profile).count()
            # OPTIONALS
            keys = [
                    'accounts_count',
                    'contacts_count',
                    'devices_count',
                    'delegation_count',
                    'documents_count',
                    'estate_count',
                    'emergency_contacts_count',
                    'family_needs_to_know',
                ]
            adjusted_values = []
            for key in keys:
                value = context.get(key, 0) or 0
                if value > 1:
                    value += 1
                adjusted_values.append(value)
            total = sum(adjusted_values) or 1  # avoid division by zero
            context['progress'] = (total / len(keys)) * 100
            context['remaining_tasks'] = len(keys) - total
            # PERMISSIONS CONTEXT 
            context['tier_display'] = user.get_tier_display_name()
            context['can_modify'] = user.can_modify_data()
            context['can_view'] = user.can_view_data()
            context['alert_due'] = False
            context['alert_attention'] = False
            context['alert_due_year'] = False
            context['alert_attention_year'] = False
            today = datetime.today().date()
# THIS COULD BE A POTENTIAL ISSUE DOWN THE ROAD ########
            review_dates = (AccountRelevanceReview.objects
                            .exclude(next_review_due__isnull=True)
                            .aggregate(
                                soonest=Min('next_review_due'),
                                farthest=Max('next_review_due')
                            )
            )

            soonest_review = review_dates['soonest']
            farthest_review = review_dates['farthest']
            if soonest_review:
                first_delta = soonest_review - today
                if first_delta.days <= 0:
                    context['alert_due'] = True
                elif first_delta.days <= 7:
                    context['alert_attention'] = True

            if farthest_review:
                last_delta = farthest_review - today
                if last_delta.days <= 0:
                    context['alert_due_year'] = True
                elif last_delta.days <= 30:
                    context['alert_attention_year'] = True
###################### STATIC STATES ISSUE #############

            ##### CAUSING ERROR FOR UNBOUND ###############
            # context['upcoming_review_days'] = first_delta
            # context['furthest_review_days'] = last_delta
            ################################################
            if user.subscription_tier == 'essentials':
                context['is_edit_active'] = user.is_essentials_edit_active()
                context['days_remaining'] = user.days_until_essentials_expires()
                context['essentials_expires'] = user.essentials_expires

            if user.subscription_tier == 'legacy':
                context['legacy_granted'] = user.legacy_granted_date

        except Profile.DoesNotExist:
            context['profile'] = None

        return context
        
# ============================================================================
# PROFILE VIEWS
# ============================================================================
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
    success_url = reverse_lazy('dashboard:profile_detail')
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
    template_name = 'dashboard/account_list.html'
    context_object_name = 'accounts'
    owner_field = 'profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            queryset = Account.objects.filter(profile=profile)
            
            # Filter by category if provided
            category_id = self.request.GET.get('account_category')
            if category_id:
                queryset = queryset.filter(category_id=category_id)
            
            # Filter by critical status
            is_critical = self.request.GET.get('critical')
            if is_critical:
                queryset = queryset.filter(is_critical=True)

            return queryset.order_by('-created_at')
        except Profile.DoesNotExist:
            return Account.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        # Fixed: Changed to get categories from DocumentCategory model
        try:
            profile = Profile.objects.get(user=self.request.user)
            context['categories'] = Account.objects.filter(profile=profile)
        except Profile.DoesNotExist:
            context['categories'] = Account.objects.none()
        return context


class AccountDetailView(ViewAccessMixin, DetailView):
    model = Account
    template_name = 'dashboard/account_detail.html'
    context_object_name = 'account'
    owner_field = 'profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        
        # Get the most recent review for this account
        # try:
        #     latest_review = AccountRelevanceReview.objects.filter(
        #         account_relevance=self.object
        #     ).order_by('-review_date').first()
        #     context['latest_review'] = latest_review
        # except AccountRelevanceReview.DoesNotExist:
        #     context['latest_review'] = None
            
        return context


class AccountCreateView(FullAccessMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = 'dashboard/account_form.html'
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
    template_name = 'dashboard/account_form.html'
    success_url = reverse_lazy('dashboard:account_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Digital account updated successfully.')
        return super().form_valid(form)


class AccountDeleteView(DeleteAccessMixin,  DeleteView):
    model = Account
    template_name = 'dashboard/account_confirm_delete.html'
    success_url = reverse_lazy('dashboard:account_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Account deleted successfully.')
        return super().delete(request, *args, **kwargs)
    

# ============================================================================
# ACCOUNT RELEVANCE REVIEW VIEWS
# ============================================================================
class AccountRelevanceReviewListView(ViewAccessMixin, ListView):
    model = AccountRelevanceReview
    template_name = 'dashboard/accountrelevancereview_list.html'
    context_object_name = 'reviews'
    owner_field = 'account__profile__user'
    paginate_by = 20

    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            # Start with all reviews for accounts belonging to this user's profile
            qs = AccountRelevanceReview.objects.filter(account_id__profile=profile)
            
            # Optionally filter by a specific account via ?account=<id>
            account_id = self.request.GET.get('account')
            if account_id:
                qs = qs.filter(account_id=account_id)
            
            return qs.order_by('-review_date')
        except Profile.DoesNotExist:
            return AccountRelevanceReview.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        # If filtering by account, add the account to context
        account_id = self.request.GET.get('account')
        if account_id:
            try:
                context['filtered_account'] = Account.objects.get(
                    id=account_id,
                    profile__user=self.request.user
                )
            except Account.DoesNotExist:
                pass
        return context


class AccountRelevanceReviewDetailView(ViewAccessMixin, DetailView):
    model = AccountRelevanceReview
    template_name = 'dashboard/accountrelevancereview_detail.html'
    context_object_name = 'review'
    owner_field = 'account__profile__user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class AccountRelevanceReviewCreateView(FullAccessMixin, CreateView):
    model = AccountRelevanceReview
    form_class = AccountRelevanceReviewForm
    template_name = 'dashboard/accountrelevancereview_form.html'
    owner_field = 'account__profile__user'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Set the reviewer to the current user
        form.instance.reviewer = self.request.user
        messages.success(self.request, 'Account review created successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        # Redirect back to the account detail page
        return reverse_lazy('dashboard:account_detail', kwargs={'pk': self.object.account.pk})


class AccountRelevanceReviewUpdateView(FullAccessMixin, UpdateView):
    model = AccountRelevanceReview
    form_class = AccountRelevanceReviewForm
    template_name = 'dashboard/accountrelevancereview_form.html'
    owner_field = 'account__profile__user'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Account review updated successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        # Redirect back to the account detail page
        return reverse_lazy('dashboard:account_detail', kwargs={'pk': self.object.account.pk})


class AccountRelevanceReviewDeleteView(DeleteAccessMixin, DeleteView):
    model = AccountRelevanceReview
    template_name = 'dashboard/accountrelevancereview_confirm_delete.html'
    owner_field = 'account__profile__user'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Account review deleted successfully.')
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        # Redirect back to the account list
        return reverse_lazy('dashboard:account_list')
    
    
# ============================================================================
# DEVICE VIEWS
# ============================================================================
class DeviceListView(ViewAccessMixin, ListView):
    model = Device
    template_name = 'dashboard/device_list.html'
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
    template_name = 'dashboard/device_detail.html'
    context_object_name = 'device'
    owner_field = 'profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class DeviceCreateView(FullAccessMixin, CreateView):
    model = Device
    form_class = DeviceForm
    template_name = 'dashboard/device_form.html'
    success_url = reverse_lazy('dashboard:device_list')
    owner_field = 'profile__user'
    
    def form_valid(self, form):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Device created successfully.')
        return super().form_valid(form)


class DeviceUpdateView(FullAccessMixin, UpdateView):
    model = Device
    form_class = DeviceForm
    template_name = 'dashboard/device_form.html'
    success_url = reverse_lazy('dashboard:device_list')
    owner_field = 'profile__user'
    
    def form_valid(self, form):
        messages.success(self.request, 'Device updated successfully.')
        return super().form_valid(form)


class DeviceDeleteView(DeleteAccessMixin, DeleteView):
    model = Device
    template_name = 'dashboard/device_confirm_delete.html'
    success_url = reverse_lazy('dashboard:device_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Device deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# IMPORTANT DOCUMENT VIEWS
# ============================================================================
class ImportantDocumentListView(ViewAccessMixin, ListView):
    model = ImportantDocument
    template_name = 'dashboard/importantdocument_list.html'
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
    template_name = 'dashboard/importantdocument_detail.html'
    context_object_name = 'document'
    owner_field = 'profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class ImportantDocumentCreateView(FullAccessMixin, CreateView):
    model = ImportantDocument
    form_class = ImportantDocumentForm
    template_name = 'dashboard/importantdocument_form.html'
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
    template_name = 'dashboard/importantdocument_form.html'
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
    template_name = 'dashboard/importantdocument_confirm_delete.html'
    success_url = reverse_lazy('dashboard:importantdocument_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Document deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# DELEGATION GRANT VIEWS
# ============================================================================
class DelegationGrantListView(ViewAccessMixin, ListView):
    model = DelegationGrant
    template_name = 'dashboard/delegationgrant_list.html'
    context_object_name = 'grants'
    owner_field = 'profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return DelegationGrant.objects.filter(profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return DelegationGrant.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class DelegationGrantCreateView(FullAccessMixin, CreateView):
    model = DelegationGrant
    form_class = DelegationGrantForm
    template_name = 'dashboard/delegationgrant_form.html'
    success_url = reverse_lazy('dashboard:delegationgrant_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Delegation grant created successfully.')
        return super().form_valid(form)


class DelegationGrantUpdateView(FullAccessMixin, UpdateView):
    model = DelegationGrant
    form_class = DelegationGrantForm
    template_name = 'dashboard/delegationgrant_form.html'
    success_url = reverse_lazy('dashboard:delegationgrant_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Delegation grant updated successfully.')
        return super().form_valid(form)


class DelegationGrantDeleteView(DeleteAccessMixin, DeleteView):
    model = DelegationGrant
    template_name = 'dashboard/delegationgrant_confirm_delete.html'
    success_url = reverse_lazy('dashboard:delegationgrant_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Delegation grant deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# EMERGENCY CONTACT VIEWS
# ============================================================================
class EmergencyContactListView(ViewAccessMixin, ListView):
    model = EmergencyContact
    template_name = 'dashboard/emergencycontact_list.html'
    context_object_name = 'emergency'
    owner_field = 'profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return EmergencyContact.objects.filter(profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return EmergencyContact.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class EmergencyContactCreateView(FullAccessMixin, CreateView):
    model = EmergencyContact
    form_class = EmergencyContactForm
    template_name = 'dashboard/emergencycontact_form.html'
    success_url = reverse_lazy('dashboard:emergencycontact_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        messages.success(self.request, 'Emergency note created successfully.')
        return super().form_valid(form)


class EmergencyContactUpdateView(FullAccessMixin, UpdateView):
    model = EmergencyContact
    form_class = EmergencyContactForm
    template_name = 'dashboard/emergencycontact_form.html'
    success_url = reverse_lazy('dashboard:emergencycontact_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Emergency note updated successfully.')
        return super().form_valid(form)


class EmergencyContactDeleteView(DeleteAccessMixin, DeleteView):
    model = EmergencyContact
    template_name = 'dashboard/emergencycontact_confirm_delete.html'
    success_url = reverse_lazy('dashboard:emergencycontact_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Emergency note deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# CHECKUP VIEWS
# ============================================================================
class CheckupListView(ViewAccessMixin, ListView):
    model = Checkup
    template_name = 'dashboard/checkup_list.html'
    context_object_name = 'checkups'
    owner_field = 'profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return Checkup.objects.filter(profile=profile).order_by('-due_date')
        except Profile.DoesNotExist:
            return Checkup.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class CheckupCreateView(FullAccessMixin, CreateView):
    model = Checkup
    form_class = CheckupForm
    template_name = 'dashboard/checkup_form.html'
    success_url = reverse_lazy('dashboard:checkup_list')
    owner_field = 'profile__user'
    
    def form_valid(self, form):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        form.instance.completed_by = self.request.user
        messages.success(self.request, 'Checkup created successfully.')
        return super().form_valid(form)


class CheckupUpdateView(FullAccessMixin, UpdateView):
    model = Checkup
    form_class = CheckupForm
    template_name = 'dashboard/checkup_form.html'
    success_url = reverse_lazy('dashboard:checkup_list')
    owner_field = 'profile__user'
    
    def form_valid(self, form):
        messages.success(self.request, 'Checkup updated successfully.')
        return super().form_valid(form)


class CheckupDeleteView(DeleteAccessMixin, DeleteView):
    model = Checkup
    template_name = 'dashboard/checkup_confirm_delete.html'
    success_url = reverse_lazy('dashboard:checkup_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Checkup deleted successfully.')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# RECOVERY REQUEST VIEWS
# ============================================================================
class RecoveryRequestListView(ViewAccessMixin, ListView):
    model = RecoveryRequest
    template_name = 'dashboard/recoveryrequest_list.html'
    context_object_name = 'requests'
    owner_field = 'profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return RecoveryRequest.objects.filter(profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return RecoveryRequest.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class RecoveryRequestCreateView(FullAccessMixin, CreateView):
    model = RecoveryRequest
    form_class = RecoveryRequestForm
    template_name = 'dashboard/recoveryrequest_form.html'
    success_url = reverse_lazy('dashboard:recoveryrequest_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        form.instance.profile = profile
        form.instance.requested_by = self.request.user
        messages.success(self.request, 'Recovery request created successfully.')
        return super().form_valid(form)


class RecoveryRequestUpdateView(FullAccessMixin, UpdateView):
    model = RecoveryRequest
    form_class = RecoveryRequestForm
    template_name = 'dashboard/recoveryrequest_form.html'
    success_url = reverse_lazy('dashboard:recoveryrequest_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Recovery request updated successfully.')
        return super().form_valid(form)


class RecoveryRequestDeleteView(DeleteAccessMixin, DeleteView):
    model = RecoveryRequest
    template_name = 'dashboard/recoveryrequest_confirm_delete.html'
    success_url = reverse_lazy('dashboard:recoveryrequest_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Recovery request deleted successfully.')
        return super().delete(request, *args, **kwargs)


class MainTemplateView(TemplateView):
    template_name = 'dashboard/main_template.html'
