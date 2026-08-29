"""
Serializers for the Call Tracer API.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from api.models import CallLog, CallStats

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer that embeds role, connect_code, and user info in response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role
        token["connect_code"] = user.connect_code
        token["consent_given"] = user.consent_given
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "role": self.user.role,
            "connect_code": self.user.connect_code,
            "admin_id": self.user.admin_id_id,
            "device_id": self.user.device_id,
            "device_model": self.user.device_model,
            "app_version": self.user.app_version,
            "consent_given": self.user.consent_given,
        }
        return data


class RegisterSerializer(serializers.ModelSerializer):
    """
    Handles registration for both admins and employees.
    - If registering as admin: auto-generates unique connect_code
    - If registering as employee: requires valid connect_code from manager
    """

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    connect_code = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Manager's connect code (e.g. OBL-XXXX-XXXX). Required for employees.",
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "password_confirm",
            "role",
            "connect_code",
            "device_id",
            "device_model",
            "app_version",
        ]

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        role = attrs.get("role", "user")
        connect_code = (attrs.get("connect_code") or "").strip().upper()

        if role == "user":
            if not connect_code:
                raise serializers.ValidationError(
                    {"connect_code": "Company connect code is required for employee registration."}
                )
            admin_user = User.objects.filter(role="admin", connect_code=connect_code).first()
            if not admin_user:
                raise serializers.ValidationError(
                    {"connect_code": "Invalid connect code."}
                )
            attrs["_admin_user"] = admin_user

        return attrs

    def create(self, validated_data):
        from api.models import generate_connect_code

        validated_data.pop("password_confirm")
        validated_data.pop("connect_code", None)
        admin_user = validated_data.pop("_admin_user", None)
        password = validated_data.pop("password")
        role = validated_data.get("role", "user")

        connect_code = None
        if role == "admin":
            while True:
                code = generate_connect_code()
                if not User.objects.filter(connect_code=code).exists():
                    connect_code = code
                    break

        user = User(
            admin_id=admin_user,
            connect_code=connect_code,
            **validated_data,
        )
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User details with aggregate call count."""

    total_call_logs = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "role",
            "admin_id",
            "connect_code",
            "device_id",
            "device_model",
            "app_version",
            "consent_given",
            "date_joined",
            "last_login",
            "total_call_logs",
        ]
        read_only_fields = ["id", "date_joined", "last_login", "connect_code"]


class CallLogItemSerializer(serializers.Serializer):
    """Validates individual call log entries inside a sync batch."""

    phone_number = serializers.CharField(max_length=20)
    call_type = serializers.ChoiceField(choices=CallLog.CALL_TYPE_CHOICES)
    duration = serializers.IntegerField(min_value=0)
    timestamp = serializers.DateTimeField()


class CallLogSyncSerializer(serializers.Serializer):
    """Validates a batch of call logs submitted for synchronization."""

    call_logs = serializers.ListField(
        child=CallLogItemSerializer(),
        allow_empty=False,
        max_length=500,
    )


class CallLogSerializer(serializers.ModelSerializer):
    """Full CallLog model serializer for admin list/detail views."""

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
        read_only_fields = ["id", "synced_at"]


class CallStatsSerializer(serializers.ModelSerializer):
    """CallStats model serializer for aggregated analytics."""

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
