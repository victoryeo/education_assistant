"""Test cases for task-related API endpoints."""

from django.urls import reverse
from rest_framework import status

from .base import TestBase


class TaskAPITests(TestBase):
    """Test task-related API endpoints."""

    def test_create_task_as_parent(self):
        """Test creating a task as a parent."""
        # Clear any existing tasks to ensure a clean state
        from ..models import Task
        Task.objects.all().delete()
        
        self.authenticate(self.parent_token)
        url = reverse('task-list')
        data = {
            'title': 'New Math Assignment',
            'description': 'Complete problems 1-20',
            'task_type': 'student',
            'assigned_to': 'student@example.com'
        }
        response = self.client.post(url, data, format='json')
        
        # Debug output to help diagnose the response structure
        print("Response data:", response.data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Math Assignment')
        self.assertEqual(response.data['description'], 'Complete problems 1-20')
        self.assertEqual(response.data['task_type'], 'student')
        
        # Check if assigned_to is a string (email) or a nested object
        assigned_to = response.data.get('assigned_to')
        if isinstance(assigned_to, dict):
            self.assertEqual(assigned_to.get('email'), 'student@example.com')
        else:
            print(f"assigned_to: {assigned_to}")
            self.assertEqual(assigned_to, 'student@example.com')
            
        self.assertFalse(response.data.get('completed', True))

    def test_list_tasks_as_student(self):
        """Test listing tasks as a student."""
        # Clear existing tasks to ensure a clean state
        from ..models import Task
        Task.objects.all().delete()
        
        # Create test tasks specifically for this test
        task1 = Task.objects.create(
            title='Task 1',
            description='Description 1',
            task_type='student',
            created_by=self.parent_user,
            assigned_to=self.student_user,
            completed=False
        )
        task2 = Task.objects.create(
            title='Task 2',
            description='Description 2',
            task_type='student',
            created_by=self.parent_user,
            assigned_to=self.student_user,
            completed=True
        )
        
        # Create a task for a different student (should not appear in results)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other_student = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            name='Other Student'
        )
        Task.objects.create(
            title='Other Task',
            description='Should not appear',
            task_type='student',
            created_by=self.parent_user,
            assigned_to=other_student,
            completed=False
        )
        
        # Authenticate and make the request
        self.authenticate(self.student_token)
        url = reverse('student-task-list')
        response = self.client.get(url)
        
        # Debug output to help diagnose the response structure
        print("Response data:", response.data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should see exactly the 2 tasks we created for this student
        self.assertEqual(len(response.data), 2, "Should only see tasks assigned to the authenticated student")
        
        # Verify the tasks are for the authenticated student
        for task in response.data:
            # Check if assigned_to is a string (email) or a nested object
            assigned_to = task.get('assigned_to')
            if isinstance(assigned_to, dict):
                self.assertEqual(assigned_to.get('email'), 'student@example.com', 
                               f"Task assigned to wrong student: {assigned_to}")
            else:
                self.assertEqual(assigned_to, 'student@example.com', 
                               f"Task assigned to wrong student: {assigned_to}")

    def test_complete_task(self):
        """Test marking a task as complete."""
        # Clear any existing tasks and history
        from ..models import Task, TaskStatusHistory
        TaskStatusHistory.objects.all().delete()
        Task.objects.all().delete()
        
        # Create a new task that's not completed
        task = Task.objects.create(
            title='Science Homework',
            description='Read chapter 5',
            task_type='student',
            created_by=self.parent_user,
            assigned_to=self.student_user,
            completed=False
        )
        
        # Authenticate as the student
        self.authenticate(self.student_token)
        url = reverse('student-task-complete', args=[task.id])
        
        # Mark as complete
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertTrue(task.completed, "Task should be marked as completed")
        
        # Check that status history was created
        history = TaskStatusHistory.objects.filter(task=task).first()
        self.assertIsNotNone(history, "Status history should be created")
        self.assertTrue(history.status, "Status should be True for completed task")
        
        # Mark as incomplete again
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertFalse(task.completed, "Task should be marked as not completed")
        
        # Verify the status history was updated
        history_count = TaskStatusHistory.objects.filter(task=task).count()
        self.assertEqual(history_count, 2, "Should have two status history entries")

    def test_task_summary(self):
        """Test getting task summary."""
        self.authenticate(self.parent_token)
        from ..models import Task
        
        # Get the actual counts from the database
        total_tasks = Task.objects.count()
        completed_tasks = Task.objects.filter(completed=True).count()
        
        url = reverse('task-summary')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_tasks'], total_tasks)
        self.assertEqual(response.data['completed_tasks'], completed_tasks)
        self.assertEqual(response.data['pending_tasks'], 1)
        self.assertEqual(response.data['completion_rate'], 50.0)
