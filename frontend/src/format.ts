export const number = (value: number) => new Intl.NumberFormat('en-GB', { maximumSignificantDigits: 6 }).format(value)
export function percent(value: number) {
  if (value > 0 && value < .01) return '<0.01%'
  if (value < 100 && value >= 99.995) return '>99.99%'
  return `${value.toFixed(2)}%`
}
export const date = (value: string) => new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium', timeStyle: 'short',
}).format(new Date(value)) + ` ${Intl.DateTimeFormat().resolvedOptions().timeZone}`
export function parseBoundary(raw: string): number | null {
  if (!/^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$/.test(raw.trim())) return null
  const value = Number(raw)
  return Number.isFinite(value) ? value : null
}
