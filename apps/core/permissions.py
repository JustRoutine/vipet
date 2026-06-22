"""
DRF permission classes for the VIPET platform.

Provides reusable permission classes for role-based and ownership-based
access control across all API viewsets.

Requirements: 8.6, 10.8, 14.5, 16.4
"""

from rest_framework import permissions


class IsClient(permissions.BasePermission):
    """
    Allow access only to authenticated users with role='client'.

    Usage: Apply to viewsets that should only be accessible to clients
    (e.g., PetViewSet, reservation creation).

    Requirements: 10.8
    """

    message = "Seuls les clients peuvent effectuer cette action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "client"
        )


class IsAdmin(permissions.BasePermission):
    """
    Allow access only to authenticated users with role='admin'.

    Usage: Apply to viewsets/actions restricted to administrators
    (e.g., service CRUD, gallery management, admin dashboard API).

    Requirements: 8.6, 14.5, 16.4
    """

    message = "Seuls les administrateurs peuvent effectuer cette action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "admin"
        )


class IsOwner(permissions.BasePermission):
    """
    Allow access only if the requesting user owns the object.

    Checks object-level ownership by comparing the object's owner-like
    attribute to request.user. Supports common ownership field names:
    'owner', 'client', 'user'.

    Usage: Apply to viewsets where object-level ownership must be enforced
    (e.g., pets belong to owner, reservations belong to client,
    notifications belong to user).
    """

    message = "Vous n'avez pas la permission d'accéder à cette ressource."

    # Field names to check for ownership, in priority order
    OWNER_FIELDS = ("owner", "client", "user")

    def has_object_permission(self, request, view, obj):
        """
        Check if request.user matches one of the ownership fields on the object.
        """
        for field_name in self.OWNER_FIELDS:
            owner = getattr(obj, field_name, None)
            if owner is not None:
                # Handle FK fields (compare user instances or PKs)
                if hasattr(owner, "pk"):
                    return owner.pk == request.user.pk
                return owner == request.user.pk
        # If no ownership field found, deny access by default
        return False
