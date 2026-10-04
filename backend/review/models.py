import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class AppendOnly(models.Model):
    """Application tripwire; database owners can still modify the database."""
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Saved records cannot be overwritten. Use the review service.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Review records cannot be deleted through the application.")


class TraceRun(AppendOnly):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=120)
    source_filename = models.CharField(max_length=255)
    source_bytes = models.BinaryField()
    source_sha256 = models.CharField(max_length=64)
    source_size = models.PositiveIntegerField()
    points = models.JSONField()
    point_count = models.PositiveIntegerField()
    time_min = models.FloatField()
    time_max = models.FloatField()
    total_area = models.FloatField()
    parser_version = models.CharField(max_length=64)
    import_calculation_version = models.CharField(max_length=64)
    import_build = models.JSONField()
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="trace_runs")
    imported_by_name = models.CharField(max_length=150)
    imported_at = models.DateTimeField()
    status = models.CharField(max_length=12, default="draft", choices=[("draft", "Draft"), ("reviewed", "Reviewed")])
    run_version = models.PositiveIntegerField(default=1)
    latest_revision = models.ForeignKey("AnalysisRevision", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    reviewed_revision = models.ForeignKey("AnalysisRevision", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    reviewed_by_name = models.CharField(max_length=150, blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True, default="")
    review_build = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-imported_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(run_version__gte=1), name="run_positive_version"),
            models.CheckConstraint(condition=Q(point_count__gte=2, point_count__lte=2000), name="run_point_count"),
            models.CheckConstraint(condition=Q(source_size__lte=262144), name="run_source_size"),
            models.CheckConstraint(condition=Q(time_min__lt=F("time_max"), total_area__gt=0), name="run_positive_window"),
            models.CheckConstraint(condition=(
                Q(status="draft", reviewed_revision__isnull=True, reviewed_by__isnull=True, reviewed_at__isnull=True, review_build__isnull=True)
                | Q(status="reviewed", reviewed_revision__isnull=False, reviewed_by__isnull=False, reviewed_at__isnull=False, review_build__isnull=False, latest_revision=F("reviewed_revision"))
            ), name="run_completion_consistent"),
        ]


class AnalysisRevision(AppendOnly):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(TraceRun, on_delete=models.PROTECT, related_name="revisions")
    revision_number = models.PositiveIntegerField()
    start_time = models.FloatField()
    end_time = models.FloatField()
    total_start_time = models.FloatField()
    total_end_time = models.FloatField()
    total_area = models.FloatField()
    selected_area = models.FloatField()
    area_fraction_percent = models.FloatField()
    point_count = models.PositiveIntegerField()
    time_unit = models.CharField(max_length=12)
    signal_unit = models.CharField(max_length=12)
    area_unit = models.CharField(max_length=12)
    fraction_unit = models.CharField(max_length=12)
    source_sha256 = models.CharField(max_length=64)
    parser_version = models.CharField(max_length=64)
    algorithm_version = models.CharField(max_length=64)
    application_version = models.CharField(max_length=32)
    git_commit = models.CharField(max_length=40, null=True)
    working_tree_dirty = models.BooleanField()
    runtime_versions = models.JSONField()
    reason = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_by_name = models.CharField(max_length=150)
    created_at = models.DateTimeField()

    class Meta:
        ordering = ["-revision_number"]
        constraints = [
            models.UniqueConstraint(fields=["run", "revision_number"], name="unique_run_revision"),
            models.CheckConstraint(condition=Q(revision_number__gte=1), name="revision_positive_number"),
            models.CheckConstraint(condition=Q(start_time__lt=F("end_time"), start_time__gte=F("total_start_time"), end_time__lte=F("total_end_time")), name="revision_valid_window"),
            models.CheckConstraint(condition=Q(total_area__gt=0, selected_area__gte=0, selected_area__lte=F("total_area"), area_fraction_percent__gte=0, area_fraction_percent__lte=100), name="revision_valid_result"),
            models.CheckConstraint(condition=~Q(reason=""), name="revision_reason_required"),
        ]


class AuditEvent(AppendOnly):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(TraceRun, on_delete=models.PROTECT, related_name="events")
    revision = models.ForeignKey(AnalysisRevision, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    event_type = models.CharField(max_length=32, choices=[(x, x) for x in ("trace_imported", "revision_saved", "review_completed")])
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    actor_name = models.CharField(max_length=150)
    occurred_at = models.DateTimeField()
    version_before = models.PositiveIntegerField()
    version_after = models.PositiveIntegerField()
    context = models.JSONField()
    request_id = models.UUIDField(unique=True)
    request_fingerprint = models.CharField(max_length=64)
    result = models.JSONField()

    class Meta:
        ordering = ["version_after"]
        constraints = [
            models.UniqueConstraint(fields=["run", "version_after"], name="unique_run_event_version"),
            models.CheckConstraint(condition=Q(version_after=F("version_before") + 1), name="event_next_version"),
        ]
