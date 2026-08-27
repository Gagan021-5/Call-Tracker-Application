"""
URL routing for the Call Tracer API.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from api.views import (
    AdminCallLogView,
    AdminProfileView,
    AdminStatsView,
    AdminUserListView,
    CallLogSyncView,
    ConsentView,
    LoginView,
    RegisterView,
)

urlpatterns = [
    # Authentication
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("consent/", ConsentView.as_view(), name="user-consent"),

    # Call log synchronization (Employee)
    path("call-logs/sync/", CallLogSyncView.as_view(), name="call-logs-sync"),

    # Admin operations (Scoped to managed employees)
    path("admin/profile/", AdminProfileView.as_view(), name="admin-profile"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-users"),
    path("admin/call-logs/", AdminCallLogView.as_view(), name="admin-call-logs"),
    path("admin/stats/<int:user_id>/", AdminStatsView.as_view(), name="admin-stats"),
]
