"""
URL configuration for the VIPET reservations app.

Client URLs (included under /client/reservations/):
  - /client/reservations/             → ReservationListView (client's reservations)
  - /client/reservations/create/      → ReservationCreateView
  - /client/reservations/<id>/cancel/ → ReservationCancelView

Admin URLs (included under /admin-panel/reservations/):
  - /admin-panel/reservations/              → AdminReservationListView
  - /admin-panel/reservations/<id>/approve/ → ReservationApproveView
  - /admin-panel/reservations/<id>/reject/  → ReservationRejectView
  - /admin-panel/reservations/<id>/complete/ → ReservationCompleteView

Requirements: 10.1, 11.1, 11.2, 11.3, 11.4, 12.1, 12.2
"""

from django.urls import path

from apps.reservations.views import (
    AdminReservationListView,
    ReservationApproveView,
    ReservationCancelView,
    ReservationCompleteView,
    ReservationCreateView,
    ReservationListView,
    ReservationRejectView,
)

app_name = "reservations"

# Client URL patterns (included at /client/reservations/)
urlpatterns = [
    path("", ReservationListView.as_view(), name="reservation_list"),
    path("create/", ReservationCreateView.as_view(), name="reservation_create"),
    path("<int:pk>/cancel/", ReservationCancelView.as_view(), name="reservation_cancel"),
]

# Admin URL patterns (to be included at /admin-panel/reservations/)
admin_urlpatterns = [
    path("", AdminReservationListView.as_view(), name="admin_list"),
    path("<int:pk>/approve/", ReservationApproveView.as_view(), name="approve"),
    path("<int:pk>/reject/", ReservationRejectView.as_view(), name="reject"),
    path("<int:pk>/complete/", ReservationCompleteView.as_view(), name="complete"),
]
