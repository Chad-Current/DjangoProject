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
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from accounts.mixins import FullAccessMixin, ViewAccessMixin, DeleteAccessMixin
from .models import (
    Profile,
    AccountCategory,
    DigitalAccount,
    AccountRelevanceReview,
    Contact,
    DelegationScope,
    DelegationGrant,
    Device,
    DigitalEstateDocument,
    FamilyNeedsToKnowSection,
    AccountDirectoryEntry,
    EmergencyNote,
    CheckupType,
    Checkup,
    CareRelationship,
    RecoveryRequest,
    DocumentCategory,
    ImportantDocument,
)
from .forms import (
    ProfileForm,
    AccountCategoryForm,
    DigitalAccountForm,
    AccountRelevanceReviewForm,
    ContactForm,
    DelegationScopeForm,
    DelegationGrantForm,
    DeviceForm,
    DigitalEstateDocumentForm,
    FamilyNeedsToKnowSectionForm,
    AccountDirectoryEntryForm,
    EmergencyNoteForm,
    CheckupTypeForm,
    CheckupForm,
    CareRelationshipForm,
    RecoveryRequestForm,
    DocumentCategoryForm,
    ImportantDocumentForm,
)


# ============================================================================
# DASHBOARD HOME
# ============================================================================
class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        try:
            profile = Profile.objects.get(user=user)
            context['profile'] = profile
            context['digital_accounts_count'] = DigitalAccount.objects.filter(profile=profile).count()
            context['contacts_count'] = Contact.objects.filter(profile=profile).count()
            context['devices_count'] = Device.objects.filter(profile=profile).count()
            context['documents_count'] = ImportantDocument.objects.filter(profile=profile).count()
        except Profile.DoesNotExist:
            context['profile'] = None
        
        context['can_modify'] = user.can_modify_data()
        context['can_view'] = user.can_view_data()
        context['tier_display'] = user.get_tier_display_name()
        
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
# ACCOUNT CATEGORY VIEWS
# ============================================================================
class AccountCategoryListView(ViewAccessMixin, ListView):
    model = AccountCategory
    template_name = 'dashboard/accountcategory_list.html'
    context_object_name = 'categories'
    owner_field = 'user'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class AccountCategoryCreateView(FullAccessMixin, CreateView):
    model = AccountCategory
    form_class = AccountCategoryForm
    template_name = 'dashboard/accountcategory_form.html'
    success_url = reverse_lazy('dashboard:accountcategory_list')
    owner_field = 'user'
    def form_valid(self, form):
        form.instance.user = self.request.user
        obj, created = AccountCategory.objects.get_or_create(
            user=self.request.user,
            name=form.cleaned_data['name'],
            defaults=form.cleaned_data
        )
        if created:
            messages.success(self.request, 'Category created successfully.')
        else:
            messages.info(self.request, 'Category already exists.')
        return redirect(self.success_url)
    # def form_valid(self, form):
    #     form.instance.user = self.request.user
    #     messages.success(self.request, 'Category created successfully.')
    #     return super().form_valid(form)


class AccountCategoryUpdateView(FullAccessMixin, UpdateView):
    model = AccountCategory
    form_class = AccountCategoryForm
    template_name = 'dashboard/accountcategory_form.html'
    success_url = reverse_lazy('dashboard:accountcategory_list')
    owner_field = 'user'
    
    def form_valid(self, form):
        messages.success(self.request, 'Category updated successfully.')
        return super().form_valid(form)


class AccountCategoryDeleteView(DeleteAccessMixin,  DeleteView):
    model = AccountCategory
    template_name = 'dashboard/accountcategory_confirm_delete.html'
    success_url = reverse_lazy('dashboard:accountcategory_list')
    owner_field = 'user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Category deleted successfully.')
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
            qs = AccountRelevanceReview.objects.filter(account__profile=profile)
            
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
                context['filtered_account'] = DigitalAccount.objects.get(
                    id=account_id,
                    profile__user=self.request.user
                )
            except DigitalAccount.DoesNotExist:
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
# DIGITAL ACCOUNT VIEWS
# ============================================================================
class DigitalAccountListView(ViewAccessMixin, ListView):
    model = DigitalAccount
    template_name = 'dashboard/account_list.html'
    context_object_name = 'accounts'
    owner_field = 'profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            queryset = DigitalAccount.objects.filter(profile=profile)
            
            # Filter by category if provided
            category_id = self.request.GET.get('category')
            if category_id:
                queryset = queryset.filter(category_id=category_id)
            
            # Filter by critical status
            is_critical = self.request.GET.get('critical')
            if is_critical:
                queryset = queryset.filter(is_critical=True)
            
            return queryset.order_by('-created_at')
        except Profile.DoesNotExist:
            return DigitalAccount.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        context['categories'] = AccountCategory.objects.filter(user=self.request.user)
        return context


class DigitalAccountDetailView(ViewAccessMixin, DetailView):
    model = DigitalAccount
    template_name = 'dashboard/account_detail.html'
    context_object_name = 'account'
    owner_field = 'profile__user'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class DigitalAccountCreateView(FullAccessMixin, CreateView):
    model = DigitalAccount
    form_class = DigitalAccountForm
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


class DigitalAccountUpdateView(FullAccessMixin, UpdateView):
    model = DigitalAccount
    form_class = DigitalAccountForm
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


class DigitalAccountDeleteView(DeleteAccessMixin,  DeleteView):
    model = DigitalAccount
    template_name = 'dashboard/account_confirm_delete.html'
    success_url = reverse_lazy('dashboard:account_list')
    owner_field = 'profile__user'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Digital account deleted successfully.')
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
            return Contact.objects.filter(profile=profile).order_by('full_name')
        except Profile.DoesNotExist:
            return Contact.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class ContactDetailView(ViewAccessMixin, DetailView):
    model = Contact
    template_name = 'dashboard/contact_detail.html'
    context_object_name = 'contact'
    owner_field = 'profile__user'
    
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
# EMERGENCY NOTE VIEWS
# ============================================================================
class EmergencyNoteListView(ViewAccessMixin, ListView):
    model = EmergencyNote
    template_name = 'dashboard/emergencynote_list.html'
    context_object_name = 'notes'
    owner_field = 'profile__user'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            profile = Profile.objects.get(user=self.request.user)
            return EmergencyNote.objects.filter(profile=profile).order_by('-created_at')
        except Profile.DoesNotExist:
            return EmergencyNote.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        return context


class EmergencyNoteCreateView(FullAccessMixin, CreateView):
    model = EmergencyNote
    form_class = EmergencyNoteForm
    template_name = 'dashboard/emergencynote_form.html'
    success_url = reverse_lazy('dashboard:emergencynote_list')
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


class EmergencyNoteUpdateView(FullAccessMixin, UpdateView):
    model = EmergencyNote
    form_class = EmergencyNoteForm
    template_name = 'dashboard/emergencynote_form.html'
    success_url = reverse_lazy('dashboard:emergencynote_list')
    owner_field = 'profile__user'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Emergency note updated successfully.')
        return super().form_valid(form)


class EmergencyNoteDeleteView(DeleteAccessMixin, DeleteView):
    model = EmergencyNote
    template_name = 'dashboard/emergencynote_confirm_delete.html'
    success_url = reverse_lazy('dashboard:emergencynote_list')
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
