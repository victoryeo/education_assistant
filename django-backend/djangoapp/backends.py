from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from .mongodb_utils import get_user_by_email

class MongoDBAuthenticationBackend(ModelBackend):
    """
    Authenticate against MongoDB user documents.
    """
    async def authenticate(self, request, username=None, password=None, **kwargs):
        # Use email as the username
        email = username
        
        # Get user from MongoDB
        user_data = await get_user_by_email(email)
        if not user_data:
            return None
            
        # Check password
        if not self._check_password(password, user_data.get('hashed_password')):
            return None
            
        # Get or create the user in Django's auth system
        UserModel = get_user_model()
        user, created = UserModel._default_manager.get_or_create(
            **{UserModel.EMAIL_FIELD: email}
        )
        
        # Update user data
        user.name = user_data.get('name', '')
        user.is_active = not user_data.get('disabled', False)
        
        # Set a dummy password to prevent password validation
        if not user.password:
            user.set_unusable_password()
            
        user.save()
        
        return user if self.user_can_authenticate(user) else None
    
    def _check_password(self, raw_password, hashed_password):
        """
        Check the password against the hashed password.
        """
        if not raw_password or not hashed_password:
            return False
            
        # Use Django's password hashing to verify the password
        return check_password(raw_password, hashed_password)
    
    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            user = UserModel._default_manager.get(pk=user_id)
            return user if self.user_can_authenticate(user) else None
        except UserModel.DoesNotExist:
            return None
