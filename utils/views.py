from django.http import JsonResponse
def custom_404_handler(request,exception=None):
    return JsonResponse({
        "success": False,
        "status_code": 404,
        "message": "Page not found.",
        "errors": {}
    }, status=404)