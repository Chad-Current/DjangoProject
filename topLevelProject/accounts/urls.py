# accounts urls
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Pricing / subscription selection
    path('payment/', views.payment_view, name='payment'),

    # Stripe subscription flow (AJAX)
    path('subscription/create/', views.create_subscription_view, name='create_subscription'),
    path('subscription/confirm/', views.confirm_subscription_view, name='confirm_subscription'),
    path('subscription/success/', views.subscription_success_view, name='subscription_success'),
    path('subscription/manage/', views.manage_subscription_view, name='subscription_manage'),
    path('subscription/cancel/', views.cancel_subscription_view, name='subscription_cancel'),
    path('subscription/upgrade/', views.upgrade_subscription_view, name='subscription_upgrade'),

    # Stripe webhook (no CSRF, no login)
    path('webhook/stripe/', views.stripe_webhook_view, name='stripe_webhook'),

    # Password Reset
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('password-reset/done/', views.password_reset_done_view, name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('password-reset/complete/', views.password_reset_complete_view, name='password_reset_complete'),
]
