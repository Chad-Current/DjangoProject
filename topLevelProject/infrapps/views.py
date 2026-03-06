# vault/views.py

import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from dashboard.models import Profile, Account, Device
from .models import VaultEntry, VaultAccessLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Guard mixin — replaces AddonRequiredMixin inline for the vault app
# so this file stays self-contained. Uses the same can_access_addon()
# method defined on CustomUser in the previous implementation.
# ---------------------------------------------------------------------------

class VaultAccessMixin(LoginRequiredMixin):
    """
    Requires:
      1. User is authenticated.
      2. User has a paid subscription tier (has_paid=True).
      3. User has an active add-on (can_access_addon()).

    Non-paying users  → /accounts/payment/
    Paying, no add-on → /accounts/addon/
    """
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not getattr(request.user, 'has_paid', False):
            messages.warning(
                request,
                'You need an active subscription to use the Vault.'
            )
            return redirect('accounts:payment')

        if not request.user.can_access_addon():
            messages.warning(
                request,
                'The Password Vault is part of the add-on subscription.'
            )
            return redirect('accounts:addon')

        return super().dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_profile_or_403(user):
    """Return the user's Profile or raise PermissionDenied."""
    try:
        return Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        raise PermissionDenied("Profile not found.")


def _get_client_ip(request) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

class VaultListView(VaultAccessMixin, ListView):
    model               = VaultEntry
    template_name       = 'infrapps/infrapps_list.html'
    context_object_name = 'entries'
    paginate_by         = 20

    def get_queryset(self):
        profile = _get_profile_or_403(self.request.user)
        qs = VaultEntry.objects.filter(profile=profile).select_related(
            'linked_account', 'linked_device'
        )

        # Optional filter by type
        entry_type = self.request.GET.get('type')
        if entry_type in ('account', 'device', 'other'):
            qs = qs.filter(entry_type=entry_type)

        return qs.order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = _get_profile_or_403(self.request.user)
        context['can_modify']    = self.request.user.can_modify_data()
        context['addon_active']  = self.request.user.can_access_addon()
        context['total_entries'] = VaultEntry.objects.filter(profile=profile).count()
        context['current_type']  = self.request.GET.get('type', '')
        return context


# ---------------------------------------------------------------------------
# DETAIL
# ---------------------------------------------------------------------------

