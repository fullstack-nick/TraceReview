import base64
import json
from .exceptions import DomainError
from .records import event_record, revision_record, review_record, timestamp


def reviewed_report(run):
    if run.status != "reviewed":
        raise DomainError("Complete this review before exporting its record.", "review_not_complete", 409)
    return {"schema_version": "tracereview-report-v1",
            "trace": {"id": str(run.id), "label": run.label, "imported_at": timestamp(run.imported_at),
                      "imported_by": {"id": run.imported_by_id, "username": run.imported_by_name},
                      "point_count": run.point_count, "parser_version": run.parser_version},
            "source": {"filename": run.source_filename, "byte_count": run.source_size, "sha256": run.source_sha256,
                       "encoding": "base64", "content": base64.b64encode(bytes(run.source_bytes)).decode("ascii")},
            "review": review_record(run),
            "revisions": [revision_record(r) for r in run.revisions.order_by("revision_number")],
            "audit_events": [event_record(e) for e in run.events.order_by("version_after")]}


def report_bytes(run):
    return (json.dumps(reviewed_report(run), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
