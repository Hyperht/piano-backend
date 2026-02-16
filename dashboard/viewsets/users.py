from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.throttling import UserRateThrottle
from users.models import CustomUser
from dashboard.serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]
    search_fields = ['email', 'username']
