from django.urls import path
from . import views

app_name = 'infrapps'

urlpatterns = [
    path('',                          views.VaultListView.as_view(),            name='vault_list'),
    path('add/',                      views.VaultCreateView.as_view(),          name='vault_create'),
    path('<slug:slug>/',              views.VaultDetailView.as_view(),          name='vault_detail'),
    path('<slug:slug>/edit/',         views.VaultUpdateView.as_view(),          name='vault_update'),
    path('<slug:slug>/delete/',       views.VaultDeleteView.as_view(),          name='vault_delete'),
    path('<slug:slug>/reveal/',       views.VaultRevealPasswordView.as_view(),  name='vault_reveal'),
]