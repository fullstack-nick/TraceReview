import io
from django.conf import settings
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.http import FileResponse, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from .exceptions import DomainError
from .models import TraceRun
from .records import trace_summary, trace_detail
from .reports import report_bytes
from .serializers import ImportSerializer, PreviewSerializer, RevisionSerializer, CompletionSerializer
from . import services


def validated(serializer_class, request):
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


@require_GET
@ensure_csrf_cookie
def session(request):
    user = {"id": request.user.pk, "username": request.user.username} if request.user.is_authenticated else None
    return JsonResponse({"authenticated": user is not None, "user": user, "csrf_token": get_token(request)})


class SessionLoginView(LoginView):
    http_method_names = ["post", "options"]

    def form_valid(self, form):
        auth_login(self.request, form.get_user())
        return JsonResponse({"user": {"id": self.request.user.pk, "username": self.request.user.username},
                             "csrf_token": get_token(self.request)})

    def form_invalid(self, form):
        return JsonResponse(DomainError("Check your username and password.", "invalid_credentials", 400).payload(), status=400)


@api_view(["POST"])
def logout(request):
    auth_logout(request)
    return Response(status=204)


class TraceList(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        try:
            offset = max(0, int(request.query_params.get("offset", 0)))
            limit = min(100, max(1, int(request.query_params.get("limit", 50))))
        except ValueError:
            raise DomainError("Use integer pagination values.")
        query = TraceRun.objects.filter(imported_by=request.user).defer("points", "source_bytes")
        return Response({"items": [trace_summary(run) for run in query[offset:offset + limit]],
                         "total": query.count(), "offset": offset, "limit": limit})

    def post(self, request):
        data = request.data  # Run upload handlers before inspecting their outcome.
        if getattr(request, "upload_too_large", False):
            raise DomainError("File exceeds 256 KiB.", "upload_too_large", 413)
        if len(request.FILES.getlist("file")) != 1:
            raise DomainError("Choose exactly one CSV.", fields={"file": ["Choose exactly one CSV."]})
        serializer = ImportSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        receipt = services.import_trace(request.user, **serializer.validated_data)
        return Response(receipt, status=200 if receipt["replayed"] else 201)


class TraceDetail(APIView):
    def get(self, request, run_id):
        with transaction.atomic():
            run = services.owned_run(request.user, run_id)
            revisions = list(run.revisions.all())
            events = list(run.events.all())
        return Response(trace_detail(run, revisions, events))


class Preview(APIView):
    parser_classes = [JSONParser]

    def post(self, request, run_id):
        return Response(services.preview_trace(request.user, run_id, **validated(PreviewSerializer, request)))


class Revisions(APIView):
    parser_classes = [JSONParser]

    def post(self, request, run_id):
        receipt = services.save_revision(request.user, run_id, **validated(RevisionSerializer, request))
        return Response(receipt, status=200 if receipt["replayed"] else 201)


class CompleteReview(APIView):
    parser_classes = [JSONParser]

    def post(self, request, run_id):
        return Response(services.complete_review(request.user, run_id, **validated(CompletionSerializer, request)))


class Report(APIView):
    def get(self, request, run_id):
        with transaction.atomic():
            run = services.owned_run(request.user, run_id)
            content = report_bytes(run)
        if request.query_params.get("download") == "1":
            return FileResponse(io.BytesIO(content), as_attachment=True,
                filename=f"tracereview-{run.id}-r{run.reviewed_revision.revision_number}.json", content_type="application/json")
        return HttpResponse(content, content_type="application/json")


class Source(APIView):
    def get(self, request, run_id):
        run = services.owned_run(request.user, run_id)
        return FileResponse(io.BytesIO(bytes(run.source_bytes)), as_attachment=True, filename=run.source_filename, content_type="text/csv")


class Example(APIView):
    def get(self, request, filename):
        if filename not in {"clean-trace.csv", "neighboring-feature.csv", "triangle.csv"}:
            raise DomainError("Example not found.", "not_found", 404)
        return FileResponse((settings.BASE_DIR / "fixtures" / filename).open("rb"), as_attachment=True, filename=filename, content_type="text/csv")


@require_GET
def index(request):
    entry = settings.FRONTEND_DIST / "index.html"
    if not entry.exists():
        return HttpResponse("Build the frontend with scripts/build.ps1, or open http://127.0.0.1:5173 during development.", status=503, content_type="text/plain")
    return FileResponse(entry.open("rb"), content_type="text/html")
