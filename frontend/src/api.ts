import type { Receipt, Report, Trace, TraceSummary, User } from './types'

interface ErrorBody {
  code: string; message: string; fields?: Record<string, string[]>; current_version?: number | null
}
export class ApiError extends Error {
  status: number
  detail: ErrorBody
  constructor(status: number, detail: ErrorBody) {
    super(detail.message); this.status = status; this.detail = detail
  }
}
let csrfToken = ''

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.method && !['GET', 'HEAD'].includes(options.method)) headers.set('X-CSRFToken', csrfToken)
  let response: Response
  try { response = await fetch(`/api/${path}`, { ...options, headers, credentials: 'same-origin' }) }
  catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, { code: 'network_error', message: 'Connection interrupted. Your entered values are retained.' })
  }
  if (!response.ok) {
    let body: { error?: ErrorBody } = {}
    try { body = await response.json() } catch { /* Server-level error may not contain JSON. */ }
    const detail = body.error ?? { code: 'request_failed', message: `The request failed (${response.status}). Your entered values are retained.` }
    if (detail.code === 'authentication_required' || detail.code === 'csrf_failed') window.dispatchEvent(new Event('tracereview-auth-required'))
    throw new ApiError(response.status, detail)
  }
  if (response.status === 204) return undefined as T
  return response.json()
}
export async function session() {
  const data = await request<{ authenticated: boolean; user: User | null; csrf_token: string }>('session/')
  csrfToken = data.csrf_token
  return data
}
export async function login(username: string, password: string) {
  await session()
  const data = await request<{ user: User; csrf_token: string }>('login/', {
    method: 'POST', body: new URLSearchParams({ username, password }),
  })
  csrfToken = data.csrf_token
  return data.user
}
export const logout = () => request<void>('logout/', { method: 'POST' })
export const getTrace = (id: string, signal?: AbortSignal) => request<Trace>(`traces/${id}/`, { signal })
export const getReport = (id: string, signal?: AbortSignal) => request<Report>(`traces/${id}/report/`, { signal })
export const listTraces = (offset = 0) => request<{ items: TraceSummary[]; total: number }>(`traces/?offset=${offset}&limit=50`)
export const post = <T = Receipt>(path: string, data: unknown, signal?: AbortSignal) => request<T>(path, {
  method: 'POST', body: JSON.stringify(data), headers: { 'Content-Type': 'application/json' }, signal,
})
export function message(error: unknown) { return error instanceof Error ? error.message : 'The request could not be completed.' }
export function isAbort(error: unknown) { return error instanceof DOMException && error.name === 'AbortError' }
