"""
Views for the Call Tracer API.

Auth endpoints:
  POST /api/auth/register — create a new employee user
  POST /api/auth/login    — obtain JWT token pair

Sync endpoint:
  POST /api/call-logs/sync — bulk create call logs (authenticated employees)

Admin endpoints:
  GET  /api/admin/users                          — list employees
  GET  /api/admin/call-logs?user_id=&start_date=&end_date= — filtered call logs
  GET  /api/admin/stats/<user_id>                — aggregated stats for a user
"""

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import CallLog, CallStats
from .permissions import IsAdminRole
from .serializers import (
    CallLogSerializer,
    CallLogSyncSerializer,
    CallStatsSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UserListSerializer,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register
    Create a new employee user account.
    """

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "message": "User registered successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login
    Returns JWT access + refresh tokens along with user role.
    Uses CustomTokenObtainPairSerializer which embeds role in JWT claims.
    """

    serializer_class = CustomTokenObtainPairSerializer


# ---------------------------------------------------------------------------
# Call log sync
# ---------------------------------------------------------------------------


class CallLogSyncView(APIView):
    """
    POST /api/call-logs/sync
    Bulk create call log entries for the authenticated user.
    Deduplication is handled via ignore_conflicts on the unique constraint
    (user, phone_number, timestamp).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CallLogSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        call_logs_data = serializer.validated_data["call_logs"]

        # Build CallLog objects
        call_log_objects = [
            CallLog(
                user=request.user,
                phone_number=entry["phone_number"],
                call_type=entry["call_type"],
                duration=entry["duration"],
                timestamp=entry["timestamp"],
            )
            for entry in call_logs_data
        ]

        # Bulk create with ignore_conflicts for deduplication
        created = CallLog.objects.bulk_create(
            call_log_objects,
            ignore_conflicts=True,
        )

        return Response(
            {
                "message": "Call logs synced successfully.",
                "submitted": len(call_logs_data),
                "created": len(created),
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------


class AdminUserListView(generics.ListAPIView):
    """
    GET /api/admin/users
    List all users with role='user' (employees).
    Admin-only endpoint.
    """

    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_queryset(self):
        return User.objects.filter(role="user").prefetch_related("call_logs")


class AdminCallLogView(generics.ListAPIView):
    """
    GET /api/admin/call-logs?user_id=<id>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    Filtered list of call logs. Admin-only.
    All query params are optional — returns all logs if none provided.
    """

    serializer_class = CallLogSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_queryset(self):
        queryset = CallLog.objects.select_related("user").all()

        user_id = self.request.query_params.get("user_id")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)

        return queryset


class AdminStatsView(APIView):
    """
    GET /api/admin/stats/<user_id>
    Returns aggregated call statistics for a specific user.
    Admin-only. Computes stats live from CallLog table.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, user_id):
        # Verify user exists and is an employee
        try:
            user = User.objects.get(id=user_id, role="user")
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        logs = CallLog.objects.filter(user=user)

        # Total calls and duration
        totals = logs.aggregate(
            total_calls=Count("id"),
            total_duration=Sum("duration"),
        )

        # Calls by type
        calls_by_type = dict(
            logs.values_list("call_type")
            .annotate(count=Count("id"))
            .values_list("call_type", "count")
        )

        # Top 5 most contacted numbers
        top_numbers = list(
            logs.values("phone_number")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        # Daily trend (last 30 days of data)
        daily_trend = list(
            logs.annotate(date=TruncDate("timestamp"))
            .values("date")
            .annotate(
                calls=Count("id"),
                duration=Sum("duration"),
            )
            .order_by("-date")[:30]
        )

        # Serialize dates for JSON
        for entry in daily_trend:
            entry["date"] = entry["date"].isoformat()

        return Response(
            {
                "user_id": user.id,
                "username": user.username,
                "total_calls": totals["total_calls"] or 0,
                "total_duration": totals["total_duration"] or 0,
                "calls_by_type": calls_by_type,
                "top_numbers": top_numbers,
                "daily_trend": daily_trend,
            }
        )
