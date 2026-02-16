# piano/users/backends.py

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # Look up the user by their email instead of username
            # FIX: Handle MultipleObjectsReturned by selecting the most recently active user
            users = UserModel.objects.filter(email=username).order_by('-last_login')
            if not users.exists():
                return None
            user = users.first()
        except Exception:
            return None
        
        # Check if the password is correct for the found user
        if user.check_password(password):
            return user
        return None