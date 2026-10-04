import hashlib
import json
from pathlib import PurePosixPath
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .calculation import analyze_trace
from .csv_input import MAX_FILE_BYTES, PARSER_VERSION, parse_csv
from .exceptions import DomainError
from .models import AnalysisRevision, AuditEvent, TraceRun
from .provenance import build_metadata
from .records import revision_record, review_record


def owned_run(user, run_id):
    return get_object_or_404(TraceRun.objects.select_related("latest_revision", "reviewed_revision"), id=run_id, imported_by=user)


def fingerprint(user, operation, payload):
    data = {"user_id": user.pk, "operation": operation, **payload}
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str).encode()).hexdigest()


def replay(user, request_id, digest):
    event = AuditEvent.objects.filter(request_id=request_id).first()
    if event is None:
        return None
    if event.actor_id != user.pk or event.request_fingerprint != digest:
        raise DomainError("This operation ID was already used for different content.", "idempotency_conflict", 409)
    return {**event.result, "replayed": True}


def assert_draft(run, expected_version=None):
    if run.status == "reviewed":
        raise DomainError("This run has been reviewed and is read-only.", "review_locked", 409, current_version=run.run_version)
    if expected_version is not None and run.run_version != expected_version:
        raise DomainError("Another tab changed this run. Reload latest before saving.", "version_conflict", 409, current_version=run.run_version)


def advance(run, expected_version):
    updated = TraceRun.objects.filter(pk=run.id, imported_by_id=run.imported_by_id, status="draft", run_version=expected_version).update(run_version=F("run_version") + 1)
    if updated != 1:
        raise DomainError("This run changed. Reload latest before saving.", "version_conflict", 409)
    run.run_version += 1


def record_event(user, run, request_id, digest, operation, before, context, revision=None):
    result = {"request_id": str(request_id), "operation": operation, "run_id": str(run.id),
              "committed_version": run.run_version, "revision": revision_record(revision) if operation == "revision_saved" else None,
              "review": review_record(run) if operation == "review_completed" else None, "replayed": False}
    AuditEvent.objects.create(run=run, revision=revision, event_type=operation, actor=user, actor_name=user.username,
                              occurred_at=timezone.now(), version_before=before, version_after=run.run_version,
                              context=context, request_id=request_id, request_fingerprint=digest, result=result)
    return result


def import_trace(user, file, request_id, label=None):
    name = PurePosixPath(file.name.replace("\\", "/")).name
    if not name.lower().endswith(".csv") or len(name) > 255 or any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise DomainError("Choose a CSV with a valid filename.", fields={"file": ["Expected a .csv file with a safe filename."]})
    if file.size > MAX_FILE_BYTES:
        raise DomainError("File exceeds 256 KiB.", "upload_too_large", 413)
    source = file.read(MAX_FILE_BYTES + 1)
    source_hash = hashlib.sha256(source).hexdigest()
    label = label if label is not None else PurePosixPath(name).stem[:120]
    if not label.strip():
        raise DomainError("Enter a trace label.", fields={"label": ["Enter a trace label."]})
    digest = fingerprint(user, "trace_imported", {"source": source_hash, "filename": name, "label": label})
    previous = replay(user, request_id, digest)
    if previous:
        return previous
    points, result = parse_csv(source)
    build = build_metadata()
    with transaction.atomic():
        previous = replay(user, request_id, digest)
        if previous:
            return previous
        run = TraceRun.objects.create(label=label, source_filename=name, source_bytes=source, source_sha256=source_hash,
              source_size=len(source), points=points, point_count=len(points), time_min=result.total_start_time,
              time_max=result.total_end_time, total_area=result.total_area, parser_version=PARSER_VERSION,
              import_calculation_version=result.algorithm_version, import_build=build,
              imported_by=user, imported_by_name=user.username, imported_at=timezone.now())
        return record_event(user, run, request_id, digest, "trace_imported", 0,
                            {"before": None, "after": {"status": "draft", "source_sha256": source_hash}})


def preview_trace(user, run_id, start_time, end_time):
    run = owned_run(user, run_id)
    assert_draft(run)
    return {**analyze_trace(run.points, start_time, end_time).to_dict(), "source_sha256": run.source_sha256, "run_version": run.run_version}


def save_revision(user, run_id, start_time, end_time, reason, expected_version, request_id):
    digest = fingerprint(user, "revision_saved", {"run_id": str(run_id), "start_time": start_time, "end_time": end_time,
                                               "reason": reason, "expected_version": expected_version})
    previous = replay(user, request_id, digest)
    if previous:
        return previous
    run = owned_run(user, run_id)
    if run.status != "draft" or run.run_version != expected_version:
        previous = replay(user, request_id, digest)
        if previous:
            return previous
    assert_draft(run, expected_version)
    result = analyze_trace(run.points, start_time, end_time).to_dict()
    build = build_metadata()
    with transaction.atomic():
        previous = replay(user, request_id, digest)
        if previous:
            return previous
        run = owned_run(user, run_id)
        assert_draft(run, expected_version)
        old_revision = str(run.latest_revision_id) if run.latest_revision_id else None
        number = run.latest_revision.revision_number + 1 if run.latest_revision_id else 1
        advance(run, expected_version)
        revision = AnalysisRevision.objects.create(run=run, revision_number=number, **result, **build,
            source_sha256=run.source_sha256, parser_version=run.parser_version, reason=reason,
            created_by=user, created_by_name=user.username, created_at=timezone.now())
        TraceRun.objects.filter(pk=run.id).update(latest_revision=revision)
        run.latest_revision = revision
        return record_event(user, run, request_id, digest, "revision_saved", expected_version,
                            {"before": {"revision_id": old_revision}, "after": {"revision_id": str(revision.id),
                             "start_time": start_time, "end_time": end_time, "reason": reason}}, revision)


def complete_review(user, run_id, revision_id, expected_version, request_id, review_note=""):
    digest = fingerprint(user, "review_completed", {"run_id": str(run_id), "revision_id": str(revision_id),
                                                  "expected_version": expected_version, "review_note": review_note})
    previous = replay(user, request_id, digest)
    if previous:
        return previous
    build = build_metadata()
    with transaction.atomic():
        previous = replay(user, request_id, digest)
        if previous:
            return previous
        run = owned_run(user, run_id)
        assert_draft(run, expected_version)
        if run.latest_revision_id != revision_id:
            raise DomainError("Complete the latest saved revision. Reload latest and try again.", "revision_conflict", 409, current_version=run.run_version)
        advance(run, expected_version)
        now = timezone.now()
        TraceRun.objects.filter(pk=run.id).update(status="reviewed", reviewed_revision=run.latest_revision,
            reviewed_by=user, reviewed_by_name=user.username, reviewed_at=now, review_note=review_note, review_build=build)
        run.refresh_from_db()
        return record_event(user, run, request_id, digest, "review_completed", expected_version,
                            {"before": {"status": "draft"}, "after": {"status": "reviewed", "revision_id": str(revision_id), "review_note": review_note}}, run.reviewed_revision)
