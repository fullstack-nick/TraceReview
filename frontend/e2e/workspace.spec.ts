import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { fileURLToPath } from 'node:url'
import { mkdir, readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const fixture = (name = 'triangle.csv') => fileURLToPath(new URL(`../../fixtures/${name}`, import.meta.url))
const artifacts = resolve('../output/playwright')

async function signIn(page: Page) {
  await page.goto('/')
  await page.getByLabel('Password', { exact: true }).fill('Test-only-analysis-791!')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
}
async function importTrace(page: Page, name = 'triangle.csv', title?: string) {
  const label = title ?? `${name === 'triangle.csv' ? 'Triangle' : 'Neighboring feature'} ${Date.now()}`
  await page.getByRole('button', { name: 'Import', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Import trace' })
  await dialog.getByLabel('CSV file').setInputFiles(fixture(name))
  await dialog.getByLabel('Label').fill(label)
  await dialog.getByRole('button', { name: 'Import trace', exact: true }).click()
  await expect(page.getByRole('heading', { name: label, exact: true })).toBeVisible()
  await expect(page.getByLabel('Start (min)')).toBeVisible()
  return page.url().match(/traces\/([a-f0-9-]+)/)![1]
}
async function preview(page: Page, start = '.5', end = '1.5') {
  await page.getByLabel('Start (min)').fill(start)
  await page.getByLabel('End (min)').fill(end)
  await page.getByRole('button', { name: 'Calculate preview', exact: true }).click()
  await expect(page.getByTestId('review-status')).toHaveText('Unsaved preview')
}
async function save(page: Page, reason = 'Initial selection around the peak.') {
  await page.getByLabel('Revision reason').fill(reason)
  await page.getByRole('button', { name: 'Save analysis revision', exact: true }).click()
  await expect(page.getByTestId('review-status')).toContainText('Saved revision')
}
async function complete(page: Page) {
  await page.getByRole('button', { name: 'Complete review', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: /Complete revision/ })
  await dialog.getByLabel('Review note').fill('Boundaries and source inspected.')
  await dialog.getByRole('button', { name: 'Complete review', exact: true }).click()
  await expect(page.getByTestId('review-status')).toContainText('Review complete')
}
async function jsonPost(page: Page, path: string, data: unknown) {
  const session = await (await page.request.get('/api/session/')).json()
  return page.request.post(path, { data, headers: { 'X-CSRFToken': session.csrf_token } })
}

test('complete workflow, historical record, reload, and exact downloads', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
  await signIn(page)
  const id = await importTrace(page)
  await preview(page)
  await expect(page.getByTestId('fraction')).toHaveText('75.00%')
  await save(page)
  await preview(page, '0', '2')
  await save(page, 'Include the complete signal.')
  await expect(page.getByTestId('review-status')).toHaveText('Saved revision 2')
  await page.getByRole('button', { name: 'History', exact: true }).click()
  await page.getByRole('button', { name: 'Revision 1', exact: true }).click()
  await expect(page.getByTestId('review-status')).toHaveText('Viewing revision 1')
  await expect(page.getByLabel('Start (min)')).toHaveAttribute('readonly', '')
  await expect(page.getByTestId('fraction')).toHaveText('75.00%')
  await page.getByRole('button', { name: 'Back to latest' }).click()
  await complete(page)
  await page.reload()
  await expect(page.getByTestId('review-status')).toHaveText('Review complete · Revision 2')
  await expect(page.getByTestId('fraction')).toHaveText('100.00%')
  await page.getByRole('button', { name: 'View report' }).click()
  await expect(page.getByText('linear-trapezoid-v1', { exact: true })).toBeVisible()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Download JSON' }).click()
  const downloaded = await downloadPromise
  const json = JSON.parse(await readFile((await downloaded.path())!, 'utf8'))
  expect(json.review.revision_number).toBe(2)
  expect(json.revisions[0].area_fraction_percent).toBe(75)
  expect(json.revisions[1].area_fraction_percent).toBe(100)
  expect(Buffer.from(json.source.content, 'base64')).toEqual(await readFile(fixture()))
  const originalPromise = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Source CSV' }).click()
  expect(await readFile((await (await originalPromise).path())!)).toEqual(await readFile(fixture()))
  const blocked = await jsonPost(page, `/api/traces/${id}/revisions/`, { start_time: 0, end_time: 2, reason: 'Attempted edit', expected_version: 4, request_id: crypto.randomUUID() })
  expect(blocked.status()).toBe(409)
  expect(errors).toEqual([])
})

test('invalid import explains location and keeps the selected file', async ({ page }) => {
  await signIn(page)
  await page.getByRole('button', { name: 'Import', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Import trace' })
  await dialog.getByLabel('CSV file').setInputFiles(fixture('invalid-duplicate-time.csv'))
  await dialog.getByRole('button', { name: 'Import trace', exact: true }).click()
  await expect(dialog.getByRole('alert')).toContainText('Line 4, time_min')
  expect(await dialog.getByLabel('CSV file').evaluate((input: HTMLInputElement) => input.files?.[0].name)).toBe('invalid-duplicate-time.csv')
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click()
})

test('edited bounds hide stale numbers and navigation can retain work', async ({ page }) => {
  await signIn(page); await importTrace(page); await preview(page); await save(page)
  await page.getByLabel('Start (min)').fill('0.25')
  await expect(page.getByTestId('fraction')).toHaveText('—')
  await page.getByLabel('End (min)').fill('0.1')
  await expect(page.getByLabel('End (min)')).toHaveAttribute('aria-invalid', 'true')
  await expect(page.getByRole('button', { name: 'Calculate preview' })).toBeDisabled()
  await page.getByLabel('Revision reason').fill('Work to retain')
  await page.getByRole('button', { name: 'Sign out' }).click()
  await page.getByRole('button', { name: 'Keep editing' }).click()
  await expect(page.getByLabel('Revision reason')).toHaveValue('Work to retain')
  await page.getByRole('button', { name: 'History', exact: true }).click()
  await page.getByRole('button', { name: 'Revision 1', exact: true }).click()
  await page.getByRole('button', { name: 'Keep editing' }).click()
  await expect(page.getByLabel('Start (min)')).toHaveValue('0.25')
})

test('late preview cannot overwrite newer boundaries even if transport ignores cancellation', async ({ page }) => {
  await page.addInitScript(() => {
    const original = window.fetch
    window.fetch = (input, init) => original(input, typeof input === 'string' && input.includes('/preview/') ? { ...init, signal: undefined } : init)
  })
  await signIn(page); await importTrace(page)
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let intercepted!: () => void
  const started = new Promise<void>(resolve => { intercepted = resolve })
  await page.route('**/preview/', async route => {
    if (route.request().postDataJSON().start_time === .25) { intercepted(); await gate }
    await route.continue()
  })
  await page.getByLabel('Start (min)').fill('.25'); await page.getByLabel('End (min)').fill('.75')
  await page.getByRole('button', { name: 'Calculate preview' }).click()
  await started
  await preview(page)
  await expect(page.getByTestId('fraction')).toHaveText('75.00%')
  const oldResponse = page.waitForResponse(response => response.url().endsWith('/preview/') && response.request().postDataJSON().start_time === .25)
  release(); await oldResponse
  await expect(page.getByTestId('fraction')).toHaveText('75.00%')
  await expect(page.getByLabel('Start (min)')).toHaveValue('.5')
})

test('non-JSON server failure retains draft and supports retry', async ({ page }) => {
  await signIn(page); await importTrace(page); await preview(page)
  await page.route('**/revisions/', route => route.fulfill({ status: 500, contentType: 'text/html', body: '<h1>Temporary failure</h1>' }))
  await page.getByLabel('Revision reason').fill('Keep this reason after failure.')
  await page.getByRole('button', { name: 'Save analysis revision' }).click()
  await expect(page.getByRole('alert')).toContainText('500')
  await expect(page.getByLabel('Revision reason')).toHaveValue('Keep this reason after failure.')
  await expect(page.getByLabel('Start (min)')).toHaveValue('.5')
  await page.unroute('**/revisions/')
  await page.getByRole('button', { name: 'Retry save' }).click()
  await expect(page.getByTestId('review-status')).toHaveText('Saved revision 1')
})

test('lost response after commit retries the original revision exactly once', async ({ page }) => {
  await signIn(page); const id = await importTrace(page); await preview(page)
  await page.route('**/revisions/', async route => { await route.fetch(); await route.abort('failed') })
  await page.getByLabel('Revision reason').fill('One intended revision.')
  await page.getByRole('button', { name: 'Save analysis revision' }).click()
  await expect(page.getByRole('button', { name: 'Retry save' })).toBeEnabled()
  expect((await (await page.request.get(`/api/traces/${id}/`)).json()).revisions).toHaveLength(1)
  await page.unroute('**/revisions/')
  await page.getByRole('button', { name: 'Retry save' }).click()
  await expect(page.getByTestId('review-status')).toHaveText('Saved revision 1')
  const data = await (await page.request.get(`/api/traces/${id}/`)).json()
  expect(data.revisions).toHaveLength(1); expect(data.run_version).toBe(2); expect(data.audit_events).toHaveLength(2)
})

test('two tabs reject stale save and keep the reason during reload', async ({ page, context }) => {
  await signIn(page); await importTrace(page)
  const other = await context.newPage(); await other.goto(page.url())
  await preview(other, '.25', '.75')
  await other.getByLabel('Revision reason').fill('Selection from the second tab.')
  await preview(page); await save(page)
  await other.getByRole('button', { name: 'Save analysis revision' }).click()
  await expect(other.getByRole('alert')).toContainText('Another tab changed')
  await expect(other.getByLabel('Revision reason')).toHaveValue('Selection from the second tab.')
  await other.getByRole('button', { name: 'Reload latest' }).click()
  await expect(other.getByText('Latest record loaded.', { exact: false })).toBeVisible()
  await preview(other, '.25', '.75')
  await other.getByRole('button', { name: 'Save analysis revision' }).click()
  await expect(other.getByTestId('review-status')).toHaveText('Saved revision 2')
  await other.close()
})

test('session expiry preserves the draft and requires reconciliation after login', async ({ page }) => {
  await signIn(page); await importTrace(page)
  await page.getByLabel('Start (min)').fill('.5'); await page.getByLabel('End (min)').fill('1.5')
  await page.getByLabel('Revision reason').fill('Preserved across sign-in.')
  await jsonPost(page, '/api/logout/', {})
  await page.getByRole('button', { name: 'Calculate preview' }).click()
  const dialog = page.getByRole('dialog', { name: 'Sign in again' })
  await dialog.getByLabel('Password', { exact: true }).fill('Test-only-analysis-791!')
  await dialog.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(dialog).not.toBeVisible()
  await expect(page.getByLabel('Revision reason')).toHaveValue('Preserved across sign-in.')
  await page.getByRole('button', { name: 'Reload latest' }).click()
  await expect(page.getByText('Latest record loaded.', { exact: false })).toBeVisible()
  await preview(page)
  await page.getByRole('button', { name: 'Save analysis revision' }).click()
  await expect(page.getByTestId('review-status')).toHaveText('Saved revision 1')
})

test('zoom does not change analysis and accessible data exposes full precision', async ({ page }) => {
  await signIn(page); const id = await importTrace(page); await preview(page)
  await expect(page.locator('.plot .js-line').first()).toBeVisible()
  const plot = page.locator('.plot').first()
  const box = (await plot.boundingBox())!
  await page.mouse.move(box.x + box.width * .3, box.y + 100)
  await page.mouse.down(); await page.mouse.move(box.x + box.width * .65, box.y + 250, { steps: 6 }); await page.mouse.up()
  await page.getByRole('button', { name: 'Reset zoom' }).click()
  await expect(page.getByTestId('fraction')).toHaveText('75.00%')
  await expect(page.getByLabel('Start (min)')).toHaveValue('.5')
  expect((await (await page.request.get(`/api/traces/${id}/`)).json()).run_version).toBe(1)
  await page.getByRole('button', { name: 'Data', exact: true }).click()
  await expect(page.getByRole('columnheader', { name: 'Time (min)' })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: 'Signal (AU)' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Data', exact: true })).toBeFocused()
  await page.getByRole('button', { name: 'Use full trace' }).click()
  await expect(page.getByTestId('fraction')).toHaveText('—')
})

test('keyboard controls, accessibility scan and narrow viewport', async ({ page }) => {
  await signIn(page); await importTrace(page, 'neighboring-feature.csv', 'Neighboring feature')
  await page.getByLabel('Start (min)').focus()
  await page.keyboard.press('Control+A'); await page.keyboard.type('3.2'); await page.keyboard.press('Tab')
  await expect(page.getByLabel('End (min)')).toBeFocused()
  await page.keyboard.press('Control+A'); await page.keyboard.type('5.1'); await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Calculate preview' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('review-status')).toHaveText('Unsaved preview')
  await page.keyboard.press('Tab'); await page.keyboard.press('Tab')
  await expect(page.getByLabel('Revision reason')).toBeFocused()
  await page.keyboard.type('Keyboard review of the prominent peak.')
  await page.keyboard.press('Tab'); await page.keyboard.press('Enter')
  await expect(page.getByTestId('review-status')).toHaveText('Saved revision 1')
  await expect(page.locator('.plot .js-line').first()).toBeVisible()
  const accessibility = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(accessibility.violations).toEqual([])
  await mkdir(artifacts, { recursive: true })
  await page.screenshot({ path: resolve(artifacts, 'workspace-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByLabel('Revision reason')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await expect.poll(() => page.locator('.plot .svg-container').first().evaluate(element => element.getBoundingClientRect().width)).toBeLessThanOrEqual(358)
  await page.screenshot({ path: resolve(artifacts, 'workspace-mobile.png'), fullPage: true })
  const narrow = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(narrow.violations).toEqual([])
})

test('application completes a review with external network blocked', async ({ page }) => {
  const external: string[] = []
  await page.route('**/*', route => {
    const host = new URL(route.request().url()).hostname
    if (host !== '127.0.0.1' && host !== 'localhost') { external.push(route.request().url()); return route.abort() }
    return route.continue()
  })
  await signIn(page); await importTrace(page); await preview(page); await save(page); await complete(page)
  await page.getByRole('button', { name: 'View report' }).click()
  await expect(page.getByText('tracereview-report-v1', { exact: true })).toBeVisible()
  expect(external).toEqual([])
})

test('interrupted import and completion recover their committed receipts without duplicates', async ({ page }) => {
  await signIn(page)
  const before = (await (await page.request.get('/api/traces/')).json()).total
  await page.route('**/api/traces/', async route => {
    if (route.request().method() === 'POST') { await route.fetch(); await route.abort('failed') }
    else await route.continue()
  })
  await page.getByRole('button', { name: 'Import', exact: true }).click()
  const upload = page.getByRole('dialog', { name: 'Import trace' })
  await upload.getByLabel('CSV file').setInputFiles(fixture())
  await upload.getByRole('button', { name: 'Import trace', exact: true }).click()
  await expect(upload.getByRole('button', { name: 'Retry import' })).toBeEnabled()
  await expect(upload.getByLabel('CSV file')).toBeDisabled()
  await page.unroute('**/api/traces/')
  await upload.getByRole('button', { name: 'Retry import' }).click()
  await expect(upload).not.toBeVisible()
  expect((await (await page.request.get('/api/traces/')).json()).total).toBe(before + 1)
  const id = page.url().match(/traces\/([a-f0-9-]+)/)![1]
  await preview(page); await save(page)
  await page.route('**/complete-review/', async route => { await route.fetch(); await route.abort('failed') })
  await page.getByRole('button', { name: 'Complete review', exact: true }).click()
  const review = page.getByRole('dialog', { name: 'Complete revision 1' })
  await review.getByRole('button', { name: 'Complete review', exact: true }).click()
  await expect(review.getByRole('button', { name: 'Retry completion' })).toBeEnabled()
  await page.unroute('**/complete-review/')
  await review.getByRole('button', { name: 'Retry completion' }).click()
  await expect(page.getByTestId('review-status')).toHaveText('Review complete · Revision 1')
  const data = await (await page.request.get(`/api/traces/${id}/`)).json()
  expect(data.run_version).toBe(3); expect(data.audit_events).toHaveLength(3)
})

test('completion in another tab preserves local values for copying', async ({ page, context }) => {
  await signIn(page); await importTrace(page); await preview(page); await save(page)
  const other = await context.newPage(); await other.goto(page.url())
  await preview(other, '.25', '1.75')
  await other.getByLabel('Revision reason').fill('Unsaved work from the other tab.')
  await complete(page)
  await other.getByRole('button', { name: 'Save analysis revision' }).click()
  await expect(other.getByRole('alert')).toContainText('read-only')
  await other.getByRole('button', { name: 'Reload latest' }).click()
  await expect(other.getByTestId('review-status')).toHaveText('Review complete · Revision 1')
  await expect(other.getByTestId('fraction')).toHaveText('75.00%')
  await other.getByText('Retained local values', { exact: true }).click()
  await expect(other.getByText('Unsaved work from the other tab.', { exact: true })).toBeVisible()
  await expect(other.getByText('.25–1.75 min', { exact: true })).toBeVisible()
  await other.close()
})

test('browser Back guards unsaved work and confirmed navigation discards it', async ({ page }) => {
  await signIn(page); const first = await importTrace(page)
  const second = await importTrace(page)
  await page.getByLabel('Revision reason').fill('Keep this until confirmed.')
  await page.goBack()
  await expect(page.getByRole('dialog', { name: 'Discard changes?' })).toBeVisible()
  await page.getByRole('button', { name: 'Keep editing' }).click()
  await expect(page.getByLabel('Revision reason')).toHaveValue('Keep this until confirmed.')
  expect(page.url()).toContain(second)
  await page.getByLabel('Trace', { exact: true }).selectOption(first)
  await page.getByRole('button', { name: 'Discard changes', exact: true }).click()
  await expect(page.getByLabel('Revision reason')).toHaveValue('')
  expect(page.url()).toContain(first)
})

test('reauthentication as a different analyst clears the previous workspace', async ({ page }) => {
  await signIn(page); const id = await importTrace(page)
  await page.getByLabel('Revision reason').fill('Private draft from analyst one.')
  await jsonPost(page, '/api/logout/', {})
  await page.getByRole('button', { name: 'Calculate preview' }).click()
  const dialog = page.getByRole('dialog', { name: 'Sign in again' })
  await dialog.getByLabel('Username').fill('other-analyst')
  await dialog.getByLabel('Password', { exact: true }).fill('Test-only-secondary-682!')
  await dialog.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Start with a trace.' })).toBeVisible()
  await expect(page.getByText('Private draft from analyst one.', { exact: true })).not.toBeVisible()
  expect((await page.request.get(`/api/traces/${id}/`)).status()).toBe(404)
})

test('security-token rotation supports sign-in recovery without losing the reason', async ({ page, context }) => {
  await signIn(page); await importTrace(page); await preview(page)
  await page.getByLabel('Revision reason').fill('Preserve after token rotation.')
  const other = await context.newPage()
  await other.goto('/')
  await other.getByRole('button', { name: 'Sign out' }).click()
  await signIn(other)
  await page.getByRole('button', { name: 'Save analysis revision' }).click()
  const dialog = page.getByRole('dialog', { name: 'Sign in again' })
  await dialog.getByLabel('Password', { exact: true }).fill('Test-only-analysis-791!')
  await dialog.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('button', { name: 'Reload latest' }).click()
  await expect(page.getByLabel('Revision reason')).toHaveValue('Preserve after token rotation.')
  await preview(page); await page.getByRole('button', { name: 'Save analysis revision' }).click()
  await expect(page.getByTestId('review-status')).toHaveText('Saved revision 1')
  await other.close()
})

test('returning to a stale tab compares versions without replacing its draft', async ({ page, context }) => {
  await signIn(page); await importTrace(page)
  const other = await context.newPage(); await other.goto(page.url())
  await other.getByLabel('Start (min)').fill('.25')
  await other.getByLabel('Revision reason').fill('Keep these local values.')
  await preview(page); await save(page)
  await other.evaluate(() => window.dispatchEvent(new Event('focus')))
  await expect(other.getByText('Another tab changed this run. Reload latest; your entries are retained.')).toBeVisible()
  await expect(other.getByLabel('Start (min)')).toHaveValue('.25')
  await expect(other.getByLabel('Revision reason')).toHaveValue('Keep these local values.')
  await expect(other.getByRole('button', { name: 'Save analysis revision' })).toBeDisabled()
  await other.close()
})
