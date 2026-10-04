def timestamp(value):
    return value.isoformat().replace("+00:00", "Z") if value else None


def revision_record(revision):
    if revision is None:
        return None
    fields = ["revision_number", "start_time", "end_time", "total_start_time", "total_end_time",
              "total_area", "selected_area", "area_fraction_percent", "point_count", "time_unit", "signal_unit",
              "area_unit", "fraction_unit", "source_sha256", "parser_version", "algorithm_version",
              "application_version", "git_commit", "working_tree_dirty", "runtime_versions", "reason"]
    return {"id": str(revision.id), **{name: getattr(revision, name) for name in fields},
            "created_by": {"id": revision.created_by_id, "username": revision.created_by_name},
            "created_at": timestamp(revision.created_at)}


def review_record(run):
    if run.status != "reviewed":
        return None
    return {"revision_id": str(run.reviewed_revision_id), "revision_number": run.reviewed_revision.revision_number,
            "reviewed_by": {"id": run.reviewed_by_id, "username": run.reviewed_by_name},
            "reviewed_at": timestamp(run.reviewed_at), "review_note": run.review_note, "application_build": run.review_build}


def event_record(event):
    return {"id": str(event.id), "event_type": event.event_type,
            "revision_id": str(event.revision_id) if event.revision_id else None,
            "actor": {"id": event.actor_id, "username": event.actor_name}, "occurred_at": timestamp(event.occurred_at),
            "version_before": event.version_before, "version_after": event.version_after, "context": event.context}


def trace_summary(run):
    return {"id": str(run.id), "label": run.label, "source_filename": run.source_filename,
            "status": run.status, "run_version": run.run_version, "imported_at": timestamp(run.imported_at),
            "latest_revision_id": str(run.latest_revision_id) if run.latest_revision_id else None,
            "reviewed_revision_id": str(run.reviewed_revision_id) if run.reviewed_revision_id else None}


def trace_detail(run, revisions, events):
    return {**trace_summary(run), "source_sha256": run.source_sha256, "source_size": run.source_size,
            "points": run.points, "point_count": run.point_count, "time_min": run.time_min, "time_max": run.time_max,
            "total_area": run.total_area, "parser_version": run.parser_version,
            "imported_by": {"id": run.imported_by_id, "username": run.imported_by_name},
            "revisions": [revision_record(r) for r in revisions], "audit_events": [event_record(e) for e in events],
            "review": review_record(run)}
