from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.core.mail import send_mail, BadHeaderError
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import FormView, UpdateView, DeletionMixin, DeleteView
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin


class Classes(TemplateView):
   template_name = "classes/classes.html"

class Puppy(TemplateView):
   template_name = "classes/puppy.html"

class Beginner(TemplateView):
   template_name = "classes/beginner.html"

class Advanced(TemplateView):
   template_name = "classes/advanced.html"

class Conformation(TemplateView):
   template_name = "classes/conformation.html"

class Service(TemplateView):
   template_name = "classes/service_class.html"

class Rally(TemplateView):
   template_name = "classes/rally.html"

class Scent(TemplateView):
   template_name = "classes/scent.html"

class Therapy(TemplateView):
   template_name = "classes/therapy.html"