from django.http import JsonResponse
import threading
from django.views.decorators.csrf import csrf_exempt
import json
from rest_framework import viewsets
from .models import Task
from .serializers import StudentTaskSerializer

class StudentTaskViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tasks to be viewed, created, or edited.
    """
    queryset = Task.objects.all()
    serializer_class = StudentTaskSerializer
    
@csrf_exempt
def index(request):
    """
    The main view that handles user queries.
    """
    if request.method == 'POST':
        # Extract the user's query from the POST data.
        query = request.POST.get('query')
        if not query:
            body = json.loads(request.body)
            print("body", body)
            query = body
        
        resultJson = JsonResponse({"query": query})
        print(resultJson)
        print("return result")
        return resultJson
    # For non-POST requests
    else:
        return JsonResponse({"query": query})

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
    # Start a new thread to build the database asynchronously.
    thread = threading.Thread(target=build_vector_store)
    thread.start()
    # Inform the requester that the database building process has started.
    return JsonResponse({'status': 'Building database...'})
