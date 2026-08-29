"""
Views for the Call Tracer API.

Authentication:
- RegisterView: registers admin (generates connect_code) or employee (verifies connect_code)
- LoginView: JWT token pair generation
- ConsentView: sets consent_given=True for authenticated employee

Call Log Operations:
- CallLogSyncView: bulk deduplicated sync with ignore_conflicts

Admin Operations (IsAdminRole):
- AdminProfileView: returns admin's own profile and connect_code
- AdminUserListView: list team employees linked to this admin
- AdminCallLogView: filtered call logs for this admin's employees
- AdminStatsView: daily & aggregate stats for an employee belonging to this admin
"""

from collections import Counter
from datetime import datetime
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from api.models import CallLog, CallStats
from api.permissions import IsAdminRole
from api.serializers import (
    CallLogSerializer,
    CallLogSyncSerializer,
    CallStatsSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()


# ── Standard Pagination ──────────────────────────────────────────────────

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


# ── Authentication Views ─────────────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    """
    Register a new user account.
    - Admins get auto-generated unique connect_code (format: XXX-NNNN-NNNN)
    - Employees must provide valid connect_code from their admin manager
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens for immediate login
        refresh = RefreshToken.for_user(user)
        refresh["username"] = user.username
        refresh["role"] = user.role
        refresh["connect_code"] = user.connect_code
        refresh["consent_given"] = user.consent_given

        return Response(
            {
                "message": "Account created successfully.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """Obtain JWT access and refresh token pair."""

    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]


class ConsentView(APIView):
    """
    POST /api/consent/
    Mark the authenticated employee as having accepted the monitoring disclosure.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user.consent_given = True
        user.save(update_fields=["consent_given"])
        return Response(
            {
                "message": "Consent recorded successfully.",
                "consent_given": True,
            },
            status=status.HTTP_200_OK,
        )


# ── Call Log Sync (Employee) ─────────────────────────────────────────────

class CallLogSyncView(APIView):
    """
    POST /api/call-logs/sync/
    Receives a batch of call logs from an employee device.
    Uses bulk_create with ignore_conflicts=True for deduplication.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CallLogSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        call_logs_data = serializer.validated_data["call_logs"]
        user = request.user

        # Build CallLog instances
        instances = [
            CallLog(
                user=user,
                phone_number=entry["phone_number"],
                call_type=entry["call_type"],
                duration=entry["duration"],
                timestamp=entry["timestamp"],
            )
            for entry in call_logs_data
        ]

        # Bulk insert with conflict ignore based on unique (user, phone_number, timestamp)
        created = CallLog.objects.bulk_create(instances, ignore_conflicts=True)
        synced_count = len(created)
        skipped_count = len(instances) - synced_count

        return Response(
            {
                "message": "Sync completed successfully.",
                "synced": synced_count,
                "skipped_duplicates": skipped_count,
                "total_received": len(instances),
            },
            status=status.HTTP_200_OK,
        )


# ── Admin Dashboard Views ────────────────────────────────────────────────

class AdminProfileView(APIView):
    """
    GET /api/admin/profile/
    Returns the requesting admin's profile including their unique connect_code.
    """

    permission_classes = [IsAdminRole]

    def get(self, request):
        admin = request.user
        return Response(
            {
                "id": admin.id,
                "username": admin.username,
                "email": admin.email,
                "role": admin.role,
                "connect_code": admin.connect_code,
                "total_employees": admin.employees.count(),
            },
            status=status.HTTP_200_OK,
        )


class AdminUserListView(generics.ListAPIView):
    """
    GET /api/admin/users/
    Lists all employees belonging to the requesting admin manager.
    """

    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return (
            User.objects.filter(admin_id=self.request.user.id)
            .annotate(total_call_logs=Count("call_logs"))
            .order_by("-date_joined")
        )


class AdminCallLogView(generics.ListAPIView):
    """
    GET /api/admin/call-logs/?user_id=&start_date=&end_date=
    Lists synced call logs for employees managed by this admin.
    """

    serializer_class = CallLogSerializer
    permission_classes = [IsAdminRole]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        admin = self.request.user
        # Scope only to employees belonging to this admin
        queryset = CallLog.objects.filter(user__admin_id=admin.id).select_related("user")

        # Filter by specific user if provided
        user_id = self.request.query_params.get("user_id")
        if user_id:
            # Verify user_id belongs to this admin
            target_user = get_object_or_404(User, id=user_id)
            if target_user.admin_id != admin and target_user != admin:
                raise PermissionDenied("You do not have permission to view logs for this user.")
            queryset = queryset.filter(user_id=user_id)

        # Filter by call_type
        call_type = self.request.query_params.get("call_type")
        if call_type in ["incoming", "outgoing", "missed"]:
            queryset = queryset.filter(call_type=call_type)

        # Filter by date range
        start_date = self.request.query_params.get("start_date")
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                queryset = queryset.filter(timestamp__gte=start_dt)
            except ValueError:
                pass

        end_date = self.request.query_params.get("end_date")
        if end_date:
            try:
                end_dt = datetime.strptime(f"{end_date} 23:59:59", "%Y-%m-%d %H:%M:%S")
                queryset = queryset.filter(timestamp__lte=end_dt)
            except ValueError:
                pass

        return queryset.order_by("-timestamp")


class AdminStatsView(APIView):
    """
    GET /api/admin/stats/ or GET /api/admin/stats/<user_id>/
    Returns real-time aggregated stats and daily trend directly from CallLog.
    """

    permission_classes = [IsAdminRole]

    def get(self, request, user_id=None):
        from django.db.models.functions import TruncDate

        admin = request.user
        user_param = user_id or request.query_params.get("user_id")

        if user_param and str(user_param) not in ["0", "all"]:
            target_user = get_object_or_404(User, id=user_param)
            if target_user.admin_id != admin and target_user != admin:
                raise PermissionDenied("You do not have permission to view stats for this user.")
            logs = CallLog.objects.filter(user=target_user)
            username = target_user.username
            device_id = target_user.device_id
            device_model = target_user.device_model
            uid = target_user.id
        else:
            # Team-wide aggregated stats
            logs = CallLog.objects.filter(user__admin_id=admin.id)
            username = "Entire Team"
            device_id = "All Devices"
            device_model = f"{admin.employees.count()} Employees"
            uid = 0

        total_calls = logs.count()
        total_duration = logs.aggregate(total=Sum("duration"))["total"] or 0

        # Type breakdown
        calls_by_type = {
            "incoming": logs.filter(call_type="incoming").count(),
            "outgoing": logs.filter(call_type="outgoing").count(),
            "missed": logs.filter(call_type="missed").count(),
        }

        # Top 5 contacted numbers
        phone_counts = Counter(logs.values_list("phone_number", flat=True))
        top_numbers = [
            {"phone_number": number, "count": count}
            for number, count in phone_counts.most_common(5)
        ]

        # Real-time daily trend directly from CallLog table
        daily_query = (
            logs.annotate(date=TruncDate("timestamp"))
            .values("date")
            .annotate(
                calls=Count("id"),
                duration=Sum("duration"),
            )
            .order_by("date")
        )
        daily_trend = [
            {
                "date": str(item["date"]),
                "calls": item["calls"],
                "duration": item["duration"] or 0,
            }
            for item in daily_query
        ]

        return Response(
            {
                "user_id": uid,
                "username": username,
                "device_id": device_id,
                "device_model": device_model,
                "total_calls": total_calls,
                "total_duration": total_duration,
                "calls_by_type": calls_by_type,
                "top_numbers": top_numbers,
                "daily_trend": daily_trend,
            },
            status=status.HTTP_200_OK,
        )
