"""
Custom permissions for the Call Tracer API.
"""

from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Allows access only to authenticated users with role='admin'.
    """

    message = "Only administrative accounts may access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )
