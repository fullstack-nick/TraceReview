import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, getTrace, isAbort, message, post } from '../../api'
import { Modal } from '../../components'
import { date, number, parseBoundary, percent } from '../../format'
import type { Preview, Receipt, Trace } from '../../types'
import { DataDialog, HistoryDialog } from './RecordViews'
import ChartBoundary from './ChartBoundary'

const TraceChart = lazy(() => import('./TraceChart'))
type Draft = { start: string; end: string; reason: string }
type Operation = { path: string; payload: Record<string, unknown>; kind: 'save' | 'complete' }

export default function Workspace({ run, historicalId, onRun, onWork, onRevision, onLatest, onReport, authGeneration }: {
  run: Trace; historicalId?: string; onRun: (run: Trace) => void; onWork: (dirty: boolean, busy: boolean) => void
  onRevision: (id: string) => void; onLatest: () => void; onReport: () => void; authGeneration: number
}) {
  const latest = run.revisions.find(r => r.id === run.latest_revision_id)
  const historical = historicalId ? run.revisions.find(r => r.id === historicalId) : undefined
  const saved = historical ?? (run.status === 'reviewed' ? run.revisions.find(r => r.id === run.reviewed_revision_id) : latest)
  const [draft, setDraft] = useState<Draft>(() => ({ start: String(saved?.start_time ?? run.time_min), end: String(saved?.end_time ?? run.time_max), reason: '' }))
  const [preview, setPreview] = useState<Preview | null>(null)
  const [busy, setBusy] = useState<'preview' | 'save' | 'complete' | 'refresh' | null>(null)
  const [error, setError] = useState<ApiError | Error | null>(null)
  const [notice, setNotice] = useState('')
  const [dialog, setDialog] = useState<'data' | 'history' | 'complete' | null>(null)
  const [reviewNote, setReviewNote] = useState('')
  const [pending, setPending] = useState<Operation | null>(null)
  const [conflict, setConflict] = useState(false)
  const [recoveredDraft, setRecoveredDraft] = useState<Draft | null>(null)
  const generation = useRef(0)
  const abort = useRef<AbortController | null>(null)
  const alive = useRef(true)
  const initialAuth = useRef(authGeneration)
  const readonly = Boolean(historicalId) || run.status === 'reviewed'
  const a = parseBoundary(draft.start), b = parseBoundary(draft.end)
  const boundsValid = a !== null && b !== null && a >= run.time_min && b <= run.time_max && a < b
  const matchesSaved = Boolean(saved && a === saved.start_time && b === saved.end_time)
  const matchingPreview = preview && a === preview.start_time && b === preview.end_time ? preview : null
  const result = readonly ? saved : matchingPreview ?? (matchesSaved ? saved : undefined)
  const boundaryDirty = a === null || b === null || a !== (latest?.start_time ?? run.time_min) || b !== (latest?.end_time ?? run.time_max)
  const dirty = !readonly && (boundaryDirty || Boolean(draft.reason.trim()) || (!latest && Boolean(preview)))
  const mutating = busy === 'save' || busy === 'complete'
  const fieldsLocked = readonly || mutating || Boolean(pending)
  const serverFields = error instanceof ApiError ? error.detail.fields ?? {} : {}
  const startError = a === null ? 'Enter a number.' : a < run.time_min || a > run.time_max ? `Use ${number(run.time_min)}–${number(run.time_max)} min.` : serverFields.start_time?.[0]
  const endError = b === null ? 'Enter a number.' : b < run.time_min || b > run.time_max ? `Use ${number(run.time_min)}–${number(run.time_max)} min.` : a !== null && b <= a ? 'Must be greater than start.' : serverFields.end_time?.[0]
  const status = historical ? `Viewing revision ${historical.revision_number}` : run.status === 'reviewed' ? `Review complete · Revision ${saved?.revision_number}` : matchingPreview ? 'Unsaved preview' : dirty ? 'Unsaved changes' : latest ? `Saved revision ${latest.revision_number}` : 'No saved revision'

  useEffect(() => { onWork(dirty || Boolean(pending), mutating) }, [dirty, pending, mutating, onWork])
  useEffect(() => {
    alive.current = true
    return () => { alive.current = false; abort.current?.abort() }
  }, [])
  useEffect(() => {
    if (initialAuth.current !== authGeneration) {
      initialAuth.current = authGeneration
      setConflict(true); setPreview(null); setNotice('Signed in. Reload latest before retrying your work.')
    }
  }, [authGeneration])
  useEffect(() => {
    const controller = new AbortController()
    const checkVersion = async () => {
      if (busy || pending || conflict || document.visibilityState === 'hidden') return
      try {
        const fresh = await getTrace(run.id, controller.signal)
        if (!controller.signal.aborted && fresh.run_version !== run.run_version) {
          setConflict(true); setPreview(null)
          setNotice('Another tab changed this run. Reload latest; your entries are retained.')
        }
      } catch { /* The next explicit action reports connection/session failures. */ }
    }
    window.addEventListener('focus', checkVersion)
    document.addEventListener('visibilitychange', checkVersion)
    return () => {
      controller.abort()
      window.removeEventListener('focus', checkVersion)
      document.removeEventListener('visibilitychange', checkVersion)
    }
  }, [run.id, run.run_version, busy, pending, conflict])

  function edit(field: keyof Draft, value: string) {
    setDraft(current => ({ ...current, [field]: value })); setError(null); setNotice('')
    if (field !== 'reason') { abort.current?.abort(); generation.current++; setPreview(null); if (busy === 'preview') setBusy(null) }
  }

  async function calculate(event?: FormEvent) {
    event?.preventDefault()
    if (!boundsValid || readonly || pending) return
    abort.current?.abort(); const controller = new AbortController(); abort.current = controller
    const requestGeneration = ++generation.current
    setBusy('preview'); setError(null); setNotice('')
    try {
      const data = await post<Preview>(`traces/${run.id}/preview/`, { start_time: a, end_time: b }, controller.signal)
      if (!alive.current || requestGeneration !== generation.current) return
      if (data.start_time !== a || data.end_time !== b) return
      if (data.run_version !== run.run_version) { setConflict(true); setNotice('Another tab changed this run. Reload latest.'); return }
      setPreview(data)
    } catch (error) {
      if (!isAbort(error) && requestGeneration === generation.current) {
        setError(error as Error); if (error instanceof ApiError && error.status === 409) setConflict(true)
      }
    } finally { if (alive.current && requestGeneration === generation.current) setBusy(null) }
  }

  async function reload() {
    setBusy('refresh'); setError(null); abort.current?.abort(); generation.current++
    try {
      const data = await getTrace(run.id)
      if (!alive.current) return
      onRun(data); setPreview(null); setPending(null); setConflict(false)
      if (data.status === 'reviewed') {
        setRecoveredDraft({ ...draft })
        const reviewed = data.revisions.find(r => r.id === data.reviewed_revision_id)!
        setDraft({ start: String(reviewed.start_time), end: String(reviewed.end_time), reason: '' })
        setNotice('This run was completed. Your local values are retained below for copying.')
      } else setNotice('Latest record loaded. Your entries are retained; calculate a fresh preview before saving.')
    } catch (error) { setError(error as Error) }
    finally { if (alive.current) setBusy(null) }
  }

  async function commit(operation: Operation) {
    setBusy(operation.kind); setError(null); setNotice(''); setPending(operation)
    try {
      const receipt = await post<Receipt>(operation.path, operation.payload)
      if (!alive.current) return
      setPending(null); setConflict(false); setPreview(null); setDialog(null)
      let updated = { ...run, run_version: receipt.committed_version }
      if (receipt.revision) {
        updated = { ...updated, latest_revision_id: receipt.revision.id, revisions: [receipt.revision, ...run.revisions.filter(r => r.id !== receipt.revision!.id)] }
        setDraft({ start: String(receipt.revision.start_time), end: String(receipt.revision.end_time), reason: '' })
      }
      if (receipt.review) updated = { ...updated, status: 'reviewed', reviewed_revision_id: receipt.review.revision_id, review: receipt.review }
      onRun(updated)
      try { const refreshed = await getTrace(run.id); if (alive.current) onRun(refreshed) }
      catch { if (alive.current) setNotice('Saved successfully. Refresh failed; use Reload latest to update the record.') }
    } catch (error) {
      if (!alive.current) return
      setError(error as Error)
      const uncertain = error instanceof ApiError && (error.status === 0 || error.status >= 500)
      if (!uncertain) setPending(null)
      if (error instanceof ApiError && error.status === 409) { setConflict(true); setDialog(null) }
    } finally { if (alive.current) setBusy(null) }
  }

  function save() {
    if (pending) { void commit(pending); return }
    if (!matchingPreview || !draft.reason.trim() || conflict) return
    void commit({ kind: 'save', path: `traces/${run.id}/revisions/`, payload: {
      start_time: a, end_time: b, reason: draft.reason.trim(), expected_version: run.run_version, request_id: crypto.randomUUID(),
    } })
  }
  function complete() {
    if (pending) { void commit(pending); return }
    void commit({ kind: 'complete', path: `traces/${run.id}/complete-review/`, payload: {
      revision_id: run.latest_revision_id, expected_version: run.run_version, review_note: reviewNote.trim(), request_id: crypto.randomUUID(),
    } })
  }

  if (historicalId && !historical) return <main className="workspace"><h1>Revision not available</h1><button onClick={onLatest}>Back to latest</button></main>
  return <main className="workspace">
    <div className="trace-heading"><div><h1>{run.label}</h1><p className="identity">{run.source_filename}<span aria-hidden="true"> · </span><span role="status" aria-live="polite" data-testid="review-status">{status}</span></p></div>
      <nav className="trace-links" aria-label="Trace records"><a href={`/api/traces/${run.id}/source/`}>Source</a><button className="text-button" onClick={() => setDialog('data')}>Data</button><button className="text-button" onClick={() => setDialog('history')}>History</button></nav></div>
    {historicalId && <p className="historical-banner">Read-only revision {historical?.revision_number ?? 'not found'}. <button className="text-button" onClick={onLatest}>Back to latest</button></p>}
    <div className="workspace-grid">
      <ChartBoundary><Suspense fallback={<div className="chart-loading" role="status">Loading chart…</div>}><TraceChart run={run} start={boundsValid ? a : null} end={boundsValid ? b : null} /></Suspense></ChartBoundary>
      <section className="analysis" aria-label="Analysis controls">
        <form onSubmit={calculate}>
          <div className="boundaries"><div><label htmlFor="start-time">Start (min)</label><input id="start-time" inputMode="decimal" value={draft.start} readOnly={readonly} disabled={mutating || Boolean(pending)} aria-invalid={Boolean(startError)} aria-describedby={startError ? 'start-error' : undefined} onChange={e => edit('start', e.target.value)} />{startError && <small className="error" id="start-error">{startError}</small>}</div>
            <div><label htmlFor="end-time">End (min)</label><input id="end-time" inputMode="decimal" value={draft.end} readOnly={readonly} disabled={mutating || Boolean(pending)} aria-invalid={Boolean(endError)} aria-describedby={endError ? 'end-error' : undefined} onChange={e => edit('end', e.target.value)} />{endError && <small className="error" id="end-error">{endError}</small>}</div></div>
          {!readonly && <div className="preview-actions"><button type="submit" disabled={!boundsValid || Boolean(busy) || Boolean(pending) || conflict}>{busy === 'preview' ? 'Calculating…' : 'Calculate preview'}</button><button className="text-button" type="button" disabled={fieldsLocked} onClick={() => { edit('start', String(run.time_min)); edit('end', String(run.time_max)) }}>Use full trace</button></div>}
        </form>
        <div className="results" aria-live="polite" aria-atomic="true">
          <p className="result-label">Selected-region area fraction</p><p className={`fraction${result ? '' : ' uncalculated'}`} data-testid="fraction">{result ? percent(result.area_fraction_percent) : '—'}</p>
          {!result && <p className="freshness">{boundsValid ? 'Calculate preview for these boundaries.' : 'Check the boundaries.'}</p>}
          <dl className="area-values"><dt>Selected area</dt><dd>{result ? number(result.selected_area) : '—'} <span>AU·min</span></dd><dt>Total area</dt><dd>{number(result?.total_area ?? run.total_area)} <span>AU·min</span></dd></dl>
        </div>
        {!readonly ? <><label htmlFor="reason">Revision reason</label><textarea id="reason" value={draft.reason} rows={3} maxLength={1000} disabled={fieldsLocked} aria-invalid={Boolean(serverFields.reason)} aria-describedby={serverFields.reason ? 'reason-error' : undefined} onChange={e => edit('reason', e.target.value)} />{serverFields.reason && <small className="error" id="reason-error">{serverFields.reason[0]}</small>}
          <div className="save-actions"><button className="primary" onClick={save} disabled={Boolean(busy) || (!pending && (!matchingPreview || !draft.reason.trim() || conflict))}>{busy === 'save' ? 'Saving…' : pending?.kind === 'save' ? 'Retry save' : 'Save analysis revision'}</button>
            <button className="text-button complete-link" onClick={() => setDialog('complete')} disabled={!latest || dirty || Boolean(busy) || Boolean(pending) || conflict}>Complete review</button></div></> : <>
          {saved && <div className="saved-reason"><p className="result-label">Revision reason</p><p className="preserve-lines">{saved.reason}</p><small>{saved.created_by.username} · {date(saved.created_at)}</small></div>}
          {run.status === 'reviewed' && !historicalId && <div className="save-actions"><button className="primary" onClick={onReport}>View report</button><a href={`/api/traces/${run.id}/report/?download=1`}>Download JSON</a></div>}
        </>}
        {error && <div className="operation-error" role="alert"><p>{message(error)}</p>{pending && <p>Outcome unknown. Retry the same operation to recover its result.</p>}</div>}
        {notice && <p className="notice" role="status">{notice}</p>}
        {(error || notice || conflict) && <button className="text-button reload" disabled={Boolean(busy)} onClick={() => void reload()}>Reload latest</button>}
        {recoveredDraft && <details><summary>Retained local values</summary><p>{recoveredDraft.start}–{recoveredDraft.end} min</p><p className="preserve-lines">{recoveredDraft.reason}</p></details>}
      </section>
    </div>
    {dialog === 'data' && <DataDialog run={run} onClose={() => setDialog(null)} />}
    {dialog === 'history' && <HistoryDialog run={run} onClose={() => setDialog(null)} onRevision={id => { setDialog(null); onRevision(id) }} />}
    {dialog === 'complete' && <Modal title={`Complete revision ${latest?.revision_number}`} onClose={() => setDialog(null)} dismissible={!mutating && !pending}>
      <p>Complete review of revision {latest?.revision_number}? This run will become read-only.</p>
      <p className="confirmation-result">{number(latest!.start_time)}–{number(latest!.end_time)} min · {percent(latest!.area_fraction_percent)}</p>
      <label htmlFor="review-note">Review note <span className="muted">(optional)</span></label><textarea id="review-note" rows={3} maxLength={2000} value={reviewNote} disabled={mutating || Boolean(pending)} onChange={e => setReviewNote(e.target.value)} />
      {error && <p className="error" role="alert">{message(error)}</p>}
      <div className="actions"><button disabled={mutating || Boolean(pending)} onClick={() => setDialog(null)}>Cancel</button><button className="primary" disabled={mutating} onClick={complete}>{mutating ? 'Completing…' : pending ? 'Retry completion' : 'Complete review'}</button></div>
    </Modal>}
  </main>
}
