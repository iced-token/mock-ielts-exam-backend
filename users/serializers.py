from users.models import User
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "first_name","last_name", "email", "username", "password")

    def create(self, validated_data):
        user = User(
            username=validated_data["username"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            email=validated_data.get("email", ""),
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=False, write_only=True)

    def validate(self, data):
        username = data.get("username")

        user = get_object_or_404(User.objects.all(), username=username)
        if user:
            if not user.is_active:
                raise serializers.ValidationError("User is inactive.")
            data["user"] = user
            return data

        raise serializers.ValidationError("Invalid username or password.")