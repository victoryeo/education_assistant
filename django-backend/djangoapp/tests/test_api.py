"""Test cases for the Django API endpoints."""

from datetime import datetime, timedelta
from django.urls import reverse
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import Task, Student, Parent, TaskStatusHistory

User = get_user_model()


class TestSetup(APITestCase):
    """Base test class with common setup for all test cases."""

    def setUp(self):
        """Set up test data for all test cases."""
        self.client = APIClient()
        
        # Create test users
        self.student_user = User.objects.create_user(
            email='student@example.com',
            password='testpass123',
            name='Test Student'
        )
        
        self.parent_user = User.objects.create_user(
            email='parent@example.com',
            password='testpass123',
            name='Test Parent'
        )
        
        # Create student and parent profiles
        self.student = Student.objects.create(
            user=self.student_user,
            grade_level='10',
            date_of_birth='2010-01-01'
        )
        
        self.parent = Parent.objects.create(user=self.parent_user)
        self.parent.children.add(self.student)
        
        # Create some test tasks
        self.task1 = Task.objects.create(
            title='Math Homework',
            description='Complete exercises 1-10',
            task_type='student',
            created_by=self.parent_user,
            assigned_to=self.student_user
        )
        
        self.task2 = Task.objects.create(
            title='Science Project',
            description='Work on the volcano project',
            task_type='student',
            created_by=self.parent_user,
            assigned_to=self.student_user,
            completed=True
        )
        
        # Get JWT tokens
        self.student_token = self.get_tokens_for_user(self.student_user)
        self.parent_token = self.get_tokens_for_user(self.parent_user)
    
    def get_tokens_for_user(self, user):
        """Generate JWT tokens for a user.
        
        Args:
            user: User instance to generate tokens for
            
        Returns:
            str: Access token for the user
        """
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate(self, token):
        """Set up authentication for test client.
        
        Args:
            token (str): JWT token for authentication
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


class AuthenticationTests(TestSetup):
    """Test authentication endpoints."""
    
    def test_student_login(self):
        """Test student login with JWT."""
        url = reverse('token_obtain_pair')
        data = {
            'email': 'student@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_parent_login(self):
        """Test parent login with JWT."""
        url = reverse('token_obtain_pair')
        data = {
            'email': 'parent@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)


class TaskAPITests(TestSetup):
    """Test task-related API endpoints."""
    
    def test_create_task_as_parent(self):
        """Test creating a task as a parent."""
        self.authenticate(self.parent_token)
        url = reverse('task-list')
        data = {
            'title': 'New Math Assignment',
            'description': 'Complete problems 1-20',
            'task_type': 'student',
            'assigned_to': 'student@example.com'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 3)
        self.assertEqual(Task.objects.get(id=response.data['id']).title, 'New Math Assignment')
    
    def test_list_tasks_as_student(self):
        """Test listing tasks as a student."""
        self.authenticate(self.student_token)
        url = reverse('student-task-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should see both tasks
    
    def test_complete_task(self):
        """Test marking a task as complete."""
        self.authenticate(self.student_token)
        url = reverse('student-task-complete', args=[self.task1.id])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task1.refresh_from_db()
        self.assertTrue(self.task1.completed)
        
        # Check that status history was created
        history = TaskStatusHistory.objects.filter(task=self.task1).first()
        self.assertIsNotNone(history)
        self.assertTrue(history.status)
    
    def test_task_summary(self):
        """Test getting task summary."""
        self.authenticate(self.parent_token)
        url = reverse('task-summary')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_tasks'], 2)
        self.assertEqual(response.data['completed_tasks'], 1)
        self.assertEqual(response.data['pending_tasks'], 1)
        self.assertEqual(response.data['completion_rate'], 50.0)


class ParentAPITests(TestSetup):
    """Test parent-specific API endpoints."""
    
    def test_parent_can_see_child_tasks(self):
        """Test that a parent can see their child's tasks."""
        self.authenticate(self.parent_token)
        url = reverse('parent-task-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should see both tasks assigned to the student
    
    def test_parent_cannot_see_other_children_tasks(self):
        """Test that a parent can only see their own children's tasks."""
        # Create another student not related to the parent
        other_student_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            name='Other Student'
        )
        other_student = Student.objects.create(user=other_student_user)
        
        # Create a task for the other student
        Task.objects.create(
            title='Private Task',
            description='Should not be visible',
            task_type='student',
            created_by=other_student_user,
            assigned_to=other_student_user
        )
        
        self.authenticate(self.parent_token)
        url = reverse('parent-task-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only see the 2 original tasks, not the one assigned to the other student
        self.assertEqual(len(response.data), 2)
        self.assertNotIn('Private Task', [t['title'] for t in response.data])
