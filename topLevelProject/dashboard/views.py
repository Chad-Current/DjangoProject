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

class AccountDirectoryView(TemplateView, LoginRequiredMixin):
   template_name = "dashboard/accountdirectory.html"

class ContactDelegationView(TemplateView, LoginRequiredMixin):
   template_name = "dashboard/contactdelegation.html"
   
class DecisionView(TemplateView, LoginRequiredMixin):
   template_name = "dashboard/decisions.html"
   
class DevicesView(TemplateView, LoginRequiredMixin):
   template_name = "dashboard/devices.html"
   
class DigitalEstateView(TemplateView, LoginRequiredMixin):
   template_name = "dashboard/digitalestate.html"
   
class EmergencyNotesView(TemplateView, LoginRequiredMixin):
   template_name = "dashboard/emergencynotes.html"
   
class FamilyAwarenessView(TemplateView, LoginRequiredMixin):
   template_name = "dashboard/familyawareness.html"
   
class ProfileView(TemplateView, LoginRequiredMixin):
   template_name = "dashboard/profile.html"
   
class AnnualReviewView(TemplateView, LoginRequiredMixin):
   template_name = "dashboard/annualreview.html"

class QuarterlyReviewView(TemplateView, LoginRequiredMixin):
   template_name = "dashboard/quarterlyreview.html"