import { useCallback, useEffect, useRef, useState } from 'react'
import { getTrace, listTraces, logout, message, session } from './api'
import { LoginForm, Modal } from './components'
import { ImportDialog, ReportView } from './features/review/RecordViews'
import Workspace from './features/review/Workspace'
import type { Trace, TraceSummary, User } from './types'

type Route = { id?: string; revision?: string; report?: boolean }
function parseRoute(hash: string): Route {
  const match = hash.match(/^#\/traces\/([0-9a-f-]{36})(\/report)?(?:\?revision=([0-9a-f-]{36}))?$/i)
  return match ? { id: match[1], report: Boolean(match[2]), revision: match[3] } : {}
}
function hashFor(route: Route) { return route.id ? `#/traces/${route.id}${route.report ? '/report' : ''}${route.revision ? `?revision=${route.revision}` : ''}` : '#/' }

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [booting, setBooting] = useState(true)
  const [traces, setTraces] = useState<TraceSummary[]>([])
  const [total, setTotal] = useState(0)
  const [run, setRun] = useState<Trace | null>(null)
  const [route, setRoute] = useState<Route>(() => parseRoute(location.hash))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [importing, setImporting] = useState(false)
  const [reauth, setReauth] = useState(false)
  const [authGeneration, setAuthGeneration] = useState(0)
  const [workspaceEpoch, setWorkspaceEpoch] = useState(0)
  const [work, setWork] = useState({ dirty: false, busy: false })
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null)
  const runRef = useRef(run), workRef = useRef(work), routeRef = useRef(route)
  const loadGeneration = useRef(0)
  useEffect(() => { runRef.current = run }, [run])
  useEffect(() => { workRef.current = work }, [work])
  useEffect(() => { routeRef.current = route }, [route])

  const updateRun = useCallback((next: Trace) => {
    if (runRef.current?.id === next.id) { runRef.current = next; setRun(next) }
    setTraces(current => current.some(r => r.id === next.id) ? current.map(r => r.id === next.id ? next : r) : [next, ...current])
  }, [])
  const updateWork = useCallback((dirty: boolean, busy: boolean) => { setWork({ dirty, busy }) }, [])
  const loadRun = useCallback(async (id: string) => {
    const generation = ++loadGeneration.current
    setLoading(true); setError('')
    try {
      const data = await getTrace(id)
      if (generation === loadGeneration.current) { runRef.current = data; setRun(data) }
    } catch (error) {
      if (generation === loadGeneration.current) { setError(message(error)); setRun(null); runRef.current = null }
    } finally { if (generation === loadGeneration.current) setLoading(false) }
  }, [])
  const applyRoute = useCallback((next: Route) => {
    setWork({ dirty: false, busy: false }); workRef.current = { dirty: false, busy: false }
    setRoute(next); routeRef.current = next; history.pushState(null, '', hashFor(next))
    if (next.id && next.id !== runRef.current?.id) void loadRun(next.id)
  }, [loadRun])
  const guard = useCallback((action: () => void) => {
    if (workRef.current.busy) return
    if (workRef.current.dirty) setPendingAction(() => action)
    else action()
  }, [])
  const navigate = (next: Route) => guard(() => applyRoute(next))

  const loadCollection = useCallback(async () => {
    const data = await listTraces()
    setTraces(data.items); setTotal(data.total)
    const currentRoute = parseRoute(location.hash)
    const id = currentRoute.id ?? data.items[0]?.id
    if (id) {
      const next = { ...currentRoute, id }
      setRoute(next); routeRef.current = next; history.replaceState(null, '', hashFor(next)); await loadRun(id)
    }
  }, [loadRun])

  useEffect(() => {
    let cancelled = false
    session().then(async data => {
      if (cancelled) return
      setUser(data.user)
      if (data.user) await loadCollection()
    }).catch(error => { if (!cancelled) setError(message(error)) }).finally(() => { if (!cancelled) setBooting(false) })
    return () => { cancelled = true }
  }, [loadCollection])
  useEffect(() => {
    const expired = () => setReauth(true)
    const hashChanged = () => {
      const target = parseRoute(location.hash)
      history.replaceState(null, '', hashFor(routeRef.current))
      guard(() => applyRoute(target.id ? target : { id: runRef.current?.id }))
    }
    window.addEventListener('tracereview-auth-required', expired)
    window.addEventListener('hashchange', hashChanged)
    return () => { window.removeEventListener('tracereview-auth-required', expired); window.removeEventListener('hashchange', hashChanged) }
  }, [applyRoute, guard])
  useEffect(() => {
    if (!work.dirty && !work.busy) return
    const leaving = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', leaving)
    return () => window.removeEventListener('beforeunload', leaving)
  }, [work])

  async function signedIn(next: User) {
    const same = user?.id === next.id
    setUser(next); setReauth(false); setError('')
    if (same) { setAuthGeneration(n => n + 1); return }
    loadGeneration.current++; setRun(null); runRef.current = null; setTraces([]); setWork({ dirty: false, busy: false })
    if (user) history.replaceState(null, '', '#/')
    try { await loadCollection() } catch (error) { setError(message(error)) }
  }
  async function signOut() {
    try {
      await logout(); loadGeneration.current++; setUser(null); setRun(null); runRef.current = null
      setTraces([]); setWork({ dirty: false, busy: false }); setReauth(false); history.replaceState(null, '', '#/')
    } catch (error) { setError(message(error)) }
  }
  async function imported(id: string) {
    setImporting(false); applyRoute({ id })
    try { const data = await listTraces(); setTraces(data.items); setTotal(data.total) }
    catch (error) { setError(message(error)) }
  }
  async function moreTraces() {
    try { const data = await listTraces(traces.length); setTraces(current => [...current, ...data.items.filter(r => !current.some(x => x.id === r.id))]); setTotal(data.total) }
    catch (error) { setError(message(error)) }
  }

  if (booting) return <main className="loading-screen" role="status">Opening TraceReview…</main>
  if (!user) return <main className="login-page">{error && <p className="error" role="alert">{error}</p>}<LoginForm onLogin={next => void signedIn(next)} /></main>
  return <>
    <a className="skip-link" href="#main-content" onClick={event => { event.preventDefault(); document.getElementById('main-content')?.focus() }}>Skip to workspace</a>
    <header className="app-header"><span className="wordmark">TraceReview</span>
      <div className="trace-selector"><label htmlFor="trace-select" className="sr-only">Trace</label><select id="trace-select" value={run?.id ?? ''} disabled={work.busy} onChange={e => navigate({ id: e.target.value })}>
        <option value="" disabled>Select a trace</option>{traces.map(trace => <option key={trace.id} value={trace.id}>{trace.label}{trace.status === 'reviewed' ? ' · Reviewed' : ''}</option>)}</select>
        {traces.length < total && <button className="text-button" onClick={() => void moreTraces()}>More traces</button>}
        <button onClick={() => guard(() => setImporting(true))} disabled={work.busy}>Import</button></div>
      <div className="account"><span>{user.username}</span><button className="text-button" disabled={work.busy} onClick={() => guard(() => { void signOut() })}>Sign out</button></div>
    </header>
    <div id="main-content" tabIndex={-1}>
      {error && <p className="app-error error" role="alert">{error}</p>}
      {loading ? <main className="loading-screen" role="status">Loading trace…</main> : run ? route.report ? <ReportView run={run} onBack={() => navigate({ id: run.id })} /> :
        <Workspace key={`${run.id}:${route.revision ?? 'latest'}:${workspaceEpoch}`} run={run} historicalId={route.revision} onRun={updateRun} onWork={updateWork}
          onRevision={id => navigate({ id: run.id, revision: id })} onLatest={() => navigate({ id: run.id })} onReport={() => navigate({ id: run.id, report: true })} authGeneration={authGeneration} /> :
        <main className="empty-workspace"><p className="eyebrow">Trace workspace</p><h1>Start with a trace.</h1><p>Import a prepared CSV to inspect and review its selected region.</p><div className="actions"><button className="primary" onClick={() => setImporting(true)}>Import trace</button><a href="/api/examples/neighboring-feature.csv">Download example</a></div></main>}
    </div>
    {importing && <ImportDialog onClose={() => setImporting(false)} onImported={id => void imported(id)} />}
    {pendingAction && <Modal title="Discard changes?" onClose={() => setPendingAction(null)}>
      <p>Your unsaved boundaries, preview and reason will be discarded.</p><div className="actions"><button onClick={() => setPendingAction(null)}>Keep editing</button><button className="primary" onClick={() => { const action = pendingAction; setPendingAction(null); setWorkspaceEpoch(x => x + 1); setWork({ dirty: false, busy: false }); action() }}>Discard changes</button></div>
    </Modal>}
    {reauth && <Modal title="Sign in again" dismissible={false} onClose={() => {}}><LoginForm reauth onLogin={next => void signedIn(next)} /></Modal>}
  </>
}
