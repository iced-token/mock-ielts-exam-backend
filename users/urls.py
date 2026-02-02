from django.urls import path, include
from users.views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('users', UserViewSet)

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register_post'),
    path("me/", GetMe.as_view(), name='get_me'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('', include(router.urls))

]
