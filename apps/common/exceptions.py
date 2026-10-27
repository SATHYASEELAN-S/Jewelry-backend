from rest_framework import status
from rest_framework.exceptions import APIException


class ResourceInUseError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This item is in use and cannot be deleted."
    default_code = "resource_in_use"