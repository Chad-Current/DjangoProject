from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .forms import UserRegistrationForm, UserLoginForm
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

def is_account_locked(user):
    """Check if user account is locked"""
    if user.account_locked_until:
        return timezone.now() < user.account_locked_until
    return False

@method_decorator(csrf_protect, name='dispatch')
class RegisterView(View):
    template_name = 'accounts/register.html'
    form_class = UserRegistrationForm
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            # Save the user with hashed password
            user = form.save()
            
            # Add additional fields
            if hasattr(user, 'last_login_ip'):
                user.last_login_ip = get_client_ip(request)
                user.save(update_fields=['last_login_ip'])
            
            logger.info(f'New user registered: {user.email}')
            messages.success(request, 'Registration successful! Please log in.')
            return redirect('accounts:login')
        
        return render(request, self.template_name, {'form': form})

@method_decorator(csrf_protect, name='dispatch')
class LoginView(View):
    template_name = 'accounts/login.html'
    form_class = UserLoginForm
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data.get('username_or_email')
            password = form.cleaned_data.get('password')
            
            # The custom backend will handle both email and username
            auth_user = authenticate(request, username=username_or_email, password=password)
            
            logger.info(f'Login attempt for: {username_or_email}')
            
            if auth_user is not None:
                # Check if account is locked
                account_locked_until = getattr(auth_user, 'account_locked_until', None)
                if account_locked_until and timezone.now() < account_locked_until:
                    messages.error(request, 'Account is temporarily locked due to multiple failed login attempts.')
                    return render(request, self.template_name, {'form': form})
                
                # Reset failed attempts (with safe attribute access)
                if hasattr(auth_user, 'failed_login_attempts'):
                    auth_user.failed_login_attempts = 0
                    auth_user.account_locked_until = None
                if hasattr(auth_user, 'last_login_ip'):
                    auth_user.last_login_ip = get_client_ip(request)
                auth_user.save()
                
                login(request, auth_user)
                logger.info(f'User logged in successfully: {auth_user.username}')
                
                # Set session expiry
                request.session.set_expiry(3600)  # 1 hour
                
                return redirect('accounts:dashboard')
            else:
                # Try to find user to increment failed attempts
                try:
                    from django.db.models import Q
                    user = User.objects.get(
                        Q(username__iexact=username_or_email) | Q(email__iexact=username_or_email)
                    )
                    
                    if hasattr(user, 'failed_login_attempts'):
                        user.failed_login_attempts += 1
                        
                        # Lock account after 5 failed attempts
                        if user.failed_login_attempts >= 5:
                            user.account_locked_until = timezone.now() + timedelta(minutes=30)
                            messages.error(request, 'Account locked for 30 minutes due to multiple failed attempts.')
                        else:
                            messages.error(request, f'Invalid password. {5 - user.failed_login_attempts} attempts remaining.')
                        
                        user.save()
                    else:
                        messages.error(request, 'Incorrect Username/Email.')
                    
                except User.DoesNotExist:
                    messages.error(request, 'User does not exist.')
                
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

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard.html'
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check session expiry
        if not self.request.session.get_expiry_age():
            logout(self.request)
            messages.warning(self.request, 'Your session has expired. Please log in again.')
            return redirect('accounts:login')
        
        context['user'] = self.request.user
        context['session_expires'] = self.request.session.get_expiry_date()
        return context

# Keep these for backward compatibility or if you prefer function-based views
register_view = RegisterView.as_view()
login_view = LoginView.as_view()
logout_view = LogoutView.as_view()
dashboard_view = DashboardView.as_view()

