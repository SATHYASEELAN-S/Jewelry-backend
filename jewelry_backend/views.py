from django.http import JsonResponse
from django.db import connection

def db_version(request):
    try:
        # Create a cursor to execute raw SQL
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            row = cursor.fetchone()
            
        # You MUST return a response object! 
        # Sending it as JSON makes it easy for your React app to read later.
        return JsonResponse({
 
            "status": "success...",
            "database_version": row[0]
        })
        
    except Exception as e:
        # If the database connection fails, return the error message
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)