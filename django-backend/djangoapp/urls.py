from django.urls import path, include
from . import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'tasks', views.StudentTaskViewSet)

urlpatterns = [
    path('', views.index, name="index"),
    path('db_status/', views.db_status, name='db_status'),  # endpoint to check build status
    path('build_db/', views.build_db, name='build_db'),  # endpoint to trigger DB building
    path('student/tasks/', include(router.urls)),
   ]
