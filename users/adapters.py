"""
Custom Social Account Adapter to handle MultipleObjectsReturned exceptions
"""
import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.core.exceptions import MultipleObjectsReturned
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to handle edge cases in social authentication
    """
    
    def pre_social_login(self, request, sociallogin):
        """
        Handle the case where a user tries to login with a social account
        that's already connected to another user
        """
        # If the social account is already connected, skip
        if sociallogin.is_existing:
            return
        
        # Try to connect to existing user by email
        try:
            email = sociallogin.account.extra_data.get('email')
            if email:
                try:
                    user = User.objects.get(email=email)
                    sociallogin.connect(request, user)
                except User.DoesNotExist:
                    pass
                except MultipleObjectsReturned:
                    user = User.objects.filter(email=email).first()
                    if user:
                        sociallogin.connect(request, user)
        except Exception as e:
            logger.error(f"Error in pre_social_login: {e}", exc_info=True)
    
    def get_connect_redirect_url(self, request, socialaccount):
        """
        Returns the URL to redirect to after successfully connecting a social account
        """
        return '/'
    
    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Allow auto signup for social accounts
        """
        return True

