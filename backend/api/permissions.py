"""
Custom permissions for the Call Tracer API.
"""

from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Allows access only to users whose role is 'admin'.
    This checks the custom role field on the User model,
    NOT Django's built-in is_staff / is_superuser flags.
    """

    message = "Access restricted to admin users only."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )
