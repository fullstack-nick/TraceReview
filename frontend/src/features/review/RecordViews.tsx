import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, getReport, isAbort, message, request } from '../../api'
import { Modal } from '../../components'
import { date, number, percent } from '../../format'
import type { Receipt, Report, Trace } from '../../types'

export function ImportDialog({ onClose, onImported }: { onClose: () => void; onImported: (id: string) => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [label, setLabel] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [operationId, setOperationId] = useState<string | null>(null)
  const [uncertain, setUncertain] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!file) { setError('Choose a CSV file.'); return }
    if (file.size > 262144) { setError('File exceeds 256 KiB.'); return }
    const id = operationId ?? crypto.randomUUID()
    setOperationId(id); setBusy(true); setError('')
    const body = new FormData(); body.append('file', file); body.append('request_id', id)
    if (label.trim()) body.append('label', label.trim())
    try {
      const result = await request<Receipt>('traces/', { method: 'POST', body })
      onImported(result.run_id)
    } catch (error) {
      const unknown = error instanceof ApiError && (error.status === 0 || error.status >= 500)
      setUncertain(unknown); setError(message(error))
      if (!unknown) setOperationId(null)
    } finally { setBusy(false) }
  }
  return <Modal title="Import trace" onClose={onClose} dismissible={!busy && !uncertain}>
    <form onSubmit={submit}>
      <p className="muted">CSV · time_min,signal_au · 2–2,000 points · up to 256 KiB</p>
      <p className="muted">Signals must be nonnegative and already prepared. <a href="/api/examples/neighboring-feature.csv">Download example</a></p>
      <label htmlFor="trace-file">CSV file</label><input id="trace-file" type="file" accept=".csv,text/csv" disabled={busy || uncertain}
        onChange={e => { setFile(e.target.files?.[0] ?? null); setError(''); setOperationId(null) }} />
      <label htmlFor="trace-label">Label <span className="muted">(optional)</span></label>
      <input id="trace-label" maxLength={120} value={label} disabled={busy || uncertain} placeholder="Use the filename"
        onChange={e => { setLabel(e.target.value); setOperationId(null) }} />
      {error && <p className="error" role="alert">{error}{uncertain && ' Retry this import to recover its original result.'}</p>}
      <div className="actions"><button className="primary" disabled={busy || !file} type="submit">{busy ? 'Importing…' : uncertain ? 'Retry import' : 'Import trace'}</button>
        {!uncertain && <button type="button" disabled={busy} onClick={onClose}>Cancel</button>}</div>
    </form>
  </Modal>
}

export function DataDialog({ run, onClose }: { run: Trace; onClose: () => void }) {
  const [page, setPage] = useState(0)
  return <Modal title="Measured data" onClose={onClose} wide>
    <div className="table-scroll"><table><caption>{run.source_filename} · {run.point_count} points</caption>
      <thead><tr><th scope="col">Point</th><th scope="col">Time (min)</th><th scope="col">Signal (AU)</th></tr></thead>
      <tbody>{run.points.slice(page * 100, (page + 1) * 100).map(([x, y], i) => <tr key={page * 100 + i}><th scope="row">{page * 100 + i + 1}</th><td>{String(x)}</td><td>{String(y)}</td></tr>)}</tbody></table></div>
    <div className="pagination"><button disabled={page === 0} onClick={() => setPage(p => p - 1)}>Previous</button><span>Page {page + 1} of {Math.ceil(run.point_count / 100)}</span><button disabled={(page + 1) * 100 >= run.point_count} onClick={() => setPage(p => p + 1)}>Next</button></div>
  </Modal>
}

