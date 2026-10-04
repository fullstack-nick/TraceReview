from django.core.files.uploadhandler import FileUploadHandler, StopUpload
from django.http import JsonResponse
from .errors import DomainError


class BoundedUploadHandler(FileUploadHandler):
    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)
        self.received = 0

    def receive_data_chunk(self, raw_data, start):
        self.received += len(raw_data)
        if self.received > 262144:
            self.request.upload_too_large = True
            raise StopUpload(connection_reset=False)
        return raw_data

    def file_complete(self, file_size):
        return None


class RequestLimitsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            size = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            size = 524289
        if size > 524288:
            return JsonResponse(DomainError("Request exceeds 512 KiB.", "upload_too_large", 413).payload(), status=413)
        response = self.get_response(request)
        if request.path.startswith("/api/") or request.path == "/":
            response["Cache-Control"] = "private, no-store"
        return response