class VaultDetailView(VaultAccessMixin, DetailView):
    model               = VaultEntry
    template_name       = 'infrapps/infrapps_detail.html'
    context_object_name = 'entry'
    slug_field          = 'slug'
    slug_url_kwarg      = 'slug'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        profile = _get_profile_or_403(self.request.user)
        if obj.profile != profile:
            raise PermissionDenied("You don't have permission to view this entry.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        # Password is NOT decrypted here — only via the reveal AJAX endpoint.
        return context


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

class VaultCreateView(VaultAccessMixin, CreateView):
    model         = VaultEntry
    template_name = 'infrapps/infrapps_form.html'
    # Fields handled manually — password goes through set_password(), not directly
    fields = [
        'entry_type',
        'label',
        'linked_account',
        'linked_device',
        'username_or_email',
        'notes',
    ]

    def get_success_url(self):
        return reverse('vault:vault_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        profile = _get_profile_or_403(self.request.user)

        # Scope FK dropdowns to the user's own data
        form.fields['linked_account'].queryset = Account.objects.filter(
            profile=profile
        ).order_by('account_name_or_provider')
        form.fields['linked_device'].queryset = Device.objects.filter(
            profile=profile
        ).order_by('device_name')

        form.fields['linked_account'].required = False
        form.fields['linked_device'].required  = False
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['addon_active'] = self.request.user.can_access_addon()
        context['page_title']   = 'Add Vault Entry'
        context['submit_label'] = 'Save Entry'
        return context

    def form_valid(self, form):
        if not self.request.user.can_modify_data():
            messages.error(self.request, "Your subscription does not allow adding entries.")
            return redirect('vault:vault_list')

        profile = _get_profile_or_403(self.request.user)
        entry   = form.save(commit=False)
        entry.profile = profile

        # Encrypt the raw password submitted in the extra field
        raw_password = self.request.POST.get('raw_password', '').strip()
        if not raw_password:
            form.add_error(None, "A password is required.")
            return self.form_invalid(form)

        entry.set_password(raw_password)

        # Auto-derive entry_type from which FK is set
        if entry.linked_account_id and not entry.linked_device_id:
            entry.entry_type = 'account'
        elif entry.linked_device_id and not entry.linked_account_id:
            entry.entry_type = 'device'

        entry.save()
        messages.success(self.request, f'"{entry.label}" saved to your vault.')
        logger.info("VaultEntry %s created by %s", entry.pk, self.request.user.email)
        return redirect(self.get_success_url())


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

class VaultUpdateView(VaultAccessMixin, UpdateView):
    model         = VaultEntry
    template_name = 'infrapps/infrapps_form.html'
    slug_field    = 'slug'
    slug_url_kwarg = 'slug'
    fields = [
        'entry_type',
        'label',
        'linked_account',
        'linked_device',
        'username_or_email',
        'notes',
    ]

    def get_success_url(self):
        return reverse('vault:vault_detail', kwargs={'slug': self.object.slug})

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        profile = _get_profile_or_403(self.request.user)
        if obj.profile != profile:
            raise PermissionDenied("You don't have permission to edit this entry.")
        return obj

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        profile = _get_profile_or_403(self.request.user)

        form.fields['linked_account'].queryset = Account.objects.filter(
            profile=profile
        ).order_by('account_name_or_provider')
        form.fields['linked_device'].queryset = Device.objects.filter(
            profile=profile
        ).order_by('device_name')

        form.fields['linked_account'].required = False
        form.fields['linked_device'].required  = False
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['addon_active']    = self.request.user.can_access_addon()
        context['page_title']      = f'Edit — {self.object.label}'
        context['submit_label']    = 'Update Entry'
        context['is_update']       = True
        # Tell the template whether the user left raw_password blank (= keep existing)
        context['password_optional'] = True
        return context

    def form_valid(self, form):
        if not self.request.user.can_modify_data():
            messages.error(self.request, "Your subscription does not allow editing entries.")
            return redirect('vault:vault_list')

        entry        = form.save(commit=False)
        raw_password = self.request.POST.get('raw_password', '').strip()

        # Only re-encrypt if a new password was supplied; otherwise keep the old token
        if raw_password:
            entry.set_password(raw_password)

        entry.save()
        messages.success(self.request, f'"{entry.label}" updated.')
        logger.info("VaultEntry %s updated by %s", entry.pk, self.request.user.email)
        return redirect(self.get_success_url())


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

class VaultDeleteView(VaultAccessMixin, DeleteView):
    model          = VaultEntry
    template_name  = 'infrapps/infrapps_confirm_delete.html'
    success_url    = reverse_lazy('vault:vault_list')
    slug_field     = 'slug'
    slug_url_kwarg = 'slug'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        profile = _get_profile_or_403(self.request.user)
        if obj.profile != profile:
            raise PermissionDenied("You don't have permission to delete this entry.")
        return obj

    def delete(self, request, *args, **kwargs):
        if not request.user.can_modify_data():
            messages.error(request, "Your subscription does not allow deleting entries.")
            return redirect('vault:vault_list')
        entry = self.get_object()
        label = entry.label
        entry.delete()
        messages.success(request, f'"{label}" removed from your vault.')
        logger.info("VaultEntry '%s' deleted by %s", label, request.user.email)
        return redirect(self.success_url)


# ---------------------------------------------------------------------------
# REVEAL PASSWORD  (AJAX POST — never GET)
# ---------------------------------------------------------------------------

class VaultRevealPasswordView(VaultAccessMixin, View):
    """
    POST /vault/<slug>/reveal/
    Returns the decrypted password as JSON and writes an audit log entry.
    The password is NEVER embedded in a page — only returned on explicit request.
    """

    def post(self, request, slug):
        if not request.user.can_access_addon():
            return JsonResponse({'success': False, 'error': 'Add-on required.'}, status=403)

        try:
            profile = _get_profile_or_403(request.user)
            entry   = VaultEntry.objects.get(slug=slug, profile=profile)
        except VaultEntry.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Entry not found.'}, status=404)
        except PermissionDenied as exc:
            return JsonResponse({'success': False, 'error': str(exc)}, status=403)

        plaintext = entry.get_password()

        # Write audit log
        VaultAccessLog.objects.create(
            entry       = entry,
            accessed_by = request.user,
            ip_address  = _get_client_ip(request),
        )
        logger.info(
            "VaultEntry %s revealed by %s from %s",
            entry.pk, request.user.email, _get_client_ip(request),
        )

        return JsonResponse({'success': True, 'password': plaintext})

    def get(self, request, slug):
        return JsonResponse(
            {'success': False, 'error': 'Use POST to reveal a password.'},
            status=405,
        )