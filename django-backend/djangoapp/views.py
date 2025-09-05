import json
import threading
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status, permissions, mixins
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.viewsets import GenericViewSet
from django.db.models import Q, Count, F, Case, When, Value, IntegerField
from django.utils import timezone
from datetime import timedelta
import json
from .mongodb_utils import get_user_by_email, create_user
from asgiref.sync import sync_to_async

from .models import Task, User, Student, Parent, TaskStatusHistory
from .education_assistant import EducationManager
from .serializers import (
    UserSerializer, StudentSerializer, ParentSerializer,
    TaskSerializer, TaskCreateSerializer, TaskUpdateSerializer,
    TaskSummarySerializer, GoogleAuthSerializer, CustomTokenObtainPairSerializer
)
from .auth_utils import verify_google_token, get_or_create_user_mongodb, get_tokens_for_user

class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain view that includes user data in the response."""
    serializer_class = CustomTokenObtainPairSerializer

class UserRegistrationView(APIView):
    """View for user registration using MongoDB."""
    permission_classes = [AllowAny]

    async def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            name = data.get('name', '')
            
            if not email or not password:
                return Response(
                    {'error': 'Email and password are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user exists in MongoDB
            existing_user = await get_user_by_email(email)
            if existing_user:
                return Response(
                    {'error': 'User with this email already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create new user in MongoDB
            user_data = {
                'email': email,
                'password': password,
                'name': name,
                'disabled': False
            }
            
            created_user = await create_user(user_data)
            if not created_user:
                return Response(
                    {'error': 'Failed to create user'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Return token pair on successful registration
            tokens = await sync_to_async(get_tokens_for_user)(created_user)
            return Response({
                'message': 'User registered successfully',
                'user': {
                    'id': created_user['id'],
                    'email': created_user['email'],
                    'name': created_user.get('name', '')
                },
                **tokens
            }, status=status.HTTP_201_CREATED)
            
        except json.JSONDecodeError:
            return Response(
                {'error': 'Invalid JSON'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoogleAuthView(APIView):
    """View for Google OAuth authentication."""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user data from Google token
        idinfo = serializer.validated_data
        email = idinfo.get('email')
        
        # Get or create user
        user = get_or_create_user(idinfo)
        if not user:
            return Response(
                {"error": "Authentication failed"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_200_OK)

class TaskViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    """
    API endpoint that allows tasks to be viewed, created, updated, or deleted.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    
    def get_queryset(self):
        # Filter tasks where the user is either the creator or assignee
        return Task.objects.filter(
            Q(created_by=self.request.user) | Q(assigned_to=self.request.user)
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskUpdateSerializer
        return TaskSerializer
    
    # Removed perform_create as it's handled in the serializer
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark a task as completed."""
        task = self.get_object()
        task.completed = True
        task.save()
        
        # Record status change
        TaskStatusHistory.objects.create(
            task=task,
            status=True,
            changed_by=request.user,
            notes="Task marked as completed"
        )
        
        return Response(
            {"status": "Task completed successfully"}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def uncomplete(self, request, pk=None):
        """Mark a completed task as not completed."""
        task = self.get_object()
        task.completed = False
        task.save()
        
        # Record status change
        TaskStatusHistory.objects.create(
            task=task,
            status=False,
            changed_by=request.user,
            notes="Task marked as not completed"
        )
        
        return Response(
            {"status": "Task uncompleted successfully"}, 
            status=status.HTTP_200_OK
        )

class TaskSummaryView(APIView):
    """API endpoint to get task summary for the current user."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get task statistics
        tasks = Task.objects.filter(
            Q(created_by=request.user) | Q(assigned_to=request.user)
        )
        
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(completed=True).count()
        pending_tasks = total_tasks - completed_tasks
        
        completion_rate = (
            (completed_tasks / total_tasks * 100) 
            if total_tasks > 0 else 0
        )
        
        # Get tasks by status
        tasks_by_status = tasks.values('completed').annotate(
            count=Count('id')
        ).order_by('completed')
        
        # Convert to a more readable format
        status_dict = {
            'completed': 0,
            'pending': 0
        }
        
        for item in tasks_by_status:
            if item['completed']:
                status_dict['completed'] = item['count']
            else:
                status_dict['pending'] = item['count']
        
        # Get recent tasks
        recent_tasks = tasks.order_by('-created_at')[:5]
        
        summary = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'completion_rate': round(completion_rate, 2),
            'tasks_by_status': status_dict,
            'recent_tasks': TaskSerializer(recent_tasks, many=True).data
        }
        
        return Response(summary, status=status.HTTP_200_OK)

