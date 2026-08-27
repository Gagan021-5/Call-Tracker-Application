"""
URL configuration for the Call Tracer API.
"""

from django.urls import path

from . import views

urlpatterns = [
    # Auth
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    # Call log sync (authenticated employees)
    path("call-logs/sync/", views.CallLogSyncView.as_view(), name="call-log-sync"),
    # Admin endpoints
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-users"),
    path("admin/call-logs/", views.AdminCallLogView.as_view(), name="admin-call-logs"),
    path(
        "admin/stats/<int:user_id>/",
        views.AdminStatsView.as_view(),
        name="admin-stats",
    ),
]