export function HistoryDialog({ run, onClose, onRevision }: { run: Trace; onClose: () => void; onRevision: (id: string) => void }) {
  return <Modal title="Analysis history" onClose={onClose} wide>
    {run.revisions.length === 0 ? <p>No saved revisions yet.</p> : <div className="table-scroll"><table>
      <caption>{run.label}</caption><thead><tr><th>Revision</th><th>Interval (min)</th><th>Area fraction</th><th>Reason</th><th>Saved by</th></tr></thead>
      <tbody>{run.revisions.map(revision => <tr key={revision.id}>
        <th scope="row"><button className="text-button" onClick={() => onRevision(revision.id)}>Revision {revision.revision_number}</button>
          {run.reviewed_revision_id === revision.id && <small>Reviewed</small>}</th>
        <td className="nowrap">{number(revision.start_time)}–{number(revision.end_time)}</td><td className="nowrap">{percent(revision.area_fraction_percent)}</td>
        <td className="reason-cell">{revision.reason}</td><td>{revision.created_by.username}<small>{date(revision.created_at)}</small></td>
      </tr>)}</tbody></table></div>}
    <details className="audit"><summary>Committed actions ({run.audit_events.length})</summary>
      <ol>{run.audit_events.map(event => <li key={event.id}><strong>{event.event_type.replaceAll('_', ' ')}</strong> · {event.actor.username} · {date(event.occurred_at)}<small>Run version {event.version_before} → {event.version_after}</small></li>)}</ol>
    </details>
  </Modal>
}

export function ReportView({ run, onBack }: { run: Trace; onBack: () => void }) {
  const [report, setReport] = useState<Report | null>(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    getReport(run.id, controller.signal).then(setReport).catch(e => { if (!isAbort(e)) setError(message(e)) })
    return () => controller.abort()
  }, [run.id, retry])
  const revision = report?.revisions.find(r => r.id === report.review.revision_id)
  return <main className="report-page">
    <button className="text-button back-link" onClick={onBack}>← Back to trace</button>
    <div className="report-title"><div><p className="eyebrow">Completed review</p><h1>{run.label}</h1></div>
      <div className="actions"><a className="button primary" href={`/api/traces/${run.id}/report/?download=1`}>Download JSON</a><a className="button" href={`/api/traces/${run.id}/source/`}>Source CSV</a></div></div>
    {error && <p className="error" role="alert">{error} <button onClick={() => { setError(''); setRetry(x => x + 1) }}>Retry</button></p>}
    {!report && !error && <p role="status">Loading reviewed record…</p>}
    {report && revision && <>
      <section className="report-result"><p>Selected-region area fraction</p><p className="fraction">{percent(revision.area_fraction_percent)}</p><p className="muted">Revision {revision.revision_number} · {number(revision.start_time)}–{number(revision.end_time)} min</p></section>
      <dl className="record-list">
        <dt>Selected interval (min)</dt><dd>{String(revision.start_time)}–{String(revision.end_time)}</dd>
        <dt>Total integration window (min)</dt><dd>Entire trace, {String(revision.total_start_time)}–{String(revision.total_end_time)}</dd>
        <dt>Selected area (AU·min)</dt><dd>{String(revision.selected_area)}</dd>
        <dt>Total area (AU·min)</dt><dd>{String(revision.total_area)}</dd>
        <dt>Area fraction (%)</dt><dd>{String(revision.area_fraction_percent)}</dd>
        <dt>Revision reason</dt><dd className="preserve-lines">{revision.reason}</dd>
        <dt>Saved by</dt><dd>{revision.created_by.username} · {date(revision.created_at)}</dd>
        <dt>Reviewed by</dt><dd>{report.review.reviewed_by.username} · {date(report.review.reviewed_at)}</dd>
        {report.review.review_note && <><dt>Review note</dt><dd className="preserve-lines">{report.review.review_note}</dd></>}
        <dt>Source</dt><dd>{report.source.filename} · {report.source.byte_count.toLocaleString('en-GB')} bytes · {report.trace.point_count} points</dd>
        <dt>Source SHA-256</dt><dd className="checksum">{report.source.sha256}</dd>
        <dt>Imported by</dt><dd>{report.trace.imported_by.username} · {date(report.trace.imported_at)}</dd>
        <dt>Calculation</dt><dd>{revision.algorithm_version}</dd>
        <dt>Input parser</dt><dd>{revision.parser_version}</dd>
        <dt>Application build</dt><dd className="checksum">{revision.application_version} · {revision.git_commit ?? 'release build'}{revision.working_tree_dirty && ' (working tree had edits)'}</dd>
        <dt>Runtime</dt><dd>{Object.entries(revision.runtime_versions).map(([k, v]) => `${k} ${v}`).join(' · ')}</dd>
        <dt>Record schema</dt><dd>{report.schema_version}</dd>
      </dl>
    </>}
  </main>
}
