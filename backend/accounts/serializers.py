from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "phone", "password", "role")

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(
            password=password,
            **validated_data,
        )
        return user


class ProfileSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "phone", "role")
        read_only_fields = ("email", "role")

    def get_role(self, obj):
        return obj.role
