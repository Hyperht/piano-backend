from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAdminUser
from users.models import ContactMessage
from products.models import Review
from users.serializers import ReviewSerializer, ContactMessageSerializer

class ReviewViewSet(viewsets.ModelViewSet):
    """
    Admin viewset for Reviews.
    Allows listing ALL reviews (flat list), detecting spam, deleting, etc.
    """
    queryset = Review.objects.all().order_by('-created_at')
    serializer_class = ReviewSerializer
    permission_classes = [IsAdminUser]

class ContactMessageViewSet(viewsets.ModelViewSet):
    """
    Admin viewset for Contact Messages.
    """
    queryset = ContactMessage.objects.all().order_by('-created_at')
    serializer_class = ContactMessageSerializer
    permission_classes = [IsAdminUser]
