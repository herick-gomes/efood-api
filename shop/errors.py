from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


class Conflict(APIException):
    status_code = 409
    default_detail = "The request conflicts with the current resource state."
    default_code = "conflict"


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        response.data = {
            "error": {"code": getattr(exc, "default_code", "validation_error"), "details": response.data}
        }
    return response
