"""
Dashboard URL configuration.

Provides two sets of URL patterns:
  - client_urlpatterns: included at /client/ (namespace: client_dashboard)
  - admin_urlpatterns:  included at /admin-panel/ (namespace: admin_dashboard)

Requirements: 14.1, 15.1
"""

from django.urls import path

from apps.dashboard.views import (
    AdminDashboardView,
    AdminPetListView,
    AdminUserListView,
    ClientDashboardView,
    LiveCameraView,
)

app_name = "dashboard"

# Client URL patterns (included at /client/)
client_urlpatterns = [
    path("", ClientDashboardView.as_view(), name="client_dashboard"),
    path("live-camera/", LiveCameraView.as_view(), name="live_camera"),
]

# Admin URL patterns (included at /admin-panel/)
admin_urlpatterns = [
    path("", AdminDashboardView.as_view(), name="admin_dashboard"),
    path("users/", AdminUserListView.as_view(), name="admin_users"),
    path("pets/", AdminPetListView.as_view(), name="admin_pets"),
]

# Default urlpatterns for backward compatibility — contains all routes.
# Access control is enforced at the view level via the respective mixins.
urlpatterns = client_urlpatterns + admin_urlpatterns
