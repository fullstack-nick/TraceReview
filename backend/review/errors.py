from django.core.exceptions import RequestDataTooBig, TooManyFilesSent, TooManyFieldsSent
from django.db import OperationalError
from django.http import JsonResponse
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from .exceptions import DomainError


def csrf_failure(request, reason=""):
    return JsonResponse(DomainError("Refresh your session and try again.", "csrf_failed", 403).payload(), status=403)


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return Response(exc.payload(), status=exc.status)
    if isinstance(exc, (RequestDataTooBig, TooManyFilesSent, TooManyFieldsSent)):
        return Response(DomainError("Upload one CSV up to 256 KiB.", "upload_too_large", 413).payload(), status=413)
    if isinstance(exc, OperationalError) and ("locked" in str(exc).lower() or "busy" in str(exc).lower()):
        return Response(DomainError("The database is busy. Your work is unchanged; retry shortly.", "database_busy", 503).payload(), status=503)
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    code, message, fields = "request_failed", "The request could not be completed.", {}
    if isinstance(exc, NotAuthenticated):
        code, message = "authentication_required", "Sign in to continue."
    elif isinstance(exc, PermissionDenied):
        code, message = ("csrf_failed", "Refresh your session and try again.") if "CSRF" in str(exc) else ("permission_denied", "This action is not available.")
    elif isinstance(exc, ValidationError):
        code, message = "validation_error", "Check the highlighted fields."
        fields = response.data if isinstance(response.data, dict) else {"form": response.data}
    elif response.status_code == 404:
        code, message = "not_found", "This trace is not available."
    elif response.status_code == 405:
        code, message = "method_not_allowed", "This action is not supported."
    elif response.status_code == 415:
        code, message = "unsupported_media_type", "Unsupported request format."
    response.data = DomainError(message, code, response.status_code, fields=fields).payload()
    return response


def server_error(request):
    return JsonResponse(DomainError("The request failed. Your entered values are retained; retry or reload the latest record.", "server_error", 500).payload(), status=500)
