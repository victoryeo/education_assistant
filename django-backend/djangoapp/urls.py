from django.urls import path, include
from rest_framework import routers
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from . import views

# Create a router for our API endpoints
router = routers.DefaultRouter()
router.register(r'tasks', views.TaskViewSet, basename='task')
router.register(r'student/tasks', views.StudentTaskViewSet, basename='student-task')
router.register(r'parent/tasks', views.ParentTaskViewSet, basename='parent-task')

# API URL patterns
api_patterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('token', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair_slash'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/google/', views.GoogleAuthView.as_view(), name='google_auth'),
    
    # Task management
    path('tasks/summary/', views.TaskSummaryView.as_view(), name='task-summary'),
    
    # Include router URLs
    path('', include(router.urls)),
]

urlpatterns = [
    # API endpoints
    *api_patterns,
    
    # Legacy endpoints (consider deprecating these in the future)
    path('', views.index, name="index"),
    path('db_status/', views.db_status, name='db_status'),
    path('build_db/', views.build_db, name='build_db'),
]
