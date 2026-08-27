"""
Serializers for the Call Tracer API.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import CallLog, CallStats

User = get_user_model()


# ---------------------------------------------------------------------------
# Auth serializers
# ---------------------------------------------------------------------------


class RegisterSerializer(serializers.ModelSerializer):
    """Handles user registration with password confirmation."""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "password_confirm",
            "device_id",
        ]
        extra_kwargs = {
            "email": {"required": True},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            device_id=validated_data.get("device_id", ""),
            role="user",  # New registrations are always employees
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends the default JWT token serializer to include the user's role
    in the token claims and in the response body, so the frontend can
    route to the correct dashboard without decoding the JWT.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Custom claims embedded in the JWT
        token["role"] = user.role
        token["username"] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Extra fields in the response body (not in the token itself)
        data["role"] = self.user.role
        data["user_id"] = self.user.id
        data["username"] = self.user.username
        return data


# ---------------------------------------------------------------------------
# CallLog serializers
# ---------------------------------------------------------------------------


class CallLogSerializer(serializers.ModelSerializer):
    """Serializer for individual call log entries."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = CallLog
        fields = [
            "id",
            "user",
            "username",
            "phone_number",
            "call_type",
            "duration",
            "timestamp",
            "synced_at",
        ]
        read_only_fields = ["id", "user", "synced_at"]


class CallLogSyncItemSerializer(serializers.Serializer):
    """
    Serializer for a single call log entry within a bulk sync request.
    Does NOT include user — that is inferred from the authenticated request.
    """

    phone_number = serializers.CharField(max_length=20)
    call_type = serializers.ChoiceField(
        choices=CallLog.CALL_TYPE_CHOICES,
    )
    duration = serializers.IntegerField(min_value=0)
    timestamp = serializers.DateTimeField()


class CallLogSyncSerializer(serializers.Serializer):
    """
    Accepts a list of call log entries for bulk sync.
    Usage: POST /api/call-logs/sync with body {"call_logs": [...]}
    """

    call_logs = CallLogSyncItemSerializer(many=True)

    def validate_call_logs(self, value):
        if not value:
            raise serializers.ValidationError("call_logs list cannot be empty.")
        if len(value) > 100:
            raise serializers.ValidationError(
                "Maximum 100 call logs per sync request."
            )
        return value


# ---------------------------------------------------------------------------
# Admin serializers
# ---------------------------------------------------------------------------


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for admin user list — shows employee details."""

    total_call_logs = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "device_id",
            "date_joined",
            "last_login",
            "total_call_logs",
        ]

    def get_total_call_logs(self, obj):
        return obj.call_logs.count()


class CallStatsSerializer(serializers.ModelSerializer):
    """Serializer for aggregated call statistics."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = CallStats
        fields = [
            "id",
            "user",
            "username",
            "date",
            "total_calls",
            "total_duration",
            "calls_by_type",
            "top_numbers",
        ]
