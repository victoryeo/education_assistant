from django.db import models

class Parent(models.Model):
    name = models.CharField(max_length=100)
    # ... other parent fields

class Student(models.Model):
    name = models.CharField(max_length=100)
    # ... other student fields

class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    completed = models.BooleanField(default=False)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    created_at = models.DateTimeField(auto_now_add=True)