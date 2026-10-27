from rest_framework.exceptions import (
    ValidationError,
    NotAuthenticated,
    AuthenticationFailed,
    PermissionDenied,
    NotFound,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.common.exceptions import ResourceInUseError

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception (bug, not a DRF-recognized error) -> still return JSON
        import logging

        logging.getLogger(__name__).exception("Unhandled exception in API view")

        return Response(
            {
                "success": False,
                "status_code": 500,
                "message": "Internal server error.",
                "errors": {},
            },
            status=500,
        )

    message = "An error occurred."
    errors = {}

    if isinstance(exc, ValidationError):
        message = "Validation Error"
        errors = response.data
    
    elif isinstance(exc, ResourceInUseError):
        message = str(exc.detail)

    elif isinstance(exc, NotAuthenticated):
        message = "Authentication credentials were not provided."

    elif isinstance(exc, AuthenticationFailed):
        message = "Invalid authentication credentials."

    elif isinstance(exc, PermissionDenied):
        message = "You do not have permission to perform this action."

    elif isinstance(exc, NotFound):
        message = "Page not found."

    elif isinstance(response.data, dict):
        message = response.data.get("detail", message)

    elif isinstance(response.data, list):
        message = str(response.data[0])

    response.data = {
        "success": False,
        "status_code": response.status_code,
        "message": message,
        "errors": errors,
    }

    return response
