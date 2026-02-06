from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from .models import Exam

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Admin foydalanuvchilar o‘zgartira oladi,
    oddiy userlar faqat ko‘rishi mumkin.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:  # GET, HEAD, OPTIONS
            return True
        return request.user and request.user.is_staff
    
class IsUserInExam(permissions.BasePermission):
    """
    Faqat exam.users ichida bo‘lgan userlargagina ruxsat beradi
    """

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and (
            request.user in obj.joined_users.all() or
            obj.is_public
        )
    
class IsExamNotOver(permissions.BasePermission):
    """
    exam.end_time va exam.start_time ga karab tekshiradi
    """

    def has_object_permission(self, request, view, obj):
        return obj.start_time < timezone.now() and obj.end_time > timezone.now()
