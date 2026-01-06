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
import logging


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check session expiry
        if not self.request.session.get_expiry_age():
            logout(self.request)
            messages.warning(self.request, 'Your session has expired. Please log in again.')
            return redirect('login')
        
        context['user'] = self.request.user
        context['session_expires'] = self.request.session.get_expiry_date()
        return context

# Create your views here.
