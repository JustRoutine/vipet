"""
URL configuration for the accounts app.

Namespace: accounts
"""

from django.urls import path

from apps.accounts.views import (
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ProfileView,
    RegisterView,
)

app_name = "accounts"

urlpatterns = [
    path("register/",                              RegisterView.as_view(),             name="register"),
    path("login/",                                 LoginView.as_view(),                name="login"),
    path("logout/",                                LogoutView.as_view(),               name="logout"),
    path("password-reset/",                        PasswordResetRequestView.as_view(), name="password_reset"),
    path("password-reset/<uidb64>/<token>/",       PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("profile/",                               ProfileView.as_view(),              name="profile"),
]
