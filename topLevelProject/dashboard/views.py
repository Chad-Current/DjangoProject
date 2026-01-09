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
# from .forms import UserRegistrationForm, UserLoginForm
import logging

class AccountDirectoryView(LoginRequiredMixin, TemplateView):
   template_name = "dashboard/accountdirectory.html"

class ContactDelegationView(LoginRequiredMixin,TemplateView):
   template_name = "dashboard/contactdelegation.html"
   
class DecisionView(LoginRequiredMixin,TemplateView):
   template_name = "dashboard/decisions.html"
   
class DevicesView(LoginRequiredMixin, TemplateView):
   template_name = "dashboard/devices.html"
   
class DigitalEstateView(LoginRequiredMixin, TemplateView):
   template_name = "dashboard/digitalestate.html"
   
class EmergencyNotesView(LoginRequiredMixin, TemplateView):
   template_name = "dashboard/emergencynotes.html"
   
class FamilyAwarenessView(LoginRequiredMixin, TemplateView):
   template_name = "dashboard/familyawareness.html"
   
class ProfileView(LoginRequiredMixin, TemplateView):
   template_name = "dashboard/profile.html"
   
class AnnualReviewView(LoginRequiredMixin, TemplateView):
   template_name = "dashboard/annualreview.html"

class QuarterlyReviewView(LoginRequiredMixin, TemplateView):
   template_name = "dashboard/quarterlyreview.html"