"""
Pet API viewset for the VIPET pets app.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 21.1, 21.7, 21.8
"""

from rest_framework import permissions, viewsets

from apps.core.permissions import IsClient
from apps.pets.models import Pet
from apps.pets.serializers import PetSerializer


class PetViewSet(viewsets.ModelViewSet):
    """
    CRUD viewset for Pet resources.

    - Requires JWT authentication + client role.
    - Queryset is filtered to only return pets owned by the requesting user.
    - Owner is automatically set to request.user on creation.
    """

    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated, IsClient]

    def get_queryset(self):
        """Return only pets belonging to the authenticated client."""
        return Pet.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """Set the owner to the currently authenticated user."""
        serializer.save(owner=self.request.user)
