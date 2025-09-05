import os
from datetime import timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

def get_or_create_user(google_user_data):
    """Get or create a user from Google OAuth data."""
    email = google_user_data.get('email')
    if not email:
        return None
        
    try:
        user = User.objects.get(email=email)
        # Update user data if needed
        user.name = google_user_data.get('name', user.name)
        user.picture = google_user_data.get('picture', user.picture)
        user.save()
        return user
    except User.DoesNotExist:
        # Create a new user
        return User.objects.create_user(
            email=email,
            name=google_user_data.get('name', ''),
            picture=google_user_data.get('picture', '')
        )

def verify_google_token(token):
    """Verify Google OAuth token and return user data."""
    try:
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        
        # Check if the token is valid
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            return None
            
        return idinfo
    except (ValueError, KeyError):
        return None

def get_tokens_for_user(user):
    """Generate JWT tokens for the user."""
    from rest_framework_simplejwt.tokens import RefreshToken
    
    refresh = RefreshToken.for_user(user)
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'access_token_expiration': (timezone.now() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']).isoformat(),
        'refresh_token_expiration': (timezone.now() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']).isoformat(),
    }
