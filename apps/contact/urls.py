"""
URL configuration for the contact app.

Public URLs (included under /contact/):
  - /contact/           → ContactPageView (public form)

Admin URLs (included under /admin-panel/contact/):
  - /admin-panel/contact/       → ContactAdminListView (admin inbox)
  - /admin-panel/contact/<id>/  → ContactAdminDetailView (marks as read)
"""

from django.urls import path

from apps.contact.views import (
    ContactAdminDetailView,
    ContactAdminListView,
    ContactPageView,
)

app_name = "contact"

# Public URL patterns (included at /contact/)
urlpatterns = [
    path("", ContactPageView.as_view(), name="contact"),
]

# Admin URL patterns (to be included at /admin-panel/contact/)
admin_urlpatterns = [
    path("", ContactAdminListView.as_view(), name="admin_list"),
    path("<int:pk>/", ContactAdminDetailView.as_view(), name="admin_detail"),
]
