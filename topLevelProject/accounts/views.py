from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from django.views import View
from django.views.generic import TemplateView
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse_lazy
from datetime import timedelta
from .forms import UserRegistrationForm, UserLoginForm, CustomPasswordResetForm, CustomSetPasswordForm
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class RegisterView(View):
    template_name = 'accounts/register.html'
    form_class = UserRegistrationForm
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:account_dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            if hasattr(user, 'last_login_ip'):
                user.last_login_ip = get_client_ip(request)
                user.save(update_fields=['last_login_ip'])
            logger.info(f'New user registered: {user.email}')
            messages.success(request, 'Registration successful! Please log in.')
            return redirect('accounts:login')
        return render(request, self.template_name, {'form': form})


class LoginView(View):
    template_name = 'accounts/login.html'
    form_class = UserLoginForm
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard:dashboard_home')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data.get('username_or_email')
            password = form.cleaned_data.get('password')
            auth_user = authenticate(request, username=username_or_email, password=password)
            
            if auth_user is not None:
                account_locked_until = getattr(auth_user, 'account_locked_until', None)
                if account_locked_until and timezone.now() < account_locked_until:
                    messages.error(request, 'Account is temporarily locked due to multiple failed login attempts.')
                    return render(request, self.template_name, {'form': form})
                
                if hasattr(auth_user, 'failed_login_attempts'):
                    auth_user.failed_login_attempts = 0
                    auth_user.account_locked_until = None
                if hasattr(auth_user, 'last_login_ip'):
                    auth_user.last_login_ip = get_client_ip(request)
                auth_user.save()
                
                login(request, auth_user)
                request.session.set_expiry(3600)
                logger.info(f'User logged in: {auth_user.username}')
                
                # Check is user has paid at least once
                if request.user.has_paid:
                    return redirect('dashboard:dashboard_home')
                else:
                    return redirect('accounts:payment')
            else:
                try:
                    from django.db.models import Q
                    user = User.objects.get(Q(username__iexact=username_or_email) | Q(email__iexact=username_or_email))
                    if hasattr(user, 'failed_login_attempts'):
                        user.failed_login_attempts += 1
                        if user.failed_login_attempts >= 5:
                            user.account_locked_until = timezone.now() + timedelta(minutes=30)
                            messages.error(request, 'Account locked for 30 minutes due to multiple failed attempts.')
                        else:
                            messages.error(request, f'Invalid credentials. {5 - user.failed_login_attempts} attempts remaining.')
                        user.save()
                    else:
                        messages.error(request, 'Invalid credentials.')
                except User.DoesNotExist:
                    messages.error(request, 'Invalid credentials.')
                logger.warning(f'Failed login attempt for: {username_or_email}')
        
        return render(request, self.template_name, {'form': form})


class LogoutView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    
    def get(self, request):
        user_email = request.user.email
        logout(request)
        logger.info(f'User logged out: {user_email}')
        messages.success(request, 'You have been logged out.')
        return redirect('accounts:login')
    
    def post(self, request):
        return self.get(request)


# class DashboardView(LoginRequiredMixin, TemplateView):
#     template_name = 'accounts/dashboard.html'
#     login_url = '/accounts/login/'
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         user = self.request.user
        
#         context['user'] = user
#         context['session_expires'] = self.request.session.get_expiry_date()
#         context['can_modify'] = user.can_modify_data()
#         context['can_view'] = user.can_view_data()
#         context['has_paid'] = user.has_paid
#         context['subscription_tier'] = user.subscription_tier
#         context['tier_display'] = user.get_tier_display_name()
        
#         # Essentials specific
#         if user.subscription_tier == 'essentials':
#             context['is_edit_active'] = user.is_essentials_edit_active()
#             context['days_remaining'] = user.days_until_essentials_expires()
#             context['essentials_expires'] = user.essentials_expires
        
#         # Legacy specific
#         if user.subscription_tier == 'legacy':
#             context['legacy_granted'] = user.legacy_granted_date
        
#         return context


class PaymentView(LoginRequiredMixin, View):
    """Handle payment selection and activation"""
    template_name = 'accounts/payment.html'
    login_url = '/accounts/login/'
    
    def get(self, request):
        if request.user.has_paid and request.user.subscription_tier != 'none':
            messages.info(request, 'You already have an active subscription.')
            return redirect('dashboard:dashboard_page')
        
        context = {
            'user': request.user,
            'essentials_price': 99.99,
            'legacy_price': 299.99,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        tier_choice = request.POST.get('tier_choice')
        
        if tier_choice == 'essentials':
            request.user.upgrade_to_essentials()
            logger.info(f'User {request.user.email} upgraded to Essentials')
            messages.success(request, 'Essentials tier activated! You have 1 year of edit access.')
            return redirect('dashboard:dashboard_home')
        
        elif tier_choice == 'legacy':
            request.user.upgrade_to_legacy()
            logger.info(f'User {request.user.email} upgraded to Legacy')
            messages.success(request, 'Legacy tier activated! You now have lifetime access.')
            return redirect('dashboard:dashboard_home')
        
        else:
            messages.error(request, 'Please select a subscription tier.')
            return redirect('accounts:payment')


# Password Reset Views
class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy('password_reset_done')
    
    def form_valid(self, form):
        messages.success(self.request, 'Password reset email has been sent.')
        return super().form_valid(form)


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('password_reset_complete')
    
    def form_valid(self, form):
        messages.success(self.request, 'Your password has been reset successfully.')
        return super().form_valid(form)


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'


# Convert to function views for easier URL mapping
register_view = RegisterView.as_view()
login_view = LoginView.as_view()
logout_view = LogoutView.as_view()
payment_view = PaymentView.as_view()
password_reset_view = CustomPasswordResetView.as_view()
password_reset_done_view = CustomPasswordResetDoneView.as_view()
password_reset_confirm_view = CustomPasswordResetConfirmView.as_view()
password_reset_complete_view = CustomPasswordResetCompleteView.as_view()
