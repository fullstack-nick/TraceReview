import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { login, message } from './api'
import type { User } from './types'

export function Modal({ title, children, onClose, wide = false, dismissible = true }: {
  title: string; children: ReactNode; onClose: () => void; wide?: boolean; dismissible?: boolean
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    const dialog = ref.current!
    const opener = document.activeElement as HTMLElement | null
    dialog.showModal()
    return () => { dialog.close(); opener?.focus() }
  }, [])
  return <dialog ref={ref} className={wide ? 'modal wide' : 'modal'} aria-labelledby={titleId}
    onCancel={event => { event.preventDefault(); if (dismissible) onClose() }}>
    <div className="modal-heading"><h2 id={titleId} tabIndex={-1}>{title}</h2>
      {dismissible && <button type="button" className="text-button" aria-label={`Close ${title.toLowerCase()}`} onClick={onClose}>Close</button>}</div>
    {children}
  </dialog>
}

export function LoginForm({ onLogin, reauth = false }: { onLogin: (user: User) => void; reauth?: boolean }) {
  const [username, setUsername] = useState('analyst')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setBusy(true)
    try { onLogin(await login(username, password)) }
    catch (error) { setError(message(error)) }
    finally { setBusy(false) }
  }
  return <form onSubmit={submit} className="login-form">
    {!reauth && <><p className="eyebrow">Local workspace</p><h1>TraceReview</h1></>}
    {reauth && <p>Sign in to continue with your saved session.</p>}
    <label htmlFor="username">Username</label><input id="username" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} required />
    <label htmlFor="password">Password</label><input id="password" type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required />
    {error && <p className="error" role="alert">{error}</p>}
    <button className="primary" disabled={busy} type="submit">{busy ? 'Signing in…' : 'Sign in'}</button>
  </form>
}
