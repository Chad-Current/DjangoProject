from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.core.mail import send_mail, BadHeaderError
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import FormView, UpdateView, DeletionMixin, DeleteView
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin


class Home(TemplateView):
   template_name = "baseapp/index.html"