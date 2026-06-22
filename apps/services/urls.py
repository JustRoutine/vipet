"""
URL configuration for the services app.

Public routes:
    /services/                    → ServiceListView (service_list)

Admin CRUD routes (under admin/ prefix):
    /services/admin/create/       → ServiceAdminCreateView (service_admin_create)
    /services/admin/<pk>/edit/    → ServiceAdminUpdateView (service_admin_update)
    /services/admin/<pk>/delete/  → ServiceAdminDeleteView (service_admin_delete)

Requirements: 9.1, 9.5
"""

from django.urls import path

from apps.services.views import (
    ServiceAdminCreateView,
    ServiceAdminDeleteView,
    ServiceAdminUpdateView,
    ServiceListView,
)

app_name = "services"

urlpatterns = [
    # Public listing (accessible to all users)
    path("", ServiceListView.as_view(), name="service_list"),

    # Admin CRUD routes
    path("admin/create/", ServiceAdminCreateView.as_view(), name="service_admin_create"),
    path("admin/<int:pk>/edit/", ServiceAdminUpdateView.as_view(), name="service_admin_update"),
    path("admin/<int:pk>/delete/", ServiceAdminDeleteView.as_view(), name="service_admin_delete"),
]
