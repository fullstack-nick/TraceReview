export interface User { id: number; username: string }
export interface Build {
  application_version: string; git_commit: string | null; working_tree_dirty: boolean
  runtime_versions: Record<string, string>
}
export interface Analysis {
  start_time: number; end_time: number; total_start_time: number; total_end_time: number
  total_area: number; selected_area: number; area_fraction_percent: number; point_count: number
  algorithm_version: string; time_unit: string; signal_unit: string; area_unit: string; fraction_unit: string
}
export interface Revision extends Analysis, Build {
  id: string; revision_number: number; source_sha256: string; parser_version: string
  reason: string; created_by: User; created_at: string
}
export interface Review {
  revision_id: string; revision_number: number; reviewed_by: User; reviewed_at: string
  review_note: string; application_build: Build
}
export interface AuditEvent {
  id: string; event_type: string; revision_id: string | null; actor: User; occurred_at: string
  version_before: number; version_after: number; context: Record<string, unknown>
}
export interface TraceSummary {
  id: string; label: string; source_filename: string; status: 'draft' | 'reviewed'; run_version: number
  imported_at: string; latest_revision_id: string | null; reviewed_revision_id: string | null
}
export interface Trace extends TraceSummary {
  source_sha256: string; source_size: number; points: [number, number][]; point_count: number
  time_min: number; time_max: number; total_area: number; parser_version: string; imported_by: User
  revisions: Revision[]; audit_events: AuditEvent[]; review: Review | null
}
export interface Preview extends Analysis { source_sha256: string; run_version: number }
export interface Receipt {
  request_id: string; operation: string; run_id: string; committed_version: number
  revision: Revision | null; review: Review | null; replayed: boolean
}
export interface Report {
  schema_version: string
  trace: { id: string; label: string; imported_at: string; imported_by: User; point_count: number; parser_version: string }
  source: { filename: string; byte_count: number; sha256: string; encoding: string; content: string }
  review: Review; revisions: Revision[]; audit_events: AuditEvent[]
}
