"""
Pet web URL configuration.

Routes for the client dashboard pet management:
  /         → PetListView (pet_list)
  /add/     → PetCreateView (pet_create)
  /<pk>/edit/   → PetUpdateView (pet_update)
  /<pk>/delete/ → PetDeleteView (pet_delete)

Requirements: 7.2
"""

from django.urls import path

from apps.pets.views import PetCreateView, PetDeleteView, PetListView, PetUpdateView

app_name = "pets"

urlpatterns = [
    path("", PetListView.as_view(), name="pet_list"),
    path("add/", PetCreateView.as_view(), name="pet_create"),
    path("<int:pk>/edit/", PetUpdateView.as_view(), name="pet_update"),
    path("<int:pk>/delete/", PetDeleteView.as_view(), name="pet_delete"),
]