class StudentTaskViewSet(TaskViewSet):
    """
    API endpoint for student-specific tasks.
    """
    def get_queryset(self):
        # Only show tasks assigned to the student
        return Task.objects.filter(
            assigned_to=self.request.user,
            task_type='student'
        ).order_by('-created_at')

class ParentTaskViewSet(TaskViewSet):
    """
    API endpoint for parent-specific tasks and assistant functionality.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.assistant_manager = EducationManager()
        self.parent_assistant = None

    def get_parent_assistant(self):
        if not self.parent_assistant and hasattr(self, 'request') and hasattr(self.request, 'user'):
            self.parent_assistant = self.assistant_manager.get_assistant('parent', user_id=self.request.user.id)
        return self.parent_assistant

    def create(self, request, *args, **kwargs):
        # Process the message if it exists in the request data
        message = request.data.get('message')
        if message:
            try:
                # Get the parent assistant and process the message
                parent_assistant = self.get_parent_assistant()
                if parent_assistant:
                    response = parent_assistant.process_message(message)
                    
                    # You can handle the response as needed
                    print(f"Processed message: {message}")
                    print(f"Assistant response: {response}")
                    
                    # Optionally add the assistant's response to the request data
                    if not isinstance(request.data, dict):
                        request.data._mutable = True
                    request.data['assistant_response'] = str(response)
                
            except Exception as e:
                print(f"Error processing message: {str(e)}")
                # Continue with task creation even if message processing fails
                pass
        
        # Call the parent class's create method to handle the actual task creation
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        # Initialize the parent assistant
        parent_assistant = self.get_parent_assistant()
        tasks = parent_assistant.get_all_tasks()
        return tasks

        """# Get all tasks for the parent's children
        parent = Parent.objects.get(user=self.request.user)
        children = parent.children.all()
        
        return Task.objects.filter(
            assigned_to__in=[child.user for child in children],
            task_type='parent'
        ).order_by('-created_at')"""
    
@csrf_exempt
def index(request):
    """
    The main view that handles user queries.
    """
    if request.method == 'POST':
        # Extract the user's query from the POST data.
        query = request.POST.get('query')
        if not query:
            try:
                body = json.loads(request.body)
                query = body.get('query')
            except (json.JSONDecodeError, AttributeError):
                return JsonResponse(
                    {"error": "Invalid JSON or query parameter"}, 
                    status=400
                )
        
        # Here you would typically process the query and generate a response
        # For now, just return the query as is
        return JsonResponse({"query": query, "response": "This is a placeholder response"})
    
    # For non-POST requests
    return JsonResponse(
        {"message": "Send a POST request with a 'query' parameter"}, 
        status=200
    )

@csrf_exempt
def db_status(request):
    """
    A view to check the status of the database.

    Returns a JSON response indicating whether the database exists and is ready to be queried.
    This is useful for the frontend to decide whether to allow the user to submit queries
    or to show a loading/wait message while the database is being prepared.
    """
    # Check if the database exists using the `database_exists` function from `logic.py`.
    exists = vector_store_exists()
    # Prepare the status message based on the existence of the database.
    status = {
        'exists': exists,
        'message': 'Database exists' if exists else 'Database is being built'
    }
    # Return the status as a JSON response.
    return JsonResponse(status)

@csrf_exempt
def build_db(request):
    """
    A view to initiate the asynchronous building of the database.

    This view starts a new thread to build the database using the `build_database` function
    from `logic.py`, allowing the web server to continue handling other requests.
    This is particularly useful for initial setup or updating the database without downtime.
    """
    thread = threading.Thread(target=build_database)
    thread.daemon = True
    thread.start()
    return JsonResponse({"status": "Database build started in the background"})