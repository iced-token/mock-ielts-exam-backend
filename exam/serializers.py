from rest_framework import serializers
from .models import ListeningTest, ReadingTest, WritingTest, Exam, UserExamSession
from django.contrib.auth import get_user_model

User = get_user_model()

class ListeningTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListeningTest
        fields = '__all__'
        extra_kwargs = {
            'answers': {'write_only': True},
        }


class ReadingTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingTest
        fields = '__all__'
        extra_kwargs = {
            'answers': {'write_only': True},
        }


class WritingTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WritingTest
        fields = "__all__"


class ExamSerializer(serializers.ModelSerializer):
    listening = serializers.PrimaryKeyRelatedField(queryset=ListeningTest.objects.all(), write_only=True)
    reading = serializers.PrimaryKeyRelatedField(queryset=ReadingTest.objects.all(), write_only=True)
    writing = serializers.PrimaryKeyRelatedField(queryset=WritingTest.objects.all(), write_only=True)
    allowed_users = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True, many=True)

    class Meta:
        model = Exam
        # serializer ichiga koshsa user examen boshlagandan oldin savollarni kurolaydi
        exclude = ['joined_users'] 

class UserExamSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserExamSession
        exclude = []