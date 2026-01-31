# ============================================================================
# PART 7: DASHBOARD APP - ALL VIEWS - CORRECTED
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
from django.db.models import Min, Max, Q
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
    Contact,
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
    ContactForm,
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
            return redirect(reverse("accounts:payment"))

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
            # ACCOUNT COUNTS
            context['app_store'] = Account.objects.filter(Q(account_category='app_store')).count()
            context['cloud_storage'] = Account.objects.filter(Q(account_category='cloud_storage')).count()
            context['email'] = Account.objects.filter(Q(account_category='email')).count()
            context['education_elearning'] = Account.objects.filter(Q(account_category='education_elearning')).count()
            context['forum_community'] = Account.objects.filter(Q(account_category='forum_community')).count()
            context['gaming_platform'] = Account.objects.filter(Q(account_category='gaming_platform')).count()
            context['social_media'] = Account.objects.filter(Q(account_category='social_media')).count()
            context['subscription_saas'] = Account.objects.filter(Q(account_category='subscription_saas')).count()
            context['streaming_media'] = Account.objects.filter(Q(account_category='streaming_media')).count()
            context['ecommerce_marketplace'] = Account.objects.filter(Q(account_category='ecommerce_marketplace')).count()
            context['online_financial'] = Account.objects.filter(Q(account_category='online_banking') | Q(account_category='neobank_digital_bank') \
                    | Q(account_category='brokerage_investment') | Q(account_category='cryptocurrency_exchange') | Q(account_category='payment_wallet') \
                    | Q(account_category='payment_processor')).count()
            context['government_portal'] = Account.objects.filter(Q(account_category='government_portal')).count()
            context['health_portal'] = Account.objects.filter(Q(account_category='health_portal')).count()
            context['smart_home_iot'] = Account.objects.filter(Q(account_category='smart_home_iot')).count()
            context['travel_booking'] = Account.objects.filter(Q(account_category='travel_booking')).count()
            context['password_manager'] = Account.objects.filter(Q(account_category='password_manager')).count()
            context['utilities_telecom_portal'] = Account.objects.filter(Q(account_category='utilities_telecom_portal')).count()
            context['not_listed'] = Account.objects.filter(Q(account_category='not_listed')).count()
            #DEVICE COUNTS
            context['phones'] = Device.objects.filter(Q(device_type='phone')).count()
            context['tablets'] = Device.objects.filter(Q(device_type='tablet')).count()
            context['laptops'] = Device.objects.filter(Q(device_type='laptop')).count()
            context['desktops'] = Device.objects.filter(Q(device_type='desktop')).count()
            context['smartwatchs'] = Device.objects.filter(Q(device_type='smartwatch')).count()
            context['others'] = Device.objects.filter(Q(device_type='other')).count()

            context['delegation_count'] = DelegationGrant.objects.filter(profile=profile).count()
            context['documents_count'] = ImportantDocument.objects.filter(profile=profile).count()
            context['estate_count'] = DigitalEstateDocument.objects.filter(profile=profile).count()
            context['contacts_count'] = Contact.objects.filter(profile=profile).count()
            context['emergency_contacts_count'] = Contact.objects.filter(profile=profile,is_emergency_contact=True).count()
            context['family_awareness_count'] = FamilyNeedsToKnowSection.objects.filter(relation__profile=profile).count()
            # OPTIONALS
            keys = [
                'accounts_count',
                'contacts_count',
                'devices_count',
                'delegation_count',
                'documents_count',
                'estate_count',
                'family_needs_to_know',
            ]
            adjusted_values = []
            for key in keys:
                value = context.get(key, 0) or 0
                if value > 1:
                    value += 1
                adjusted_values.append(value)
            total = sum(adjusted_values) or 1
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
            
            review_dates = (AccountRelevanceReview.objects
                            .exclude(next_review_due__isnull=True)
                            .aggregate(
                                soonest=Min('next_review_due'),
                                farthest=Max('next_review_due')
                            ))

            soonest_review = review_dates['soonest']
            farthest_review = review_dates['farthest']
            context['soonest'] = soonest_review
            
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
            
            category_id = self.request.GET.get('account_category')
            if category_id:
                queryset = queryset.filter(category_id=category_id)
            
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


class AccountDeleteView(DeleteAccessMixin, DeleteView):
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
            qs = AccountRelevanceReview.objects.filter(account__profile=profile)
            
            account_id = self.request.GET.get('account')
            if account_id:
                qs = qs.filter(account_id=account_id)
            
            return qs.order_by('-review_date')
        except Profile.DoesNotExist:
            return AccountRelevanceReview.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
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
        form.instance.reviewer = self.request.user
        messages.success(self.request, 'Account review created successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
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
        return reverse_lazy('dashboard:account_detail', kwargs={'pk': self.object.account.pk})


class AccountRelevanceReviewDeleteView(DeleteAccessMixin, DeleteView):
    model = AccountRelevanceReview
    template_name = 'dashboard/accountrelevancereview_confirm_delete.html'
    owner_field = 'account__profile__user'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Account review deleted successfully.')
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
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
# DIGITAL ESTATE DOCUMENT VIEWS
# ============================================================================
class EstateListView(ViewAccessMixin, ListView):
    model = DigitalEstateDocument
    template_name = 'dashboard/estate_list.html'
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
    template_name = 'dashboard/estate_detail.html'
    context_object_name = 'estate'
    owner_field = 'profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class EstateCreateView(FullAccessMixin, CreateView):
    model = DigitalEstateDocument
    form_class = DigitalEstateDocumentForm
    template_name = 'dashboard/estate_form.html'
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
    template_name = 'dashboard/estate_form.html'
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
    template_name = 'dashboard/estate_confirm_delete.html'
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
    template_name = 'dashboard/familyawareness_list.html'
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
    template_name = 'dashboard/familyawareness_detail.html'
    context_object_name = 'familyawareness'
    owner_field = 'relation__profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class FamilyAwarenessCreateView(FullAccessMixin, CreateView):
    model = FamilyNeedsToKnowSection
    form_class = FamilyNeedsToKnowSectionForm
    template_name = 'dashboard/familyawareness_form.html'
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
    template_name = 'dashboard/familyawareness_form.html'
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
    template_name = 'dashboard/familyawareness_confirm_delete.html'
    success_url = reverse_lazy('dashboard:familyawareness_list')
    owner_field = 'contact__profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Family awareness section deleted successfully.')
        return super().delete(request, *args, **kwargs)
   
    def get_success_url(self):
        return reverse_lazy('dashboard:familyawareness_list')
    
    def get_success_url(self):
        return reverse_lazy('dashboard:account_list')
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
# CONTACT VIEWS
# ============================================================================
class ContactListView(ViewAccessMixin, ListView):
    model = Contact
    template_name = 'dashboard/contact_list.html'
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


class ContactCreateView(FullAccessMixin, CreateView):
    model = Contact
    form_class = ContactForm
    template_name = 'dashboard/contact_form.html'
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
    template_name = 'dashboard/contact_form.html'
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
    template_name = 'dashboard/contact_confirm_delete.html'
    success_url = reverse_lazy('dashboard:contact_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Contact deleted successfully.')
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